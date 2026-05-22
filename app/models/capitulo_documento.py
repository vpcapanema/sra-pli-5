from app import db
from app.models.mixins import AuditoriaMixin


class CapituloDocumento(db.Model, AuditoriaMixin):
    __tablename__ = 'capitulos_documento'

    id_capitulo_documento = db.Column(db.Integer, primary_key=True)
    id_relatorio = db.Column(
        db.Integer,
        db.ForeignKey('relatorios_producao.id'),
        nullable=False
    )
    id_capitulo_pai = db.Column(
        db.Integer,
        db.ForeignKey('capitulos_documento.id_capitulo_documento'),
        nullable=True
    )
    id_usuario_responsavel = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id'),
        nullable=True
    )
    ordem_capitulo = db.Column(db.Integer, nullable=False)
    nome_capitulo = db.Column(db.String(200), nullable=True)
    titulo_capitulo = db.Column(db.String(300), nullable=False)
    indice_capitulo = db.Column(db.String(50), nullable=True)
    nivel_capitulo = db.Column(db.Integer, nullable=False, default=1)
    status_capitulo = db.Column(
        db.String(50), nullable=False, default='em_edicao'
    )
    conteudo_docx = db.Column(db.LargeBinary, nullable=True)
    observacao_coordenador = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True)

    relatorio = db.relationship(
        'RelatorioProducao', back_populates='capitulos'
    )
    responsavel = db.relationship(
        'Usuario', foreign_keys=[id_usuario_responsavel]
    )
    capitulo_pai = db.relationship(
        'CapituloDocumento',
        remote_side=[id_capitulo_documento],
        backref='subcapitulos'
    )
    elementos = db.relationship('ElementoConteudo', back_populates='capitulo')
