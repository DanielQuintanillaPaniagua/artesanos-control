from flask import Blueprint, jsonify, request, send_file, current_app
from flask_login import login_required, current_user
from datetime import date, datetime, timedelta
from io import BytesIO

from app import db
from app.models.factura import Factura
from app.models.detalle_factura import DetalleFactura
from app.models.categoria import Categoria
from app.models.sucursal import Sucursal
from app.models.user import User
from app.models.proveedor import Proveedor
from app.utils.permisos import owner_o_supervisor_api
from app.services.excel_service import (
    exportar_facturas_excel,
    exportar_usuarios_excel,
    exportar_sucursales_excel,
)


bp = Blueprint('reportes_api', __name__, url_prefix='/api/reportes')


# ============================================================
# HELPERS
# ============================================================
def _solo_owner():
    """Owner o supervisor pueden acceder a reportes."""
    if not (current_user.is_owner() or current_user.is_supervisor()):
        return jsonify({'success': False, 'error': 'Solo el administrador o supervisor pueden acceder'}), 403
    return None

def _parse_fechas():
    hoy = date.today()
    desde_str = request.args.get('desde')
    hasta_str = request.args.get('hasta')

    if desde_str:
        try:
            desde = datetime.strptime(desde_str, '%Y-%m-%d').date()
        except ValueError:
            desde = hoy.replace(day=1)
    else:
        desde = hoy.replace(day=1)

    if hasta_str:
        try:
            hasta = datetime.strptime(hasta_str, '%Y-%m-%d').date()
        except ValueError:
            hasta = hoy
    else:
        hasta = hoy

    return desde, hasta


