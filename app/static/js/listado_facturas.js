// ============================================
// Listado de Facturas - Filtros rapidos de fecha
// ============================================

function _fmt(d) {
    // YYYY-MM-DD
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

function _aplicar(desde, hasta) {
    document.getElementById('filtro-desde').value = desde;
    document.getElementById('filtro-hasta').value = hasta;
    document.getElementById('filtrosForm').submit();
}

function presetHoy() {
    const hoy = new Date();
    _aplicar(_fmt(hoy), _fmt(hoy));
}

function presetEstaSemana() {
    // Lunes a domingo de la semana actual
    const hoy = new Date();
    const dia = hoy.getDay(); // 0 = domingo, 1 = lunes...
    const offsetLunes = (dia === 0 ? -6 : 1 - dia);
    const lunes = new Date(hoy);
    lunes.setDate(hoy.getDate() + offsetLunes);
    const domingo = new Date(lunes);
    domingo.setDate(lunes.getDate() + 6);
    _aplicar(_fmt(lunes), _fmt(domingo));
}

function presetEsteMes() {
    const hoy = new Date();
    const primero = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
    const ultimo = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0);
    _aplicar(_fmt(primero), _fmt(ultimo));
}

function presetMesAnterior() {
    const hoy = new Date();
    const primero = new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1);
    const ultimo = new Date(hoy.getFullYear(), hoy.getMonth(), 0);
    _aplicar(_fmt(primero), _fmt(ultimo));
}

function presetUltimos30() {
    const hoy = new Date();
    const hace30 = new Date();
    hace30.setDate(hoy.getDate() - 30);
    _aplicar(_fmt(hace30), _fmt(hoy));
}
