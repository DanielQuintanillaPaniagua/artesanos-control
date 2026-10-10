from datetime import datetime, timezone
from app import db

class Conversacion(db.Model):
    """Una conversacion del chat interno (general o por sucursal)."""
    __tablename__ = 'conversaciones'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'general', 'sucursal' o 'directo'
    sucursal_id = db.Column(db.Integer, db.ForeignKey('sucursales.id'), nullable=True)

    # Para chats directos (1 a 1 entre supervisores)
    usuario_a_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    usuario_b_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    sucursal = db.relationship('Sucursal')
    usuario_a = db.relationship('User', foreign_keys=[usuario_a_id])
    usuario_b = db.relationship('User', foreign_keys=[usuario_b_id])
    mensajes = db.relationship('Mensaje', backref='conversacion', cascade='all, delete-orphan')
    miembros = db.relationship('ConversacionMiembro', backref='conversacion', cascade='all, delete-orphan')

    def ultimo_mensaje(self):
        """Devuelve el ultimo mensaje de la conversacion."""
        return Mensaje.query.filter_by(conversacion_id=self.id).order_by(Mensaje.created_at.desc()).first()

    def to_dict(self, usuario_actual=None):
        ultimo = self.ultimo_mensaje()
        no_leidos = 0

        if usuario_actual:
            miembro = ConversacionMiembro.query.filter_by(
                conversacion_id=self.id,
                usuario_id=usuario_actual.id,
            ).first()
            if miembro:
                no_leidos = Mensaje.query.filter(
                    Mensaje.conversacion_id == self.id,
                    Mensaje.created_at > miembro.ultima_lectura,
                    Mensaje.usuario_id != usuario_actual.id,
                ).count()
            else:
                no_leidos = Mensaje.query.filter(
                    Mensaje.conversacion_id == self.id,
                    Mensaje.usuario_id != usuario_actual.id,
                ).count()

        return {
            'id': self.id,
            'nombre': self.nombre,
            'tipo': self.tipo,
            'sucursal_id': self.sucursal_id,
            'sucursal_nombre': self.sucursal.nombre if self.sucursal else None,
            'ultimo_mensaje': ultimo.contenido[:80] if ultimo else 'Sin mensajes',
            'ultimo_mensaje_usuario': ultimo.usuario.nombre if ultimo and ultimo.usuario else None,
            'ultimo_mensaje_fecha': ultimo.created_at.isoformat() if ultimo else None,
            'no_leidos': no_leidos,
        }

    def __repr__(self):
        return f'<Conversacion {self.nombre}>'


class Mensaje(db.Model):
    """Un mensaje dentro de una conversacion."""
    __tablename__ = 'mensajes'

    id = db.Column(db.Integer, primary_key=True)
    conversacion_id = db.Column(
        db.Integer,
        db.ForeignKey('conversaciones.id'),
        nullable=False,
        index=True,
    )
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id'),
        nullable=False,
        index=True,
    )
    contenido = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    usuario = db.relationship('User')

    def to_dict(self):
        return {
            'id': self.id,
            'conversacion_id': self.conversacion_id,
            'usuario_id': self.usuario_id,
            'usuario_nombre': self.usuario.nombre if self.usuario else 'Desconocido',
            'usuario_rol': self.usuario.rol if self.usuario else None,
            'usuario_sucursal': self.usuario.sucursal.nombre if self.usuario and self.usuario.sucursal else None,
            'contenido': self.contenido,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<Mensaje {self.id} de {self.usuario_nombre if hasattr(self, "usuario_nombre") else self.usuario_id}>'


class ConversacionMiembro(db.Model):
    """Relacion entre usuario y conversacion (con tracking de ultima lectura)."""
    __tablename__ = 'conversacion_miembros'

    id = db.Column(db.Integer, primary_key=True)
    conversacion_id = db.Column(
        db.Integer,
        db.ForeignKey('conversaciones.id'),
        nullable=False,
        index=True,
    )
    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id'),
        nullable=False,
        index=True,
    )
    ultima_lectura = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        db.UniqueConstraint('conversacion_id', 'usuario_id', name='uq_conv_user'),
    )

    def __repr__(self):
        return f'<ConversacionMiembro conv={self.conversacion_id} user={self.usuario_id}>'


