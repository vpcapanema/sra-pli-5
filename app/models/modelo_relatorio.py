from app import db
from app.models.mixins import AuditoriaMixin


class ModeloRelatorio(db.Model, AuditoriaMixin):
    __tablename__ = 'modelos_relatorio'

    id_modelo_relatorio = db.Column(db.Integer, primary_key=True)
    nome_modelo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True)

    relatorios_base = db.relationship(
        'RelatorioBase', back_populates='modelo'
    )
    relatorios_producao = db.relationship(
        'RelatorioProducao', back_populates='modelo'
    )
    relatorios_finalizados = db.relationship(
        'RelatorioFinalizado', back_populates='modelo'
    )
