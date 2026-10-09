from pathlib import Path
from flask import Blueprint, render_template, abort, request, redirect, url_for, flash, Response
import csv
import io
from flask_login import login_required, current_user
from datetime import date, datetime

from app import db
from app.models.user import User
from app.models.sucursal import Sucursal
from app.models.factura import Factura
from app.models.detalle_factura import DetalleFactura

bp = Blueprint('admin', __name__, url_prefix='/admin')


def _solo_owner():
    if not current_user.is_owner():
        abort(403)


# ==================================================
# PANEL PRINCIPAL
# ==================================================
@bp.route('/')
@login_required
def index():
    _solo_owner()

    hoy = date.today()
    inicio_mes = hoy.replace(day=1)

    usuarios_activos = User.query.filter_by(estado='Activo').count()
    total_usuarios = User.query.count()
    total_sucursales = Sucursal.query.count()
    sucursales_activas = Sucursal.query.filter_by(estado='Activa').count()

    facturas_mes = Factura.query.filter(Factura.fecha >= inicio_mes).all()
    total_facturas_mes = len(facturas_mes)
    total_observadas = sum(1 for f in facturas_mes if f.estado == 'Observada')

    usuarios = User.query.order_by(User.id.desc()).limit(5).all()

    sucursales_data = []
    for s in Sucursal.query.order_by(Sucursal.nombre).all():
        facturas_suc = [f for f in facturas_mes if f.sucursal_id == s.id]
        sucursales_data.append({
            'obj': s,
            'facturas_mes': len(facturas_suc),
        })

    return render_template(
        'admin/index.html',
        usuarios_activos=usuarios_activos,
        total_usuarios=total_usuarios,
        total_sucursales=total_sucursales,
        sucursales_activas=sucursales_activas,
        total_facturas_mes=total_facturas_mes,
        total_observadas=total_observadas,
        usuarios=usuarios,
        sucursales_data=sucursales_data,
    )


# ==================================================
# USUARIOS
# ==================================================
@bp.route('/usuarios')
@login_required
def usuarios():
    _solo_owner()

    # Supervisor solo ve usuarios de su sucursal
    query = User.query
    if current_user.is_supervisor():
        query = query.filter(User.sucursal_id == current_user.sucursal_id)

    usuarios = query.order_by(User.nombre).all()
    return render_template('admin/usuarios.html', usuarios=usuarios)


@bp.route('/usuarios/nuevo', methods=['GET', 'POST'])
@login_required
def usuario_nuevo():
    _solo_owner()
    sucursales = Sucursal.query.order_by(Sucursal.nombre).all()

    # Supervisor: solo puede crear usuarios en su propia sucursal
    if current_user.is_supervisor():
        sucursales = [s for s in sucursales if s.id == current_user.sucursal_id]
    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()
        usuario = (request.form.get('usuario') or '').strip().lower()
        email = (request.form.get('email') or '').strip().lower() or None
        rol = request.form.get('rol') or 'empleado'
        sucursal_id = request.form.get('sucursal_id', type=int)
        password = request.form.get('password') or ''

        # Supervisor: forzar su propia sucursal y bloquear crear owners
        if current_user.is_supervisor():
            sucursal_id = current_user.sucursal_id
            if rol == 'owner':
                flash('Un supervisor no puede crear administradores.', 'danger')
                return render_template('admin/usuario_form.html', modo='nuevo',
                                       usuario=None, sucursales=sucursales, form_data=request.form)

        # Validaciones
        errores = []
        if not nombre or len(nombre) < 3:
            errores.append('El nombre debe tener al menos 3 caracteres.')
        if not usuario or len(usuario) < 3:
            errores.append('El usuario debe tener al menos 3 caracteres.')
        if len(password) < 6:
            errores.append('La contrasena debe tener al menos 6 caracteres.')
        if User.query.filter_by(usuario=usuario).first():
            errores.append(f'El usuario "{usuario}" ya existe.')
        if email and User.query.filter_by(email=email).first():
            errores.append(f'El email "{email}" ya esta en uso.')
        if rol not in ('owner', 'empleado', 'supervisor'):
            errores.append('Rol invalido.')
        # Owner: sucursal obligatoria
        if rol in ('empleado', 'supervisor') and not sucursal_id:
            errores.append('Los empleados y supervisores deben tener una sucursal asignada.')
        if sucursal_id and not Sucursal.query.get(sucursal_id):
            errores.append('La sucursal seleccionada no existe.')

        if errores:
            for e in errores:
                flash(e, 'danger')
            return render_template(
                'admin/usuario_form.html',
                modo='nuevo',
                usuario=None,
                sucursales=sucursales,
                form_data=request.form,
            )

        # Crear
        u = User(
            nombre=nombre,
            usuario=usuario,
            email=email,
            rol=rol,
            sucursal_id=sucursal_id if rol in ('empleado', 'supervisor') else None,
            estado='Activo',
        )
        u.set_password(password)
        db.session.add(u)
        db.session.commit()

        flash(f'Usuario "{u.nombre}" creado correctamente.', 'success')
        return redirect(url_for('admin.usuarios'))

    return render_template(
        'admin/usuario_form.html',
        modo='nuevo',
        usuario=None,
        sucursales=sucursales,
        form_data={},
    )


