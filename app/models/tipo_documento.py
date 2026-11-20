from datetime import datetime
from app import db


# Tipos que existian antes de que el Owner pudiera crear los suyos.
# (codigo = lo que se guarda en la factura y sale en el Excel, etiqueta = lo que ve el usuario)
TIPOS_BASE = [
    ('FCC', 'FCC (Factura Consumidor Final)'),
    ('FC', 'FC (Factura Comercial)'),
    ('NOTA DE ENVIO', 'Nota de envio'),
    ('OTROS', 'Otros'),
]


class TipoDocumento(db.Model):
    __tablename__ = 'tipos_documento'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), nullable=False, unique=True)
    etiqueta = db.Column(db.String(80), nullable=False)
    estado = db.Column(db.String(20), default='Activo', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def asegurar_base(cls):
        """Crea los tipos originales si la tabla esta vacia (idempotente)."""
        if cls.query.count() > 0:
            return
        for codigo, etiqueta in TIPOS_BASE:
            db.session.add(cls(codigo=codigo, etiqueta=etiqueta, estado='Activo'))
        db.session.commit()

    @classmethod
    def activos(cls):
        """Tipos activos para el formulario: 'Otros' siempre al final."""
        cls.asegurar_base()
        return (
            cls.query.filter(cls.estado == 'Activo')
            .order_by(db.case((cls.codigo == 'OTROS', 1), else_=0), cls.id)
            .all()
        )

    def to_dict(self):
        return {'id': self.id, 'codigo': self.codigo, 'etiqueta': self.etiqueta, 'estado': self.estado}

    def __repr__(self):
        return f'<TipoDocumento {self.codigo}>'