"""
MAASTrap - MAAS Bootstrap Configuration Generator

This application provides a web interface and API for generating
Ubuntu 24.04 autoinstaller configurations that bootstrap a MAAS
region controller with custom network settings and DHCP configuration.
"""

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import yaml
import os
import tempfile
import subprocess
import shutil
from pathlib import Path
from jinja2 import Template

app = FastAPI(
    title="MAASTrap",
    description="Bootstrap MAAS Region Controller with Custom Network Configuration",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


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
    interfaces: List[NetworkInterface] = Field(..., description="Network interface configurations")
    maas_config: MAASConfig = Field(..., description="MAAS configuration")
    timezone: str = Field(default="UTC", description="System timezone")
    locale: str = Field(default="en_US.UTF-8", description="System locale")


def generate_netplan_config(interfaces: List[NetworkInterface]) -> dict:
    """Generate netplan network configuration"""
    ethernets = {}
    
    for iface in interfaces:
        # Parse IP and CIDR
        ip_cidr = iface.ip_address
        
        eth_config = {
            "addresses": [ip_cidr]
        }
        
        if iface.gateway:
            # Use routes for gateway configuration (modern netplan)
            eth_config["routes"] = [
                {
                    "to": "default",
                    "via": iface.gateway
                }
            ]
        
        if iface.dns_servers:
            eth_config["nameservers"] = {
                "addresses": iface.dns_servers
            }
        
        ethernets[iface.name] = eth_config
    
    return {
        "network": {
            "version": 2,
            "ethernets": ethernets
        }
    }


def generate_autoinstall_config(request: AutoinstallRequest) -> dict:
    """Generate Ubuntu autoinstall configuration"""
    
    netplan_config = generate_netplan_config(request.interfaces)
    
    # Build list of DHCP-enabled networks for MAAS configuration
    dhcp_networks = [iface for iface in request.interfaces if iface.enable_dhcp]
    
    # Create late-commands for MAAS installation and configuration
    late_commands = [
        # Update package lists
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
        # Extract network from IP (simplified - assumes /24)
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
        "keyboard": {
            "layout": "us"
        },
        "network": netplan_config["network"],
        "identity": {
            "hostname": request.hostname,
            "username": "ubuntu",
            "password": "$6$rounds=4096$saltsalt$YwWx9qPJZnVbGzLH3RDLxWnVx8LmeqLCKJLf6QDp5EJPYLHThK.YHVkFN5FJzlV5WbG3lmKPOGMFHmLgwMHpW."  # password: ubuntu
        },
        "ssh": {
            "install-server": True,
            "allow-pw": True
        },
        "storage": {
            "layout": {
                "name": "lvm"
            }
        },
        "packages": [
            "net-tools",
            "curl",
            "wget",
            "vim"
        ],
        "late-commands": late_commands
    }
    
    return autoinstall


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web UI"""
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    
    if os.path.exists(html_path):
        with open(html_path, 'r') as f:
            return HTMLResponse(content=f.read())
    
    # Fallback inline HTML if file doesn't exist
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>MAASTrap - MAAS Bootstrap Configuration</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            h1 { color: #E95420; }
            .error { color: red; }
            .success { color: green; }
        </style>
    </head>
    <body>
        <h1>MAASTrap - MAAS Bootstrap Configuration</h1>
        <p>Web UI loading... Please check that static files are properly configured.</p>
    </body>
    </html>
    """)


@app.post("/api/generate")
async def generate_config(request: AutoinstallRequest):
    """Generate autoinstall configuration"""
    try:
        config = generate_autoinstall_config(request)
        
        # Convert to YAML for download
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
async def generate_iso(
    base_iso: UploadFile = File(...),
    config_json: str = Form(...)
):
    """
    Generate a bootable ISO with autoinstall configuration embedded.
    
    Requires:
    - base_iso: Ubuntu 24.04 server ISO file
    - config_json: JSON configuration (same format as /api/generate endpoint)
    """
    import json
    
    try:
        # Parse the configuration
        config_data = json.loads(config_json)
        request = AutoinstallRequest(**config_data)
        
        # Generate autoinstall config
        config = generate_autoinstall_config(request)
        
        # Create temporary directory for ISO building
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Save uploaded ISO
            base_iso_path = temp_path / "base.iso"
            with open(base_iso_path, "wb") as f:
                shutil.copyfileobj(base_iso.file, f)
            
            # Create cloud-init files
            user_data_path = temp_path / "user-data"
            meta_data_path = temp_path / "meta-data"
            
            # Write user-data (autoinstall config)
            user_data_content = "#cloud-config\nautoinstall:\n"
            yaml_content = yaml.dump(config, default_flow_style=False, sort_keys=False)
            # Indent the YAML content
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
                # Fall back to creating a simple ISO with user-data and meta-data
                # This requires genisoimage or mkisofs
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
                
                # Create a simple seed ISO
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
                # Use cloud-localds
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
                    "Content-Disposition": f"attachment; filename=maas-autoinstall-{request.hostname}.iso"
                }
            )
    
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON configuration: {str(e)}")
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"ISO generation failed: {e.stderr.decode() if e.stderr else str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ISO generation error: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "MAASTrap"}


if __name__ == "__main__":
    import uvicorn
    
    # Create static directory if it doesn't exist
    os.makedirs("static", exist_ok=True)
    
    print("Starting MAASTrap server...")
    print("Access the UI at: http://localhost:8000")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
