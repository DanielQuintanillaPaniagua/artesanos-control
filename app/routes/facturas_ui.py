from flask import Blueprint, render_template, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_

from app import db
from app.models.factura import Factura
from app.models.proveedor import Proveedor
from app.models.sucursal import Sucursal

bp = Blueprint('facturas_ui', __name__, url_prefix='/facturas')


@bp.route('/')
@login_required
def list_page():
    page = request.args.get('page', 1, type=int)
    q = (request.args.get('q') or '').strip()
    sucursal_id = request.args.get('sucursal', type=int)
    per_page = 10

    query = Factura.query

    # Empleado: forzado a su sucursal
    if current_user.is_empleado():
        query = query.filter(Factura.sucursal_id == current_user.sucursal_id)
    # Owner: filtra por la sucursal elegida (o ve todas si no elige)
    elif sucursal_id:
        query = query.filter(Factura.sucursal_id == sucursal_id)

    if q:
        query = query.outerjoin(Proveedor, Factura.proveedor_id == Proveedor.id).filter(
            or_(
                Factura.numero_factura.ilike(f'%{q}%'),
                Proveedor.nombre.ilike(f'%{q}%')
            )
        )

    facturas = query.order_by(Factura.fecha.desc(), Factura.id.desc()) \
                   .paginate(page=page, per_page=per_page, error_out=False)

    sucursales = Sucursal.query.order_by(Sucursal.nombre).all()

    return render_template(
        'facturas/list.html',
        facturas=facturas,
        q=q,
        sucursal_id=sucursal_id,
        sucursales=sucursales,
    )


@bp.route('/new')
@login_required
def create_page():
    return render_template('facturas/form.html')


@bp.route('/<int:factura_id>')
@login_required
def detail_page(factura_id):
    factura = Factura.query.get_or_404(factura_id)

    if current_user.is_empleado() and factura.sucursal_id != current_user.sucursal_id:
        abort(403)

    return render_template('facturas/detail.html', factura=factura)
