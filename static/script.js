// Global state
let interfaceCounter = 0;
let generatedYAML = '';

// Initialize with one interface
document.addEventListener('DOMContentLoaded', () => {
    addInterface();
});

function addInterface() {
    interfaceCounter++;
    const container = document.getElementById('interfaces-container');
    
    const interfaceCard = document.createElement('div');
    interfaceCard.className = 'interface-card';
    interfaceCard.id = `interface-${interfaceCounter}`;
    
    interfaceCard.innerHTML = `
        <h3>
            <span>Interface ${interfaceCounter}</span>
            <button type="button" class="btn btn-danger" onclick="removeInterface(${interfaceCounter})">🗑️ Remove</button>
        </h3>
        <div class="interface-grid">
            <div class="form-group">
                <label>Interface Name:</label>
                <input type="text" id="iface-name-${interfaceCounter}" placeholder="eth0, ens192, etc." value="eth${interfaceCounter - 1}">
            </div>
            <div class="form-group">
                <label>IP Address (CIDR):</label>
                <input type="text" id="iface-ip-${interfaceCounter}" placeholder="192.168.1.10/24">
            </div>
            <div class="form-group">
                <label>Gateway (optional):</label>
                <input type="text" id="iface-gateway-${interfaceCounter}" placeholder="192.168.1.1">
            </div>
            <div class="form-group">
                <label>DNS Servers:</label>
                <div class="dns-servers" id="dns-container-${interfaceCounter}">
                    <div class="dns-server-group">
                        <input type="text" id="dns-${interfaceCounter}-1" placeholder="8.8.8.8" value="8.8.8.8">
                    </div>
                    <div class="dns-server-group">
                        <input type="text" id="dns-${interfaceCounter}-2" placeholder="8.8.4.4" value="8.8.4.4">
                    </div>
                </div>
            </div>
        </div>
        <div class="checkbox-group">
            <input type="checkbox" id="iface-dhcp-${interfaceCounter}">
            <label for="iface-dhcp-${interfaceCounter}">Enable DHCP on this network</label>
        </div>
    `;
    
    container.appendChild(interfaceCard);
}

function removeInterface(id) {
    const element = document.getElementById(`interface-${id}`);
    if (element) {
        element.remove();
    }
}

function collectInterfaces() {
    const interfaces = [];
    const container = document.getElementById('interfaces-container');
    const cards = container.querySelectorAll('.interface-card');
    
    cards.forEach(card => {
        const id = card.id.split('-')[1];
        const name = document.getElementById(`iface-name-${id}`).value;
        const ip = document.getElementById(`iface-ip-${id}`).value;
        const gateway = document.getElementById(`iface-gateway-${id}`).value;
        const enableDhcp = document.getElementById(`iface-dhcp-${id}`).checked;
        
        // Collect DNS servers
        const dnsServers = [];
        const dns1 = document.getElementById(`dns-${id}-1`).value;
        const dns2 = document.getElementById(`dns-${id}-2`).value;
        
        if (dns1) dnsServers.push(dns1);
        if (dns2) dnsServers.push(dns2);
        
        if (name && ip) {
            interfaces.push({
                name: name,
                ip_address: ip,
                gateway: gateway || null,
                dns_servers: dnsServers,
                enable_dhcp: enableDhcp
            });
        }
    });
    
    return interfaces;
}

async function generateConfig() {
    // Hide previous outputs
    document.getElementById('output-section').style.display = 'none';
    document.getElementById('error-section').style.display = 'none';
    
    // Collect form data
    const hostname = document.getElementById('hostname').value;
    const timezone = document.getElementById('timezone').value;
    const locale = document.getElementById('locale').value;
    const maasUsername = document.getElementById('maas-username').value;
    const maasEmail = document.getElementById('maas-email').value;
    const maasPassword = document.getElementById('maas-password').value;
    const maasRegion = document.getElementById('maas-region').value;
    const interfaces = collectInterfaces();
    
    // Validation
    if (!hostname) {
        showError('Hostname is required');
        return;
    }
    
    if (!maasEmail) {
        showError('MAAS admin email is required');
        return;
    }
    
    if (!maasPassword) {
        showError('MAAS admin password is required');
        return;
    }
    
    if (interfaces.length === 0) {
        showError('At least one network interface is required');
        return;
    }
    
    // Prepare request
    const request = {
        hostname: hostname,
        timezone: timezone,
        locale: locale,
        interfaces: interfaces,
        maas_config: {
            admin_username: maasUsername,
            admin_email: maasEmail,
            admin_password: maasPassword,
            region_name: maasRegion
        }
    };
    
    try {
        const response = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(request)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate configuration');
        }
        
        const data = await response.json();
        
        if (data.success) {
            generatedYAML = data.yaml;
            document.getElementById('output-content').textContent = generatedYAML;
            document.getElementById('output-section').style.display = 'block';
            
            // Scroll to output
            document.getElementById('output-section').scrollIntoView({ behavior: 'smooth' });
        } else {
            showError('Failed to generate configuration');
        }
    } catch (error) {
        showError(error.message);
    }
}

function showError(message) {
    document.getElementById('error-content').textContent = message;
    document.getElementById('error-section').style.display = 'block';
    document.getElementById('error-section').scrollIntoView({ behavior: 'smooth' });
}

function copyToClipboard() {
    const content = document.getElementById('output-content').textContent;
    navigator.clipboard.writeText(content).then(() => {
        alert('Configuration copied to clipboard!');
    }).catch(err => {
        alert('Failed to copy to clipboard: ' + err);
    });
}

function downloadYAML() {
    const content = document.getElementById('output-content').textContent;
    const blob = new Blob([content], { type: 'text/yaml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'user-data.yaml';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
