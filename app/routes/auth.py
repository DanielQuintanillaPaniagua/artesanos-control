# app/routes/auth.py
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User

bp = Blueprint('auth', __name__)


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Inicio de sesion."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        password = request.form.get('password', '')

        user = User.query.filter_by(usuario=usuario).first()

        if user is None or not user.check_password(password):
            flash('Usuario o contrasena incorrectos', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user)
        flash(f'Bienvenido, {user.nombre}', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('login.html')


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesion correctamente', 'info')
    return redirect(url_for('auth.login'))