# ============================================================
# GET /api/reportes/facturas
# Reporte JSON de facturas
# ============================================================
@bp.route('/facturas', methods=['GET'])
@login_required
def facturas():
    """Devuelve las facturas en formato JSON con filtros."""
    err = _solo_owner()
    if err: return err

    try:
        desde, hasta = _parse_fechas()
        sucursal_id = request.args.get('sucursal', type=int)
        estado = request.args.get('estado')

        query = Factura.query.filter(
            Factura.fecha >= desde,
            Factura.fecha <= hasta,
        )

        if sucursal_id:
            query = query.filter(Factura.sucursal_id == sucursal_id)
        if estado:
            query = query.filter(Factura.estado == estado)

        facturas = query.order_by(Factura.fecha.desc()).all()

        # Serializar
        data = []
        total_monto = 0
        for f in facturas:
            monto = f.total_factura or 0
            total_monto += monto
            data.append({
                'id': f.id,
                'numero_factura': f.numero_factura,
                'fecha': f.fecha.isoformat() if f.fecha else None,
                'tipo_documento': f.tipo_documento,
                'proveedor': f.proveedor.nombre if f.proveedor else None,
                'sucursal': f.sucursal.nombre if f.sucursal else None,
                'usuario': f.usuario.nombre if f.usuario else None,
                'total': round(monto, 2),
                'estado': f.estado,
                'observacion': f.observacion,
            })

        return jsonify({
            'success': True,
            'periodo': {'desde': desde.isoformat(), 'hasta': hasta.isoformat()},
            'filtros': {
                'sucursal_id': sucursal_id,
                'estado': estado,
            },
            'total': len(data),
            'monto_total': round(total_monto, 2),
            'facturas': data,
        })
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# GET /api/reportes/usuarios
# Reporte JSON de usuarios
# ============================================================
@bp.route('/usuarios', methods=['GET'])
@login_required
def usuarios():
    """Devuelve los usuarios en formato JSON."""
    err = _solo_owner()
    if err: return err

    try:
        rol = request.args.get('rol')
        estado = request.args.get('estado')
        sucursal_id = request.args.get('sucursal', type=int)

        query = User.query
        if rol:
            query = query.filter(User.rol == rol)
        if estado:
            query = query.filter(User.estado == estado)
        if sucursal_id:
            query = query.filter(User.sucursal_id == sucursal_id)

        usuarios = query.order_by(User.nombre).all()

        data = []
        for u in usuarios:
            data.append({
                'id': u.id,
                'nombre': u.nombre,
                'usuario': u.usuario,
                'email': u.email,
                'rol': u.rol,
                'sucursal': u.sucursal.nombre if u.sucursal else 'Todas',
                'estado': u.estado,
            })

        return jsonify({
            'success': True,
            'total': len(data),
            'usuarios': data,
        })
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# GET /api/reportes/sucursales
# Reporte JSON de sucursales
# ============================================================
@bp.route('/sucursales', methods=['GET'])
@login_required
def sucursales():
    """Devuelve las sucursales con estadisticas del mes."""
    err = _solo_owner()
    if err: return err

    try:
        hoy = date.today()
        inicio_mes = hoy.replace(day=1)

        data = []
        for s in Sucursal.query.order_by(Sucursal.nombre).all():
            facturas_suc = Factura.query.filter(
                Factura.fecha >= inicio_mes,
                Factura.sucursal_id == s.id,
            ).all()

            monto = sum((f.total_factura or 0) for f in facturas_suc)
            val = sum(1 for f in facturas_suc if f.estado == 'Validada')
            obs = sum(1 for f in facturas_suc if f.estado == 'Observada')
            usuarios = User.query.filter_by(sucursal_id=s.id).count()

            data.append({
                'id': s.id,
                'nombre': s.nombre,
                'direccion': s.direccion,
                'telefono': s.telefono,
                'estado': s.estado,
                'usuarios': usuarios,
                'facturas_mes': len(facturas_suc),
                'monto_mes': round(monto, 2),
                'validadas': val,
                'observadas': obs,
            })

        return jsonify({
            'success': True,
            'periodo': {'desde': inicio_mes.isoformat(), 'hasta': hoy.isoformat()},
            'total': len(data),
            'sucursales': data,
        })
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# GET /api/reportes/resumen
# Resumen general de todos los recursos
# ============================================================
@bp.route('/resumen', methods=['GET'])
@login_required
def resumen():
    """Resumen general: facturas, usuarios, sucursales, proveedores."""
    err = _solo_owner()
    if err: return err

    try:
        desde, hasta = _parse_fechas()

        facturas = Factura.query.filter(
            Factura.fecha >= desde,
            Factura.fecha <= hasta,
        ).all()

        total_monto = sum((f.total_factura or 0) for f in facturas)

        return jsonify({
            'success': True,
            'periodo': {'desde': desde.isoformat(), 'hasta': hasta.isoformat()},
            'resumen': {
                'total_facturas': len(facturas),
                'monto_total': round(total_monto, 2),
                'validadas': sum(1 for f in facturas if f.estado == 'Validada'),
                'observadas': sum(1 for f in facturas if f.estado == 'Observada'),
                'total_usuarios': User.query.count(),
                'usuarios_activos': User.query.filter_by(estado='Activo').count(),
                'total_sucursales': Sucursal.query.count(),
                'sucursales_activas': Sucursal.query.filter_by(estado='Activa').count(),
                'total_proveedores': Proveedor.query.count(),
                'proveedores_activos': Proveedor.query.filter_by(estado='Activo').count(),
                'total_categorias': Categoria.query.count(),
                'categorias_activas': Categoria.query.filter_by(estado='Activa').count(),
            },
        })
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# GET /api/reportes/facturas.xlsx
# Descarga Excel de facturas
# ============================================================
@bp.route('/facturas.xlsx', methods=['GET'])
@login_required
def facturas_xlsx():
    """Descarga el reporte de facturas en Excel."""
    err = _solo_owner()
    if err: return err

    try:
        desde, hasta = _parse_fechas()
        sucursal_id = request.args.get('sucursal', type=int)
        estado = request.args.get('estado')

        query = Factura.query.filter(
            Factura.fecha >= desde,
            Factura.fecha <= hasta,
        )
        if sucursal_id:
            query = query.filter(Factura.sucursal_id == sucursal_id)
        if estado:
            query = query.filter(Factura.estado == estado)

        facturas = query.order_by(Factura.fecha.asc()).all()
        categorias = Categoria.query.filter_by(estado='Activa').order_by(Categoria.orden).all()

        buffer = exportar_facturas_excel(facturas, categorias)
        filename = f'facturas_{date.today().strftime("%Y%m%d")}.xlsx'

        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# GET /api/reportes/usuarios.xlsx
# Descarga Excel de usuarios
# ============================================================
@bp.route('/usuarios.xlsx', methods=['GET'])
@login_required
def usuarios_xlsx():
    """Descarga el reporte de usuarios en Excel."""
    err = _solo_owner()
    if err: return err

    try:
        usuarios = User.query.order_by(User.nombre).all()
        buffer = exportar_usuarios_excel(usuarios)
        filename = f'usuarios_{date.today().strftime("%Y%m%d")}.xlsx'

        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# GET /api/reportes/sucursales.xlsx
# Descarga Excel de sucursales
# ============================================================
@bp.route('/sucursales.xlsx', methods=['GET'])
@login_required
def sucursales_xlsx():
    """Descarga el reporte de sucursales en Excel."""
    err = _solo_owner()
    if err: return err

    try:
        hoy = date.today()
        inicio_mes = hoy.replace(day=1)

        sucursales_data = []
        for s in Sucursal.query.order_by(Sucursal.nombre).all():
            facturas_suc = Factura.query.filter(
                Factura.fecha >= inicio_mes,
                Factura.sucursal_id == s.id,
            ).count()
            usuarios_suc = User.query.filter_by(sucursal_id=s.id).count()
            sucursales_data.append({
                'obj': s,
                'facturas_mes': facturas_suc,
                'usuarios': usuarios_suc,
            })

        buffer = exportar_sucursales_excel(sucursales_data)
        filename = f'sucursales_{date.today().strftime("%Y%m%d")}.xlsx'

        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500
