"""Modelo de relatórios finalizados do SRA."""

from app import db


class RelatorioFinalizado(db.Model):
    """Representa um relatório finalizado e exportado."""
    __tablename__ = 'relatorios_finalizados'

    id = db.Column(db.Integer, primary_key=True)
    relatorio_id = db.Column(
        db.Integer,
        db.ForeignKey('relatorios_producao.id'),
        nullable=True
    )
    modelo_id = db.Column(
        db.Integer,
        db.ForeignKey('modelos_relatorio.id_modelo_relatorio'),
        nullable=True
    )
    biblioteca_id = db.Column(
        db.Integer,
        db.ForeignKey(
            'bibliotecas_formatacao_canonica.'
            'id_biblioteca_formatacao_canonica'
        ),
        nullable=True
    )
    status_id = db.Column(
        db.Integer,
        db.ForeignKey('dom_status_relatorios.id'),
        nullable=True
    )
    snapshot_conteudo = db.Column(db.JSON, nullable=True)
    artefato_docx = db.Column(db.LargeBinary, nullable=True)
    nome_arquivo = db.Column(db.String(300), nullable=True)
    caminho_arquivo = db.Column(db.String(500), nullable=True)
    finalizado_por = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id'),
        nullable=False
    )
    data_finalizacao = db.Column(
        db.DateTime, default=db.func.now(), nullable=False
    )
    checksum_docx = db.Column(db.String(64), nullable=True)
    revisao_id = db.Column(db.Integer, nullable=True)
    codigo = db.Column(db.String(20), nullable=True)
    titulo = db.Column(db.String(300), nullable=True)
    mes_referencia = db.Column(db.Date, nullable=True)
    ano_referencia = db.Column(db.Integer, nullable=True)
    periodo_inicio = db.Column(db.Date, nullable=True)
    periodo_fim = db.Column(db.Date, nullable=True)
    numero_medicao = db.Column(db.Integer, nullable=True)
    versao = db.Column(
        db.String(20), nullable=False, default='R00'
    )
    sincronizado_em = db.Column(
        db.DateTime, default=db.func.now(), nullable=False
    )

    relatorio_producao = db.relationship(
        'RelatorioProducao', back_populates='finalizacoes'
    )
    finalizador = db.relationship(
        'Usuario', foreign_keys=[finalizado_por]
    )
    modelo = db.relationship('ModeloRelatorio', foreign_keys=[modelo_id])
    biblioteca = db.relationship(
        'BibliotecaFormatacaoCanonica',
        foreign_keys=[biblioteca_id]
    )
    status = db.relationship('DomStatusRelatorio', foreign_keys=[status_id])
