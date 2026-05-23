import secrets
from datetime import datetime, timedelta, timezone

from werkzeug.security import (
    generate_password_hash, check_password_hash
)
from app import db
from app.models.usuario import Usuario
from app.models.dominio import DomPerfilUsuario
from app.services.servico_email import ServicoEmail

PERFIS_VALIDOS = ('admin', 'coordenador', 'autor')
CONVITE_HORAS = 72
RESET_HORAS = 1


class ServicoUsuario:

    @staticmethod
    def autenticar(email, senha, perfil):
        # Converter perfil string para ID
        perfil_obj = DomPerfilUsuario.query.filter_by(
            codigo=perfil
        ).first()
        if not perfil_obj:
            return None

        usuario = Usuario.query.filter_by(
            email=email, perfil_id=perfil_obj.id
        ).first()
        if (
            usuario
            and usuario.ativo
            and usuario.senha_hash
            and check_password_hash(
                usuario.senha_hash, senha
            )
        ):
            return usuario
        return None

    @staticmethod
    def convidar_usuario(nome, email, perfil):
        if perfil not in PERFIS_VALIDOS:
            raise ValueError(
                f'Perfil inválido: {perfil}'
            )
        token = secrets.token_urlsafe(48)
        expiracao = datetime.now(timezone.utc) + timedelta(
            hours=CONVITE_HORAS
        )
        usuario = Usuario(
            nome=nome,
            perfil=perfil,
            email=email,
            ativo=False,
            token_convite=token,
            token_expiracao=expiracao,
        )
        db.session.add(usuario)
        db.session.commit()

        link = ServicoEmail.enviar_convite(
            email, nome, token
        )
        return usuario, link

    @staticmethod
    def obter_por_token(token):
        return Usuario.query.filter_by(
            token_convite=token
        ).first()

    @staticmethod
    def ativar_conta(token, senha):
        usuario = Usuario.query.filter_by(
            token_convite=token
        ).first()
        if not usuario:
            return None, 'Token inválido.'

        agora = datetime.now(timezone.utc)
        exp = usuario.token_expiracao
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp and agora > exp:
            return None, 'Token expirado.'

        usuario.senha_hash = generate_password_hash(senha)
        usuario.ativo = True
        usuario.token_convite = None
        usuario.token_expiracao = None
        db.session.commit()
        return usuario, None

    @staticmethod
    def reenviar_convite(id_usuario):
        usuario = Usuario.query.get(id_usuario)
        if not usuario or usuario.ativo:
            return None
        token = secrets.token_urlsafe(48)
        usuario.token_convite = token
        usuario.token_expiracao = datetime.now(
            timezone.utc
        ) + timedelta(hours=CONVITE_HORAS)
        db.session.commit()
        link = ServicoEmail.enviar_convite(
            usuario.email, usuario.nome, token
        )
        return link

    @staticmethod
    def listar_usuarios():
        return Usuario.query.order_by(
            Usuario.nome
        ).all()

    @staticmethod
    def obter_por_id(id_usuario):
        return Usuario.query.get(id_usuario)

    @staticmethod
    def atualizar_usuario(id_usuario, **dados):
        usuario = Usuario.query.get(id_usuario)
        if not usuario:
            return None
        for campo, valor in dados.items():
            if campo == 'senha' and valor:
                usuario.senha_hash = generate_password_hash(
                    valor
                )
            elif hasattr(usuario, campo):
                setattr(usuario, campo, valor)
        db.session.commit()
        return usuario

    @staticmethod
    def solicitar_recuperacao(email):
        usuario = Usuario.query.filter_by(
            email=email, ativo=True
        ).first()
        if not usuario:
            return None
        token = secrets.token_urlsafe(48)
        usuario.token_convite = token
        usuario.token_expiracao = datetime.now(
            timezone.utc
        ) + timedelta(hours=RESET_HORAS)
        db.session.commit()
        ServicoEmail.enviar_recuperacao(
            usuario.email, usuario.nome, token
        )
        return usuario

    @staticmethod
    def redefinir_senha(token, nova_senha):
        usuario = Usuario.query.filter_by(
            token_convite=token, ativo=True
        ).first()
        if not usuario:
            return None, 'Token inválido.'

        agora = datetime.now(timezone.utc)
        exp = usuario.token_expiracao
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp and agora > exp:
            return None, 'Token expirado.'

        usuario.senha_hash = generate_password_hash(
            nova_senha
        )
        usuario.token_convite = None
        usuario.token_expiracao = None
        db.session.commit()
        return usuario, None

    @staticmethod
    def alternar_ativo(id_usuario):
        usuario = Usuario.query.get(id_usuario)
        if not usuario:
            return None
        usuario.ativo = not usuario.ativo
        db.session.commit()
        return usuario
