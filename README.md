# MAASTrap

Bootstrap your datacenter with MAAS (Metal as a Service)

## Overview

MAASTrap is a comprehensive web-based tool that helps you bootstrap MAAS region controllers with customized Ubuntu autoinstaller ISOs. The tool provides:

- **Admin Portal**: Manage Ubuntu base images (Jammy 22.04, Noble 24.04, etc.)
- **MAAS Version Management**: Configure which MAAS versions are available per Ubuntu version
- **User Interface**: Select Ubuntu and MAAS versions, configure networks, generate ISOs
- **Automated ISO Generation**: Create bootable ISOs from pre-configured images
- **MAAS PPA Integration**: Automatically adds the correct MAAS PPA during installation

## Features

### Admin Portal
- **Authenticated Access**: Secure admin portal with JWT authentication
- **Image Management**: Upload and manage Ubuntu base ISO images
- **MAAS Version Mapping**: Configure available MAAS versions (3.2, 3.3, 3.4, etc.) per Ubuntu release
- **PPA Configuration**: Specify MAAS PPA URLs for each version

### User Interface (Vanilla Framework)
- **Ubuntu Version Selection**: Choose from available Ubuntu images (Jammy, Noble, etc.)
- **MAAS Version Selection**: Select MAAS version based on selected Ubuntu image
- **Network Configuration**: Define interfaces, IP addresses, gateways, and DNS
- **DHCP Management**: Enable DHCP on selected networks
- **ISO Generation**: Download customized bootable ISOs ready for deployment

### Generated Configurations
- Ubuntu autoinstaller (cloud-init) format
- Netplan network configuration
- MAAS region+rack controller installation
- Automatic database setup via MAAS debian packages
- MAAS PPA integration
- DHCP configuration on specified networks

## Quick Start

### Prerequisites

- Python 3.9 or higher
- SQLite (included with Python)
- Ubuntu Server ISOs (22.04/24.04) for admin to upload

### Installation

1. Clone the repository:
```bash
git clone https://github.com/r00ta/MAASTrap.git
cd MAASTrap
```

2. Install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Access the application:
- User Interface: `http://localhost:8000`
- Admin Portal: `http://localhost:8000/admin`
- Default admin credentials: `admin` / `admin` (change immediately!)

## Usage

### For Administrators

1. **Login to Admin Portal**
   - Navigate to `http://localhost:8000/admin`
   - Login with admin credentials

2. **Upload Ubuntu Images**
   - Click "Add Ubuntu Image"
   - Provide image name, version, codename
   - Upload the Ubuntu Server ISO file

3. **Configure MAAS Versions**
   - For each Ubuntu image, add available MAAS versions
   - Specify MAAS version number (e.g., "3.2", "3.3")
   - Provide PPA URL (e.g., "ppa:maas/3.2")

### For Users

1. **Select Versions**
   - Choose Ubuntu version from dropdown
   - Select desired MAAS version

2. **Configure System**
   - Set hostname, timezone, locale
   - Configure MAAS admin credentials

3. **Configure Network**
   - Add network interfaces
   - Set IP addresses, gateways, DNS
   - Enable DHCP on selected networks

4. **Generate ISO**
   - Click "Generate ISO"
   - Download the customized bootable ISO
   - Boot target machine from ISO for automated installation

## Architecture

- **Backend**: FastAPI with SQLAlchemy ORM
- **Database**: SQLite (configurable to PostgreSQL/MySQL)
- **Authentication**: JWT-based with bcrypt password hashing
- **Frontend**: Vanilla Framework (Ubuntu's official CSS framework)
- **ISO Generation**: cloud-localds or genisoimage

## API Endpoints

### Public Endpoints
- `GET /` - User interface
- `GET /api/images` - List available Ubuntu images and MAAS versions
- `POST /api/generate` - Generate autoinstaller YAML configuration
- `POST /api/generate-iso` - Generate and download bootable ISO
- `GET /api/health` - Health check

### Admin Endpoints (Requires Authentication)
- `GET /admin` - Admin portal interface
- `POST /api/auth/login` - Admin authentication
- `GET /api/admin/images` - List all images with MAAS versions
- `POST /api/admin/images` - Upload new Ubuntu image
- `DELETE /api/admin/images/{id}` - Delete Ubuntu image
- `POST /api/admin/maas-versions` - Add MAAS version to image
- `DELETE /api/admin/maas-versions/{id}` - Delete MAAS version

## Configuration

### Environment Variables

- `DATABASE_URL`: Database connection string (default: `sqlite:///./maastrap.db`)
- `SECRET_KEY`: JWT secret key (change in production!)

### MAAS PPA Examples

- MAAS 3.2: `ppa:maas/3.2`
- MAAS 3.3: `ppa:maas/3.3`
- MAAS 3.4: `ppa:maas/3.4`
- MAAS Latest Stable: `ppa:maas/stable`

## Development

To run in development mode:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## Docker Support

A Dockerfile is provided for containerized deployment:
```bash
docker build -t maastrap .
docker run -p 8000:8000 -v ./images:/app/images maastrap
```

## Security Considerations

1. **Change Default Admin Password**: Immediately change the default admin/admin credentials
2. **Use HTTPS in Production**: Configure a reverse proxy with SSL/TLS
3. **Secure Secret Key**: Set a strong SECRET_KEY environment variable
4. **Database Backups**: Regularly backup the maastrap.db file
5. **File Storage**: Ensure the images directory has appropriate permissions

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
