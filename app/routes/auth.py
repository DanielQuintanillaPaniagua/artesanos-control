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

        # 1. Usuario o contrasena incorrectos
        if user is None or not user.check_password(password):
            flash('Usuario o contrasena incorrectos', 'danger')
            return redirect(url_for('auth.login'))

        # 2. Usuario inactivo
        if user.estado != 'Activo':
            flash('Tu cuenta esta inactiva. Contacta al administrador.', 'danger')
            return redirect(url_for('auth.login'))

        # 3. Empleado sin sucursal asignada
        if user.is_empleado() and not user.sucursal_id:
            flash('Tu cuenta no tiene una sucursal asignada. Contacta al administrador.', 'danger')
            return redirect(url_for('auth.login'))

        # 4. Empleado con sucursal inactiva
        if user.is_empleado() and user.sucursal and user.sucursal.estado != 'Activa':
            flash(f'La sucursal "{user.sucursal.nombre}" esta inactiva. Contacta al administrador.', 'danger')
            return redirect(url_for('auth.login'))

        # Todo OK
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
