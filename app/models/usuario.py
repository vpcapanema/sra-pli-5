from flask_login import UserMixin
from app import db


class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False, unique=True)
    email_secundario = db.Column(db.String(200), nullable=True)
    nome_de_usuario = db.Column(db.String(100), nullable=False, unique=True)
    senha_hash = db.Column(db.String(256), nullable=False)
    perfil_id = db.Column(
        db.Integer,
        db.ForeignKey('dom_perfis_usuario.id'),
        nullable=False
    )
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    notificacoes_ativas = db.Column(
        db.Boolean, default=True, nullable=False
    )
    email_verificado_em = db.Column(db.DateTime, nullable=True)
    token_convite = db.Column(db.String(128), nullable=True, unique=True)
    token_recuperacao = db.Column(db.String(128), nullable=True, unique=True)
    token_expiracao = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(
        db.DateTime, default=db.func.now(), nullable=False
    )
    atualizado_em = db.Column(db.DateTime, nullable=True)
    desativado_em = db.Column(db.DateTime, nullable=True)

    perfil = db.relationship('DomPerfilUsuario')
    notificacoes = db.relationship(
        'Notificacao', back_populates='usuario'
    )

    def get_id(self):
        return str(self.id)
