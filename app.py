"""
MAASTrap - MAAS Bootstrap Configuration Generator

This application provides a web interface and API for generating
Ubuntu 24.04 autoinstaller configurations that bootstrap a MAAS
region controller with custom network settings and DHCP configuration.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import yaml
import os
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

    @validator('ip_address')
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
        
        # Install MAAS packages
        "curtin in-target --target=/target -- apt-get install -y maas postgresql",
        
        # Initialize MAAS database
        "curtin in-target --target=/target -- sudo -u postgres psql -c \"CREATE USER maas WITH PASSWORD 'maas'\"",
        "curtin in-target --target=/target -- sudo -u postgres createdb -O maas maasdb",
        
        # Initialize MAAS region
        f"curtin in-target --target=/target -- maas init region+rack --database-uri postgresql://maas:maas@localhost/maasdb --maas-url http://{request.interfaces[0].ip_address.split('/')[0]}:5240/MAAS",
        
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
