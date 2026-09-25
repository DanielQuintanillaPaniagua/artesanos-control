// ============================================
// ARTESANOS CONTROL - Formulario de Facturas (Empleado)
// ============================================

let _categoriasCache = [];
const CATEGORIAS_PRINCIPALES = ['Comida', 'Bebida', 'Limpieza'];


// ============================================
// CARGAR CATEGORIAS (separando principales)
// ============================================
async function cargarCategorias() {
    const contPrincipales = document.getElementById('categorias-principales');
    const contOtras = document.getElementById('categorias-grid');
    if (!contPrincipales || !contOtras) return;

    try {
        const resp = await fetch('/api/facturas/categorias', { credentials: 'same-origin' });
        const data = await resp.json();
        _categoriasCache = data.categorias || [];

        if (!_categoriasCache.length) {
            contPrincipales.innerHTML = '<p style="color:#888;">No hay categorias</p>';
            return;
        }

        const principales = _categoriasCache.filter(c => CATEGORIAS_PRINCIPALES.includes(c.nombre));
        const otras = _categoriasCache.filter(c => !CATEGORIAS_PRINCIPALES.includes(c.nombre));

        // PRINCIPALES
        contPrincipales.innerHTML = principales.map(c => `
            <div class="categoria-item">
                <label>${c.nombre}</label>
                <input type="number" step="0.01" min="0" 
                       data-categoria-id="${c.id}" 
                       class="monto-input monto-principal" 
                       placeholder="0.00">
            </div>
        `).join('');

        // OTRAS
        contOtras.innerHTML = otras.map(c => `
            <div class="categoria-item">
                <label>${c.nombre}</label>
                <input type="number" step="0.01" min="0" 
                       data-categoria-id="${c.id}" 
                       class="monto-input monto-otras" 
                       placeholder="0.00">
            </div>
        `).join('');

        // Listeners
        document.querySelectorAll('.monto-input').forEach(inp => {
            inp.addEventListener('input', () => {
                recalcular();
                actualizarBadgeOtras();
            });
        });

        recalcular();
        actualizarBadgeOtras();

    } catch (err) {
        console.error('Error categorias:', err);
        contPrincipales.innerHTML = '<p style="color:#d42f2f;">Error al cargar categorias</p>';
    }
}


// ============================================
// BADGE DE OTRAS CATEGORIAS USADAS
// ============================================
function actualizarBadgeOtras() {
    const otras = document.querySelectorAll('.monto-otras');
    let count = 0;
    otras.forEach(inp => {
        if (parseFloat(inp.value) > 0) count++;
    });

    const badge = document.getElementById('badge-otras');
    if (badge) {
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    }
}


// ============================================
// MODAL
// ============================================
function abrirModal() {
    document.getElementById('modal-otras').style.display = 'flex';
}

function cerrarModal() {
    document.getElementById('modal-otras').style.display = 'none';
}


// ============================================
// CARGAR PROVEEDORES
// ============================================
async function cargarProveedores() {
    const select = document.getElementById('proveedor_id');
    if (!select) return;

    try {
        const resp = await fetch('/api/facturas/proveedores', { credentials: 'same-origin' });
        const data = await resp.json();
        (data.proveedores || []).forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = p.nombre;
            select.appendChild(opt);
        });
    } catch (err) {
        console.error('Error proveedores:', err);
    }
}


// ============================================
// RECALCULAR EN VIVO
// ============================================
function recalcular() {
    const inputs = document.querySelectorAll('.monto-input');
    let total = 0;
    inputs.forEach(inp => {
        total += parseFloat(inp.value) || 0;
    });

    const totalDeclarado = parseFloat(document.getElementById('total_factura').value) || 0;
    const diferencia = Math.abs(total - totalDeclarado);

    document.getElementById('total-ingresado').textContent = '$' + total.toFixed(2);
    document.getElementById('total-declarado').textContent = '$' + totalDeclarado.toFixed(2);
    document.getElementById('diferencia').textContent = '$' + diferencia.toFixed(2);

    const estado = document.getElementById('estado-validacion');
    if (total === 0 && totalDeclarado === 0) {
        estado.className = 'estado-validacion';
        estado.innerHTML = '<i class="bi bi-hourglass-split"></i> Ingresa los montos';
    } else if (diferencia <= 0.01) {
        estado.className = 'estado-validacion validada';
        estado.innerHTML = '<i class="bi bi-check-circle-fill"></i> FACTURA VALIDADA';
    } else {
        estado.className = 'estado-validacion observada';
        estado.innerHTML = '<i class="bi bi-exclamation-triangle-fill"></i> DESCUADRE: $' + diferencia.toFixed(2);
    }
}


// ============================================
// GUARDAR FACTURA
// ============================================
async function guardarFactura() {
    const numero = document.getElementById('numero_factura').value.trim();
    const proveedor_id = document.getElementById('proveedor_id').value;
    const fecha = document.getElementById('fecha').value;
    const tipo_documento = document.getElementById('tipo_documento').value;
    const detalle = document.getElementById('detalle').value.trim();
    const total_factura = parseFloat(document.getElementById('total_factura').value) || 0;

    if (!numero) { alert('Ingresa el numero de factura'); return; }
    if (total_factura <= 0) { alert('Ingresa el total de la factura'); return; }

    const detalles = [];
    document.querySelectorAll('.monto-input').forEach(inp => {
        const monto = parseFloat(inp.value) || 0;
        if (monto > 0) {
            detalles.push({
                categoria_id: parseInt(inp.dataset.categoriaId),
                monto: monto
            });
        }
    });

    if (!detalles.length) { alert('Ingresa al menos una categoria con monto'); return; }

    const datos = {
        numero_factura: numero,
        proveedor_id: proveedor_id ? parseInt(proveedor_id) : null,
        fecha: fecha,
        tipo_documento: tipo_documento,
        detalle: detalle,
        total_factura: total_factura,
        detalles: detalles
    };

    try {
        const resp = await fetch('/api/facturas/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(datos)
        });
        const data = await resp.json();

        if (data.success) {
            alert(data.message);
            document.getElementById('numero_factura').value = '';
            document.getElementById('detalle').value = '';
            document.getElementById('total_factura').value = '';
            document.querySelectorAll('.monto-input').forEach(inp => inp.value = '');
            recalcular();
            actualizarBadgeOtras();
        } else {
            alert('Error: ' + (data.error || 'No se pudo guardar'));
        }
    } catch (err) {
        console.error(err);
        alert('Error de conexion');
    }
}


// ============================================
// INICIALIZACION
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('categorias-principales')) {
        cargarCategorias();
        cargarProveedores();

        const fechaInput = document.getElementById('fecha');
        if (fechaInput && !fechaInput.value) {
            fechaInput.value = new Date().toISOString().split('T')[0];
        }

        document.getElementById('total_factura').addEventListener('input', recalcular);

        const btnGuardar = document.getElementById('btn-guardar');
        if (btnGuardar) {
            btnGuardar.addEventListener('click', guardarFactura);
        }

        // Modal
        const btnOtras = document.getElementById('btn-otras');
        if (btnOtras) btnOtras.addEventListener('click', abrirModal);

        const btnCloseModal = document.getElementById('btn-close-modal');
        if (btnCloseModal) btnCloseModal.addEventListener('click', cerrarModal);

        const btnCerrarModal = document.getElementById('btn-cerrar-modal');
        if (btnCerrarModal) btnCerrarModal.addEventListener('click', cerrarModal);

        const modal = document.getElementById('modal-otras');
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) cerrarModal();
            });
        }
    }
});
