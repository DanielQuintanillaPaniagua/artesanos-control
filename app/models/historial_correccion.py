from datetime import datetime, timezone
from app import db


class HistorialCorreccion(db.Model):
    __tablename__ = "historial_correcciones"

    id = db.Column(db.Integer, primary_key=True)
    # ondelete='CASCADE': si se borra la factura, se borran sus correcciones.
    # Evita IntegrityError al eliminar facturas con historial.
    factura_id = db.Column(
        db.Integer,
        db.ForeignKey("facturas.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    usuario_nombre = db.Column(db.String(120), nullable=False)
    fecha = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    motivo = db.Column(db.String(300), nullable=False)
    antes = db.Column(db.Text, nullable=False)
    despues = db.Column(db.Text, nullable=False)

    factura = db.relationship("Factura", backref="historial_correcciones")
    usuario = db.relationship("User", backref="correcciones")