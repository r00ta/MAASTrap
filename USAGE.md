# MAASTrap Usage Guide

## Installation

### Option 1: Direct Python Installation

```bash
# Clone the repository
git clone https://github.com/r00ta/MAASTrap.git
cd MAASTrap

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### Option 2: Docker

```bash
# Build and run with Docker
docker build -t maastrap .
docker run -p 8000:8000 maastrap
```

### Option 3: Docker Compose

```bash
# Run with docker-compose
docker-compose up -d
```

## Using the Web Interface

1. Open your browser and navigate to `http://localhost:8000`
2. Fill in the system configuration
3. Configure MAAS settings
4. Add network interfaces
5. Click "Generate Autoinstall Config"
6. Download or copy the generated YAML

## Using the API

### Generate Configuration

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d @examples/simple-config.json
```

### Health Check

```bash
curl http://localhost:8000/api/health
```

## What Gets Installed

The autoinstaller configuration will:

1. Install Ubuntu 24.04 Server
2. Configure network interfaces according to your specification
3. Install MAAS packages (maas, maas-region-controller)
4. Install and configure PostgreSQL database
5. Initialize MAAS region controller
6. Create MAAS admin user
7. Configure DHCP on specified networks

## Post-Installation

After the system boots:

1. Access MAAS web interface at: `http://<your-ip>:5240/MAAS`
2. Log in with the credentials you specified
3. Continue MAAS configuration

## Security Considerations

1. Always use strong, unique passwords for MAAS admin
2. Consider firewall rules for MAAS services
3. In production, configure HTTPS for MAAS web interface