@bp.route('/usuarios/<int:user_id>/editar', methods=['GET', 'POST'])
@login_required
def usuario_editar(user_id):
    _solo_owner()
    u = User.query.get_or_404(user_id)

    # Supervisor: solo puede editar usuarios de su sucursal
    if current_user.is_supervisor() and u.sucursal_id != current_user.sucursal_id:
        abort(403)

    sucursales = Sucursal.query.order_by(Sucursal.nombre).all()

    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()
        usuario = (request.form.get('usuario') or '').strip().lower()
        email = (request.form.get('email') or '').strip().lower() or None
        rol = request.form.get('rol') or 'empleado'
        sucursal_id = request.form.get('sucursal_id', type=int)
        password = (request.form.get('password') or '').strip()

        # Supervisor: forzar su propia sucursal y bloquear crear owners
        if current_user.is_supervisor():
            sucursal_id = current_user.sucursal_id
            if rol == 'owner':
                flash('Un supervisor no puede promover a administrador.', 'danger')
                return render_template('admin/usuario_form.html', modo='editar',
                                       usuario=u, sucursales=sucursales, form_data=request.form)

        errores = []
        if not nombre or len(nombre) < 3:
            errores.append('El nombre debe tener al menos 3 caracteres.')
        if not usuario or len(usuario) < 3:
            errores.append('El usuario debe tener al menos 3 caracteres.')
        # Usuario unico (excepto el mismo)
        existe = User.query.filter(User.usuario == usuario, User.id != u.id).first()
        if existe:
            errores.append(f'El usuario "{usuario}" ya existe.')
        if email:
            existe_email = User.query.filter(User.email == email, User.id != u.id).first()
            if existe_email:
                errores.append(f'El email "{email}" ya esta en uso.')
        if rol not in ('owner','supervisor','empleado'):
            errores.append('Rol invalido.')
        if rol in ('empleado', 'supervisor') and not sucursal_id:
            errores.append('Los empleados y supervisores deben tener una sucursal asignada.')
        # Password opcional: si se ingresa, minimo 6
        if password and len(password) < 6:
            errores.append('La nueva contrasena debe tener al menos 6 caracteres.')
        # No desactivarse a si mismo
        nuevo_estado = request.form.get('estado', u.estado)
        if u.id == current_user.id and nuevo_estado != 'Activo':
            errores.append('No puedes desactivar tu propio usuario.')

        if errores:
            for e in errores:
                flash(e, 'danger')
            return render_template(
                'admin/usuario_form.html',
                modo='editar',
                usuario=u,
                sucursales=sucursales,
                form_data=request.form,
            )

        # Actualizar
        u.nombre = nombre
        u.usuario = usuario
        u.email = email
        u.rol = rol
        u.sucursal_id = sucursal_id if rol in ('empleado', 'supervisor') else None
        u.estado = nuevo_estado
        if password:
            u.set_password(password)

        db.session.commit()
        flash(f'Usuario "{u.nombre}" actualizado.', 'success')
        return redirect(url_for('admin.usuarios'))

    return render_template(
        'admin/usuario_form.html',
        modo='editar',
        usuario=u,
        sucursales=sucursales,
        form_data={},
    )


