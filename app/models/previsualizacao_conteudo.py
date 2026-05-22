from app import db
from app.models.mixins import AuditoriaMixin


class PrevisualizacaoConteudo(db.Model, AuditoriaMixin):
    __tablename__ = 'previsualizacoes_conteudo'

    id_previsualizacao_conteudo = db.Column(db.Integer, primary_key=True)
    id_envio_conteudo = db.Column(
        db.Integer,
        db.ForeignKey('envios_conteudo.id_envio_conteudo'),
        nullable=False
    )
    tipo_previsualizacao = db.Column(db.String(50), nullable=False)
    caminho_saida = db.Column(db.String(500), nullable=True)
    resultado_html = db.Column(db.Text, nullable=True)

    envio = db.relationship('EnvioConteudo', back_populates='previsualizacoes')
