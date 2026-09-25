from datetime import datetime
from app import db 

class Sucursal(db.Model):
    __tablename__ = 'sucursales'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    direccion = db.Column(db.String(200), nullable=True)
    telefono = db.Column(db.String(30), nullable=True)
    estado = db.Column(db.String(20), default='Activa', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'direccion': self.direccion,
            'telefono': self.telefono,
            'estado': self.estado,
        }
    def __repr__(self):
        return f'<Sucursal {self.nombre}>'
    

    
    