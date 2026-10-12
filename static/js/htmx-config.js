// HTMX Configuration for Django CSRF
document.addEventListener('DOMContentLoaded', () => {
    document.body.addEventListener('htmx:configRequest', (event) => {
        // Read CSRF token from cookies if available
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, 10) === 'csrftoken=') {
                    cookieValue = decodeURIComponent(cookie.substring(10));
                    break;
                }
            }
        }
        if (cookieValue) {
            event.detail.headers['X-CSRFToken'] = cookieValue;
        }
    });

    // Handle HTMX response errors gracefully
    document.body.addEventListener('htmx:responseError', (event) => {
        console.error('HTMX error:', event.detail);
    });
});
