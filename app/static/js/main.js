// ============================================
// ARTESANOS CONTROL - Utilidades generales
// ============================================

// Prevenir cambio de valor en inputs[type=number] con la rueda del mouse
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('input[type="number"]').forEach(function(input) {
        input.addEventListener('wheel', function(e) {
            e.preventDefault();
            this.blur();
        }, { passive: false });
    });
});
