from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from app import db
from app.models.sucursal import Sucursal
from app.models.user import User
from app.models.factura import Factura


bp = Blueprint('sucursales_api', __name__, url_prefix='/api/sucursales')


# ============================================================
# HELPERS
# ============================================================
def _solo_owner():
    if not current_user.is_owner():
        return jsonify({'success': False, 'error': 'Solo el administrador puede acceder'}), 403
    return None


def _serializar(s, incluir_stats=False):
    data = {
        'id': s.id,
        'nombre': s.nombre,
        'direccion': s.direccion,
        'telefono': s.telefono,
        'estado': s.estado,
        'created_at': s.created_at.isoformat() if s.created_at else None,
    }

    if incluir_stats:
        from datetime import date
        hoy = date.today()
        inicio_mes = hoy.replace(day=1)

        data['total_usuarios'] = User.query.filter_by(sucursal_id=s.id).count()
        data['facturas_mes'] = Factura.query.filter(
            Factura.fecha >= inicio_mes,
            Factura.sucursal_id == s.id,
        ).count()

    return data


# ============================================================
# GET /api/sucursales/
# Listar todas las sucursales
# ============================================================
@bp.route('/', methods=['GET'])
@login_required
def listar():
    try:
        estado = request.args.get('estado')
        con_stats = request.args.get('stats', 'false').lower() == 'true'

        query = Sucursal.query
        if estado:
            query = query.filter(Sucursal.estado == estado)

        sucursales = query.order_by(Sucursal.nombre).all()

        return jsonify({
            'success': True,
            'total': len(sucursales),
            'sucursales': [_serializar(s, incluir_stats=con_stats) for s in sucursales],
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# GET /api/sucursales/<id>
# Ver una sucursal
# ============================================================
@bp.route('/<int:sucursal_id>', methods=['GET'])
@login_required
def ver(sucursal_id):
    s = Sucursal.query.get(sucursal_id)
    if not s:
        return jsonify({'success': False, 'error': 'Sucursal no encontrada'}), 404

    return jsonify({
        'success': True,
        'sucursal': _serializar(s, incluir_stats=True),
    })


# ============================================================
# POST /api/sucursales/
# Crear sucursal
# ============================================================
@bp.route('/', methods=['POST'])
@login_required
def crear():
    err = _solo_owner()
    if err: return err

    data = request.get_json(silent=True) or {}

    nombre = (data.get('nombre') or '').strip()
    direccion = (data.get('direccion') or '').strip() or None
    telefono = (data.get('telefono') or '').strip() or None
    estado = data.get('estado') or 'Activa'

    errores = []
    if not nombre or len(nombre) < 3:
        errores.append('El nombre debe tener al menos 3 caracteres')
    if Sucursal.query.filter(Sucursal.nombre.ilike(nombre)).first():
        errores.append(f'Ya existe una sucursal con el nombre "{nombre}"')
    if estado not in ('Activa', 'Inactiva'):
        errores.append('Estado invalido')

    if errores:
        return jsonify({'success': False, 'errores': errores}), 400

    try:
        s = Sucursal(
            nombre=nombre,
            direccion=direccion,
            telefono=telefono,
            estado=estado,
        )
        db.session.add(s)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Sucursal "{s.nombre}" creada',
            'sucursal': _serializar(s),
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# PUT /api/sucursales/<id>
# Actualizar sucursal
# ============================================================
@bp.route('/<int:sucursal_id>', methods=['PUT'])
@login_required
def actualizar(sucursal_id):
    err = _solo_owner()
    if err: return err

    s = Sucursal.query.get(sucursal_id)
    if not s:
        return jsonify({'success': False, 'error': 'Sucursal no encontrada'}), 404

    data = request.get_json(silent=True) or {}

    nombre = (data.get('nombre') or '').strip()
    direccion = (data.get('direccion') or '').strip() or None
    telefono = (data.get('telefono') or '').strip() or None
    estado = data.get('estado') or 'Activa'

    errores = []
    if not nombre or len(nombre) < 3:
        errores.append('El nombre debe tener al menos 3 caracteres')

    existe = Sucursal.query.filter(
        Sucursal.nombre.ilike(nombre),
        Sucursal.id != s.id,
    ).first()
    if existe:
        errores.append(f'Ya existe otra sucursal con el nombre "{nombre}"')

    if estado not in ('Activa', 'Inactiva'):
        errores.append('Estado invalido')

    if errores:
        return jsonify({'success': False, 'errores': errores}), 400

    try:
        s.nombre = nombre
        s.direccion = direccion
        s.telefono = telefono
        s.estado = estado
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Sucursal "{s.nombre}" actualizada',
            'sucursal': _serializar(s),
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# DELETE /api/sucursales/<id>
# Desactivar sucursal (soft delete)
# ============================================================
@bp.route('/<int:sucursal_id>', methods=['DELETE'])
@login_required
def eliminar(sucursal_id):
    err = _solo_owner()
    if err: return err

    s = Sucursal.query.get(sucursal_id)
    if not s:
        return jsonify({'success': False, 'error': 'Sucursal no encontrada'}), 404

    # Verificar si tiene facturas
    total_facturas = Factura.query.filter_by(sucursal_id=s.id).count()
    if total_facturas > 0:
        return jsonify({
            'success': False,
            'error': f'No se puede eliminar: la sucursal tiene {total_facturas} facturas asociadas. Desactivala en su lugar.',
        }), 400

    try:
        s.estado = 'Inactiva'
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Sucursal "{s.nombre}" desactivada',
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# POST /api/sucursales/<id>/toggle-estado
# Activar/desactivar
# ============================================================
@bp.route('/<int:sucursal_id>/toggle-estado', methods=['POST'])
@login_required
def toggle_estado(sucursal_id):
    err = _solo_owner()
    if err: return err

    s = Sucursal.query.get(sucursal_id)
    if not s:
        return jsonify({'success': False, 'error': 'Sucursal no encontrada'}), 404

    try:
        s.estado = 'Inactiva' if s.estado == 'Activa' else 'Activa'
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Sucursal "{s.nombre}" ahora esta {s.estado.lower()}',
            'estado': s.estado,
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
