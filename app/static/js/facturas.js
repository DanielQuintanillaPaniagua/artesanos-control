// ============================================
// ARTESANOS CONTROL - Formulario de Facturas
// ============================================

let _categoriasCache = [];
let _alertaActual = null;
const CATEGORIAS_PRINCIPALES = ['Comida', 'Bebida', 'Limpieza'];


// ============================================
// ALERTA FLOTANTE
// ============================================
function mostrarAlerta(mensaje) {
    if (_alertaActual) _alertaActual.remove();

    const alerta = document.createElement('div');
    alerta.className = 'alerta-descuadre';
    alerta.innerHTML = `<i class="bi bi-exclamation-triangle-fill"></i> ${mensaje}`;
    document.body.appendChild(alerta);
    _alertaActual = alerta;

    // Auto-ocultar despues de 5 segundos
    setTimeout(() => {
        if (_alertaActual === alerta) {
            alerta.remove();
            _alertaActual = null;
        }
    }, 5000);
}

function ocultarAlerta() {
    if (_alertaActual) {
        _alertaActual.remove();
        _alertaActual = null;
    }
}


// ============================================
// CARGAR CATEGORIAS
// ============================================

// ============================================
// BLOQUEO DE NEGATIVOS
// ============================================
function bloquearNegativos(e) {
    const teclasBloqueadas = ['-', 'e', 'E', '+'];
    if (teclasBloqueadas.includes(e.key)) {
        e.preventDefault();
        return false;
    }
    return true;
}

function bloquearPegadoNegativo(e) {
    const portapapeles = (e.clipboardData || window.clipboardData).getData('text');
    if (portapapeles.includes('-')) {
        e.preventDefault();
        return false;
    }
    return true;
}
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

        contPrincipales.innerHTML = principales.map(c => `
            <div class="categoria-item">
                <label>${c.nombre}</label>
                <input type="number" step="0.01" min="0"
                       data-categoria-id="${c.id}"
                       class="monto-input monto-principal"
                       placeholder="0.00">
            </div>
        `).join('');

        contOtras.innerHTML = otras.map(c => `
            <div class="categoria-item">
                <label>${c.nombre}</label>
                <input type="number" step="0.01" min="0"
                       data-categoria-id="${c.id}"
                       class="monto-input monto-otras"
                       placeholder="0.00">
            </div>
        `).join('');

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
// MODALES
// ============================================
function abrirModal() {
    document.getElementById('modal-otras').style.display = 'flex';
}

function cerrarModal() {
    document.getElementById('modal-otras').style.display = 'none';
}

function abrirModalProveedor() {
    document.getElementById('modal-proveedor').style.display = 'flex';
    document.getElementById('nuevo-prov-nombre').value = '';
    document.getElementById('nuevo-prov-telefono').value = '';
    document.getElementById('nuevo-prov-email').value = '';
    document.getElementById('error-nuevo-proveedor').style.display = 'none';
    document.getElementById('nuevo-prov-nombre').focus();
}

function cerrarModalProveedor() {
    document.getElementById('modal-proveedor').style.display = 'none';
}

function mostrarErrorProveedor(msg) {
    const err = document.getElementById('error-nuevo-proveedor');
    err.textContent = msg;
    err.style.display = 'block';
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
// GUARDAR NUEVO PROVEEDOR
// ============================================
async function guardarNuevoProveedor() {
    const nombre = document.getElementById('nuevo-prov-nombre').value.trim();
    const telefono = document.getElementById('nuevo-prov-telefono').value.trim();
    const email = document.getElementById('nuevo-prov-email').value.trim();

    if (!nombre) {
        mostrarErrorProveedor('El nombre es obligatorio');
        return;
    }

    const btnGuardar = document.getElementById('btn-guardar-proveedor');
    btnGuardar.disabled = true;
    btnGuardar.innerHTML = '<i class="bi bi-hourglass-split"></i> Creando...';

    try {
        const resp = await fetch('/api/facturas/proveedores', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ nombre, telefono, email })
        });
        const data = await resp.json();

        if (data.success) {
            const select = document.getElementById('proveedor_id');
            const opt = document.createElement('option');
            opt.value = data.proveedor.id;
            opt.textContent = data.proveedor.nombre;
            select.appendChild(opt);
            select.value = data.proveedor.id;
            cerrarModalProveedor();
        } else {
            mostrarErrorProveedor(data.error || 'Error al crear proveedor');
        }
    } catch (err) {
        console.error(err);
        mostrarErrorProveedor('Error de conexion');
    } finally {
        btnGuardar.disabled = false;
        btnGuardar.innerHTML = '<i class="bi bi-check-lg"></i> Crear proveedor';
    }
}


