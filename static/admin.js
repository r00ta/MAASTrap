// Global state
let authToken = null;

// Check if already logged in
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('authToken');
    if (token) {
        authToken = token;
        loadAdminDashboard();
    }
});

// Login form handler
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        if (!response.ok) {
            throw new Error('Invalid credentials');
        }
        
        const data = await response.json();
        authToken = data.access_token;
        localStorage.setItem('authToken', authToken);
        
        loadAdminDashboard();
    } catch (error) {
        document.getElementById('login-error-message').textContent = error.message;
        document.getElementById('login-error').classList.remove('hidden');
    }
});

function loadAdminDashboard() {
    document.getElementById('login-section').classList.add('hidden');
    document.getElementById('admin-dashboard').classList.remove('hidden');
    loadImages();
}

async function loadImages() {
    try {
        const response = await fetch('/api/admin/images', {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load images');
        }
        
        const images = await response.json();
        displayImages(images);
    } catch (error) {
        console.error('Error loading images:', error);
        alert('Failed to load images: ' + error.message);
    }
}

function displayImages(images) {
    const tbody = document.getElementById('images-table-body');
    tbody.innerHTML = '';
    
    images.forEach(img => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${img.name}</td>
            <td>${img.version}</td>
            <td>${img.codename}</td>
            <td>
                ${img.maas_versions.map(mv => `MAAS ${mv.version}`).join(', ')}
                <button type="button" class="p-button--base is-dense" onclick="showAddMAASVersionModal(${img.id})">
                    <i class="p-icon--plus"></i> Add
                </button>
            </td>
            <td>
                <button type="button" class="p-button--base is-dense" onclick="deleteImage(${img.id})">
                    <i class="p-icon--delete"></i> Delete
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

function showAddImageModal() {
    document.getElementById('add-image-modal').classList.remove('hidden');
}

function closeAddImageModal() {
    document.getElementById('add-image-modal').classList.add('hidden');
    document.getElementById('add-image-form').reset();
}

document.getElementById('add-image-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData();
    formData.append('name', document.getElementById('image-name').value);
    formData.append('version', document.getElementById('image-version').value);
    formData.append('codename', document.getElementById('image-codename').value);
    formData.append('iso_file', document.getElementById('image-file').files[0]);
    
    try {
        const response = await fetch('/api/admin/images', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to upload image');
        }
        
        closeAddImageModal();
        loadImages();
    } catch (error) {
        alert('Failed to upload image: ' + error.message);
    }
});

async function deleteImage(imageId) {
    if (!confirm('Are you sure you want to delete this image?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/admin/images/${imageId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete image');
        }
        
        loadImages();
    } catch (error) {
        alert('Failed to delete image: ' + error.message);
    }
}

function showAddMAASVersionModal(imageId) {
    document.getElementById('maas-ubuntu-image-id').value = imageId;
    document.getElementById('add-maas-version-modal').classList.remove('hidden');
}

function closeAddMAASVersionModal() {
    document.getElementById('add-maas-version-modal').classList.add('hidden');
    document.getElementById('add-maas-version-form').reset();
}

document.getElementById('add-maas-version-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData();
    formData.append('version', document.getElementById('maas-version').value);
    formData.append('ppa_url', document.getElementById('maas-ppa').value);
    formData.append('ubuntu_image_id', document.getElementById('maas-ubuntu-image-id').value);
    
    try {
        const response = await fetch('/api/admin/maas-versions', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Failed to add MAAS version');
        }
        
        closeAddMAASVersionModal();
        loadImages();
    } catch (error) {
        alert('Failed to add MAAS version: ' + error.message);
    }
});
