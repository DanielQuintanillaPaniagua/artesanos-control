from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from datetime import date, timedelta

from app import db
from app.models.factura import Factura
from app.models.categoria import Categoria
from app.models.sucursal import Sucursal
from app.models.proveedor import Proveedor


bp = Blueprint('dashboard_api', __name__, url_prefix='/api/dashboard')


# ============================================================
# HELPERS
# ============================================================
def _rango(desde=None, hasta=None):
    """Devuelve (desde, hasta) como fechas. Default: mes actual."""
    hoy = date.today()
    if not desde:
        desde = hoy.replace(day=1)
    else:
        try:
            desde = date.fromisoformat(desde)
        except (ValueError, TypeError):
            desde = hoy.replace(day=1)

    if not hasta:
        hasta = hoy
    else:
        try:
            hasta = date.fromisoformat(hasta)
        except (ValueError, TypeError):
            hasta = hoy

    return desde, hasta


def _query_base():
    """Query base filtrada por rol del usuario.

    Owner: ve todas
    Supervisor: solo su sucursal
    Empleado: solo su sucursal
    """
    query = Factura.query

    # Todos los que NO son owner ven solo su sucursal
    if not current_user.is_owner():
        if current_user.sucursal_id:
            query = query.filter(Factura.sucursal_id == current_user.sucursal_id)
        else:
            query = query.filter(Factura.id == -1)

    return query


