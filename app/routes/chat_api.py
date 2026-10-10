from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone

from app import db
from app.models.chat import Conversacion, Mensaje, ConversacionMiembro
from app.models.user import User


bp = Blueprint('chat_api', __name__, url_prefix='/api/chat')


# ============================================================
# HELPERS
# ============================================================
def _solo_staff():
    """Solo owner y supervisor pueden usar el chat."""
    if not (current_user.is_owner() or current_user.is_supervisor()):
        return jsonify({'ok': False, 'error': 'Solo administradores y supervisores pueden usar el chat'}), 403
    return None


def _conversacion_directa(usuario1_id, usuario2_id):
    """Busca una conversacion directa entre 2 usuarios (en cualquier orden)."""
    return Conversacion.query.filter(
        Conversacion.tipo == 'directo',
        db.or_(
            db.and_(Conversacion.usuario_a_id == usuario1_id, Conversacion.usuario_b_id == usuario2_id),
            db.and_(Conversacion.usuario_a_id == usuario2_id, Conversacion.usuario_b_id == usuario1_id),
        )
    ).first()


def _conversaciones_visibles():
    """Devuelve las conversaciones que el usuario puede ver.

    Owner: General + sucursales + sus chats directos
    Supervisor: General + sus chats directos
    """
    if current_user.is_owner():
        # Owner: General + sucursales + sus directos
        return Conversacion.query.filter(
            db.or_(
                Conversacion.tipo.in_(['general', 'sucursal']),
                db.and_(
                    Conversacion.tipo == 'directo',
                    db.or_(
                        Conversacion.usuario_a_id == current_user.id,
                        Conversacion.usuario_b_id == current_user.id,
                    )
                )
            )
        ).order_by(Conversacion.tipo.desc(), Conversacion.nombre).all()

    # Supervisor: General + chats directos
    conversaciones = Conversacion.query.filter(
        db.or_(
            Conversacion.tipo == 'general',
            db.and_(
                Conversacion.tipo == 'directo',
                db.or_(
                    Conversacion.usuario_a_id == current_user.id,
                    Conversacion.usuario_b_id == current_user.id,
                )
            )
        )
    ).all()

    return conversaciones


def _puede_acceder(conv):
    """Verifica si el usuario actual puede acceder a la conversacion."""
    if current_user.is_owner():
        # Owner puede acceder a general, sucursal, y sus directos
        if conv.tipo in ('general', 'sucursal'):
            return True
        if conv.tipo == 'directo':
            return current_user.id in (conv.usuario_a_id, conv.usuario_b_id)
        return False

    # Supervisor
    if conv.tipo == 'general':
        return True
    if conv.tipo == 'sucursal':
        return conv.sucursal_id == current_user.sucursal_id
    if conv.tipo == 'directo':
        return current_user.id in (conv.usuario_a_id, conv.usuario_b_id)
    return False


def _nombre_conversacion(conv):
    """Devuelve el nombre visible de la conversacion para el usuario actual.

    Para chats directos, muestra el nombre del OTRO usuario.
    """
    if conv.tipo == 'directo':
        otro_id = conv.usuario_b_id if conv.usuario_a_id == current_user.id else conv.usuario_a_id
        otro = User.query.get(otro_id)
        if otro:
            sucursal_nombre = otro.sucursal.nombre if otro.sucursal else 'Sin sucursal'
            return f"{otro.nombre} ({sucursal_nombre})"
    return conv.nombre


