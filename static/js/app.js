document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

// AJAX helper
function ajax(url, options = {}) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
    const defaults = {
        headers: {
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest',
        },
    };
    return fetch(url, { ...defaults, ...options });
}