@bp.route('/usuarios/<int:user_id>/toggle-estado', methods=['POST'])
@login_required
def usuario_toggle_estado(user_id):
    _solo_owner()
    u = User.query.get_or_404(user_id)

    if u.id == current_user.id:
        flash('No puedes cambiar tu propio estado.', 'warning')
        return redirect(url_for('admin.usuarios'))

    u.estado = 'Inactivo' if u.estado == 'Activo' else 'Activo'
    db.session.commit()

    flash(f'Usuario "{u.nombre}" ahora esta {u.estado.lower()}.', 'success')
    return redirect(url_for('admin.usuarios'))


@bp.route('/usuarios/<int:user_id>/resetear-password', methods=['POST'])
@login_required
def usuario_resetear_password(user_id):
    _solo_owner()
    u = User.query.get_or_404(user_id)

    password = (request.form.get('password') or '').strip()
    confirmar = (request.form.get('confirmar') or '').strip()

    errores = []
    if len(password) < 6:
        errores.append('La contrasena debe tener al menos 6 caracteres.')
    if password != confirmar:
        errores.append('Las contrasenas no coinciden.')

    if errores:
        for e in errores:
            flash(e, 'danger')
        return redirect(url_for('admin.usuarios'))

    u.set_password(password)
    db.session.commit()

    flash(f'Contrasena de "{u.nombre}" actualizada correctamente.', 'success')
    return redirect(url_for('admin.usuarios'))

# ==================================================
# SUCURSALES
# ==================================================
@bp.route('/sucursales')
@login_required
def sucursales():
    _solo_owner()

    hoy = date.today()
    inicio_mes = hoy.replace(day=1)

    sucursales_data = []
    for s in Sucursal.query.order_by(Sucursal.nombre).all():
        facturas_suc = Factura.query.filter(
            Factura.fecha >= inicio_mes,
            Factura.sucursal_id == s.id,
        ).count()
        usuarios_suc = User.query.filter_by(sucursal_id=s.id).count()
        sucursales_data.append({
            'obj': s,
            'facturas_mes': facturas_suc,
            'usuarios': usuarios_suc,
        })

    return render_template('admin/sucursales.html', sucursales_data=sucursales_data)


@bp.route('/sucursales/nueva', methods=['GET', 'POST'])
@login_required
def sucursal_nueva():
    _solo_owner()

    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()
        direccion = (request.form.get('direccion') or '').strip() or None
        telefono = (request.form.get('telefono') or '').strip() or None
        estado = request.form.get('estado') or 'Activa'

        errores = []
        if not nombre or len(nombre) < 3:
            errores.append('El nombre debe tener al menos 3 caracteres.')
        if Sucursal.query.filter(Sucursal.nombre.ilike(nombre)).first():
            errores.append(f'Ya existe una sucursal con el nombre "{nombre}".')
        if estado not in ('Activa', 'Inactiva'):
            errores.append('Estado invalido.')

        if errores:
            for e in errores:
                flash(e, 'danger')
            return render_template(
                'admin/sucursal_form.html',
                modo='nueva',
                sucursal=None,
                form_data=request.form,
            )

        s = Sucursal(
            nombre=nombre,
            direccion=direccion,
            telefono=telefono,
            estado=estado,
        )
        db.session.add(s)
        db.session.commit()

        flash(f'Sucursal "{s.nombre}" creada correctamente.', 'success')
        return redirect(url_for('admin.sucursales'))

    return render_template(
        'admin/sucursal_form.html',
        modo='nueva',
        sucursal=None,
        form_data={},
    )


