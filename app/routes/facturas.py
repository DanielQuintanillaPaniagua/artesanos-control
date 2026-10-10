from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from app import db
from app.models.factura import Factura
from app.models.detalle_factura import DetalleFactura
from app.models.proveedor import Proveedor
from app.models.categoria import Categoria
from app.services.validacion import validar_factura
import math
bp = Blueprint('facturas', __name__, url_prefix='/api/facturas')

def _parsear_numero(valor, nombre='valor'):
    """Convierte un valor a float de forma segura.
    
    Devuelve (float, None) si es valido, o (None, mensaje_error) si no.
    """
    if valor is None:
        return 0.0, None
    try:
        numero = float(valor)
    except (ValueError, TypeError):
        return None, f'{nombre} debe ser un numero valido'
    
    if not math.isfinite(numero):
        return None, f'{nombre} debe ser un numero finito'
    
    return numero, None

def _sucursal_activa(user):
    """Verifica que el usuario tenga sucursal activa."""
    if not (user.is_empleado() or user.is_supervisor()):
        return False, 'Solo los empleados y supervisores pueden registrar facturas'
    if not user.sucursal_id:
        return False, 'Tu cuenta no tiene una sucursal asignada'
    if not user.sucursal or user.sucursal.estado != 'Activa':
        return False, 'Tu sucursal esta inactiva. No podes registrar facturas'
    return True, None


@bp.route('/', methods=['GET'])
@login_required
def list_facturas():
    query = Factura.query
    # Todos los que NO son owner ven solo su sucursal (empleado + supervisor)
    if not current_user.is_owner():
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
    # Todos los que NO son owner solo pueden ver facturas de su sucursal
    if not current_user.is_owner() and factura.sucursal_id != current_user.sucursal_id:
        return jsonify({'success': False, 'error': 'Sin permisos'}), 403
    return jsonify({'success': True, 'factura': factura.to_dict()})


@bp.route('/', methods=['POST'])
@login_required
def create_factura():
    # === BLOQUEO: empleado con sucursal activa ===
    ok, error = _sucursal_activa(current_user)
    if not ok:
        return jsonify({'success': False, 'error': error}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No se enviaron datos'}), 400

    numero = (data.get('numero_factura') or '').strip()
    proveedor_id = data.get('proveedor_id')
    fecha_str = data.get('fecha')
    tipo_documento = (data.get('tipo_documento') or '').strip()
    detalle = (data.get('detalle') or '').strip()
    total_factura, err = _parsear_numero(data.get('total_factura'), 'El total')
    if err:
        return jsonify({'success': False, 'error': err}), 400
    detalles = data.get('detalles', [])

    # 1. Validar campos requeridos
    if not numero:
        return jsonify({'success': False, 'error': 'Numero de factura obligatorio'}), 400

    if not detalles:
        return jsonify({'success': False, 'error': 'Debes ingresar al menos una categoria'}), 400

    # 2. Validar que los montos sean positivos
    for d in detalles:
        monto, err = _parsear_numero(d.get('monto'), 'El monto')
        if err:
            return jsonify({'success': False, 'error': err}), 400
        if monto < 0:
            return jsonify({
                'success': False,
                'error': 'El monto de una categoria no puede ser negativo'
            }), 400

    # 3. Validar el total
    if total_factura <= 0:
        return jsonify({
            'success': False,
            'error': 'El total de la factura debe ser mayor a cero'
        }), 400

        # 4. Validar la suma
    suma_detalles = sum(
        _parsear_numero(d.get('monto'))[0] or 0
        for d in detalles
    )
    if suma_detalles > total_factura + 0.01:
        return jsonify({
            'success': False,
            'error': f'La suma de categorias (${suma_detalles:.2f}) supera el total de la factura (${total_factura:.2f})'
        }), 400

    # 5. Validar cuadre (ANTES de usarla)
    es_valida, mensaje, _ = validar_factura(detalles, total_factura)

    # 6. REGLA: empleados NO pueden guardar facturas descuadradas
    if not es_valida and current_user.is_empleado():
        return jsonify({
            'success': False,
            'error': f'El desglose no cuadra con el total. Diferencia: ${total_factura - suma_detalles:.2f}. Contacta a tu supervisor.',
            'requiere_revision': True
        }), 400

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
    # Solo el owner puede eliminar facturas
    if not current_user.is_owner():
        return jsonify({
            'success': False,
            'error': 'Solo el administrador puede eliminar facturas.'
        }), 403

    factura = Factura.query.get(id)
    if not factura:
        return jsonify({'success': False, 'error': 'Factura no encontrada'}), 404

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


@bp.route('/proveedores', methods=['POST'])
@login_required
def create_proveedor():
    """Crea un proveedor nuevo desde el formulario de facturas."""
    # === BLOQUEO: empleado con sucursal activa ===
    ok, error = _sucursal_activa(current_user)
    if not ok:
        return jsonify({'success': False, 'error': error}), 403

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No se enviaron datos'}), 400

    nombre = (data.get('nombre') or '').strip()
    telefono = (data.get('telefono') or '').strip()
    email = (data.get('email') or '').strip()

    if not nombre:
        return jsonify({'success': False, 'error': 'El nombre es obligatorio'}), 400

    existente = Proveedor.query.filter(
        Proveedor.nombre.ilike(nombre)
    ).first()
    if existente:
        return jsonify({
            'success': False,
            'error': 'Ya existe un proveedor con ese nombre',
            'proveedor': existente.to_dict()
        }), 409

    proveedor = Proveedor(
        nombre=nombre,
        telefono=telefono or None,
        email=email or None,
        estado='Activo'
    )
    db.session.add(proveedor)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Proveedor "{nombre}" creado',
        'proveedor': proveedor.to_dict()
    }), 201
