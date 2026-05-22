from app import db
from app.models.mixins import AuditoriaMixin


class AcaoRevisao(db.Model, AuditoriaMixin):
    __tablename__ = 'acoes_revisao'

    id_acao_revisao = db.Column(db.Integer, primary_key=True)
    id_revisao = db.Column(
        db.Integer,
        db.ForeignKey('revisoes.id_revisao'),
        nullable=False
    )
    tipo_acao = db.Column(db.String(50), nullable=False)
    descricao_acao = db.Column(db.Text, nullable=True)

    revisao = db.relationship('Revisao', back_populates='acoes')
