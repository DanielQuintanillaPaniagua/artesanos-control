from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from datetime import datetime, timezone

from app import db
from app.models.user import User, PasswordResetToken
from app.services.email_service import enviar_email_recuperacion


bp = Blueprint('recuperar', __name__, url_prefix='/recuperar')


# ============================================================
# PASO 1: Solicitar recuperacion (ingresa email)
# ============================================================
@bp.route('/', methods=['GET', 'POST'])
def solicitar():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()

        # Respuesta generica SIEMPRE (no revelar si el email existe)
        mensaje_generico = 'Si el correo esta registrado, te enviamos un link para restablecer tu contrasena.'

        if not email:
            flash('Debes ingresar un correo electronico.', 'danger')
            return render_template('recuperar/solicitar.html')

        user = User.query.filter(User.email == email).first()

        if user and user.estado == 'Activo':
            # Generar token
            token = PasswordResetToken.generar(user.id)

            # Armar link completo
            link = url_for('recuperar.cambiar_con_token', token=token.token, _external=True)

            # Enviar email (no bloquear si falla)
            ok, error = enviar_email_recuperacion(user.email, user.nombre, link)
            if not ok:
                current_app.logger.error(f"Error al enviar email a {email}: {error}")

        flash(mensaje_generico, 'info')
        return render_template('recuperar/solicitar.html')

    return render_template('recuperar/solicitar.html')


# ============================================================
# PASO 2: Cambiar contrasena con token
# ============================================================
@bp.route('/<token>', methods=['GET', 'POST'])
def cambiar_con_token(token):
    # Buscar token en la BD
    reset = PasswordResetToken.query.filter_by(token=token).first()

    # Validar
    if not reset:
        flash('El link de recuperacion no es valido o ya fue usado.', 'danger')
        return redirect(url_for('auth.login'))

    if not reset.es_valido():
        flash('El link de recuperacion expiro. Solicita uno nuevo.', 'danger')
        return redirect(url_for('recuperar.solicitar'))

    user = reset.user
    if not user or user.estado != 'Activo':
        flash('Tu cuenta no esta activa. Contacta al administrador.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        nueva = (request.form.get('nueva') or '').strip()
        confirmar = (request.form.get('confirmar') or '').strip()

        errores = []
        if len(nueva) < 6:
            errores.append('La contrasena debe tener al menos 6 caracteres.')
        if nueva != confirmar:
            errores.append('Las contrasenas no coinciden.')
        if user.check_password(nueva):
            errores.append('La nueva contrasena debe ser diferente a la actual.')

        if errores:
            for e in errores:
                flash(e, 'danger')
            return render_template('recuperar/cambiar.html', token=token, user=user)

        # Cambiar contrasena
        user.set_password(nueva)
        reset.usado = True
        db.session.commit()

        flash('Contrasena actualizada correctamente. Ya podes iniciar sesion.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('recuperar/cambiar.html', token=token, user=user)
