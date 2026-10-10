// ============================================
// ARTESANOS CONTROL - Utilidades generales
// ============================================

// ============================================
// CSRF TOKEN - Interceptor global para fetch
// ============================================
(function () {
    const meta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = meta ? meta.getAttribute('content') : null;

    if (!csrfToken) {
        console.warn('⚠️ No se encontro el meta tag CSRF');
        return;
    }

    // Guardar el fetch original
    const originalFetch = window.fetch;

    // Interceptor: agrega el header X-CSRFToken a todas las peticiones que modifican
    window.fetch = function (url, options = {}) {
        const method = (options.method || 'GET').toUpperCase();

        // Solo para metodos que modifican datos
        if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(method)) {
            options.headers = options.headers || {};

            // Si es Headers, usar set; si es objeto, asignar
            if (options.headers instanceof Headers) {
                options.headers.set('X-CSRFToken', csrfToken);
            } else {
                options.headers['X-CSRFToken'] = csrfToken;
            }
        }

        return originalFetch(url, options);
    };

    console.log('✅ CSRF interceptor activo');
})();


// ============================================
// Prevenir cambio de valor en inputs[type=number]
// con la rueda del mouse
// ============================================
document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('input[type="number"]').forEach(function (input) {
        input.addEventListener('wheel', function (e) {
            e.preventDefault();
            this.blur();
        }, { passive: false });
    });
});