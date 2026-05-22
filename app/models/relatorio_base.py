from app import db
from app.models.mixins import AuditoriaMixin


class RelatorioBase(db.Model, AuditoriaMixin):
    __tablename__ = 'relatorios_base'

    id_relatorio_base = db.Column(db.Integer, primary_key=True)
    id_modelo_relatorio = db.Column(
        db.Integer,
        db.ForeignKey('modelos_relatorio.id_modelo_relatorio'),
        nullable=False
    )
    titulo = db.Column(db.String(300), nullable=False)
    versao = db.Column(db.String(50), nullable=True)
    caminho_arquivo = db.Column(db.String(500), nullable=True)
    status_relatorio = db.Column(db.String(50), nullable=False, default='ativo')

    modelo = db.relationship('ModeloRelatorio', back_populates='relatorios_base')
    # versoes_trabalho = db.relationship('VersaoTrabalho', back_populates='relatorio_base')  # REMOVIDO: substituído por RelatorioProducao
