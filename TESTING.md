# MAASTrap Testing Guide

## Manual Testing Checklist

### Web UI Testing

1. **Access the UI**
   ```bash
   python app.py
   # Navigate to http://localhost:8000
   ```

2. **Test System Configuration**
   - [ ] Enter hostname
   - [ ] Modify timezone
   - [ ] Change locale
   - [ ] Verify default values are populated

3. **Test MAAS Configuration**
   - [ ] Enter admin username
   - [ ] Enter admin email (validate email format)
   - [ ] Enter admin password
   - [ ] Set region name

4. **Test Network Interface Management**
   - [ ] Default interface loads (Interface 1)
   - [ ] Click "+ Add Interface" - should create Interface 2
   - [ ] Add multiple interfaces (3+)
   - [ ] Click "Remove" button - should remove specific interface
   - [ ] Fill in interface details:
     - Interface name (eth0, ens192, etc.)
     - IP address with CIDR (e.g., 192.168.1.10/24)
     - Gateway (optional)
     - DNS servers
     - Enable/disable DHCP checkbox

5. **Test Configuration Generation**
   - [ ] Click "Generate Autoinstall Config"
   - [ ] Verify configuration appears in output section
   - [ ] Configuration should be valid YAML
   - [ ] Click "Copy to Clipboard" - verify clipboard has content
   - [ ] Click "Download YAML" - verify file downloads

6. **Test Error Handling**
   - [ ] Submit without email - should show error
   - [ ] Submit without password - should show error
   - [ ] Submit with invalid IP format - should show error
   - [ ] Submit without CIDR notation - should show error

### API Testing

1. **Health Check**
   ```bash
   curl http://localhost:8000/api/health
   # Expected: {"status":"healthy","service":"MAASTrap"}
   ```

2. **Generate Configuration - Simple**
   ```bash
   curl -X POST http://localhost:8000/api/generate \
     -H "Content-Type: application/json" \
     -d @examples/simple-config.json
   ```

3. **Generate Configuration - Multi-Network**
   ```bash
   curl -X POST http://localhost:8000/api/generate \
     -H "Content-Type: application/json" \
     -d @examples/multi-network.json
   ```

4. **Verify Generated Configuration**
   - [ ] Contains valid netplan network configuration
   - [ ] Includes all specified interfaces
   - [ ] DHCP commands only for enabled networks
   - [ ] MAAS initialization commands present
   - [ ] Admin user creation with correct credentials
   - [ ] PostgreSQL setup commands included

### Docker Testing

1. **Build Docker Image**
   ```bash
   docker build -t maastrap .
   ```

2. **Run Container**
   ```bash
   docker run -p 8000:8000 maastrap
   ```

3. **Test Container**
   ```bash
   curl http://localhost:8000/api/health
   ```

4. **Docker Compose**
   ```bash
   docker-compose up -d
   docker-compose logs
   curl http://localhost:8000/api/health
   docker-compose down
   ```

### Security Testing

1. **Dependency Vulnerability Check**
   - All dependencies should be at patched versions
   - FastAPI >= 0.109.1 (fixes ReDoS vulnerability)
   - No known vulnerabilities in PyYAML, Jinja2, Pydantic, Uvicorn

2. **Code Analysis**
   - CodeQL should report 0 alerts for Python
   - CodeQL should report 0 alerts for JavaScript

3. **Input Validation**
   - [ ] IP addresses validated for CIDR notation
   - [ ] Email format validated
   - [ ] Required fields enforced

## Automated Testing

### Python Syntax Check
```bash
python -m py_compile app.py
```

### JavaScript Syntax Check
```bash
node -c static/script.js
```

### Run Application
```bash
python app.py
# Server should start on http://0.0.0.0:8000
```

## Expected Outputs

### Sample Generated Configuration

The generated configuration should include:

1. **Network Configuration**
   - Netplan version 2
   - Ethernet interfaces with static IPs
   - Routes (gateway) if specified
   - DNS nameservers if specified

2. **System Identity**
   - Hostname
   - Default user: ubuntu
   - Hashed password

3. **SSH Configuration**
   - SSH server installed
   - Password authentication allowed

4. **Storage**
   - LVM layout

5. **Packages**
   - net-tools
   - curl
   - wget
   - vim

6. **Late Commands**
   - apt-get update
   - Install MAAS and PostgreSQL
   - Create PostgreSQL user and database
   - Initialize MAAS region+rack
   - Create admin user
   - Configure DHCP (for enabled networks only)

## Known Issues and Limitations

1. **DHCP Range**: Currently hardcoded to .100-.200
2. **Network Calculation**: Assumes /24 networks for DHCP configuration
3. **Password Hash**: Uses static salt (should be randomized in production)
4. **ISO Creation**: Manual process, not automated in the tool

## Performance Considerations

- UI should load in < 2 seconds
- Configuration generation should complete in < 1 second
- API responses should be < 500ms

## Browser Compatibility

Tested and working on:
- Chrome/Chromium (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Troubleshooting

### Server won't start
```bash
# Check if port 8000 is already in use
lsof -i :8000
# Kill existing process if needed
pkill -f "python app.py"
```

### Dependencies won't install
```bash
# Upgrade pip
pip install --upgrade pip
# Install with verbose output
pip install -v -r requirements.txt
```

### Docker build fails
```bash
# Clear Docker cache
docker system prune -a
# Rebuild without cache
docker build --no-cache -t maastrap .
```

## Success Criteria

- ✅ Web UI loads without errors
- ✅ Can add/remove network interfaces dynamically
- ✅ Configuration generation produces valid YAML
- ✅ API endpoints respond correctly
- ✅ Docker container builds and runs
- ✅ No security vulnerabilities detected
- ✅ All manual tests pass
- ✅ Generated config includes all required components