@bp.route('/sucursales/<int:sucursal_id>/editar', methods=['GET', 'POST'])
@login_required
def sucursal_editar(sucursal_id):
    _solo_owner()
    s = Sucursal.query.get_or_404(sucursal_id)

    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()
        direccion = (request.form.get('direccion') or '').strip() or None
        telefono = (request.form.get('telefono') or '').strip() or None
        estado = request.form.get('estado') or 'Activa'

        errores = []
        if not nombre or len(nombre) < 3:
            errores.append('El nombre debe tener al menos 3 caracteres.')
        # Nombre unico (excepto la misma)
        existe = Sucursal.query.filter(
            Sucursal.nombre.ilike(nombre),
            Sucursal.id != s.id,
        ).first()
        if existe:
            errores.append(f'Ya existe otra sucursal con el nombre "{nombre}".')
        if estado not in ('Activa', 'Inactiva'):
            errores.append('Estado invalido.')

        if errores:
            for e in errores:
                flash(e, 'danger')
            return render_template(
                'admin/sucursal_form.html',
                modo='editar',
                sucursal=s,
                form_data=request.form,
            )

        s.nombre = nombre
        s.direccion = direccion
        s.telefono = telefono
        s.estado = estado

        db.session.commit()
        flash(f'Sucursal "{s.nombre}" actualizada.', 'success')
        return redirect(url_for('admin.sucursales'))

    return render_template(
        'admin/sucursal_form.html',
        modo='editar',
        sucursal=s,
        form_data={},
    )


@bp.route('/sucursales/<int:sucursal_id>/toggle-estado', methods=['POST'])
@login_required
def sucursal_toggle_estado(sucursal_id):
    _solo_owner()
    s = Sucursal.query.get_or_404(sucursal_id)

    s.estado = 'Inactiva' if s.estado == 'Activa' else 'Activa'
    db.session.commit()

    flash(f'Sucursal "{s.nombre}" ahora esta {s.estado.lower()}.', 'success')
    return redirect(url_for('admin.sucursales'))


# ==================================================
# REPORTES CSV
# ==================================================
def _csv_response(rows, headers, filename):
    """Genera una respuesta CSV descargable con BOM UTF-8 (compatible Excel)."""
    output = io.StringIO()
    output.write('\ufeff')  # BOM para Excel
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)

    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )


@bp.route('/reportes')
@login_required
def reportes():
    _solo_owner()
    sucursales = Sucursal.query.order_by(Sucursal.nombre).all()
    return render_template('admin/reportes.html', sucursales=sucursales)


@bp.route('/reportes/facturas.csv')
@login_required
def reporte_facturas_csv():
    _solo_owner()

    desde_str = (request.args.get('desde') or '').strip()
    hasta_str = (request.args.get('hasta') or '').strip()
    sucursal_id = request.args.get('sucursal', type=int)
    estado = (request.args.get('estado') or '').strip()

    query = Factura.query

    if desde_str:
        try:
            desde = datetime.strptime(desde_str, '%Y-%m-%d').date()
            query = query.filter(Factura.fecha >= desde)
        except ValueError:
            pass
    if hasta_str:
        try:
            hasta = datetime.strptime(hasta_str, '%Y-%m-%d').date()
            query = query.filter(Factura.fecha <= hasta)
        except ValueError:
            pass
    if sucursal_id:
        query = query.filter(Factura.sucursal_id == sucursal_id)
    if estado:
        query = query.filter(Factura.estado == estado)

    facturas = query.order_by(Factura.fecha.desc(), Factura.id.desc()).all()

    headers = ['ID', 'Numero Factura', 'Fecha', 'Proveedor', 'Sucursal',
               'Usuario', 'Tipo Doc', 'Total', 'Estado', 'Observacion']
    rows = []
    for f in facturas:
        rows.append([
            f.id,
            f.numero_factura or '',
            f.fecha.strftime('%d/%m/%Y') if f.fecha else '',
            f.proveedor.nombre if f.proveedor else '',
            f.sucursal.nombre if f.sucursal else '',
            f.usuario.nombre if f.usuario else '',
            f.tipo_documento or '',
            f'{f.total_factura:.2f}' if f.total_factura else '0.00',
            f.estado or '',
            (f.observacion or '').replace('\n', ' ').replace('\r', ''),
        ])

    fecha_str = date.today().strftime('%Y%m%d')
    return _csv_response(rows, headers, f'facturas_{fecha_str}.csv')


