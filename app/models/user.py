from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    usuario = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), default='empleado', nullable=False)
    sucursal_id = db.Column(db.Integer, db.ForeignKey('sucursales.id'), nullable=True)
    estado = db.Column(db.String(20), default='Activo', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sucursal = db.relationship('Sucursal', backref='usuarios')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_owner(self):
        return self.rol == 'owner'

    def is_empleado(self):
        return self.rol == 'empleado'

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'usuario': self.usuario,
            'email': self.email,
            'rol': self.rol,
            'sucursal_id': self.sucursal_id,
            'sucursal_nombre': self.sucursal.nombre if self.sucursal else None,
            'estado': self.estado
        }

    def __repr__(self):
        return f'<User {self.usuario}>'