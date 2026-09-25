from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.factura import Factura
from datetime import date

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
def index():
    hoy = date.today()
    inicio_mes = hoy.replace(day=1)

    facturas_mes = Factura.query.filter(
        Factura.fecha >= inicio_mes,
        Factura.sucursal_id == current_user.sucursal_id
    ).all() if current_user.sucursal_id else []

    total_facturas = len(facturas_mes)
    total_monto = sum(f.total_factura for f in facturas_mes)
    total_validadas = sum(1 for f in facturas_mes if f.estado == 'Validada')
    total_observadas = sum(1 for f in facturas_mes if f.estado == 'Observada')
    porcentaje = (total_validadas / total_facturas * 100) if total_facturas > 0 else 0

    desempeno = [{
        'sucursal': current_user.sucursal.nombre if current_user.sucursal else 'Sin sucursal',
        'total_facturas': total_facturas,
        'total_monto': total_monto,
        'validadas': total_validadas,
        'observadas': total_observadas,
        'porcentaje': round(porcentaje, 1)
    }]

    return render_template('dashboard.html',
        total_facturas=total_facturas,
        total_monto=total_monto,
        total_validadas=total_validadas,
        total_observadas=total_observadas,
        desempeno=desempeno
    )