# ============================================================
# GET /api/chat/conversaciones
# ============================================================
@bp.route('/conversaciones', methods=['GET'])
@login_required
def listar_conversaciones():
    err = _solo_staff()
    if err: return err

    try:
        conversaciones = _conversaciones_visibles()

        # Serializar con nombre personalizado
        data = []
        for c in conversaciones:
            d = c.to_dict(usuario_actual=current_user)
            d['nombre'] = _nombre_conversacion(c)
            data.append(d)

        # Ordenar: directos primero, luego general, luego sucursal
        orden = {'directo': 0, 'general': 1, 'sucursal': 2}
        data.sort(key=lambda x: (orden.get(x['tipo'], 99), x['nombre']))

        return jsonify({
            'ok': True,
            'total': len(data),
            'conversaciones': data,
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# GET /api/chat/supervisores
# Lista de otros supervisores para iniciar chat directo
# ============================================================
@bp.route('/supervisores', methods=['GET'])
@login_required
def listar_supervisores():
    err = _solo_staff()
    if err: return err

    try:
        if current_user.is_owner():
            # Owner: ve TODOS los supervisores
            supervisores = User.query.filter(
                User.rol == 'supervisor',
                User.estado == 'Activo',
            ).order_by(User.nombre).all()
        else:
            # Supervisor: ve OTROS supervisores + owners
            supervisores = User.query.filter(
                User.estado == 'Activo',
                User.id != current_user.id,
                User.rol.in_(['owner', 'supervisor']),
            ).order_by(User.rol.desc(), User.nombre).all()

        data = [{
            'id': s.id,
            'nombre': s.nombre,
            'usuario': s.usuario,
            'rol': s.rol,
            'sucursal': s.sucursal.nombre if s.sucursal else None,
        } for s in supervisores]

        return jsonify({
            'ok': True,
            'total': len(data),
            'supervisores': data,
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# POST /api/chat/directo/<user_id>
# Crear o abrir una conversacion directa con otro usuario
# ============================================================
@bp.route('/directo/<int:user_id>', methods=['POST'])
@login_required
def abrir_directo(user_id):
    err = _solo_staff()
    if err: return err

    if user_id == current_user.id:
        return jsonify({'ok': False, 'error': 'No puedes chatear contigo mismo'}), 400

    otro = User.query.get(user_id)
    if not otro or otro.estado != 'Activo':
        return jsonify({'ok': False, 'error': 'Usuario no encontrado'}), 404

    # Solo se puede chatear con owner o supervisor
    if otro.rol not in ('owner', 'supervisor'):
        return jsonify({'ok': False, 'error': 'Solo puedes chatear con administradores o supervisores'}), 403

    try:
        conv = _conversacion_directa(current_user.id, user_id)

        if not conv:
            conv = Conversacion(
                nombre=f'Directo {current_user.id}-{user_id}',
                tipo='directo',
                usuario_a_id=current_user.id,
                usuario_b_id=user_id,
            )
            db.session.add(conv)
            db.session.commit()

        return jsonify({
            'ok': True,
            'conversacion_id': conv.id,
            'nombre': _nombre_conversacion(conv),
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# GET /api/chat/conversaciones/<id>/mensajes
# ============================================================
@bp.route('/conversaciones/<int:conv_id>/mensajes', methods=['GET'])
@login_required
def listar_mensajes(conv_id):
    err = _solo_staff()
    if err: return err

    conv = Conversacion.query.get(conv_id)
    if not conv:
        return jsonify({'ok': False, 'error': 'Conversacion no encontrada'}), 404

    if not _puede_acceder(conv):
        return jsonify({'ok': False, 'error': 'Sin permisos'}), 403

    try:
        mensajes = (
            Mensaje.query
            .filter_by(conversacion_id=conv.id)
            .order_by(Mensaje.created_at.desc())
            .limit(100)
            .all()
        )
        mensajes.reverse()

        # Serializar conversacion con nombre personalizado
        conv_data = conv.to_dict(usuario_actual=current_user)
        conv_data['nombre'] = _nombre_conversacion(conv)

        return jsonify({
            'ok': True,
            'conversacion': conv_data,
            'total': len(mensajes),
            'mensajes': [m.to_dict() for m in mensajes],
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# POST /api/chat/conversaciones/<id>/mensajes
# ============================================================
@bp.route('/conversaciones/<int:conv_id>/mensajes', methods=['POST'])
@login_required
def enviar_mensaje(conv_id):
    err = _solo_staff()
    if err: return err

    conv = Conversacion.query.get(conv_id)
    if not conv:
        return jsonify({'ok': False, 'error': 'Conversacion no encontrada'}), 404

    if not _puede_acceder(conv):
        return jsonify({'ok': False, 'error': 'Sin permisos'}), 403

    data = request.get_json(silent=True) or {}
    contenido = (data.get('contenido') or '').strip()

    if not contenido:
        return jsonify({'ok': False, 'error': 'El mensaje no puede estar vacio'}), 400

    if len(contenido) > 2000:
        return jsonify({'ok': False, 'error': 'El mensaje es demasiado largo (max 2000 caracteres)'}), 400

    try:
        mensaje = Mensaje(
            conversacion_id=conv.id,
            usuario_id=current_user.id,
            contenido=contenido,
        )
        db.session.add(mensaje)

        miembro = ConversacionMiembro.query.filter_by(
            conversacion_id=conv.id,
            usuario_id=current_user.id,
        ).first()
        if not miembro:
            miembro = ConversacionMiembro(
                conversacion_id=conv.id,
                usuario_id=current_user.id,
            )
            db.session.add(miembro)

        miembro.ultima_lectura = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({
            'ok': True,
            'mensaje': mensaje.to_dict(),
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500


# ============================================================
# POST /api/chat/conversaciones/<id>/marcar-leido
# ============================================================
@bp.route('/conversaciones/<int:conv_id>/marcar-leido', methods=['POST'])
@login_required
def marcar_leido(conv_id):
    err = _solo_staff()
    if err: return err

    conv = Conversacion.query.get(conv_id)
    if not conv:
        return jsonify({'ok': False, 'error': 'Conversacion no encontrada'}), 404

    if not _puede_acceder(conv):
        return jsonify({'ok': False, 'error': 'Sin permisos'}), 403

    try:
        miembro = ConversacionMiembro.query.filter_by(
            conversacion_id=conv.id,
            usuario_id=current_user.id,
        ).first()

        if not miembro:
            miembro = ConversacionMiembro(
                conversacion_id=conv.id,
                usuario_id=current_user.id,
            )
            db.session.add(miembro)

        miembro.ultima_lectura = datetime.now(timezone.utc)
        db.session.commit()

        return jsonify({'ok': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(e)}), 500