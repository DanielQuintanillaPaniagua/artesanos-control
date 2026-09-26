// ARTESANOS CONTROL - Modo Offline (LocalStorage)

const COLA_KEY = 'artesanos_facturas_pendientes';
const SYNC_INTERVAL = 30000; // 30 segundos


// GESTION DE LA COLA
function obtenerCola() {
    try {
        return JSON.parse(localStorage.getItem(COLA_KEY) || '[]');
    } catch (e) {
        console.error('Error leyendo cola:', e);
        return [];
    }
}

function guardarCola(cola) {
    try {
        localStorage.setItem(COLA_KEY, JSON.stringify(cola));
        actualizarBadgeBanner();
    } catch (e) {
        console.error('Error guardando cola:', e);
        mostrarBanner('Error: no se pudo guardar localmente', 'offline');
    }
}

function agregarALaCola(factura) {
    const cola = obtenerCola();
    cola.push({
        ...factura,
        _id_local: Date.now() + Math.random(),
        _fecha_guardado: new Date().toISOString()
    });
    guardarCola(cola);
    return cola.length;
}

function eliminarDeLaCola(idLocal) {
    const cola = obtenerCola().filter(f => f._id_local !== idLocal);
    guardarCola(cola);
    return cola.length;
}


// DETECCION DE CONEXION
function hayConexion() {
    return navigator.onLine;
}


// BANNER
function mostrarBanner(mensaje, tipo = 'offline', contador = null) {
    const banner = document.getElementById('banner-conexion');
    const texto = document.getElementById('banner-texto');
    const badge = document.getElementById('banner-contador');
    const icono = banner.querySelector('i');

    if (!banner) return;

    banner.style.display = 'flex';
    banner.className = 'banner-conexion ' + tipo;
    texto.textContent = mensaje;

    // Iconos por tipo
    if (tipo === 'online') {
        icono.className = 'bi bi-check-circle-fill';
    } else if (tipo === 'sincronizando') {
        icono.className = 'bi bi-arrow-repeat';
    } else {
        icono.className = 'bi bi-wifi-off';
    }

    // Contador
    if (contador !== null && contador > 0) {
        badge.textContent = contador;
        badge.style.display = 'inline-block';
    } else {
        badge.style.display = 'none';
    }

    document.body.classList.add('tiene-banner');
}

function ocultarBanner() {
    const banner = document.getElementById('banner-conexion');
    if (banner) {
        banner.style.display = 'none';
        document.body.classList.remove('tiene-banner');
    }
}

function actualizarBadgeBanner() {
    const cola = obtenerCola();
    const banner = document.getElementById('banner-conexion');

    if (cola.length === 0) {
        if (hayConexion()) {
            ocultarBanner();
        } else {
            mostrarBanner('Sin conexion', 'offline');
        }
        return;
    }

    if (hayConexion()) {
        mostrarBanner(`Sincronizando ${cola.length} factura(s)...`, 'sincronizando', cola.length);
    } else {
        mostrarBanner(`Sin conexion - ${cola.length} factura(s) en cola`, 'offline', cola.length);
    }
}


// SINCRONIZACION
let _sincronizando = false;

async function sincronizarCola() {
    if (_sincronizando) return;
    if (!hayConexion()) return;

    const cola = obtenerCola();
    if (!cola.length) {
        actualizarBadgeBanner();
        return;
    }

    _sincronizando = true;
    let enviadas = 0;
    let fallidas = 0;

    for (const factura of [...cola]) {
        try {
            // Quitar campos locales antes de enviar
            const datosEnviar = { ...factura };
            delete datosEnviar._id_local;
            delete datosEnviar._fecha_guardado;

            const resp = await fetch('/api/facturas/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify(datosEnviar)
            });

            const data = await resp.json();

            if (data.success) {
                eliminarDeLaCola(factura._id_local);
                enviadas++;
            } else {
                // Error del servidor (ej: duplicada) → sacar de la cola y avisar
                console.warn('Factura rechazada:', data.error);
                eliminarDeLaCola(factura._id_local);
                fallidas++;
            }
        } catch (err) {
            // Error de red → mantener en cola
            console.error('Error enviando factura:', err);
            break; // Detener el bucle, seguimos sin conexion
        }
    }

    _sincronizando = false;

    // Actualizar UI
    const colaFinal = obtenerCola();
    if (colaFinal.length === 0) {
        if (enviadas > 0) {
            mostrarBanner(`Sincronizado: ${enviadas} factura(s) enviada(s)`, 'online');
            setTimeout(ocultarBanner, 3000);
        } else {
            ocultarBanner();
        }
    } else {
        actualizarBadgeBanner();
    }

    // Recargar listado si estamos en la pagina de facturas
    if (typeof cargarFacturas === 'function' && document.getElementById('facturas-list')) {
        if (enviadas > 0) cargarFacturas();
    }

    return { enviadas, fallidas };
}


// EVENTOS DE CONEXION
window.addEventListener('online', () => {
    console.log('Conexion recuperada');
    sincronizarCola();
});

window.addEventListener('offline', () => {
    console.log('Sin conexion');
    actualizarBadgeBanner();
});


// INICIALIZACION
document.addEventListener('DOMContentLoaded', () => {
    // Actualizar estado al cargar
    setTimeout(() => {
        actualizarBadgeBanner();
        if (hayConexion()) {
            sincronizarCola();
        }
    }, 1000);

    // Sincronizar cada 30 segundos
    setInterval(() => {
        if (hayConexion()) {
            const cola = obtenerCola();
            if (cola.length > 0) {
                sincronizarCola();
            }
        }
    }, SYNC_INTERVAL);
});
