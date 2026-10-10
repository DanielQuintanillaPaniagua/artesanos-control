from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timezone

from app import db
from app.models.chat import Conversacion, Mensaje, ConversacionMiembro


bp = Blueprint('chat_api', __name__, url_prefix='/api/chat')


# ============================================================
# HELPERS
# ============================================================
def _solo_staff():
    """Solo owner y supervisor pueden usar el chat."""
    if not (current_user.is_owner() or current_user.is_supervisor()):
        return jsonify({'ok': False, 'error': 'Solo administradores y supervisores pueden usar el chat'}), 403
    return None


def _conversaciones_visibles():
    """Devuelve las conversaciones que el usuario puede ver.

    Owner: todas
    Supervisor: General + su sucursal
    """
    query = Conversacion.query

    if current_user.is_supervisor():
        # General + su sucursal
        query = query.filter(
            db.or_(
                Conversacion.tipo == 'general',
                db.and_(
                    Conversacion.tipo == 'sucursal',
                    Conversacion.sucursal_id == current_user.sucursal_id,
                )
            )
        )
    # Owner: sin filtro (ve todas)

    return query.order_by(Conversacion.tipo.desc(), Conversacion.nombre).all()


def _puede_acceder(conv):
    """Verifica si el usuario actual puede acceder a la conversacion."""
    if current_user.is_owner():
        return True
    if conv.tipo == 'general':
        return True
    if current_user.is_supervisor() and conv.sucursal_id == current_user.sucursal_id:
        return True
    return False


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
        return jsonify({
            'ok': True,
            'total': len(conversaciones),
            'conversaciones': [c.to_dict(usuario_actual=current_user) for c in conversaciones],
        })
    except Exception as e:
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
        # Ultimos 100 mensajes
        mensajes = (
            Mensaje.query
            .filter_by(conversacion_id=conv.id)
            .order_by(Mensaje.created_at.desc())
            .limit(100)
            .all()
        )
        mensajes.reverse()  # Orden cronologico

        return jsonify({
            'ok': True,
            'conversacion': conv.to_dict(usuario_actual=current_user),
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

        # Actualizar ultima_lectura del autor
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