@bp.route('/reportes/usuarios.csv')
@login_required
def reporte_usuarios_csv():
    _solo_owner()

    rol = (request.args.get('rol') or '').strip()
    sucursal_id = request.args.get('sucursal', type=int)
    estado = (request.args.get('estado') or '').strip()

    query = User.query
    if rol:
        query = query.filter(User.rol == rol)
    if sucursal_id:
        query = query.filter(User.sucursal_id == sucursal_id)
    if estado:
        query = query.filter(User.estado == estado)

    usuarios = query.order_by(User.nombre).all()

    headers = ['ID', 'Nombre', 'Usuario', 'Email', 'Rol', 'Sucursal', 'Estado']
    rows = []
    for u in usuarios:
        rows.append([
            u.id,
            u.nombre or '',
            u.usuario or '',
            u.email or '',
            u.rol or '',
            u.sucursal.nombre if u.sucursal else 'Todas',
            u.estado or '',
        ])

    fecha_str = date.today().strftime('%Y%m%d')
    return _csv_response(rows, headers, f'usuarios_{fecha_str}.csv')


@bp.route('/reportes/sucursales.csv')
@login_required
def reporte_sucursales_csv():
    _solo_owner()

    hoy = date.today()
    inicio_mes = hoy.replace(day=1)

    headers = ['ID', 'Nombre', 'Direccion', 'Telefono', 'Estado',
               'Usuarios', 'Facturas del mes', 'Monto del mes']
    rows = []
    for s in Sucursal.query.order_by(Sucursal.nombre).all():
        facturas_suc = Factura.query.filter(
            Factura.fecha >= inicio_mes,
            Factura.sucursal_id == s.id,
        ).all()
        usuarios_suc = User.query.filter_by(sucursal_id=s.id).count()
        monto = sum((f.total_factura or 0) for f in facturas_suc)

        rows.append([
            s.id,
            s.nombre or '',
            s.direccion or '',
            s.telefono or '',
            s.estado or '',
            usuarios_suc,
            len(facturas_suc),
            f'{monto:.2f}',
        ])

    fecha_str = date.today().strftime('%Y%m%d')
    return _csv_response(rows, headers, f'sucursales_{fecha_str}.csv')
    # ==================================================
# CONFIGURACION DEL SISTEMA
# ==================================================
from flask import send_file, jsonify
from app.services.system_service import (
    get_system_info, get_server_status, get_recent_logs,
    get_smtp_status, create_backup, limpiar_tokens_expirados,
    get_backup_dir,
)


@bp.route('/configuracion')
@login_required
def configuracion():
    _solo_owner()

    return render_template(
        'admin/configuracion.html',
        system_info=get_system_info(),
        server_status=get_server_status(),
        smtp_status=get_smtp_status(),
        logs=get_recent_logs(lines=50),
    )


@bp.route('/configuracion/backup', methods=['POST'])
@login_required
def configuracion_backup():
    _solo_owner()

    ok, resultado = create_backup()
    if ok:
        flash(f'Backup creado: {Path(resultado).name}', 'success')
    else:
        flash(f'Error al crear backup: {resultado}', 'danger')

    return redirect(url_for('admin.configuracion'))


@bp.route('/configuracion/backup/descargar')
@login_required
def configuracion_backup_descargar():
    _solo_owner()

    backup_dir = get_backup_dir()
    archivos = sorted(backup_dir.glob('*.sql'), key=lambda p: p.stat().st_mtime, reverse=True)

    if not archivos:
        flash('No hay backups disponibles. Crea uno primero.', 'warning')
        return redirect(url_for('admin.configuracion'))

    ultimo = archivos[0]
    return send_file(str(ultimo), as_attachment=True, download_name=ultimo.name)


