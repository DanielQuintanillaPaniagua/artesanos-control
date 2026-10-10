from flask import Blueprint,render_template,abort
from flask_login import login_required, current_user

bp = Blueprint('chat_ui', __name__,url_prefix='/chat')

@bp.route('/')
@login_required
def index():
        # Solo owner y supervisor pueden usar el chat
    if not (current_user.is_owner() or current_user.is_supervisor()):
        abort(403)
    return render_template('chat/index.html')
