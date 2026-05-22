from app import db
from app.models.mixins import AuditoriaMixin


class Dominio(db.Model, AuditoriaMixin):
    __tablename__ = 'dominios'

    id_dominio = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False, index=True)
    valor = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(255), nullable=True)
    ativo = db.Column(db.Boolean, default=True)

    __table_args__ = (
        db.UniqueConstraint('tipo', 'valor', name='uq_dominio_tipo_valor'),
    )


class DomPerfilUsuario(db.Model):
    __tablename__ = 'dom_perfis_usuario'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=False, unique=True)
    descricao = db.Column(db.String(100), nullable=False)
    nivel_acesso = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(
        db.DateTime, default=db.func.now(), nullable=False
    )


class DomStatusRelatorio(db.Model):
    __tablename__ = 'dom_status_relatorios'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), nullable=False, unique=True)
    descricao = db.Column(db.String(100), nullable=False)
    ordem = db.Column(db.Integer, default=0)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(
        db.DateTime, default=db.func.now(), nullable=False
    )
