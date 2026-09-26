// ============================================
// Prevenir cambio de valor en inputs[type=number]
// al usar la rueda del mouse
// ============================================

document.addEventListener('wheel', function(e) {
    // Si el elemento activo es un input number, bloquear el scroll
    if (document.activeElement.type === 'number') {
        document.activeElement.blur();
    }
}, { passive: false });


// Alternativa: aplicar solo a inputs .monto-input
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('input[type="number"]').forEach(function(input) {
        input.addEventListener('wheel', function(e) {
            e.preventDefault();
            this.blur();
        });
    });
});
