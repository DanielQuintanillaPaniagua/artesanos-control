from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user

from app import db
from app.models.user import User
from app.models.sucursal import Sucursal


bp = Blueprint('usuarios_api', __name__, url_prefix='/api/usuarios')


# ============================================================
# HELPERS
# ============================================================
def _puede_gestionar_usuarios():
    """
    Owner o supervisor pueden gestionar usuarios.
    Devuelve None si OK, o (jsonify, status) si hay error.
    """
    if not (current_user.is_owner() or current_user.is_supervisor()):
        return jsonify({
            'success': False,
            'error': 'Solo el administrador o supervisor pueden acceder'
        }), 403
    return None


def _puede_tocar(target):
    """
    Valida si el usuario actual puede gestionar al usuario `target`.

    Reglas:
      - Owner: puede tocar a cualquiera EXCEPTO a sí mismo en ciertos casos
        (cambio de rol/estado de sí mismo se valida aparte).
      - Supervisor: solo usuarios de SU MISMA sucursal y que NO sean owner.
    Devuelve None si OK, o (jsonify, status) si hay error.
    """
    if current_user.is_owner():
        return None

    # Supervisor
    if current_user.is_supervisor():
        if target.is_owner():
            return jsonify({
                'success': False,
                'error': 'Un supervisor no puede gestionar a un administrador'
            }), 403
        if target.sucursal_id != current_user.sucursal_id:
            return jsonify({
                'success': False,
                'error': 'Solo podes gestionar usuarios de tu sucursal'
            }), 403
        return None

    # Empleado u otro rol
    return jsonify({
        'success': False,
        'error': 'No tenes permiso para gestionar usuarios'
    }), 403


def _validar_target_para_supervisor(rol, sucursal_id, target=None):
    """
    Valida reglas específicas cuando el current_user es supervisor.

    - No puede crear ni promover a 'owner'.
    - No puede mover usuarios a otra sucursal.
    - Si target es él mismo, no puede cambiarse el rol.

    Devuelve lista de errores (strings).
    """
    errores = []
    if not current_user.is_supervisor():
        return errores

    if rol == 'owner':
        errores.append('Un supervisor no puede crear ni promover administradores.')

    # Forzar sucursal propia (por si mandan otra)
    if sucursal_id and sucursal_id != current_user.sucursal_id:
        errores.append('Solo podes asignar usuarios a tu propia sucursal.')

    # No puede cambiarse su propio rol
    if target is not None and target.id == current_user.id:
        if rol != current_user.rol:
            errores.append('No podes cambiar tu propio rol.')

    return errores


def _serializar(u):
    return {
        'id': u.id,
        'nombre': u.nombre,
        'usuario': u.usuario,
        'email': u.email,
        'rol': u.rol,
        'sucursal_id': u.sucursal_id,
        'sucursal_nombre': u.sucursal.nombre if u.sucursal else None,
        'estado': u.estado,
        'created_at': u.created_at.isoformat() if u.created_at else None,
    }


# ============================================================
# GET /api/usuarios/
# Listar usuarios
# ============================================================
@bp.route('/', methods=['GET'])
@login_required
def listar():
    err = _puede_gestionar_usuarios()
    if err: return err

    try:
        rol = request.args.get('rol')
        estado = request.args.get('estado')
        sucursal_id = request.args.get('sucursal', type=int)

        query = User.query

        # Supervisor: solo su sucursal
        if current_user.is_supervisor():
            query = query.filter(User.sucursal_id == current_user.sucursal_id)
            # Supervisor tampoco puede ver owners (no están en su sucursal de todas formas,
            # pero por si acaso owner tuviera sucursal asignada)
            query = query.filter(User.rol != 'owner')

        if rol:
            query = query.filter(User.rol == rol)
        if estado:
            query = query.filter(User.estado == estado)
        if sucursal_id:
            query = query.filter(User.sucursal_id == sucursal_id)

        usuarios = query.order_by(User.nombre).all()

        return jsonify({
            'success': True,
            'total': len(usuarios),
            'usuarios': [_serializar(u) for u in usuarios],
        })
    except Exception:
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# GET /api/usuarios/<id>
# Ver un usuario
# ============================================================
@bp.route('/<int:user_id>', methods=['GET'])
@login_required
def ver(user_id):
    err = _puede_gestionar_usuarios()
    if err: return err

    u = db.session.get(User, user_id)
    if not u:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

    err = _puede_tocar(u)
    if err: return err

    return jsonify({'success': True, 'usuario': _serializar(u)})


