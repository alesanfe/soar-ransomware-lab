// UI helpers + auth headers — leaf module (no project imports).

export function escapeHtml(value) {
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

export function fmtTs(value) {
    const n = Number(value);
    if (!n) return '—';
    const ms = n > 1e12 ? n : n * 1000;
    const d = new Date(ms);
    return isNaN(d) ? '—' : d.toLocaleString();
}

export function getAuthHeaders() {
    const token = localStorage.getItem('auth_token');
    return token ? {'Authorization': `Bearer ${token}`} : {};
}

export function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = show ? 'flex' : 'none';
}

export function showMessage(message, type) {
    // Create a temporary message element
    const messageElement = document.createElement('div');
    messageElement.className = `text-${type}`;
    messageElement.textContent = message;
    messageElement.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem;
        background: white;
        border-radius: 0.375rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 1001;
        max-width: 300px;
    `;

    document.body.appendChild(messageElement);

    // Remove after 3 seconds
    setTimeout(() => {
        document.body.removeChild(messageElement);
    }, 3000);
}
