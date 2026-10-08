from flask import Blueprint, render_template, abort
from flask_login import login_required, current_user

bp = Blueprint('artesanos_ai', __name__, url_prefix='/artesanos-ai')


@bp.route('/')
@login_required
def index():
    # Solo el owner puede acceder a Artesanos AI
    if not (current_user.is_owner() or current_user.is_supervisor()):
        abort(403)
    return render_template('artesanos-ai/index.html')
