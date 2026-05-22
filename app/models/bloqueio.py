from app import db
from app.models.mixins import AuditoriaMixin


class Bloqueio(db.Model, AuditoriaMixin):
    __tablename__ = 'bloqueios'

    id_bloqueio = db.Column(db.Integer, primary_key=True)
    id_relatorio = db.Column(
        db.Integer,
        db.ForeignKey('relatorios_producao.id'),
        nullable=False
    )
    motivo_bloqueio = db.Column(db.Text, nullable=False)
    ativo = db.Column(db.Boolean, default=True)

    relatorio = db.relationship('RelatorioProducao', back_populates='bloqueios')
