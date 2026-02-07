// Main JavaScript utilities
document.addEventListener('DOMContentLoaded', () => {
    // Auto-hide messages after 5 seconds
    document.querySelectorAll('.message').forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 300);
        }, 5000);
    });
});

// Helper functions
function showToast(elementId, message, type = 'success') {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = message;
        el.className = `toast ${type}`;
        el.classList.remove('hidden');
        setTimeout(() => el.classList.add('hidden'), 3000);
    }
}

async function fetchJSON(url, options = {}) {
    const response = await fetch(url, {
        headers: {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        },
        ...options
    });
    return response.json();
}
