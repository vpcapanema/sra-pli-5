from app import db
from app.models.mixins import AuditoriaMixin


class EnvioConteudo(db.Model, AuditoriaMixin):
    __tablename__ = 'envios_conteudo'

    id_envio_conteudo = db.Column(db.Integer, primary_key=True)
    id_relatorio = db.Column(
        db.Integer,
        db.ForeignKey('relatorios_producao.id'),
        nullable=False
    )
    id_usuario = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id'),
        nullable=False
    )
    nome_arquivo = db.Column(db.String(300), nullable=False)
    caminho_arquivo = db.Column(db.String(500), nullable=False)
    status_envio = db.Column(db.String(50), nullable=False, default='pendente')

    relatorio = db.relationship('RelatorioProducao', back_populates='envios')
    previsualizacoes = db.relationship(
        'PrevisualizacaoConteudo', back_populates='envio'
    )
