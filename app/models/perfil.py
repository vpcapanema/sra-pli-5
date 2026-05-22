from app import db
from app.models.mixins import AuditoriaMixin


class Perfil(db.Model, AuditoriaMixin):
    __tablename__ = 'perfis'

    id_perfil = db.Column(db.Integer, primary_key=True)
    nome_perfil = db.Column(db.String(100), unique=True, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True)

    usuarios = db.relationship('UsuarioPerfil', back_populates='perfil')
