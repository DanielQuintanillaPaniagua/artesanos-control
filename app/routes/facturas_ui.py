from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('facturas_ui', __name__, url_prefix='/facturas')


@bp.route('/')
@login_required
def list_page():
    return render_template('facturas/list.html')


@bp.route('/new')
@login_required
def create_page():
    return render_template('facturas/form.html')