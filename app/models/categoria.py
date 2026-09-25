from datetime import datetime
from app import db


class Categoria(db.Model):
    __tablename__ = 'categorias'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    grupo = db.Column(db.String(50), nullable=True)
    orden = db.Column(db.Integer, default=0)
    estado = db.Column(db.String(20), default='Activa', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'grupo': self.grupo,
            'orden': self.orden
        }

    def __repr__(self):
        return f'<Categoria {self.nombre}>'