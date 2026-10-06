import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user

from app import db
from app.models.factura import Factura
from app.models.detalle_factura import DetalleFactura
from app.models.proveedor import Proveedor
from app.models.categoria import Categoria
from app.models.historial_correccion import HistorialCorreccion

editar_factura_bp = Blueprint("editar_factura", __name__)


def _no_es_owner():
    return not current_user.is_owner()


def _instantanea(factura, detalles):
    return {
        "proveedor_id": factura.proveedor_id,
        "fecha": factura.fecha.isoformat() if factura.fecha else None,
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
    historial = (
        HistorialCorreccion.query
        .filter_by(factura_id=factura.id)
        .order_by(HistorialCorreccion.fecha.desc())
        .limit(5)
        .all()
    )

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
        detalle = [
            (int(d["categoria_id"]), Decimal(str(d["monto"])))
            for d in datos["detalle"]
        ]
        proveedor_id = int(datos["proveedor_id"])
        fecha = datetime.strptime(datos["fecha"], "%Y-%m-%d").date()
    except (KeyError, ValueError, InvalidOperation, TypeError):
        return jsonify(error="Datos invalidos"), 400

    if any(m < 0 for _, m in detalle):
        return jsonify(error="Los montos por categoria no pueden ser negativos"), 400

    motivo = (datos.get("motivo") or "").strip()
    if len(motivo) < 5:
        return jsonify(error="Escribe el motivo de la correccion (minimo 5 caracteres)"), 400

    suma = sum((m for _, m in detalle), Decimal("0"))
    if total <= 0 or total != suma:
        diferencia = total - suma
        return jsonify(error=f"El desglose no coincide con la factura. Diferencia: ${diferencia}"), 400

    if not Proveedor.query.get(proveedor_id):
        return jsonify(error="Proveedor inexistente"), 400

    ids_cat = {c for c, _ in detalle}
    existentes = {c.id for c in Categoria.query.filter(Categoria.id.in_(ids_cat)).all()}
    faltantes = ids_cat - existentes
    if faltantes:
        return jsonify(error=f"Categorias inexistentes: {sorted(faltantes)}"), 400

    try:
        antes = _instantanea(
            factura,
            DetalleFactura.query.filter_by(factura_id=factura.id).all(),
        )

        factura.total_factura = float(total)
        factura.fecha = fecha
        factura.proveedor_id = proveedor_id
        factura.estado = "Validada"

        DetalleFactura.query.filter_by(factura_id=factura.id).delete()
        nuevos = [
            DetalleFactura(factura_id=factura.id, categoria_id=c, monto=float(m))
            for c, m in detalle
        ]
        db.session.add_all(nuevos)
        db.session.flush()

        despues = _instantanea(factura, nuevos)

        usuario_nombre = (
            getattr(current_user, "nombre", None)
            or getattr(current_user, "usuario", None)
            or f"user-{current_user.id}"
        )

        db.session.add(HistorialCorreccion(
            factura_id=factura.id,
            usuario_id=current_user.id,
            usuario_nombre=usuario_nombre,
            motivo=motivo,
            antes=json.dumps(antes),
            despues=json.dumps(despues),
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Error al guardar correccion de factura %s", factura_id
        )
        return jsonify(error="No se pudo guardar. Intenta de nuevo."), 500

    return jsonify(ok=True)
