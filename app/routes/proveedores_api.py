from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user

from app import db
from app.models.proveedor import Proveedor
from app.models.factura import Factura


bp = Blueprint('proveedores_api', __name__, url_prefix='/api/proveedores')


# ============================================================
# HELPERS
# ============================================================
def _serializar(p, incluir_stats=False):
    data = {
        'id': p.id,
        'nombre': p.nombre,
        'telefono': p.telefono,
        'email': p.email,
        'estado': p.estado,
        'created_at': p.created_at.isoformat() if p.created_at else None,
    }

    if incluir_stats:
        facturas = Factura.query.filter_by(proveedor_id=p.id).all()
        data['total_facturas'] = len(facturas)
        data['monto_total'] = round(sum((f.total_factura or 0) for f in facturas), 2)

    return data


# ============================================================
# GET /api/proveedores/
# Listar todos los proveedores
# ============================================================
@bp.route('/', methods=['GET'])
@login_required
def listar():
    try:
        estado = request.args.get('estado')
        buscar = request.args.get('buscar', '').strip()
        con_stats = request.args.get('stats', 'false').lower() == 'true'

        query = Proveedor.query
        if estado:
            query = query.filter(Proveedor.estado == estado)
        if buscar:
            query = query.filter(Proveedor.nombre.ilike(f'%{buscar}%'))

        proveedores = query.order_by(Proveedor.nombre).all()

        return jsonify({
            'success': True,
            'total': len(proveedores),
            'proveedores': [_serializar(p, incluir_stats=con_stats) for p in proveedores],
        })
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# GET /api/proveedores/<id>
# Ver un proveedor
# ============================================================
@bp.route('/<int:proveedor_id>', methods=['GET'])
@login_required
def ver(proveedor_id):
    p = Proveedor.query.get(proveedor_id)
    if not p:
        return jsonify({'success': False, 'error': 'Proveedor no encontrado'}), 404

    return jsonify({
        'success': True,
        'proveedor': _serializar(p, incluir_stats=True),
    })


# ============================================================
# POST /api/proveedores/
# Crear proveedor
# ============================================================
@bp.route('/', methods=['POST'])
@login_required
def crear():
    data = request.get_json(silent=True) or {}

    nombre = (data.get('nombre') or '').strip()
    telefono = (data.get('telefono') or '').strip() or None
    email = (data.get('email') or '').strip() or None
    estado = data.get('estado') or 'Activo'

    errores = []
    if not nombre or len(nombre) < 2:
        errores.append('El nombre debe tener al menos 2 caracteres')
    if Proveedor.query.filter(Proveedor.nombre.ilike(nombre)).first():
        errores.append(f'Ya existe un proveedor con el nombre "{nombre}"')
    if estado not in ('Activo', 'Inactivo'):
        errores.append('Estado invalido')

    if errores:
        return jsonify({'success': False, 'errores': errores}), 400

    try:
        p = Proveedor(
            nombre=nombre,
            telefono=telefono,
            email=email,
            estado=estado,
        )
        db.session.add(p)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Proveedor "{p.nombre}" creado',
            'proveedor': _serializar(p),
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# PUT /api/proveedores/<id>
# Actualizar proveedor
# ============================================================
@bp.route('/<int:proveedor_id>', methods=['PUT'])
@login_required
def actualizar(proveedor_id):
    p = Proveedor.query.get(proveedor_id)
    if not p:
        return jsonify({'success': False, 'error': 'Proveedor no encontrado'}), 404

    data = request.get_json(silent=True) or {}

    nombre = (data.get('nombre') or '').strip()
    telefono = (data.get('telefono') or '').strip() or None
    email = (data.get('email') or '').strip() or None
    estado = data.get('estado') or 'Activo'

    errores = []
    if not nombre or len(nombre) < 2:
        errores.append('El nombre debe tener al menos 2 caracteres')

    existe = Proveedor.query.filter(
        Proveedor.nombre.ilike(nombre),
        Proveedor.id != p.id,
    ).first()
    if existe:
        errores.append(f'Ya existe otro proveedor con el nombre "{nombre}"')

    if estado not in ('Activo', 'Inactivo'):
        errores.append('Estado invalido')

    if errores:
        return jsonify({'success': False, 'errores': errores}), 400

    try:
        p.nombre = nombre
        p.telefono = telefono
        p.email = email
        p.estado = estado
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Proveedor "{p.nombre}" actualizado',
            'proveedor': _serializar(p),
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# DELETE /api/proveedores/<id>
# Desactivar proveedor (soft delete)
# ============================================================
@bp.route('/<int:proveedor_id>', methods=['DELETE'])
@login_required
def eliminar(proveedor_id):
    p = Proveedor.query.get(proveedor_id)
    if not p:
        return jsonify({'success': False, 'error': 'Proveedor no encontrado'}), 404

    # Verificar si tiene facturas
    total_facturas = Factura.query.filter_by(proveedor_id=p.id).count()
    if total_facturas > 0:
        return jsonify({
            'success': False,
            'error': f'No se puede eliminar: el proveedor tiene {total_facturas} facturas asociadas. Desactivalo en su lugar.',
        }), 400

    try:
        p.estado = 'Inactivo'
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Proveedor "{p.nombre}" desactivado',
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# POST /api/proveedores/<id>/toggle-estado
# Activar/desactivar
# ============================================================
@bp.route('/<int:proveedor_id>/toggle-estado', methods=['POST'])
@login_required
def toggle_estado(proveedor_id):
    p = Proveedor.query.get(proveedor_id)
    if not p:
        return jsonify({'success': False, 'error': 'Proveedor no encontrado'}), 404

    try:
        p.estado = 'Inactivo' if p.estado == 'Activo' else 'Activo'
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Proveedor "{p.nombre}" ahora esta {p.estado.lower()}',
            'estado': p.estado,
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500
