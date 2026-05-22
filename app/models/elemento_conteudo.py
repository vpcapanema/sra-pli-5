from app import db
from app.models.mixins import AuditoriaMixin


class ElementoConteudo(db.Model, AuditoriaMixin):
    __tablename__ = 'elementos_conteudo'

    id_elemento_conteudo = db.Column(db.Integer, primary_key=True)
    id_capitulo_documento = db.Column(
        db.Integer,
        db.ForeignKey('capitulos_documento.id_capitulo_documento'),
        nullable=False
    )
    tipo_elemento = db.Column(db.String(50), nullable=False)
    ordem_elemento = db.Column(db.Integer, nullable=False)
    numero_elemento = db.Column(db.Integer, nullable=True)
    conteudo_original = db.Column(db.Text, nullable=True)
    conteudo_processado = db.Column(db.Text, nullable=True)
    propriedades_formatacao_json = db.Column(db.Text, nullable=True)

    capitulo = db.relationship('CapituloDocumento', back_populates='elementos')
