from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app import limiter, _key_func_usuario
from app.services.artesanos_ai import preguntar_a_artesanos_ai


bp = Blueprint('ai_api', __name__, url_prefix='/api/ai')


@bp.route('/chat', methods=['POST'])
@login_required
@limiter.limit("30 per hour", key_func=_key_func_usuario)
def chat():
    """Endpoint para consultar a Artesanos AI.

    Limite: 30 preguntas por hora por usuario.
    - Razon: la API de Gemini tiene costo por request. Un usuario legitimo
      no hace mas de 5-10 preguntas al dia. 30/hora es generoso.
    """
    if not (current_user.is_owner() or current_user.is_supervisor()):
        return jsonify({'ok': False, 'error': 'Solo el administrador puede usar Artesanos AI'}), 403

    data = request.get_json(silent=True) or {}
    mensaje = (data.get('mensaje') or '').strip()
    historial = data.get('historial', [])

    if not mensaje:
        return jsonify({'ok': False, 'error': 'Mensaje vacio'}), 400

    if len(mensaje) > 1000:
        return jsonify({'ok': False, 'error': 'La pregunta es demasiado larga (max 1000 caracteres)'}), 400

    sucursal_id = data.get('sucursal_id')

    if current_user.is_supervisor():
        sucursal_id = current_user.sucursal_id

    resultado = preguntar_a_artesanos_ai(mensaje, historial=historial, sucursal_id=sucursal_id)

    if resultado.get('ok'):
        return jsonify({'ok': True, 'respuesta': resultado['respuesta']})
    else:
        return jsonify({'ok': False, 'error': resultado.get('error', 'Error desconocido')}), 500