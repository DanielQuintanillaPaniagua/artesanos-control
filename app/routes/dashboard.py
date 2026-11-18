from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from datetime import date, datetime, timedelta, timezone

from app import db
from app.models.factura import Factura
from app.models.categoria import Categoria
from app.models.sucursal import Sucursal

bp = Blueprint('dashboard', __name__)


def _metricas_query(query):
    facturas = query.all()
    total_facturas = len(facturas)
    total_monto = sum((f.total_factura or 0) for f in facturas)
    validadas = sum(1 for f in facturas if f.estado == 'Validada')
    observadas = sum(1 for f in facturas if f.estado == 'Observada')
    porcentaje = (validadas / total_facturas * 100) if total_facturas else 0
    return {
        'total_facturas': total_facturas,
        'total_monto': total_monto,
        'validadas': validadas,
        'observadas': observadas,
        'porcentaje': round(porcentaje, 1),
        'facturas': facturas,
    }


def _por_categoria(facturas):
    colores = ['#1f6b45', '#2f6f8f', '#c9963c', '#7a5fc9', '#6b7688']

    acumulado = {}
    for f in facturas:
        for d in f.detalles:
            cid = d.categoria_id
            acumulado[cid] = acumulado.get(cid, 0) + (d.monto or 0)

    ordenado = sorted(acumulado.items(), key=lambda x: x[1], reverse=True)[:5]
    total = sum(m for _, m in ordenado) or 1

    ids = [cid for cid, _ in ordenado]
    categorias = {c.id: c.nombre for c in Categoria.query.filter(Categoria.id.in_(ids)).all()} if ids else {}

    resultado = []
    for i, (cid, monto) in enumerate(ordenado):
        resultado.append({
            'nombre': categorias.get(cid, f'Cat {cid}'),
            'monto': monto,
            'porcentaje': (monto / total) * 100,
            'color': colores[i % len(colores)],
        })
    return resultado


def _gradient_donut(por_categoria):
    if not por_categoria:
        return '#e5e9e6'
    partes = []
    acumulado = 0
    for c in por_categoria:
        inicio = acumulado
        acumulado += c['porcentaje']
        partes.append(f"{c['color']} {inicio:.2f}% {acumulado:.2f}%")
    return f"conic-gradient({', '.join(partes)})"


# El Salvador es UTC-6 todo el año (sin horario de verano). Asi "hoy" no se adelanta
# un dia despues de las 6 pm cuando el servidor esta en UTC.
ZONA_SV = timezone(timedelta(hours=-6))


def _hoy():
    return datetime.now(ZONA_SV).date()


PERIODOS = {
    'hoy': 'Hoy',
    'ayer': 'Ayer',
    'semana': 'Últimos 7 días',
    'mes': 'Este mes',
}
DIAS_ES = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']


def _rango_periodo(periodo):
    """Devuelve (desde, hasta) segun el periodo elegido para las graficas."""
    hoy = _hoy()
    if periodo == 'hoy':
        return hoy, hoy
    if periodo == 'ayer':
        ayer = hoy - timedelta(days=1)
        return ayer, ayer
    if periodo == 'semana':
        return hoy - timedelta(days=6), hoy
    return hoy.replace(day=1), hoy


def _facturas_grafico(desde, hasta, sucursal_id):
    query = Factura.query.filter(Factura.fecha >= desde, Factura.fecha <= hasta)
    if sucursal_id:
        query = query.filter(Factura.sucursal_id == sucursal_id)
    return query.all()


