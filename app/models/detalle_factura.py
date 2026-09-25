from app import db


class DetalleFactura(db.Model):
    __tablename__ = 'detalle_factura'

    id = db.Column(db.Integer, primary_key=True)
    factura_id = db.Column(db.Integer, db.ForeignKey('facturas.id'), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=False)
    monto = db.Column(db.Float, default=0.0, nullable=False)

    categoria = db.relationship('Categoria', backref='detalles')

    def to_dict(self):
        return {
            'id': self.id,
            'factura_id': self.factura_id,
            'categoria_id': self.categoria_id,
            'categoria_nombre': self.categoria.nombre if self.categoria else None,
            'monto': self.monto
        }

    def __repr__(self):
        return f'<DetalleFactura {self.categoria_id}: {self.monto}>'