from datetime import datetime, date
from app import db


class Factura(db.Model):
    __tablename__ = 'facturas'

    id = db.Column(db.Integer, primary_key=True)
    numero_factura = db.Column(db.String(50), nullable=False, index=True)
    fecha = db.Column(db.Date, default=date.today, nullable=False)
    tipo_documento = db.Column(db.String(30), nullable=True)
    detalle = db.Column(db.String(200), nullable=True)
    total_factura = db.Column(db.Float, default=0.0, nullable=False)
    proveedor_id = db.Column(db.Integer, db.ForeignKey('proveedores.id'), nullable=True)
    sucursal_id = db.Column(db.Integer, db.ForeignKey('sucursales.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    estado = db.Column(db.String(20), default='Validada', nullable=False)
    observacion = db.Column(db.String(300), nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    proveedor = db.relationship('Proveedor', backref='facturas')
    sucursal = db.relationship('Sucursal', backref='facturas')
    usuario = db.relationship('User', backref='facturas')
    detalles = db.relationship('DetalleFactura', backref='factura', cascade='all, delete-orphan')

    def to_dict(self, incluir_detalles=True):
        data = {
            'id': self.id,
            'numero_factura': self.numero_factura,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'tipo_documento': self.tipo_documento,
            'detalle': self.detalle,
            'total_factura': self.total_factura,
            'proveedor_id': self.proveedor_id,
            'proveedor_nombre': self.proveedor.nombre if self.proveedor else None,
            'sucursal_id': self.sucursal_id,
            'sucursal_nombre': self.sucursal.nombre if self.sucursal else None,
            'usuario_nombre': self.usuario.nombre if self.usuario else None,
            'estado': self.estado,
            'observacion': self.observacion,
            'fecha_registro': self.fecha_registro.isoformat() if self.fecha_registro else None
        }
        if incluir_detalles:
            data['detalles'] = [d.to_dict() for d in self.detalles]
        return data

    def __repr__(self):
        return f'<Factura {self.numero_factura}>'