@bp.route('/configuracion/test-email', methods=['POST'])
@login_required
def configuracion_test_email():
    _solo_owner()

    from app.services.email_service import enviar_email

    if not current_user.email:
        return jsonify({'ok': False, 'error': 'Tu usuario no tiene email configurado'}), 400

    html = """
    <div style="font-family:Arial,sans-serif;max-width:500px;margin:0 auto;padding:20px;">
        <h2 style="color:#0f4630;">Prueba de SMTP</h2>
        <p>Si estas viendo este correo, el sistema de envio de Artesanos Control funciona correctamente.</p>
        <p style="color:#6c7b83;font-size:12px;">Enviado desde el panel de administracion.</p>
    </div>
    """

    ok, error = enviar_email(
        current_user.email,
        'Prueba SMTP - Artesanos Control',
        html,
        'Prueba SMTP de Artesanos Control. Si ves este correo, todo funciona.'
    )

    if ok:
        return jsonify({'ok': True, 'mensaje': f'Correo enviado a {current_user.email}'})
    return jsonify({'ok': False, 'error': error}), 500


@bp.route('/configuracion/logs/descargar')
@login_required
def configuracion_logs_descargar():
    _solo_owner()

    logs = get_recent_logs(lines=500)
    contenido = '\n'.join(logs)

    from io import BytesIO
    buffer = BytesIO(contenido.encode('utf-8'))

    filename = f'logs_{date.today().strftime("%Y%m%d")}.txt'
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype='text/plain')


@bp.route('/configuracion/limpiar-tokens', methods=['POST'])
@login_required
def configuracion_limpiar_tokens():
    _solo_owner()

    try:
        total = limpiar_tokens_expirados()
        flash(f'{total} tokens expirados eliminados.', 'success')
    except Exception as e:
        flash(f'Error al limpiar: {e}', 'danger')

    return redirect(url_for('admin.configuracion'))
    # ==================================================
# REPORTES EXCEL
# ==================================================
from app.services.excel_service import (
    exportar_facturas_excel,
    exportar_usuarios_excel,
    exportar_sucursales_excel,
    importar_facturas_excel,
)
from app.models.categoria import Categoria
from app.models.proveedor import Proveedor


