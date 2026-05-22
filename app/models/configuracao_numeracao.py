from app import db
from app.models.mixins import AuditoriaMixin


class ConfiguracaoNumeracao(db.Model, AuditoriaMixin):
    __tablename__ = 'configuracoes_numeracao'

    id_configuracao_numeracao = db.Column(db.Integer, primary_key=True)
    id_biblioteca_formatacao_canonica = db.Column(
        db.Integer,
        db.ForeignKey(
            'bibliotecas_formatacao_canonica'
            '.id_biblioteca_formatacao_canonica'
        ),
        nullable=False
    )
    tipo_entidade = db.Column(db.String(50), nullable=False)
    estilo_docx = db.Column(db.String(100), nullable=True)
    formato_numeracao = db.Column(db.String(50), nullable=False)
    separador = db.Column(db.String(10), nullable=True)
    prefixo = db.Column(db.String(50), nullable=True)
    herdar_indice_pai = db.Column(db.Boolean, default=False)
    reiniciar_por_capitulo = db.Column(db.Boolean, default=True)
    ordem_configuracao = db.Column(db.Integer, nullable=False)
    origem = db.Column(db.String(20), nullable=False, default='auto_detectado')
    padrao_ativo = db.Column(db.Boolean, default=True)

    biblioteca_formatacao = db.relationship(
        'BibliotecaFormatacaoCanonica',
        back_populates='configuracoes_numeracao'
    )
