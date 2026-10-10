// ============================================
// CHAT ENTRE SUCURSALES
// ============================================

let _conversacionActual = null;
let _pollingInterval = null;
let _conversaciones = [];

const chatList = document.getElementById('chat-list');
const chatMessages = document.getElementById('chat-messages');
const chatTitle = document.getElementById('chat-title');
const chatSubtitle = document.getElementById('chat-subtitle');
const chatInput = document.getElementById('chat-input');
const chatForm = document.getElementById('chat-form');
const chatSearch = document.getElementById('chat-search');


// ============================================
// HELPERS
// ============================================
function iniciales(nombre) {
    if (!nombre) return '?';
    const partes = nombre.trim().split(' ');
    if (partes.length >= 2) {
        return (partes[0][0] + partes[1][0]).toUpperCase();
    }
    return nombre.substring(0, 2).toUpperCase();
}

function formatearHora(isoString) {
    if (!isoString) return '';
    const d = new Date(isoString);
    const ahora = new Date();
    const mismoDia = d.toDateString() === ahora.toDateString();

    if (mismoDia) {
        return d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    }
    return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit' });
}

function formatearFechaSeparador(isoString) {
    const d = new Date(isoString);
    const ahora = new Date();
    const ayer = new Date(ahora);
    ayer.setDate(ayer.getDate() - 1);

    if (d.toDateString() === ahora.toDateString()) return 'Hoy';
    if (d.toDateString() === ayer.toDateString()) return 'Ayer';
    return d.toLocaleDateString('es-ES', { day: '2-digit', month: 'long', year: 'numeric' });
}


// ============================================
// CARGAR CONVERSACIONES
// ============================================
async function cargarConversaciones() {
    try {
        const resp = await fetch('/api/chat/conversaciones', { credentials: 'same-origin' });
        const data = await resp.json();

        if (!data.ok) {
            chatList.innerHTML = `<li class="chat-list-empty">Error: ${data.error}</li>`;
            return;
        }

        _conversaciones = data.conversaciones || [];
        renderizarConversaciones();
    } catch (err) {
        console.error('Error cargando conversaciones:', err);
        chatList.innerHTML = '<li class="chat-list-empty">Error de conexion</li>';
    }
}

function renderizarConversaciones() {
    const filtro = (chatSearch.value || '').toLowerCase();
    const filtradas = _conversaciones.filter(c =>
        c.nombre.toLowerCase().includes(filtro)
    );

    if (!filtradas.length) {
        chatList.innerHTML = '<li class="chat-list-empty">Sin conversaciones</li>';
        return;
    }

    chatList.innerHTML = filtradas.map(c => `
        <li class="chat-item ${_conversacionActual === c.id ? 'active' : ''}"
            data-id="${c.id}"
            onclick="seleccionarConversacion(${c.id})">
            <div class="chat-item-avatar ${c.tipo === 'general' ? 'general' : ''}">
                ${iniciales(c.nombre)}
            </div>
            <div class="chat-item-body">
                <div class="chat-item-title">
                    <span>${c.nombre}</span>
                    ${c.no_leidos > 0 ? `<span class="chat-item-badge">${c.no_leidos}</span>` : ''}
                </div>
                <div class="chat-item-preview">
                    ${c.ultimo_mensaje_usuario ? c.ultimo_mensaje_usuario + ': ' : ''}${c.ultimo_mensaje}
                </div>
            </div>
        </li>
    `).join('');
}


// ============================================
// SELECCIONAR CONVERSACION
// ============================================
function seleccionarConversacion(convId) {
    _conversacionActual = convId;

    const conv = _conversaciones.find(c => c.id === convId);
    if (!conv) return;

    // Actualizar header
    chatTitle.textContent = conv.nombre;
    chatSubtitle.textContent = conv.tipo === 'general'
        ? 'Canal general (todos)'
        : `Sucursal: ${conv.sucursal_nombre || conv.nombre}`;

    // Habilitar input
    chatInput.disabled = false;
    chatForm.querySelector('button').disabled = false;
    chatInput.focus();

    // Renderizar
    renderizarConversaciones();
    cargarMensajes();

    // Marcar como leido
    fetch(`/api/chat/conversaciones/${convId}/marcar-leido`, {
        method: 'POST',
        credentials: 'same-origin'
    }).then(() => {
        // Actualizar el contador de no leidos localmente
        const c = _conversaciones.find(x => x.id === convId);
        if (c) c.no_leidos = 0;
        renderizarConversaciones();
    });
}


// ============================================
// CARGAR MENSAJES
// ============================================
async function cargarMensajes() {
    if (!_conversacionActual) return;

    try {
        const resp = await fetch(`/api/chat/conversaciones/${_conversacionActual}/mensajes`, {
            credentials: 'same-origin'
        });
        const data = await resp.json();

        if (!data.ok) {
            chatMessages.innerHTML = `<div class="chat-empty"><p>Error: ${data.error}</p></div>`;
            return;
        }

        renderizarMensajes(data.mensajes || []);
    } catch (err) {
        console.error('Error cargando mensajes:', err);
    }
}