def _linea_periodo(facturas, desde, hasta):
    """Datos de la grafica 'Facturas por dia' para el rango elegido."""
    dias = [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]

    if len(dias) < 2:
        return {
            'linea_puntos': None,
            'linea_circulos': [],
            'linea_etiquetas': [],
            'linea_mensaje': 'Con un solo día no hay línea que mostrar. Elige "Últimos 7 días" o "Este mes".',
        }

    conteo = {d: 0 for d in dias}
    for f in facturas:
        if f.fecha in conteo:
            conteo[f.fecha] += 1

    max_val = max(conteo.values()) if any(conteo.values()) else 1
    ancho = 560
    x_ini, x_fin = 10, 550
    y_ini, y_fin = 145, 20
    paso_x = (x_fin - x_ini) / (len(dias) - 1)

    puntos_svg = []
    circulos = []
    etiquetas = []
    for i, d in enumerate(dias):
        val = conteo[d]
        x = x_ini + (paso_x * i)
        y = y_ini - ((val / max_val) * (y_ini - y_fin))
        puntos_svg.append(f"{x:.1f},{y:.1f}")
        circulos.append({'x': f"{x:.1f}", 'y': f"{y:.1f}", 'titulo': f"{d.strftime('%d/%m')}: {val}"})

        if len(dias) <= 7:
            texto = DIAS_ES[d.weekday()]
        elif i % 5 == 0 or (i == len(dias) - 1 and (len(dias) - 1) % 5 >= 3):
            texto = str(d.day)
        else:
            texto = ''
        if texto:
            etiquetas.append({'texto': texto, 'left': f"{(x / ancho) * 100:.2f}"})

    return {
        'linea_puntos': ' '.join(puntos_svg),
        'linea_circulos': circulos,
        'linea_etiquetas': etiquetas,
        'linea_mensaje': None,
    }


@bp.route('/')
@login_required
def index():
    sucursal_id_filtro = request.args.get('sucursal', type=int)
    hoy = _hoy()
    inicio_mes = hoy.replace(day=1)

    # Periodo de las graficas (Ayer / Ultimos 7 dias / Este mes)
    periodo = request.args.get('periodo', 'mes')
    if periodo not in PERIODOS:
        periodo = 'mes'
    desde_graf, hasta_graf = _rango_periodo(periodo)

    base = Factura.query.filter(Factura.fecha >= inicio_mes)

    # ------- Empleado o supervisor: solo su sucursal -------
    if current_user.is_empleado() or current_user.is_supervisor():
        if current_user.sucursal_id:
            base = base.filter(Factura.sucursal_id == current_user.sucursal_id)
        else:
            base = base.filter(Factura.id == -1)

        metricas = _metricas_query(base)

        # Graficas segun el periodo elegido (solo su sucursal)
        facturas_graf = _facturas_grafico(desde_graf, hasta_graf, current_user.sucursal_id or -1)
        metricas['por_categoria'] = _por_categoria(facturas_graf)
        metricas['donut_gradient'] = _gradient_donut(metricas['por_categoria'])
        metricas.update(_linea_periodo(facturas_graf, desde_graf, hasta_graf))

        return render_template(
            'dashboard.html',
            metricas=metricas,
            sucursal_filtro=None,
            sucursales=[],
            periodo=periodo,
            periodos=PERIODOS,
        )

    # ------- Owner -------
    if sucursal_id_filtro:
        base = base.filter(Factura.sucursal_id == sucursal_id_filtro)

    metricas = _metricas_query(base)

    # Graficas segun el periodo elegido
    facturas_graf = _facturas_grafico(desde_graf, hasta_graf, sucursal_id_filtro)
    metricas['por_categoria'] = _por_categoria(facturas_graf)
    metricas['donut_gradient'] = _gradient_donut(metricas['por_categoria'])
    metricas.update(_linea_periodo(facturas_graf, desde_graf, hasta_graf))

    # Desglose por sucursal (siempre las 3, sin importar el filtro)
    base_sin_filtro = Factura.query.filter(Factura.fecha >= inicio_mes).all()
    por_sucursal = []
    for s in Sucursal.query.order_by(Sucursal.nombre).all():
        f_suc = [f for f in base_sin_filtro if f.sucursal_id == s.id]
        if not f_suc:
            por_sucursal.append({
                'nombre': s.nombre,
                'total_facturas': 0,
                'total_monto': 0,
                'validadas': 0,
                'observadas': 0,
                'porcentaje': 0,
            })
            continue
        val = sum(1 for f in f_suc if f.estado == 'Validada')
        obs = sum(1 for f in f_suc if f.estado == 'Observada')
        tot = len(f_suc)
        por_sucursal.append({
            'nombre': s.nombre,
            'total_facturas': tot,
            'total_monto': sum((f.total_factura or 0) for f in f_suc),
            'validadas': val,
            'observadas': obs,
            'porcentaje': round((val / tot * 100) if tot else 0, 1),
        })

    metricas['por_sucursal'] = por_sucursal
    sucursales = Sucursal.query.order_by(Sucursal.nombre).all()

    return render_template(
        'dashboard.html',
        metricas=metricas,
        sucursal_filtro=sucursal_id_filtro,
        sucursales=sucursales,
        periodo=periodo,
        periodos=PERIODOS,
    )