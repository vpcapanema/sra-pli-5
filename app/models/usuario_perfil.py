from app import db
from app.models.mixins import AuditoriaMixin


class UsuarioPerfil(db.Model, AuditoriaMixin):
    __tablename__ = 'usuarios_perfis'

    id_usuario_perfil = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuarios.id_usuario'), nullable=False)
    id_perfil = db.Column(db.Integer, db.ForeignKey('perfis.id_perfil'), nullable=False)

    usuario = db.relationship('Usuario', back_populates='perfis')
    perfil = db.relationship('Perfil', back_populates='usuarios')
