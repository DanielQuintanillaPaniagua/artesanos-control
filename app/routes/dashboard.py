from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from datetime import date, timedelta

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


def _linea_semana(facturas):
    hoy = date.today()
    dias = [(hoy - timedelta(days=i)) for i in range(6, -1, -1)]
    conteo = {d: 0 for d in dias}
    for f in facturas:
        if f.fecha in conteo:
            conteo[f.fecha] += 1

    max_val = max(conteo.values()) if any(conteo.values()) else 1
    x_ini, x_fin = 10, 490
    y_ini, y_fin = 145, 20
    paso_x = (x_fin - x_ini) / 6

    puntos_svg = []
    circulos = []
    for i, d in enumerate(dias):
        val = conteo[d]
        x = x_ini + (paso_x * i)
        y = y_ini - ((val / max_val) * (y_ini - y_fin))
        puntos_svg.append(f"{x:.1f},{y:.1f}")
        circulos.append({'x': f"{x:.1f}", 'y': f"{y:.1f}"})

    return {
        'linea_puntos': ' '.join(puntos_svg),
        'linea_circulos': circulos,
    }


@bp.route('/')
@login_required
def index():
    sucursal_id_filtro = request.args.get('sucursal', type=int)
    hoy = date.today()
    inicio_mes = hoy.replace(day=1)

    base = Factura.query.filter(Factura.fecha >= inicio_mes)

    # ------- Empleado: solo su sucursal -------
    if current_user.is_empleado():
        if current_user.sucursal_id:
            base = base.filter(Factura.sucursal_id == current_user.sucursal_id)
        else:
            base = base.filter(Factura.id == -1)

        metricas = _metricas_query(base)
        metricas['por_categoria'] = _por_categoria(metricas['facturas'])
        metricas['donut_gradient'] = _gradient_donut(metricas['por_categoria'])
        metricas.update(_linea_semana(metricas['facturas']))

        return render_template(
            'dashboard.html',
            metricas=metricas,
            sucursal_filtro=None,
            sucursales=[],
        )

    # ------- Owner -------
    if sucursal_id_filtro:
        base = base.filter(Factura.sucursal_id == sucursal_id_filtro)

    metricas = _metricas_query(base)
    metricas['por_categoria'] = _por_categoria(metricas['facturas'])
    metricas['donut_gradient'] = _gradient_donut(metricas['por_categoria'])
    metricas.update(_linea_semana(metricas['facturas']))

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
    )