function renderizarMensajes(mensajes) {
    if (!mensajes.length) {
        chatMessages.innerHTML = `
            <div class="chat-empty">
                <i class="bi bi-chat-dots fs-1"></i>
                <p>No hay mensajes todavia. Escribi el primero.</p>
            </div>
        `;
        return;
    }

    let html = '';
    let fechaAnterior = null;

    mensajes.forEach(m => {
        const fecha = m.created_at ? new Date(m.created_at) : null;
        const fechaStr = fecha ? fecha.toDateString() : null;

        // Separador de fecha
        if (fechaStr && fechaStr !== fechaAnterior) {
            html += `<div class="chat-date-separator">${formatearFechaSeparador(m.created_at)}</div>`;
            fechaAnterior = fechaStr;
        }

        const esMio = m.usuario_id === window.CURRENT_USER_ID;
        html += `
            <div class="chat-msg ${esMio ? 'mine' : ''}">
                <div class="chat-msg-avatar">${iniciales(m.usuario_nombre)}</div>
                <div class="chat-msg-body">
                    ${!esMio ? `<div class="chat-msg-author">${m.usuario_nombre}</div>` : ''}
                    <div class="chat-msg-bubble">${escapeHtml(m.contenido)}</div>
                    <div class="chat-msg-time">${formatearHora(m.created_at)}</div>
                </div>
            </div>
        `;
    });

    chatMessages.innerHTML = html;
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function escapeHtml(texto) {
    const div = document.createElement('div');
    div.textContent = texto;
    return div.innerHTML;
}


// ============================================
// ENVIAR MENSAJE
// ============================================
async function enviarMensaje(e) {
    e.preventDefault();
    if (!_conversacionActual) return;

    const contenido = chatInput.value.trim();
    if (!contenido) return;

    chatInput.disabled = true;
    chatForm.querySelector('button').disabled = true;

    try {
        const resp = await fetch(`/api/chat/conversaciones/${_conversacionActual}/mensajes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ contenido })
        });
        const data = await resp.json();

        if (data.ok) {
            chatInput.value = '';
            await cargarMensajes();
            // Actualizar la lista (ultimo mensaje)
            await cargarConversaciones();
        } else {
            alert('Error: ' + data.error);
        }
    } catch (err) {
        console.error('Error enviando:', err);
        alert('Error de conexion');
    } finally {
        chatInput.disabled = false;
        chatForm.querySelector('button').disabled = false;
        chatInput.focus();
    }
}


// ============================================
// POLLING (cada 10 segundos)
// ============================================
function iniciarPolling() {
    if (_pollingInterval) clearInterval(_pollingInterval);
    _pollingInterval = setInterval(async () => {
        if (_conversacionActual) {
            await cargarMensajes();
        }
        await cargarConversaciones();
    }, 10000);
}
// ============================================
// MODAL: NUEVO CHAT DIRECTO
// ============================================
const modalNuevoChat = document.getElementById('modalNuevoChat');
const chatSupervisoresList = document.getElementById('chatSupervisoresList');

async function abrirModalNuevoChat() {
    if (!modalNuevoChat) return;

    chatSupervisoresList.innerHTML = '<li class="text-muted text-center py-3">Cargando...</li>';
    modalNuevoChat.showModal();

    try {
        const resp = await fetch('/api/chat/supervisores', { credentials: 'same-origin' });
        const data = await resp.json();

        if (!data.ok) {
            chatSupervisoresList.innerHTML = `<li class="text-danger text-center py-3">Error: ${data.error}</li>`;
            return;
        }

        if (!data.supervisores.length) {
            chatSupervisoresList.innerHTML = '<li class="text-muted text-center py-3">No hay otros supervisores</li>';
            return;
        }

        chatSupervisoresList.innerHTML = data.supervisores.map(s => `
            <li class="chat-supervisor-item" onclick="abrirChatDirecto(${s.id})">
                <div class="chat-supervisor-avatar">${iniciales(s.nombre)}</div>
                <div>
                    <div class="chat-supervisor-name">${s.nombre}</div>
                    <div class="chat-supervisor-sucursal">${s.sucursal || 'Sin sucursal'}</div>
                </div>
            </li>
        `).join('');
    } catch (err) {
        console.error('Error:', err);
        chatSupervisoresList.innerHTML = '<li class="text-danger text-center py-3">Error de conexion</li>';
    }
}

function cerrarModalNuevoChat() {
    if (modalNuevoChat) modalNuevoChat.close();
}

async function abrirChatDirecto(userId) {
    try {
        const resp = await fetch(`/api/chat/directo/${userId}`, {
            method: 'POST',
            credentials: 'same-origin'
        });
        const data = await resp.json();

        if (!data.ok) {
            alert('Error: ' + data.error);
            return;
        }

        cerrarModalNuevoChat();

        // Recargar conversaciones y seleccionar la nueva
        await cargarConversaciones();
        seleccionarConversacion(data.conversacion_id);
    } catch (err) {
        console.error('Error:', err);
        alert('Error de conexion');
    }
}

// Cerrar modal al hacer clic afuera
if (modalNuevoChat) {
    modalNuevoChat.addEventListener('click', (e) => {
        if (e.target === modalNuevoChat) cerrarModalNuevoChat();
    });
}


// ============================================
// INICIALIZACION
// ============================================
document.addEventListener('DOMContentLoaded', () => {
    if (!chatList) return;

    // Obtener ID del usuario desde un atributo del body
    window.CURRENT_USER_ID = parseInt(document.body.dataset.userId || '0');

    cargarConversaciones();
    iniciarPolling();

    // Buscador
    if (chatSearch) {
        chatSearch.addEventListener('input', renderizarConversaciones);
    }
});
