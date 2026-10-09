from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app import db

bp = Blueprint('perfil', __name__, url_prefix='/perfil')

def _solo_owner():
    """Owner y supervisor pueden gestionar su propia contrasena.
    Los empleados deben pedirle al admin que les cambie la clave."""
    if not (current_user.is_owner() or current_user.is_supervisor()):
        abort(403)


@bp.route('/')
@login_required
def index():
    _solo_owner()
    return render_template('perfil.html', usuario=current_user)


@bp.route('/cambiar-password', methods=['POST'])
@login_required
def cambiar_password():
    _solo_owner()

    actual = (request.form.get('actual') or '').strip()
    nueva = (request.form.get('nueva') or '').strip()
    confirmar = (request.form.get('confirmar') or '').strip()

    errores = []
    if not actual:
        errores.append('Debes ingresar tu contrasena actual.')
    elif not current_user.check_password(actual):
        errores.append('La contrasena actual no es correcta.')

    if len(nueva) < 6:
        errores.append('La nueva contrasena debe tener al menos 6 caracteres.')
    if nueva != confirmar:
        errores.append('Las contrasenas nuevas no coinciden.')
    if actual and nueva and actual == nueva:
        errores.append('La nueva contrasena debe ser diferente a la actual.')

    if errores:
        for e in errores:
            flash(e, 'danger')
        return redirect(url_for('perfil.index'))

    current_user.set_password(nueva)
    db.session.commit()

    flash('Contrasena actualizada correctamente.', 'success')
    return redirect(url_for('perfil.index'))
