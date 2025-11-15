# Example Configurations

This directory contains example configuration files for MAASTrap.

## Using Example Configurations

You can use these example configurations with the API:

```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d @examples/simple-config.json
```

## Files

- **simple-config.json**: Single network interface with DHCP
- **multi-network.json**: Multiple network interfaces with selective DHCP

## Configuration Format

Each configuration file should include:

- `hostname`: Hostname for the MAAS region controller
- `timezone`: System timezone (e.g., "UTC", "America/New_York")
- `locale`: System locale (e.g., "en_US.UTF-8")
- `interfaces`: Array of network interface configurations
  - `name`: Interface name (e.g., "eth0", "ens192")
  - `ip_address`: IP address with CIDR notation (e.g., "192.168.1.10/24")
  - `gateway`: Gateway IP address (optional)
  - `dns_servers`: Array of DNS server addresses (optional)
  - `enable_dhcp`: Boolean to enable DHCP on this network
- `maas_config`: MAAS configuration
  - `admin_username`: MAAS admin username
  - `admin_email`: MAAS admin email
  - `admin_password`: MAAS admin password
  - `region_name`: MAAS region name

## Modifying Examples

1. Copy an example file
2. Edit the configuration to match your network setup
3. Test with the API or use the web UI at http://localhost:8000
