from app import db
from app.models.mixins import AuditoriaMixin


class BibliotecaFormatacaoCanonica(db.Model, AuditoriaMixin):
    """Biblioteca de formatação canônica extraída de um DOCX modelo."""

    __tablename__ = 'bibliotecas_formatacao_canonica'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    id_biblioteca_formatacao_canonica = db.Column(
        db.Integer, primary_key=True
    )
    nome_biblioteca = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    arquivo_docx = db.Column(db.String(300), nullable=True)
    caminho_arquivo = db.Column(db.String(500), nullable=True)
    extraida = db.Column(db.Boolean, default=False)
    ativa = db.Column(db.Boolean, default=True)

    configuracoes_numeracao = db.relationship(
        'ConfiguracaoNumeracao',
        back_populates='biblioteca_formatacao'
    )
