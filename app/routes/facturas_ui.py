from flask import Blueprint, render_template, request, abort, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import or_
from datetime import datetime, date

from app import db
from app.models.factura import Factura
from app.models.proveedor import Proveedor
from app.models.sucursal import Sucursal

bp = Blueprint('facturas_ui', __name__, url_prefix='/facturas')


def _parse_fecha(s):
    """Parsea 'YYYY-MM-DD' a date, o None si falla."""
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


@bp.route('/')
@login_required
def list_page():
    page = request.args.get('page', 1, type=int)
    q = (request.args.get('q') or '').strip()
    sucursal_id = request.args.get('sucursal', type=int)
    desde_str = request.args.get('desde', '').strip()
    hasta_str = request.args.get('hasta', '').strip()
    per_page = 10

    desde = _parse_fecha(desde_str)
    hasta = _parse_fecha(hasta_str)

    query = Factura.query

    # Rol
    if current_user.is_empleado():
        query = query.filter(Factura.sucursal_id == current_user.sucursal_id)
    elif sucursal_id:
        query = query.filter(Factura.sucursal_id == sucursal_id)

    # Rango de fechas
    if desde:
        query = query.filter(Factura.fecha >= desde)
    if hasta:
        query = query.filter(Factura.fecha <= hasta)

    # Busqueda
    if q:
        query = query.outerjoin(Proveedor, Factura.proveedor_id == Proveedor.id).filter(
            or_(
                Factura.numero_factura.ilike(f'%{q}%'),
                Proveedor.nombre.ilike(f'%{q}%'),
            )
        )

    facturas = (
        query.order_by(Factura.fecha.desc(), Factura.id.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    sucursales = Sucursal.query.filter_by(estado='Activa').order_by(Sucursal.nombre).all()

    return render_template(
        'facturas/list.html',
        facturas=facturas,
        q=q,
        sucursal_id=sucursal_id,
        sucursales=sucursales,
        desde=desde_str,
        hasta=hasta_str,
    )


@bp.route('/new')
@login_required
def create_page():
    if current_user.is_owner():
        flash('Solo los empleados pueden registrar facturas. Los administradores solo supervisan.', 'warning')
        return redirect(url_for('facturas_ui.list_page'))

    if not current_user.sucursal_id:
        flash('Tu cuenta no tiene una sucursal asignada. Contacta al administrador.', 'danger')
        return redirect(url_for('facturas_ui.list_page'))

    if not current_user.sucursal or current_user.sucursal.estado != 'Activa':
        flash('Tu sucursal esta inactiva. No podes registrar facturas.', 'danger')
        return redirect(url_for('facturas_ui.list_page'))

    return render_template('facturas/form.html')


@bp.route('/<int:factura_id>')
@login_required
def detail_page(factura_id):
    factura = Factura.query.get_or_404(factura_id)

    if current_user.is_empleado() and factura.sucursal_id != current_user.sucursal_id:
        abort(403)

    return render_template('facturas/detail.html', factura=factura)