# ============================================================
# POST /api/usuarios/
# Crear usuario
# ============================================================
@bp.route('/', methods=['POST'])
@login_required
def crear():
    err = _puede_gestionar_usuarios()
    if err: return err

    data = request.get_json(silent=True) or {}

    nombre = (data.get('nombre') or '').strip()
    usuario = (data.get('usuario') or '').strip().lower()
    email = (data.get('email') or '').strip().lower() or None
    rol = data.get('rol') or 'empleado'
    sucursal_id = data.get('sucursal_id')
    password = data.get('password') or ''

    # Si es supervisor, forzar su propia sucursal
    if current_user.is_supervisor():
        sucursal_id = current_user.sucursal_id

    errores = []
    if not nombre or len(nombre) < 3:
        errores.append('El nombre debe tener al menos 3 caracteres')
    if not usuario or len(usuario) < 3:
        errores.append('El usuario debe tener al menos 3 caracteres')
    if len(password) < 6:
        errores.append('La contrasena debe tener al menos 6 caracteres')
    if User.query.filter_by(usuario=usuario).first():
        errores.append(f'El usuario "{usuario}" ya existe')
    if email and User.query.filter_by(email=email).first():
        errores.append(f'El email "{email}" ya esta en uso')
    if rol not in ('owner', 'empleado', 'supervisor'):
        errores.append('Rol invalido')
    if rol in ('empleado', 'supervisor') and not sucursal_id:
        errores.append('Los empleados y supervisores deben tener una sucursal asignada.')
    if sucursal_id and not db.session.get(Sucursal, sucursal_id):
        errores.append('La sucursal seleccionada no existe.')

    # Reglas específicas de supervisor
    errores.extend(_validar_target_para_supervisor(rol, sucursal_id, target=None))

    if errores:
        return jsonify({'success': False, 'errores': errores}), 400

    try:
        u = User(
            nombre=nombre,
            usuario=usuario,
            email=email,
            rol=rol,
            sucursal_id=sucursal_id if rol in ('empleado', 'supervisor') else None,
            estado='Activo',
        )
        u.set_password(password)
        db.session.add(u)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Usuario "{u.nombre}" creado',
            'usuario': _serializar(u),
        }), 201
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# PUT /api/usuarios/<id>
# Actualizar usuario
# ============================================================
@bp.route('/<int:user_id>', methods=['PUT'])
@login_required
def actualizar(user_id):
    err = _puede_gestionar_usuarios()
    if err: return err

    u = db.session.get(User, user_id)
    if not u:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

    err = _puede_tocar(u)
    if err: return err

    data = request.get_json(silent=True) or {}

    nombre = (data.get('nombre') or '').strip()
    usuario = (data.get('usuario') or '').strip().lower()
    email = (data.get('email') or '').strip().lower() or None
    rol = data.get('rol') or 'empleado'
    sucursal_id = data.get('sucursal_id')
    password = (data.get('password') or '').strip()
    estado = data.get('estado') or u.estado

    # Supervisor: forzar su sucursal
    if current_user.is_supervisor():
        sucursal_id = current_user.sucursal_id

    errores = []
    if not nombre or len(nombre) < 3:
        errores.append('El nombre debe tener al menos 3 caracteres')
    if not usuario or len(usuario) < 3:
        errores.append('El usuario debe tener al menos 3 caracteres')

    existe = User.query.filter(User.usuario == usuario, User.id != u.id).first()
    if existe:
        errores.append(f'El usuario "{usuario}" ya existe')

    if email:
        existe_email = User.query.filter(User.email == email, User.id != u.id).first()
        if existe_email:
            errores.append(f'El email "{email}" ya esta en uso')

    if rol not in ('owner', 'supervisor', 'empleado'):
        errores.append('Rol invalido')
    if rol in ('empleado', 'supervisor') and not sucursal_id:
        errores.append('Los empleados y supervisores deben tener una sucursal asignada.')
    if password and len(password) < 6:
        errores.append('La contrasena debe tener al menos 6 caracteres')

    # Nadie puede desactivarse a sí mismo
    if u.id == current_user.id and estado != 'Activo':
        errores.append('No puedes desactivar tu propio usuario')

    # Reglas específicas de supervisor
    errores.extend(_validar_target_para_supervisor(rol, sucursal_id, target=u))

    # Nadie (excepto owner) puede cambiar su propio rol
    if u.id == current_user.id and rol != u.rol and not current_user.is_owner():
        errores.append('No podes cambiar tu propio rol.')

    if errores:
        return jsonify({'success': False, 'errores': errores}), 400

    try:
        u.nombre = nombre
        u.usuario = usuario
        u.email = email
        u.rol = rol
        u.sucursal_id = sucursal_id if rol in ('empleado', 'supervisor') else None
        u.estado = estado
        if password:
            u.set_password(password)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Usuario "{u.nombre}" actualizado',
            'usuario': _serializar(u),
        })
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# DELETE /api/usuarios/<id>
# Desactivar usuario (soft delete)
# ============================================================
@bp.route('/<int:user_id>', methods=['DELETE'])
@login_required
def eliminar(user_id):
    err = _puede_gestionar_usuarios()
    if err: return err

    u = db.session.get(User, user_id)
    if not u:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

    err = _puede_tocar(u)
    if err: return err

    if u.id == current_user.id:
        return jsonify({'success': False, 'error': 'No puedes eliminarte a ti mismo'}), 400

    try:
        u.estado = 'Inactivo'
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Usuario "{u.nombre}" desactivado',
        })
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500


# ============================================================
# POST /api/usuarios/<id>/toggle-estado
# Activar/desactivar
# ============================================================
@bp.route('/<int:user_id>/toggle-estado', methods=['POST'])
@login_required
def toggle_estado(user_id):
    err = _puede_gestionar_usuarios()
    if err: return err

    u = db.session.get(User, user_id)
    if not u:
        return jsonify({'success': False, 'error': 'Usuario no encontrado'}), 404

    err = _puede_tocar(u)
    if err: return err

    if u.id == current_user.id:
        return jsonify({'success': False, 'error': 'No puedes cambiar tu propio estado'}), 400

    try:
        u.estado = 'Inactivo' if u.estado == 'Activo' else 'Activo'
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Usuario "{u.nombre}" ahora esta {u.estado.lower()}',
            'estado': u.estado,
        })
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Error en endpoint")
        return jsonify({'success': False, 'error': 'Error interno del servidor'}), 500