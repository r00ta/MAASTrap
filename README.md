# MAASTrap

Bootstrap your datacenter with MAAS (Metal as a Service)

## Overview

MAASTrap is a web-based tool that helps you bootstrap a MAAS region controller by generating a customized Ubuntu 24.04 autoinstaller ISO. The tool allows you to:

- Configure network interfaces for your MAAS region controller
- Specify which VLANs should have DHCP enabled
- Generate a bootable ISO that automatically installs and configures MAAS

## Features

- **Web UI**: Simple interface to configure network settings
- **Network Configuration**: Define interfaces, IP addresses, gateways, and DNS
- **DHCP Management**: Select which networks should have DHCP enabled
- **Autoinstaller Generation**: Creates Ubuntu 24.04 cloud-init configuration
- **MAAS Installation**: Automatically installs and configures MAAS region controller

## Quick Start

### Prerequisites

- Python 3.9 or higher
- Ubuntu 24.04 ISO (for generating custom ISOs)

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

4. Open your browser and navigate to `http://localhost:8000`

## Usage

1. **Configure Network**: Enter the network configuration for your MAAS region controller
   - Interface name (e.g., eth0, ens192)
   - IP address with CIDR (e.g., 192.168.1.10/24)
   - Gateway
   - DNS servers

2. **Enable DHCP**: Select which networks should have DHCP enabled

3. **Generate Configuration**: Click "Generate Autoinstall Config" to create the cloud-init configuration

4. **Download**: The configuration will be displayed and ready for ISO generation

## Architecture

- **Backend**: FastAPI-based REST API
- **Frontend**: Modern HTML/CSS/JavaScript UI
- **Templates**: Jinja2 templates for cloud-init generation

## API Endpoints

- `GET /`: Serve the web UI
- `POST /api/generate`: Generate autoinstaller configuration
  - Accepts network configuration JSON
  - Returns cloud-init YAML configuration

## Configuration Format

The tool generates cloud-init autoinstall configuration that:
- Configures network interfaces using netplan
- Installs MAAS packages (maas, maas-region-controller)
- Sets up PostgreSQL database for MAAS
- Initializes MAAS region controller
- Configures DHCP on specified VLANs

## Development

To run in development mode:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## Docker Support

A Dockerfile is provided for containerized deployment:
```bash
docker build -t maastrap .
docker run -p 8000:8000 maastrap
```

## License

See LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
