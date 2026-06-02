"""Modelo de usuário do sistema SRA."""

from flask_login import UserMixin
from app import db


class Usuario(db.Model, UserMixin):
    """Modelo de usuário do sistema.

    Representa um usuário do SRA com autenticação, perfil e notificações.
    """
    __tablename__ = 'usuarios'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    email_secundario = db.Column(db.String(200), nullable=True)
    nome_de_usuario = db.Column(db.String(100), nullable=False, unique=True)
    senha_hash = db.Column(db.String(256), nullable=False)
    perfil_id = db.Column(
        db.Integer,
        db.ForeignKey('dominios.id_dominio'),
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

    perfil = db.relationship('Dominio')
    notificacoes = db.relationship(
        'Notificacao', back_populates='usuario'
    )

    __table_args__ = (
        db.UniqueConstraint(
            'email',
            'perfil_id',
            name='uq_usuarios_email_perfil'
        ),
    )

    def get_id(self):
        return str(self.id)
