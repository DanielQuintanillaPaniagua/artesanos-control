import json
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

# AJUSTAR estos imports si en tu proyecto se llaman distinto
from app import db
from app.models.factura import Factura
from app.models.detalle_factura import DetalleFactura
from app.models.proveedor import Proveedor
from app.models.categoria import Categoria
from app.models.historial_correccion import HistorialCorreccion  # NUEVO (tuyo)

editar_factura_bp = Blueprint("editar_factura", __name__)


def _no_es_owner():
    return current_user.rol != "owner"   # AJUSTAR: valor exacto del rol en User


def _instantanea(factura, detalles):
    """Foto de la factura para guardar en el historial (antes / después)."""
    return {
        "proveedor_id": factura.proveedor_id,
        "fecha": str(factura.fecha),
        "total": str(factura.total_factura),
        "detalle": {str(d.categoria_id): str(d.monto) for d in detalles},
    }


@editar_factura_bp.route("/facturas/<int:factura_id>/editar")
@login_required
def pantalla_editar(factura_id):
    if _no_es_owner():
        return "Acceso denegado", 403

    factura = Factura.query.get_or_404(factura_id)
    detalles = DetalleFactura.query.filter_by(factura_id=factura.id).all()
    historial = (HistorialCorreccion.query.filter_by(factura_id=factura.id)
                 .order_by(HistorialCorreccion.fecha.desc()).limit(5).all())

    return render_template(
        "facturas/editar_factura.html",
        factura=factura,
        proveedores=Proveedor.query.all(),
        categorias=Categoria.query.all(),
        montos={d.categoria_id: d.monto for d in detalles},
        historial=historial,
    )


@editar_factura_bp.route("/api/facturas/<int:factura_id>", methods=["PUT"])
@login_required
def guardar_correccion(factura_id):
    if _no_es_owner():
        return jsonify(error="Solo el administrador puede editar facturas"), 403

    factura = Factura.query.get_or_404(factura_id)
    datos = request.get_json(silent=True) or {}

    try:
        total = Decimal(str(datos["total_factura"]))
        detalle = [(int(d["categoria_id"]), Decimal(str(d["monto"])))
                   for d in datos["detalle"]]
        proveedor_id = int(datos["proveedor_id"])
    except (KeyError, ValueError, InvalidOperation, TypeError):
        return jsonify(error="Datos inválidos"), 400

    motivo = (datos.get("motivo") or "").strip()
    if len(motivo) < 5:
        return jsonify(error="Escribe el motivo de la corrección (mínimo 5 caracteres)"), 400

    # Validación exacta en el backend: la que manda, nunca la del navegador ni la IA
    suma = sum((m for _, m in detalle), Decimal("0"))
    if total <= 0 or total != suma:
        return jsonify(error=f"El desglose no coincide con la factura. Diferencia: ${total - suma}"), 400

    try:
        antes = _instantanea(factura, DetalleFactura.query.filter_by(factura_id=factura.id).all())

        factura.total_factura = total
        factura.fecha = datos["fecha"]        # si la columna es Date: datetime.strptime(...).date()
        factura.proveedor_id = proveedor_id
        factura.estado = "Validada"

        DetalleFactura.query.filter_by(factura_id=factura.id).delete()
        nuevos = [DetalleFactura(factura_id=factura.id, categoria_id=c, monto=m) for c, m in detalle]
        db.session.add_all(nuevos)

        despues = _instantanea(factura, nuevos)
        db.session.add(HistorialCorreccion(
            factura_id=factura.id,
            usuario_id=current_user.id,
            usuario_nombre=getattr(current_user, "nombre", str(current_user.id)),
            motivo=motivo,
            antes=json.dumps(antes),
            despues=json.dumps(despues),
        ))
        db.session.commit()      # factura + detalle + historial se guardan juntos o no se guarda nada
    except Exception:
        db.session.rollback()
        return jsonify(error="No se pudo guardar. Intenta de nuevo."), 500

    return jsonify(ok=True)