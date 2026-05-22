from app import db
from app.models.mixins import AuditoriaMixin


class Notificacao(db.Model, AuditoriaMixin):
    __tablename__ = 'notificacoes'

    id_notificacao = db.Column(db.Integer, primary_key=True)
    id_usuario_destino = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id'),
        nullable=False
    )
    tipo_notificacao = db.Column(db.String(50), nullable=False)
    mensagem = db.Column(db.Text, nullable=False)
    lida = db.Column(db.Boolean, default=False)

    usuario = db.relationship('Usuario', back_populates='notificacoes')
