from app import db
from app.models.mixins import AuditoriaMixin


# MODELO OBSOLETO - Substituído por RelatorioProducao
# Mantido apenas para referência durante migração
class VersaoTrabalho(db.Model, AuditoriaMixin):
    __tablename__ = 'versoes_trabalho'

    id_versao_trabalho = db.Column(db.Integer, primary_key=True)
    id_relatorio_base = db.Column(
        db.Integer,
        db.ForeignKey('relatorios_base.id_relatorio_base'),
        nullable=False
    )
    id_biblioteca_formatacao_canonica = db.Column(
        db.Integer,
        db.ForeignKey(
            'bibliotecas_formatacao_canonica'
            '.id_biblioteca_formatacao_canonica'
        ),
        nullable=True
    )
    titulo = db.Column(db.String(300), nullable=False)
    status_versao = db.Column(
        db.String(50), nullable=False, default='em_edicao'
    )
    bloqueado = db.Column(db.Boolean, default=False)

    # Relationships removidos - modelo obsoleto
    # relatorio_base = db.relationship(
    #     'RelatorioBase', back_populates='versoes_trabalho'
    # )
    # biblioteca_formatacao = db.relationship(
    #     'BibliotecaFormatacaoCanonica'
    # )
    # capitulos = db.relationship('CapituloDocumento', back_populates='versao_trabalho')
    # envios = db.relationship('EnvioConteudo', back_populates='versao_trabalho')
    # revisoes = db.relationship('Revisao', back_populates='versao_trabalho')
    # bloqueios = db.relationship('Bloqueio', back_populates='versao_trabalho')
