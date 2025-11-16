"""
MAASTrap - MAAS Bootstrap Configuration Generator with Admin Portal

This application provides a web interface and API for generating
Ubuntu autoinstaller configurations that bootstrap a MAAS region controller
with custom network settings and DHCP configuration.

Features:
- Admin portal for managing base Ubuntu images
- MAAS version management per Ubuntu image
- User interface for selecting Ubuntu version and MAAS version
- Automated ISO generation from pre-configured images
"""

from fastapi import FastAPI, HTTPException, Depends, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import timedelta
import yaml
import os
import tempfile
import subprocess
import shutil
from pathlib import Path

# Import local modules
from database import get_db, init_db, User, UbuntuImage, MAASVersion
from auth import (
    UserLogin, Token, verify_password, create_access_token,
    get_current_user, require_admin, get_password_hash,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(
    title="MAASTrap",
    description="Bootstrap MAAS Region Controller with Custom Network Configuration",
    version="2.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    # Create images directory if it doesn't exist
    os.makedirs("images", exist_ok=True)


# ============================================================================
# Data Models
# ============================================================================

class NetworkInterface(BaseModel):
    """Network interface configuration"""
    name: str = Field(..., description="Interface name (e.g., eth0, ens192)")
    ip_address: str = Field(..., description="IP address with CIDR (e.g., 192.168.1.10/24)")
    gateway: Optional[str] = Field(None, description="Gateway IP address")
    dns_servers: Optional[List[str]] = Field(default_factory=list, description="DNS server addresses")
    enable_dhcp: bool = Field(False, description="Enable DHCP on this network")

    @field_validator('ip_address')
    @classmethod
    def validate_ip(cls, v):
        """Validate IP address format"""
        if '/' not in v:
            raise ValueError('IP address must include CIDR notation (e.g., 192.168.1.10/24)')
        return v


class MAASConfig(BaseModel):
    """MAAS configuration"""
    admin_username: str = Field(default="admin", description="MAAS admin username")
    admin_email: str = Field(..., description="MAAS admin email")
    admin_password: str = Field(..., description="MAAS admin password")
    region_name: str = Field(default="maas-region", description="MAAS region name")


class AutoinstallRequest(BaseModel):
    """Request to generate autoinstall configuration"""
    hostname: str = Field(..., description="Hostname for the MAAS region controller")
    ubuntu_image_id: int = Field(..., description="Ubuntu image ID")
    maas_version_id: int = Field(..., description="MAAS version ID")
    interfaces: List[NetworkInterface] = Field(..., description="Network interface configurations")
    maas_config: MAASConfig = Field(..., description="MAAS configuration")
    timezone: str = Field(default="UTC", description="System timezone")
    locale: str = Field(default="en_US.UTF-8", description="System locale")


class UbuntuImageCreate(BaseModel):
    """Create Ubuntu image"""
    name: str
    codename: str
    version: str


class MAASVersionCreate(BaseModel):
    """Create MAAS version"""
    version: str
    ppa_url: str
    ubuntu_image_id: int


# ============================================================================
# Helper Functions
# ============================================================================

def generate_netplan_config(interfaces: List[NetworkInterface]) -> dict:
    """Generate netplan network configuration"""
    ethernets = {}
    
    for iface in interfaces:
        ip_cidr = iface.ip_address
        eth_config = {"addresses": [ip_cidr]}
        
        if iface.gateway:
            eth_config["routes"] = [{"to": "default", "via": iface.gateway}]
        
        if iface.dns_servers:
            eth_config["nameservers"] = {"addresses": iface.dns_servers}
        
        ethernets[iface.name] = eth_config
    
    return {"network": {"version": 2, "ethernets": ethernets}}


def generate_autoinstall_config(request: AutoinstallRequest, maas_ppa: str) -> dict:
    """Generate Ubuntu autoinstall configuration with MAAS PPA"""
    
    netplan_config = generate_netplan_config(request.interfaces)
    dhcp_networks = [iface for iface in request.interfaces if iface.enable_dhcp]
    
    # Create late-commands for MAAS installation and configuration
    late_commands = [
        # Update package lists
        "curtin in-target --target=/target -- apt-get update",
        
        # Add MAAS PPA
        f"curtin in-target --target=/target -- add-apt-repository -y {maas_ppa}",
        "curtin in-target --target=/target -- apt-get update",
        
        # Install MAAS packages (debs automatically create database and user)
        "curtin in-target --target=/target -- apt-get install -y maas",
        
        # Initialize MAAS region
        f"curtin in-target --target=/target -- maas init region+rack --maas-url http://{request.interfaces[0].ip_address.split('/')[0]}:5240/MAAS",
        
        # Create admin user
        f"curtin in-target --target=/target -- maas createadmin --username {request.maas_config.admin_username} --email {request.maas_config.admin_email} --password {request.maas_config.admin_password}",
    ]
    
    # Add DHCP configuration for each enabled network
    for iface in dhcp_networks:
        ip_part = iface.ip_address.split('/')[0]
        network_parts = ip_part.split('.')
        network_base = '.'.join(network_parts[:3])
        
        late_commands.append(
            f"curtin in-target --target=/target -- maas admin subnet update {network_base}.0/24 gateway_ip={iface.gateway or network_base + '.1'}"
        )
        late_commands.append(
            f"curtin in-target --target=/target -- maas admin ipranges create type=dynamic start_ip={network_base}.100 end_ip={network_base}.200"
        )
    
    autoinstall = {
        "version": 1,
        "locale": request.locale,
        "keyboard": {"layout": "us"},
        "network": netplan_config["network"],
        "identity": {
            "hostname": request.hostname,
            "username": "ubuntu",
            "password": "$6$rounds=4096$saltsalt$YwWx9qPJZnVbGzLH3RDLxWnVx8LmeqLCKJLf6QDp5EJPYLHThK.YHVkFN5FJzlV5WbG3lmKPOGMFHmLgwMHpW."
        },
        "ssh": {"install-server": True, "allow-pw": True},
        "storage": {"layout": {"name": "lvm"}},
        "packages": ["net-tools", "curl", "wget", "vim", "software-properties-common"],
        "late-commands": late_commands
    }
    
    return autoinstall


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/api/auth/login", response_model=Token)
async def login(user_login: UserLogin, db: Session = Depends(get_db)):
    """Admin login endpoint"""
    user = db.query(User).filter(User.username == user_login.username).first()
    if not user or not verify_password(user_login.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ============================================================================
# Admin Portal - Ubuntu Images Management
# ============================================================================

@app.get("/api/admin/images")
async def list_images(
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """List all Ubuntu images"""
    images = db.query(UbuntuImage).all()
    return [
        {
            "id": img.id,
            "name": img.name,
            "codename": img.codename,
            "version": img.version,
            "is_active": img.is_active,
            "maas_versions": [
                {"id": mv.id, "version": mv.version, "ppa_url": mv.ppa_url}
                for mv in img.maas_versions if mv.is_active
            ]
        }
        for img in images
    ]


@app.post("/api/admin/images")
async def create_image(
    name: str = Form(...),
    codename: str = Form(...),
    version: str = Form(...),
    iso_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Upload a new Ubuntu image"""
    # Save the ISO file
    iso_path = f"images/{codename}-{version}.iso"
    with open(iso_path, "wb") as f:
        shutil.copyfileobj(iso_file.file, f)
    
    # Create database entry
    image = UbuntuImage(
        name=name,
        codename=codename,
        version=version,
        iso_path=iso_path
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    
    return {"id": image.id, "name": image.name, "message": "Image uploaded successfully"}


@app.delete("/api/admin/images/{image_id}")
async def delete_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Delete an Ubuntu image"""
    image = db.query(UbuntuImage).filter(UbuntuImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Delete the ISO file
    if os.path.exists(image.iso_path):
        os.remove(image.iso_path)
    
    db.delete(image)
    db.commit()
    
    return {"message": "Image deleted successfully"}


# ============================================================================
# Admin Portal - MAAS Versions Management
# ============================================================================

@app.post("/api/admin/maas-versions")
async def create_maas_version(
    version: str = Form(...),
    ppa_url: str = Form(...),
    ubuntu_image_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Add a MAAS version for an Ubuntu image"""
    maas_version = MAASVersion(
        version=version,
        ppa_url=ppa_url,
        ubuntu_image_id=ubuntu_image_id
    )
    db.add(maas_version)
    db.commit()
    db.refresh(maas_version)
    
    return {"id": maas_version.id, "version": maas_version.version, "message": "MAAS version added successfully"}


@app.delete("/api/admin/maas-versions/{version_id}")
async def delete_maas_version(
    version_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_admin)
):
    """Delete a MAAS version"""
    maas_version = db.query(MAASVersion).filter(MAASVersion.id == version_id).first()
    if not maas_version:
        raise HTTPException(status_code=404, detail="MAAS version not found")
    
    db.delete(maas_version)
    db.commit()
    
    return {"message": "MAAS version deleted successfully"}


# ============================================================================
# Public Endpoints - User Interface
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web UI"""
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    
    if os.path.exists(html_path):
        with open(html_path, 'r') as f:
            return HTMLResponse(content=f.read())
    
    return HTMLResponse(content="<h1>MAASTrap</h1><p>UI not found</p>")


@app.get("/admin", response_class=HTMLResponse)
async def admin_portal():
    """Serve the admin portal UI"""
    html_path = os.path.join(os.path.dirname(__file__), "static", "admin.html")
    
    if os.path.exists(html_path):
        with open(html_path, 'r') as f:
            return HTMLResponse(content=f.read())
    
    return HTMLResponse(content="<h1>Admin Portal</h1><p>UI not found</p>")


@app.get("/api/images")
async def get_available_images(db: Session = Depends(get_db)):
    """Get list of available Ubuntu images for users"""
    images = db.query(UbuntuImage).filter(UbuntuImage.is_active == True).all()
    return [
        {
            "id": img.id,
            "name": img.name,
            "version": img.version,
            "maas_versions": [
                {"id": mv.id, "version": mv.version}
                for mv in img.maas_versions if mv.is_active
            ]
        }
        for img in images
    ]


@app.post("/api/generate")
async def generate_config(request: AutoinstallRequest, db: Session = Depends(get_db)):
    """Generate autoinstall configuration"""
    try:
        # Get MAAS version info
        maas_version = db.query(MAASVersion).filter(MAASVersion.id == request.maas_version_id).first()
        if not maas_version:
            raise HTTPException(status_code=404, detail="MAAS version not found")
        
        config = generate_autoinstall_config(request, maas_version.ppa_url)
        yaml_content = yaml.dump(config, default_flow_style=False, sort_keys=False)
        
        return JSONResponse(
            content={
                "success": True,
                "config": config,
                "yaml": yaml_content
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/generate-iso")
async def generate_iso(request: AutoinstallRequest, db: Session = Depends(get_db)):
    """
    Generate a bootable ISO with autoinstall configuration embedded.
    Uses pre-configured Ubuntu image from database.
    """
    try:
        # Get Ubuntu image
        ubuntu_image = db.query(UbuntuImage).filter(UbuntuImage.id == request.ubuntu_image_id).first()
        if not ubuntu_image:
            raise HTTPException(status_code=404, detail="Ubuntu image not found")
        
        # Get MAAS version info
        maas_version = db.query(MAASVersion).filter(MAASVersion.id == request.maas_version_id).first()
        if not maas_version:
            raise HTTPException(status_code=404, detail="MAAS version not found")
        
        # Generate autoinstall config
        config = generate_autoinstall_config(request, maas_version.ppa_url)
        
        # Create temporary directory for ISO building
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create cloud-init files
            user_data_path = temp_path / "user-data"
            meta_data_path = temp_path / "meta-data"
            
            # Write user-data (autoinstall config)
            user_data_content = "#cloud-config\nautoinstall:\n"
            yaml_content = yaml.dump(config, default_flow_style=False, sort_keys=False)
            indented_yaml = "\n".join("  " + line for line in yaml_content.split("\n"))
            user_data_content += indented_yaml
            
            with open(user_data_path, "w") as f:
                f.write(user_data_content)
            
            # Write empty meta-data
            with open(meta_data_path, "w") as f:
                f.write("")
            
            # Generate output ISO with cloud-localds
            output_iso_path = temp_path / "maas-autoinstall.iso"
            
            # Check if cloud-localds is available
            result = subprocess.run(
                ["which", "cloud-localds"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # Fall back to genisoimage
                iso_cmd = None
                for cmd in ["genisoimage", "mkisofs"]:
                    check_result = subprocess.run(
                        ["which", cmd],
                        capture_output=True,
                        text=True
                    )
                    if check_result.returncode == 0:
                        iso_cmd = cmd
                        break
                
                if not iso_cmd:
                    raise HTTPException(
                        status_code=500,
                        detail="ISO generation tools not available. Please install cloud-image-utils or genisoimage/mkisofs."
                    )
                
                subprocess.run(
                    [
                        iso_cmd,
                        "-output", str(output_iso_path),
                        "-volid", "cidata",
                        "-joliet",
                        "-rock",
                        str(user_data_path),
                        str(meta_data_path)
                    ],
                    check=True,
                    capture_output=True
                )
            else:
                subprocess.run(
                    [
                        "cloud-localds",
                        str(output_iso_path),
                        str(user_data_path),
                        str(meta_data_path)
                    ],
                    check=True,
                    capture_output=True
                )
            
            # Read the generated ISO
            iso_content = output_iso_path.read_bytes()
            
            # Return as downloadable file
            return StreamingResponse(
                iter([iso_content]),
                media_type="application/x-iso9660-image",
                headers={
                    "Content-Disposition": f"attachment; filename=maas-{ubuntu_image.codename}-{maas_version.version}-{request.hostname}.iso"
                }
            )
    
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"ISO generation failed: {e.stderr.decode() if e.stderr else str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ISO generation error: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "MAASTrap", "version": "2.0.0"}


if __name__ == "__main__":
    import uvicorn
    
    # Create necessary directories
    os.makedirs("static", exist_ok=True)
    os.makedirs("images", exist_ok=True)
    
    # Initialize database
    init_db()
    
    print("Starting MAASTrap server...")
    print("Access the UI at: http://localhost:8000")
    print("Access the Admin Portal at: http://localhost:8000/admin")
    print("Default admin credentials: admin/admin (change immediately!)")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