# ============================================================
# GET /api/dashboard/stats
# Metricas principales del dashboard
# ============================================================
@bp.route('/stats', methods=['GET'])
@login_required
def stats():
    """Devuelve las metricas principales del dashboard."""
    try:
        desde_str = request.args.get('desde')
        hasta_str = request.args.get('hasta')
        sucursal_id = request.args.get('sucursal', type=int)

        desde, hasta = _rango(desde_str, hasta_str)

        query = _query_base().filter(
            Factura.fecha >= desde,
            Factura.fecha <= hasta,
        )

        if current_user.is_owner() and sucursal_id:
            query = query.filter(Factura.sucursal_id == sucursal_id)

        facturas = query.all()

        total_facturas = len(facturas)
        total_monto = sum((f.total_factura or 0) for f in facturas)
        validadas = sum(1 for f in facturas if f.estado == 'Validada')
        observadas = sum(1 for f in facturas if f.estado == 'Observada')
        porcentaje = round((validadas / total_facturas * 100) if total_facturas else 0, 1)

        return jsonify({
            'success': True,
            'periodo': {
                'desde': desde.isoformat(),
                'hasta': hasta.isoformat(),
            },
            'stats': {
                'total_facturas': total_facturas,
                'total_monto': round(total_monto, 2),
                'validadas': validadas,
                'observadas': observadas,
                'porcentaje_validacion': porcentaje,
            }
        })
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# GET /api/dashboard/facturas-por-sucursal
# Tabla comparativa de desempeno por sucursal
# ============================================================
@bp.route('/facturas-por-sucursal', methods=['GET'])
@login_required
def facturas_por_sucursal():
    """Desglose por sucursal del periodo."""
    try:
        desde_str = request.args.get('desde')
        hasta_str = request.args.get('hasta')
        desde, hasta = _rango(desde_str, hasta_str)

        facturas = Factura.query.filter(
            Factura.fecha >= desde,
            Factura.fecha <= hasta,
        ).all()

        resultado = []
        for s in Sucursal.query.order_by(Sucursal.nombre).all():
            f_suc = [f for f in facturas if f.sucursal_id == s.id]
            total = len(f_suc)
            val = sum(1 for f in f_suc if f.estado == 'Validada')
            obs = sum(1 for f in f_suc if f.estado == 'Observada')
            monto = sum((f.total_factura or 0) for f in f_suc)

            resultado.append({
                'sucursal_id': s.id,
                'sucursal': s.nombre,
                'estado': s.estado,
                'total_facturas': total,
                'total_monto': round(monto, 2),
                'validadas': val,
                'observadas': obs,
                'porcentaje_validacion': round((val / total * 100) if total else 0, 1),
            })

        return jsonify({
            'success': True,
            'periodo': {'desde': desde.isoformat(), 'hasta': hasta.isoformat()},
            'sucursales': resultado,
            'total_sucursales': len(resultado),
        })
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# GET /api/dashboard/facturas-por-categoria
# Desglose por categoria (para el donut)
# ============================================================
@bp.route('/facturas-por-categoria', methods=['GET'])
@login_required
def facturas_por_categoria():
    """Desglose por categoria del periodo."""
    try:
        desde_str = request.args.get('desde')
        hasta_str = request.args.get('hasta')
        limite = request.args.get('limite', 10, type=int)
        desde, hasta = _rango(desde_str, hasta_str)

        query = _query_base().filter(
            Factura.fecha >= desde,
            Factura.fecha <= hasta,
        )
        facturas = query.all()

        acumulado = {}
        for f in facturas:
            for d in f.detalles:
                cid = d.categoria_id
                acumulado[cid] = acumulado.get(cid, 0) + (d.monto or 0)

        ordenado = sorted(acumulado.items(), key=lambda x: x[1], reverse=True)[:limite]
        total = sum(m for _, m in ordenado) or 1

        ids = [cid for cid, _ in ordenado]
        cats = {c.id: c.nombre for c in Categoria.query.filter(Categoria.id.in_(ids)).all()} if ids else {}

        resultado = []
        for cid, monto in ordenado:
            resultado.append({
                'categoria_id': cid,
                'categoria': cats.get(cid, f'Cat {cid}'),
                'monto': round(monto, 2),
                'porcentaje': round((monto / total) * 100, 2),
            })

        return jsonify({
            'success': True,
            'periodo': {'desde': desde.isoformat(), 'hasta': hasta.isoformat()},
            'categorias': resultado,
            'total_categorias': len(resultado),
        })
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# GET /api/dashboard/facturas-por-dia
# Serie temporal de facturas (para grafica de linea)
# ============================================================
@bp.route('/facturas-por-dia', methods=['GET'])
@login_required
def facturas_por_dia():
    """Facturas agrupadas por dia en los ultimos N dias."""
    try:
        dias = request.args.get('dias', 7, type=int)
        if dias < 1 or dias > 90:
            dias = 7

        hoy = date.today()
        inicio = hoy - timedelta(days=dias - 1)

        query = _query_base().filter(Factura.fecha >= inicio)
        facturas = query.all()

        # Agrupar por dia
        conteo = {}
        monto = {}
        for i in range(dias):
            d = inicio + timedelta(days=i)
            conteo[d] = 0
            monto[d] = 0

        for f in facturas:
            if f.fecha in conteo:
                conteo[f.fecha] += 1
                monto[f.fecha] += (f.total_factura or 0)

        resultado = []
        for d in sorted(conteo.keys()):
            resultado.append({
                'fecha': d.isoformat(),
                'dia_semana': d.strftime('%a'),
                'total_facturas': conteo[d],
                'total_monto': round(monto[d], 2),
            })

        return jsonify({
            'success': True,
            'dias': dias,
            'desde': inicio.isoformat(),
            'hasta': hoy.isoformat(),
            'serie': resultado,
        })
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# GET /api/dashboard/top-proveedores
# Top N proveedores por monto
# ============================================================
@bp.route('/top-proveedores', methods=['GET'])
@login_required
def top_proveedores():
    """Proveedores con mayor monto del periodo."""
    try:
        desde_str = request.args.get('desde')
        hasta_str = request.args.get('hasta')
        limite = request.args.get('limite', 5, type=int)
        desde, hasta = _rango(desde_str, hasta_str)

        query = _query_base().filter(
            Factura.fecha >= desde,
            Factura.fecha <= hasta,
        )
        facturas = query.all()

        acumulado = {}
        for f in facturas:
            if f.proveedor:
                nombre = f.proveedor.nombre
                acumulado[nombre] = acumulado.get(nombre, 0) + (f.total_factura or 0)

        ordenado = sorted(acumulado.items(), key=lambda x: x[1], reverse=True)[:limite]
        total = sum(m for _, m in ordenado) or 1

        resultado = []
        for nombre, monto in ordenado:
            resultado.append({
                'proveedor': nombre,
                'monto': round(monto, 2),
                'porcentaje': round((monto / total) * 100, 2),
            })

        return jsonify({
            'success': True,
            'periodo': {'desde': desde.isoformat(), 'hasta': hasta.isoformat()},
            'proveedores': resultado,
        })
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# GET /api/dashboard/alerts
# Alertas activas (facturas observadas)
# ============================================================
@bp.route('/alerts', methods=['GET'])
@login_required
def alerts():
    """Devuelve las alertas activas del negocio."""
    try:
        desde_str = request.args.get('desde')
        hasta_str = request.args.get('hasta')
        desde, hasta = _rango(desde_str, hasta_str)

        query = _query_base().filter(
            Factura.fecha >= desde,
            Factura.fecha <= hasta,
            Factura.estado == 'Observada',
        )
        observadas = query.order_by(Factura.fecha.desc()).limit(20).all()

        alertas = []
        for f in observadas:
            alertas.append({
                'tipo': 'factura_observada',
                'severidad': 'alta',
                'factura_id': f.id,
                'numero_factura': f.numero_factura,
                'sucursal': f.sucursal.nombre if f.sucursal else None,
                'proveedor': f.proveedor.nombre if f.proveedor else None,
                'total': round(f.total_factura or 0, 2),
                'fecha': f.fecha.isoformat() if f.fecha else None,
                'observacion': f.observacion or 'Sin detalle',
            })

        return jsonify({
            'success': True,
            'alertas': alertas,
            'total': len(alertas),
        })
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# GET /api/dashboard/resumen
# Endpoint TODO EN UNO (para dashboards externos)
# ============================================================
@bp.route('/resumen', methods=['GET'])
@login_required
def resumen():
    """Endpoint todo-en-uno con todos los datos del dashboard."""
    try:
        desde_str = request.args.get('desde')
        hasta_str = request.args.get('hasta')
        desde, hasta = _rango(desde_str, hasta_str)

        query = _query_base().filter(
            Factura.fecha >= desde,
            Factura.fecha <= hasta,
        )
        facturas = query.all()

        # Stats
        total = len(facturas)
        val = sum(1 for f in facturas if f.estado == 'Validada')
        obs = sum(1 for f in facturas if f.estado == 'Observada')
        monto = sum((f.total_factura or 0) for f in facturas)

        # Por sucursal
        por_sucursal = []
        for s in Sucursal.query.order_by(Sucursal.nombre).all():
            f_suc = [f for f in facturas if f.sucursal_id == s.id]
            por_sucursal.append({
                'sucursal': s.nombre,
                'total_facturas': len(f_suc),
                'total_monto': round(sum((f.total_factura or 0) for f in f_suc), 2),
            })

        # Por categoria
        acum = {}
        for f in facturas:
            for d in f.detalles:
                acum[d.categoria_id] = acum.get(d.categoria_id, 0) + (d.monto or 0)

        top_cats = sorted(acum.items(), key=lambda x: x[1], reverse=True)[:5]
        ids = [c for c, _ in top_cats]
        cats = {c.id: c.nombre for c in Categoria.query.filter(Categoria.id.in_(ids)).all()} if ids else {}
        por_categoria = [
            {'categoria': cats.get(c, f'Cat {c}'), 'monto': round(m, 2)}
            for c, m in top_cats
        ]

        return jsonify({
            'success': True,
            'periodo': {'desde': desde.isoformat(), 'hasta': hasta.isoformat()},
            'resumen': {
                'total_facturas': total,
                'total_monto': round(monto, 2),
                'validadas': val,
                'observadas': obs,
            },
            'por_sucursal': por_sucursal,
            'top_categorias': por_categoria,
        })
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500
