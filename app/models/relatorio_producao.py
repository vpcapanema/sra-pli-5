from app import db


class RelatorioProducao(db.Model):
    """Relatório em produção (versão de trabalho) no fluxo SRA."""

    __tablename__ = 'relatorios_producao'

    id = db.Column(db.Integer, primary_key=True)

    @property
    def id_versao_trabalho(self):
        """Alias para compatibilidade com rotas antigas."""
        return self.id
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
    codigo_d20 = db.Column(
        db.String(20), nullable=False, default='D-20'
    )
    numero_medicao = db.Column(db.Integer, nullable=False)
    mes_referencia = db.Column(db.Date, nullable=False)
    periodo_inicio = db.Column(db.Date, nullable=False)
    periodo_fim = db.Column(db.Date, nullable=False)
    titulo_curto = db.Column(db.String(300), nullable=True)
    status_id = db.Column(
        db.Integer,
        db.ForeignKey('dominios.id_dominio'),
        nullable=False
    )
    criado_por = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id'),
        nullable=False
    )
    criado_em = db.Column(
        db.DateTime, default=db.func.now(), nullable=False
    )
    atualizado_em = db.Column(db.DateTime, nullable=True)
    ano_referencia = db.Column(db.Integer, nullable=True)
    versao_atual = db.Column(
        db.String(20), nullable=False, default='R00'
    )
    bloqueio_edicao = db.Column(
        db.Boolean, default=False, nullable=False
    )
    caminho_template = db.Column(db.String(500), nullable=True)

    status = db.relationship('Dominio')
    criador = db.relationship('Usuario', foreign_keys=[criado_por])
    modelo = db.relationship('ModeloRelatorio', foreign_keys=[modelo_id])
    biblioteca = db.relationship(
        'BibliotecaFormatacaoCanonica',
        foreign_keys=[biblioteca_id]
    )
    capitulos = db.relationship(
        'CapituloDocumento', back_populates='relatorio'
    )
    envios = db.relationship(
        'EnvioConteudo', back_populates='relatorio'
    )
    revisoes = db.relationship(
        'Revisao', back_populates='relatorio'
    )
    bloqueios = db.relationship(
        'Bloqueio', back_populates='relatorio'
    )
    finalizacoes = db.relationship(
        'RelatorioFinalizado',
        back_populates='relatorio_producao'
    )