@bp.route('/reportes/facturas.xlsx')
@login_required
def reporte_facturas_excel():
    _solo_owner()

    desde_str = (request.args.get('desde') or '').strip()
    hasta_str = (request.args.get('hasta') or '').strip()
    sucursal_id = request.args.get('sucursal', type=int)
    estado = (request.args.get('estado') or '').strip()

    query = Factura.query

    if desde_str:
        try:
            desde = datetime.strptime(desde_str, '%Y-%m-%d').date()
            query = query.filter(Factura.fecha >= desde)
        except ValueError:
            pass
    if hasta_str:
        try:
            hasta = datetime.strptime(hasta_str, '%Y-%m-%d').date()
            query = query.filter(Factura.fecha <= hasta)
        except ValueError:
            pass
    if sucursal_id:
        query = query.filter(Factura.sucursal_id == sucursal_id)
    if estado:
        query = query.filter(Factura.estado == estado)

    facturas = query.order_by(Factura.fecha.asc(), Factura.id.asc()).all()
    categorias = Categoria.query.filter_by(estado='Activa').order_by(Categoria.orden).all()

    buffer = exportar_facturas_excel(facturas, categorias)
    filename = f'facturas_{date.today().strftime("%Y%m%d")}.xlsx'

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@bp.route('/reportes/usuarios.xlsx')
@login_required
def reporte_usuarios_excel():
    _solo_owner()

    usuarios = User.query.order_by(User.nombre).all()
    buffer = exportar_usuarios_excel(usuarios)
    filename = f'usuarios_{date.today().strftime("%Y%m%d")}.xlsx'

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@bp.route('/reportes/sucursales.xlsx')
@login_required
def reporte_sucursales_excel():
    _solo_owner()

    hoy = date.today()
    inicio_mes = hoy.replace(day=1)

    sucursales_data = []
    for s in Sucursal.query.order_by(Sucursal.nombre).all():
        facturas_suc = Factura.query.filter(
            Factura.fecha >= inicio_mes,
            Factura.sucursal_id == s.id,
        ).count()
        usuarios_suc = User.query.filter_by(sucursal_id=s.id).count()
        sucursales_data.append({
            'obj': s,
            'facturas_mes': facturas_suc,
            'usuarios': usuarios_suc,
        })

    buffer = exportar_sucursales_excel(sucursales_data)
    filename = f'sucursales_{date.today().strftime("%Y%m%d")}.xlsx'

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# ==================================================
# IMPORTAR FACTURAS DESDE EXCEL
# ==================================================
@bp.route('/importar', methods=['GET', 'POST'])
@login_required
def importar_excel():
    _solo_owner()

    sucursales = Sucursal.query.order_by(Sucursal.nombre).all()
    resultado = None

    if request.method == 'POST':
        archivo = request.files.get('archivo')
        sucursal_id = request.form.get('sucursal_id', type=int)

        if not archivo:
            flash('Debes seleccionar un archivo.', 'danger')
            return render_template('admin/importar.html', sucursales=sucursales)

        if not sucursal_id:
            flash('Debes elegir una sucursal.', 'danger')
            return render_template('admin/importar.html', sucursales=sucursales)

        if not archivo.filename.lower().endswith(('.xlsx', '.xls')):
            flash('El archivo debe ser Excel (.xlsx)', 'danger')
            return render_template('admin/importar.html', sucursales=sucursales)

        categorias = Categoria.query.filter_by(estado='Activa').all()
        ok, data, resumen = importar_facturas_excel(
            archivo.stream, categorias, sucursal_id, current_user.id
        )

        if not ok:
            flash(f'Error: {data}', 'danger')
            return render_template('admin/importar.html', sucursales=sucursales)

        # Insertar facturas
        importadas = 0
        proveedores_creados = 0

        for f_data in data:
            # Buscar o crear proveedor
            proveedor = None
            if f_data['detalle']:
                # Extraer nombre de proveedor (antes del primer guion)
                nombre_prov = f_data['detalle'].split(' - ')[0].strip()[:150]
                if nombre_prov:
                    proveedor = Proveedor.query.filter(
                        Proveedor.nombre.ilike(nombre_prov)
                    ).first()
                    if not proveedor:
                        proveedor = Proveedor(
                            nombre=nombre_prov,
                            estado='Activo',
                        )
                        db.session.add(proveedor)
                        db.session.flush()
                        proveedores_creados += 1

            # Crear factura
            factura = Factura(
                numero_factura=f'IMP-{datetime.now().strftime("%Y%m%d%H%M%S")}-{importadas+1}',
                fecha=f_data['fecha'],
                tipo_documento=f_data['tipo_documento'],
                detalle=f_data['detalle'],
                total_factura=f_data['total'],
                proveedor_id=proveedor.id if proveedor else None,
                sucursal_id=sucursal_id,
                usuario_id=current_user.id,
                estado='Validada',
            )
            db.session.add(factura)
            db.session.flush()

            for d in f_data['detalles']:
                detalle = DetalleFactura(
                    factura_id=factura.id,
                    categoria_id=d['categoria_id'],
                    monto=d['monto'],
                )
                db.session.add(detalle)

            importadas += 1

        db.session.commit()

        resultado = {
            'importadas': importadas,
            'proveedores_creados': proveedores_creados,
            'total_filas': resumen.get('total_filas', 0),
            'sin_fecha': resumen.get('sin_fecha', 0),
            'sin_monto': resumen.get('sin_monto', 0),
        }

        flash(f'{importadas} facturas importadas correctamente.', 'success')

    return render_template('admin/importar.html', sucursales=sucursales, resultado=resultado)


# ==================================================
# API DOCS
# ==================================================
@bp.route('/api-docs')
@login_required
def api_docs():
    _solo_owner()
    from flask import current_app
    total = len([r for r in current_app.url_map.iter_rules() if '/api/' in r.rule])
    return render_template('api_docs.html', total_endpoints=total)