// ============================================
// RECALCULAR EN VIVO
// ============================================
function recalcular() {
    const inputs = document.querySelectorAll('.monto-input');
    let total = 0;
    let hayNegativos = false;

    inputs.forEach(inp => {
        const valor = parseFloat(inp.value) || 0;
        if (valor < 0) {
            inp.classList.add('invalido');
            hayNegativos = true;
        } else {
            inp.classList.remove('invalido');
            total += valor;
        }
    });

    const totalDeclarado = parseFloat(document.getElementById('total_factura').value) || 0;
    const diferencia = Math.abs(total - totalDeclarado);
    const excedido = total > totalDeclarado + 0.01;

    document.getElementById('total-ingresado').textContent = '$' + total.toFixed(2);
    document.getElementById('total-declarado').textContent = '$' + totalDeclarado.toFixed(2);
    document.getElementById('diferencia').textContent = '$' + diferencia.toFixed(2);

    const estado = document.getElementById('estado-validacion');
    const btnGuardar = document.getElementById('btn-guardar');

    // ============================================
    // PRIORIDAD 1: BLOQUEO POR NEGATIVOS
    // ============================================
    if (hayNegativos) {
        estado.className = 'estado-validacion observada';
        estado.innerHTML = '<i class="bi bi-x-circle-fill"></i> LOS MONTOS NO PUEDEN SER NEGATIVOS';
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.classList.add('disabled');
        }
        mostrarAlerta('Los montos no pueden ser negativos');
        return;
    }

    // ============================================
    // PRIORIDAD 2: BLOQUEO POR EXCESO
    // ============================================
    if (excedido) {
        estado.className = 'estado-validacion observada';
        estado.innerHTML = '<i class="bi bi-x-circle-fill"></i> NO PUEDES SUPERAR EL TOTAL DE LA FACTURA';
        if (btnGuardar) {
            btnGuardar.disabled = true;
            btnGuardar.classList.add('disabled');
        }
        mostrarAlerta(`La suma ($${total.toFixed(2)}) supera el total ($${totalDeclarado.toFixed(2)})`);
        return;
    }

    // ============================================
    // ESTADO NORMAL
    // ============================================
    if (btnGuardar) {
        btnGuardar.disabled = false;
        btnGuardar.classList.remove('disabled');
    }

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

    // Marcar categorias excedidas
    inputs.forEach(inp => {
        const item = inp.closest('.categoria-item');
        if (item) {
            const monto = parseFloat(inp.value) || 0;
            if (monto > totalDeclarado && totalDeclarado > 0) {
                item.classList.add('excedida');
            } else {
                item.classList.remove('excedida');
            }
        }
    });
}

function limpiarFormularioFactura() {
    document.getElementById('numero_factura').value = '';
    document.getElementById('detalle').value = '';
    document.getElementById('total_factura').value = '';
    document.querySelectorAll('.monto-input').forEach(inp => inp.value = '');
    recalcular();
    actualizarBadgeOtras();
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

    if (!numero) { mostrarAlerta('Ingresa el numero de factura'); return; }
    if (total_factura <= 0) { mostrarAlerta('Ingresa el total de la factura'); return; }

    const detalles = [];
    let totalIngresado = 0;
    document.querySelectorAll('.monto-input').forEach(inp => {
        const monto = parseFloat(inp.value) || 0;
        if (monto > 0) {
            detalles.push({
                categoria_id: parseInt(inp.dataset.categoriaId),
                monto: monto
            });
            totalIngresado += monto;
        }
    });

    if (!detalles.length) { mostrarAlerta('Ingresa al menos una categoria con monto'); return; }

    if (totalIngresado > total_factura + 0.01) {
        mostrarAlerta('NO PUEDES GUARDAR: la suma supera el total de la factura');
        return;
    }

    const datos = {
        numero_factura: numero,
        proveedor_id: proveedor_id ? parseInt(proveedor_id) : null,
        fecha: fecha,
        tipo_documento: tipo_documento,
        detalle: detalle,
        total_factura: total_factura,
        detalles: detalles
    };

    // ====== DETECCION OFFLINE ======
    if (!navigator.onLine) {
        const totalCola = agregarALaCola(datos);
        mostrarAlerta(`Sin conexion. Factura guardada localmente (${totalCola} en cola)`);
        limpiarFormularioFactura();
        return;
    }
    // =================================

    const btnGuardar = document.getElementById('btn-guardar');
    btnGuardar.disabled = true;
    btnGuardar.innerHTML = '<i class="bi bi-hourglass-split"></i> Guardando...';

    try {
        const resp = await fetch('/api/facturas/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify(datos)
        });
        const data = await resp.json();

        if (data.success) {
            mostrarAlerta('Factura guardada correctamente');
            limpiarFormularioFactura();
        } else {
            mostrarAlerta('Error: ' + (data.error || 'No se pudo guardar'));
        }
    } catch (err) {
        // Si falla por red, guardar en cola local
        console.error('Error de red, guardando en cola:', err);
        const totalCola = agregarALaCola(datos);
        mostrarAlerta(`Sin conexion. Factura guardada localmente (${totalCola} en cola)`);
        limpiarFormularioFactura();
    } finally {
        btnGuardar.disabled = false;
        btnGuardar.innerHTML = '<i class="bi bi-check-lg"></i> Guardar factura';
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

        const totalInput = document.getElementById('total_factura');
        if (totalInput) {
            totalInput.addEventListener('input', recalcular);
        }

        const btnGuardar = document.getElementById('btn-guardar');
        if (btnGuardar) {
            btnGuardar.addEventListener('click', guardarFactura);
        }

        // Modal categorias
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

        // Modal proveedor
        const btnNuevoProveedor = document.getElementById('btn-nuevo-proveedor');
        if (btnNuevoProveedor) btnNuevoProveedor.addEventListener('click', abrirModalProveedor);

        const btnCloseModalProv = document.getElementById('btn-close-modal-proveedor');
        if (btnCloseModalProv) btnCloseModalProv.addEventListener('click', cerrarModalProveedor);

        const btnCancelarProv = document.getElementById('btn-cancelar-proveedor');
        if (btnCancelarProv) btnCancelarProv.addEventListener('click', cerrarModalProveedor);

        const btnGuardarProv = document.getElementById('btn-guardar-proveedor');
        if (btnGuardarProv) btnGuardarProv.addEventListener('click', guardarNuevoProveedor);

        const modalProv = document.getElementById('modal-proveedor');
        if (modalProv) {
            modalProv.addEventListener('click', (e) => {
                if (e.target === modalProv) cerrarModalProveedor();
            });
        }

        const inputNombre = document.getElementById('nuevo-prov-nombre');
        if (inputNombre) {
            inputNombre.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    guardarNuevoProveedor();
                }
            });
        }
    }
});
