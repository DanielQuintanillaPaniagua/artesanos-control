from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user

from app import db
from app.models.categoria import Categoria
from app.models.detalle_factura import DetalleFactura


bp = Blueprint('categorias_api', __name__, url_prefix='/api/categorias')


# ============================================================
# HELPERS
# ============================================================
def _solo_owner():
    if not current_user.is_owner():
        return jsonify({'success': False, 'error': 'Solo el administrador puede acceder'}), 403
    return None


def _serializar(c, incluir_stats=False):
    data = {
        'id': c.id,
        'nombre': c.nombre,
        'grupo': c.grupo,
        'orden': c.orden,
        'estado': c.estado,
    }

    if incluir_stats:
        detalles = DetalleFactura.query.filter_by(categoria_id=c.id).all()
        data['total_facturas'] = len(set(d.factura_id for d in detalles))
        data['monto_total'] = round(sum((d.monto or 0) for d in detalles), 2)

    return data


# ============================================================
# GET /api/categorias/
# Listar todas las categorias
# ============================================================
@bp.route('/', methods=['GET'])
@login_required
def listar():
    try:
        estado = request.args.get('estado')
        grupo = request.args.get('grupo')
        con_stats = request.args.get('stats', 'false').lower() == 'true'

        query = Categoria.query
        if estado:
            query = query.filter(Categoria.estado == estado)
        if grupo:
            query = query.filter(Categoria.grupo == grupo)

        categorias = query.order_by(Categoria.orden).all()

        # Agrupar por grupo (opcional)
        agrupadas = {}
        for c in categorias:
            g = c.grupo or 'Sin grupo'
            if g not in agrupadas:
                agrupadas[g] = []
            agrupadas[g].append(_serializar(c, incluir_stats=con_stats))

        return jsonify({
            'success': True,
            'total': len(categorias),
            'categorias': [_serializar(c, incluir_stats=con_stats) for c in categorias],
            'por_grupo': agrupadas,
        })
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# GET /api/categorias/grupos
# Listar todos los grupos unicos
# ============================================================
@bp.route('/grupos', methods=['GET'])
@login_required
def grupos():
    try:
        grupos_unicos = db.session.query(Categoria.grupo).distinct().all()
        resultado = sorted([g[0] for g in grupos_unicos if g[0]])

        return jsonify({
            'success': True,
            'total': len(resultado),
            'grupos': resultado,
        })
    except Exception as e:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# GET /api/categorias/<id>
# Ver una categoria
# ============================================================
@bp.route('/<int:categoria_id>', methods=['GET'])
@login_required
def ver(categoria_id):
    c = Categoria.query.get(categoria_id)
    if not c:
        return jsonify({'success': False, 'error': 'Categoria no encontrada'}), 404

    return jsonify({
        'success': True,
        'categoria': _serializar(c, incluir_stats=True),
    })


# ============================================================
# POST /api/categorias/
# Crear categoria (solo owner)
# ============================================================
@bp.route('/', methods=['POST'])
@login_required
def crear():
    err = _solo_owner()
    if err: return err

    data = request.get_json(silent=True) or {}

    nombre = (data.get('nombre') or '').strip()
    grupo = (data.get('grupo') or '').strip() or None
    orden = data.get('orden', 0)
    estado = data.get('estado') or 'Activa'

    errores = []
    if not nombre or len(nombre) < 2:
        errores.append('El nombre debe tener al menos 2 caracteres')
    if Categoria.query.filter(Categoria.nombre.ilike(nombre)).first():
        errores.append(f'Ya existe una categoria con el nombre "{nombre}"')
    if estado not in ('Activa', 'Inactiva'):
        errores.append('Estado invalido')

    if errores:
        return jsonify({'success': False, 'errores': errores}), 400

    try:
        c = Categoria(
            nombre=nombre,
            grupo=grupo,
            orden=orden,
            estado=estado,
        )
        db.session.add(c)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Categoria "{c.nombre}" creada',
            'categoria': _serializar(c),
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# PUT /api/categorias/<id>
# Actualizar categoria (solo owner)
# ============================================================
@bp.route('/<int:categoria_id>', methods=['PUT'])
@login_required
def actualizar(categoria_id):
    err = _solo_owner()
    if err: return err

    c = Categoria.query.get(categoria_id)
    if not c:
        return jsonify({'success': False, 'error': 'Categoria no encontrada'}), 404

    data = request.get_json(silent=True) or {}

    nombre = (data.get('nombre') or '').strip()
    grupo = (data.get('grupo') or '').strip() or None
    orden = data.get('orden', c.orden)
    estado = data.get('estado') or c.estado

    errores = []
    if not nombre or len(nombre) < 2:
        errores.append('El nombre debe tener al menos 2 caracteres')

    existe = Categoria.query.filter(
        Categoria.nombre.ilike(nombre),
        Categoria.id != c.id,
    ).first()
    if existe:
        errores.append(f'Ya existe otra categoria con el nombre "{nombre}"')

    if estado not in ('Activa', 'Inactiva'):
        errores.append('Estado invalido')

    if errores:
        return jsonify({'success': False, 'errores': errores}), 400

    try:
        c.nombre = nombre
        c.grupo = grupo
        c.orden = orden
        c.estado = estado
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Categoria "{c.nombre}" actualizada',
            'categoria': _serializar(c),
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# DELETE /api/categorias/<id>
# Desactivar categoria (soft delete)
# ============================================================
@bp.route('/<int:categoria_id>', methods=['DELETE'])
@login_required
def eliminar(categoria_id):
    err = _solo_owner()
    if err: return err

    c = Categoria.query.get(categoria_id)
    if not c:
        return jsonify({'success': False, 'error': 'Categoria no encontrada'}), 404

    total_detalles = DetalleFactura.query.filter_by(categoria_id=c.id).count()
    if total_detalles > 0:
        return jsonify({
            'success': False,
            'error': f'No se puede eliminar: la categoria tiene {total_detalles} registros en facturas. Desactivala en su lugar.',
        }), 400

    try:
        c.estado = 'Inactiva'
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Categoria "{c.nombre}" desactivada',
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# POST /api/categorias/<id>/toggle-estado
# Activar/desactivar (solo owner)
# ============================================================
@bp.route('/<int:categoria_id>/toggle-estado', methods=['POST'])
@login_required
def toggle_estado(categoria_id):
    err = _solo_owner()
    if err: return err

    c = Categoria.query.get(categoria_id)
    if not c:
        return jsonify({'success': False, 'error': 'Categoria no encontrada'}), 404

    try:
        c.estado = 'Inactiva' if c.estado == 'Activa' else 'Activa'
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Categoria "{c.nombre}" ahora esta {c.estado.lower()}',
            'estado': c.estado,
        })
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500
