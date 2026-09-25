from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from app.models.factura import Factura
from app.models.detalle_factura import DetalleFactura
from app.models.proveedor import Proveedor
from app.models.categoria import Categoria
from app.services.validacion import validar_factura

bp = Blueprint('facturas', __name__, url_prefix='/api/facturas')


@bp.route('/', methods=['GET'])
@login_required
def list_facturas():
    query = Factura.query
    if current_user.is_empleado():
        query = query.filter_by(sucursal_id=current_user.sucursal_id)

    facturas = query.order_by(Factura.fecha.desc()).all()
    return jsonify({
        'success': True,
        'total': len(facturas),
        'facturas': [f.to_dict(incluir_detalles=False) for f in facturas]
    })


@bp.route('/<int:id>', methods=['GET'])
@login_required
def get_factura(id):
    factura = Factura.query.get(id)
    if not factura:
        return jsonify({'success': False, 'error': 'Factura no encontrada'}), 404
    if current_user.is_empleado() and factura.sucursal_id != current_user.sucursal_id:
        return jsonify({'success': False, 'error': 'Sin permisos'}), 403
    return jsonify({'success': True, 'factura': factura.to_dict()})


@bp.route('/', methods=['POST'])
@login_required
def create_factura():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No se enviaron datos'}), 400

    numero = (data.get('numero_factura') or '').strip()
    proveedor_id = data.get('proveedor_id')
    fecha_str = data.get('fecha')
    tipo_documento = (data.get('tipo_documento') or '').strip()
    detalle = (data.get('detalle') or '').strip()
    total_factura = float(data.get('total_factura') or 0)
    detalles = data.get('detalles', [])

    if not numero:
        return jsonify({'success': False, 'error': 'Numero de factura obligatorio'}), 400
    if not detalles:
        return jsonify({'success': False, 'error': 'Debes ingresar al menos una categoria'}), 400

    es_valida, mensaje, _ = validar_factura(detalles, total_factura)
    estado = 'Validada' if es_valida else 'Observada'

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else date.today()
    except ValueError:
        fecha = date.today()

    sucursal_id = current_user.sucursal_id

    factura = Factura(
        numero_factura=numero, fecha=fecha, tipo_documento=tipo_documento,
        detalle=detalle, total_factura=total_factura, proveedor_id=proveedor_id,
        sucursal_id=sucursal_id, usuario_id=current_user.id,
        estado=estado, observacion=None if es_valida else mensaje
    )
    db.session.add(factura)
    db.session.flush()

    for d in detalles:
        monto = float(d.get('monto', 0))
        if monto > 0:
            db.session.add(DetalleFactura(
                factura_id=factura.id,
                categoria_id=d.get('categoria_id'),
                monto=monto
            ))

    db.session.commit()

    return jsonify({
        'success': True, 'message': mensaje,
        'es_valida': es_valida, 'factura': factura.to_dict()
    }), 201


@bp.route('/<int:id>', methods=['DELETE'])
@login_required
def delete_factura(id):
    factura = Factura.query.get(id)
    if not factura:
        return jsonify({'success': False, 'error': 'Factura no encontrada'}), 404
    if current_user.is_empleado() and factura.sucursal_id != current_user.sucursal_id:
        return jsonify({'success': False, 'error': 'Sin permisos'}), 403
    db.session.delete(factura)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Factura eliminada'})


# DATOS AUXILIARES PARA EL FORMULARIO

@bp.route('/categorias', methods=['GET'])
@login_required
def list_categorias():
    categorias = Categoria.query.filter_by(estado='Activa').order_by(Categoria.orden).all()
    return jsonify({
        'success': True,
        'categorias': [c.to_dict() for c in categorias]
    })


@bp.route('/proveedores', methods=['GET'])
@login_required
def list_proveedores():
    proveedores = Proveedor.query.filter_by(estado='Activo').order_by(Proveedor.nombre).all()
    return jsonify({
        'success': True,
        'proveedores': [p.to_dict() for p in proveedores]
    })