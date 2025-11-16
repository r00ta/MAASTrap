// Global state
let interfaceCounter = 0;
let generatedYAML = '';
let availableImages = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadAvailableImages();
    addInterface(); // Add first interface by default
});

async function loadAvailableImages() {
    try {
        const response = await fetch('/api/images');
        const images = await response.json();
        availableImages = images;
        
        const select = document.getElementById('ubuntu-image');
        select.innerHTML = '<option value="">Select Ubuntu version...</option>';
        
        images.forEach(img => {
            const option = document.createElement('option');
            option.value = img.id;
            option.textContent = `${img.name} (${img.version})`;
            option.dataset.maasVersions = JSON.stringify(img.maas_versions);
            select.appendChild(option);
        });
    } catch (error) {
        showError('Failed to load available Ubuntu images: ' + error.message);
    }
}

document.getElementById('ubuntu-image').addEventListener('change', function() {
    const selectedOption = this.options[this.selectedIndex];
    const maasVersionSelect = document.getElementById('maas-version');
    
    if (!selectedOption.value) {
        maasVersionSelect.disabled = true;
        maasVersionSelect.innerHTML = '<option value="">Select MAAS version...</option>';
        return;
    }
    
    const maasVersions = JSON.parse(selectedOption.dataset.maasVersions || '[]');
    maasVersionSelect.disabled = false;
    maasVersionSelect.innerHTML = '<option value="">Select MAAS version...</option>';
    
    maasVersions.forEach(mv => {
        const option = document.createElement('option');
        option.value = mv.id;
        option.textContent = `MAAS ${mv.version}`;
        maasVersionSelect.appendChild(option);
    });
});

function addInterface() {
    interfaceCounter++;
    const container = document.getElementById('interfaces-container');
    
    const interfaceCard = document.createElement('div');
    interfaceCard.className = 'p-card';
    interfaceCard.id = `interface-${interfaceCounter}`;
    interfaceCard.style.marginBottom = '1rem';
    
    interfaceCard.innerHTML = `
        <div class="p-card__content">
            <div class="u-clearfix">
                <h3 class="p-card__title u-float-left">Interface ${interfaceCounter}</h3>
                <button type="button" class="p-button--base has-icon u-float-right" onclick="removeInterface(${interfaceCounter})">
                    <i class="p-icon--delete"></i>
                    <span>Remove</span>
                </button>
            </div>
            <form class="p-form p-form--stacked">
                <div class="p-form__group row">
                    <div class="col-6">
                        <label for="iface-name-${interfaceCounter}">Interface Name:</label>
                        <input class="p-form__control" type="text" id="iface-name-${interfaceCounter}" placeholder="eth0, ens192, etc." value="eth${interfaceCounter - 1}">
                    </div>
                    <div class="col-6">
                        <label for="iface-ip-${interfaceCounter}">IP Address (CIDR):</label>
                        <input class="p-form__control" type="text" id="iface-ip-${interfaceCounter}" placeholder="192.168.1.10/24">
                    </div>
                </div>
                <div class="p-form__group row">
                    <div class="col-6">
                        <label for="iface-gateway-${interfaceCounter}">Gateway (optional):</label>
                        <input class="p-form__control" type="text" id="iface-gateway-${interfaceCounter}" placeholder="192.168.1.1">
                    </div>
                    <div class="col-6">
                        <label>DNS Servers:</label>
                        <input class="p-form__control" type="text" id="dns-${interfaceCounter}-1" placeholder="8.8.8.8" value="8.8.8.8" style="margin-bottom: 0.5rem;">
                        <input class="p-form__control" type="text" id="dns-${interfaceCounter}-2" placeholder="8.8.4.4" value="8.8.4.4">
                    </div>
                </div>
                <div class="p-form__group">
                    <label class="p-checkbox">
                        <input type="checkbox" id="iface-dhcp-${interfaceCounter}" class="p-checkbox__input">
                        <span class="p-checkbox__label">Enable DHCP on this network</span>
                    </label>
                </div>
            </form>
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
    const cards = container.querySelectorAll('.p-card');
    
    cards.forEach(card => {
        const id = card.id.split('-')[1];
        const name = document.getElementById(`iface-name-${id}`).value;
        const ip = document.getElementById(`iface-ip-${id}`).value;
        const gateway = document.getElementById(`iface-gateway-${id}`).value;
        const enableDhcp = document.getElementById(`iface-dhcp-${id}`).checked;
        
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

async function generateISO() {
    // Hide previous messages
    document.getElementById('output-section').classList.add('hidden');
    document.getElementById('error-section').classList.add('hidden');
    
    // Validate selections
    const ubuntuImageId = document.getElementById('ubuntu-image').value;
    const maasVersionId = document.getElementById('maas-version').value;
    
    if (!ubuntuImageId) {
        showError('Please select an Ubuntu version');
        return;
    }
    
    if (!maasVersionId) {
        showError('Please select a MAAS version');
        return;
    }
    
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
    
    const request = {
        hostname: hostname,
        ubuntu_image_id: parseInt(ubuntuImageId),
        maas_version_id: parseInt(maasVersionId),
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
    
    // Show progress
    document.getElementById('progress').classList.remove('hidden');
    
    try {
        // First generate the YAML config for display
        const configResponse = await fetch('/api/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(request)
        });
        
        if (!configResponse.ok) {
            const error = await configResponse.json();
            throw new Error(error.detail || 'Failed to generate configuration');
        }
        
        const configData = await configResponse.json();
        
        if (configData.success) {
            generatedYAML = configData.yaml;
            document.getElementById('output-content').textContent = generatedYAML;
            document.getElementById('output-section').classList.remove('hidden');
        }
        
        // Now generate the ISO
        const isoResponse = await fetch('/api/generate-iso', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(request)
        });
        
        if (!isoResponse.ok) {
            const error = await isoResponse.json();
            throw new Error(error.detail || 'Failed to generate ISO');
        }
        
        // Download the ISO
        const blob = await isoResponse.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `maas-autoinstall-${hostname}.iso`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        // Hide progress
        document.getElementById('progress').classList.add('hidden');
        
        // Scroll to output
        document.getElementById('output-section').scrollIntoView({ behavior: 'smooth' });
    } catch (error) {
        document.getElementById('progress').classList.add('hidden');
        showError(error.message);
    }
}

function showError(message) {
    document.getElementById('error-content').textContent = message;
    document.getElementById('error-section').classList.remove('hidden');
    document.getElementById('error-section').scrollIntoView({ behavior: 'smooth' });
}

function copyToClipboard() {
    const content = document.getElementById('output-content').textContent;
    navigator.clipboard.writeText(content).then(() => {
        // Show success notification
        const notification = document.createElement('div');
        notification.className = 'p-notification--positive';
        notification.style.position = 'fixed';
        notification.style.top = '1rem';
        notification.style.right = '1rem';
        notification.style.zIndex = '9999';
        notification.innerHTML = `
            <div class="p-notification__content">
                <p class="p-notification__message">Configuration copied to clipboard!</p>
            </div>
        `;
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 3000);
    }).catch(err => {
        showError('Failed to copy to clipboard: ' + err);
    });
}
