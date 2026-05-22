from app import db
from app.models.mixins import AuditoriaMixin


class Revisao(db.Model, AuditoriaMixin):
    __tablename__ = 'revisoes'

    id_revisao = db.Column(db.Integer, primary_key=True)
    id_relatorio = db.Column(
        db.Integer,
        db.ForeignKey('relatorios_producao.id'),
        nullable=False
    )
    id_usuario_coordenador = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id'),
        nullable=False
    )
    status_revisao = db.Column(db.String(50), nullable=False)
    observacao = db.Column(db.Text, nullable=True)

    relatorio = db.relationship('RelatorioProducao', back_populates='revisoes')
    acoes = db.relationship('AcaoRevisao', back_populates='revisao')
