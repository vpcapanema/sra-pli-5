from app import db
from app.models.mixins import AuditoriaMixin


class RegistroAuditoria(db.Model, AuditoriaMixin):
    __tablename__ = 'registros_auditoria'

    id_registro_auditoria = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id'),
        nullable=True
    )
    acao = db.Column(db.String(100), nullable=False)
    entidade = db.Column(db.String(100), nullable=False)
    identificador_entidade = db.Column(db.String(100), nullable=True)
    detalhe = db.Column(db.Text, nullable=True)
