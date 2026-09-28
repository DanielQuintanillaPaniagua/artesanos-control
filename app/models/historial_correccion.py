from datetime import datetime

from app import db  # AJUSTAR si su instancia db vive en otro lugar


class HistorialCorreccion(db.Model):
    """Registro de auditoría: cada vez que el Owner corrige una factura."""
    __tablename__ = "historial_correcciones"

    id = db.Column(db.Integer, primary_key=True)
    factura_id = db.Column(db.Integer, nullable=False, index=True)
    usuario_id = db.Column(db.Integer, nullable=False)
    usuario_nombre = db.Column(db.String(120), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    motivo = db.Column(db.String(300), nullable=False)
    antes = db.Column(db.Text, nullable=False)     # JSON con los valores anteriores
    despues = db.Column(db.Text, nullable=False)   # JSON con los valores nuevos 