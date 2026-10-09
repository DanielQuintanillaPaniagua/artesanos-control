from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from app.services.artesanos_ai import preguntar_a_artesanos_ai


bp = Blueprint('ai_api', __name__, url_prefix='/api/ai')


@bp.route('/chat', methods=['POST'])
@login_required
def chat():
    """Endpoint para consultar a Artesanos AI."""
    if not (current_user.is_owner() or current_user.is_supervisor()):
        return jsonify({'ok': False, 'error': 'Solo el administrador puede usar Artesanos AI'}), 403

    data = request.get_json(silent=True) or {}
    mensaje = (data.get('mensaje') or '').strip()
    historial = data.get('historial', [])

    if not mensaje:
        return jsonify({'ok': False, 'error': 'Mensaje vacio'}), 400

    # Opcional: filtro por sucursal
    sucursal_id = data.get('sucursal_id')

    # Supervisor: forzar su propia sucursal (no puede ver otras)
    if current_user.is_supervisor():
        sucursal_id = current_user.sucursal_id

    resultado = preguntar_a_artesanos_ai(mensaje, historial=historial, sucursal_id=sucursal_id)

    if resultado.get('ok'):
        return jsonify({'ok': True, 'respuesta': resultado['respuesta']})
    else:
        return jsonify({'ok': False, 'error': resultado.get('error', 'Error desconocido')}), 500
