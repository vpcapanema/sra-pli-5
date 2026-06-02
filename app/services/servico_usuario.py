"""Serviço de usuários, autenticação, convites e recuperação de senha."""

import secrets
from datetime import datetime, timedelta, timezone

from werkzeug.security import (
    generate_password_hash, check_password_hash
)
from app import db
from app.models.usuario import Usuario
from app.models.dominio import Dominio
from app.services.servico_email import ServicoEmail

PERFIS_VALIDOS = ('admin', 'coordenador', 'autor')
CONVITE_HORAS = 72
RESET_HORAS = 1


class ServicoUsuario:
    """Centraliza operações de cadastro, acesso e ciclo de senha."""

    @staticmethod
    def _gerar_nome_de_usuario(email):
        """Gera nome de usuário único a partir do e-mail."""
        base = (email or '').split('@')[0].strip().lower()
        base = ''.join(
            c if c.isalnum() or c in '._-' else '.'
            for c in base
        ).strip('._-') or 'usuario'
        candidato = base
        contador = 1
        while Usuario.query.filter_by(
            nome_de_usuario=candidato
        ).first():
            contador += 1
            candidato = f'{base}{contador}'
        return candidato

    @staticmethod
    def autenticar(email, senha, perfil):
        """Autentica usuário ativo pelo e-mail, senha e perfil informado."""
        # Converter perfil string para ID via tabela `dominios`
        perfil_obj = Dominio.query.filter_by(
            tipo='perfil_usuario', valor=perfil
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
        """Cria usuário inativo e envia convite de ativação."""
        if perfil not in PERFIS_VALIDOS:
            raise ValueError(
                f'Perfil inválido: {perfil}'
            )
        perfil_obj = Dominio.query.filter_by(
            tipo='perfil_usuario',
            valor=perfil,
            ativo=True
        ).first()
        if not perfil_obj:
            raise ValueError(
                f'Perfil não encontrado: {perfil}'
            )
        if Usuario.query.filter_by(
            email=email,
            perfil_id=perfil_obj.id
        ).first():
            raise ValueError(
                f'E-mail já cadastrado para o perfil {perfil}.'
            )
        token = secrets.token_urlsafe(48)
        expiracao = datetime.now(timezone.utc) + timedelta(
            hours=CONVITE_HORAS
        )
        usuario = Usuario(
            nome=nome,
            email=email,
            nome_de_usuario=ServicoUsuario._gerar_nome_de_usuario(
                email
            ),
            senha_hash=generate_password_hash(
                secrets.token_urlsafe(32)
            ),
            perfil_id=perfil_obj.id,
            ativo=False,
            token_convite=token,
            token_expiracao=expiracao,
        )
        db.session.add(usuario)
        db.session.commit()

        try:
            link = ServicoEmail.enviar_convite(
                email, nome, token
            )
        except RuntimeError as erro:
            db.session.delete(usuario)
            db.session.commit()
            raise ValueError(str(erro)) from erro
        return usuario, link

    @staticmethod
    def obter_por_token(token):
        """Busca usuário pelo token de convite."""
        return Usuario.query.filter_by(
            token_convite=token
        ).first()

    @staticmethod
    def obter_por_token_recuperacao(token):
        """Busca usuário pelo token de recuperação de senha."""
        return Usuario.query.filter_by(
            token_recuperacao=token
        ).first()

    @staticmethod
    def ativar_conta(token, senha):
        """Ativa conta com token válido e define a senha inicial."""
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
        """Gera novo token e reenvia convite para usuário inativo."""
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
        """Lista usuários ordenados por nome."""
        return Usuario.query.order_by(
            Usuario.nome
        ).all()

    @staticmethod
    def obter_por_id(id_usuario):
        """Busca usuário por ID."""
        return Usuario.query.get(id_usuario)

    @staticmethod
    def atualizar_usuario(id_usuario, **dados):
        """Atualiza campos do usuário, incluindo senha quando informada."""
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
    def solicitar_recuperacao(email, perfil):
        """Gera token de recuperação e envia link por e-mail."""
        perfil_obj = Dominio.query.filter_by(
            tipo='perfil_usuario', valor=perfil
        ).first()
        if not perfil_obj:
            return None
        usuario = Usuario.query.filter_by(
            email=email,
            perfil_id=perfil_obj.id,
            ativo=True
        ).first()
        if not usuario:
            return None
        token = secrets.token_urlsafe(48)
        usuario.token_recuperacao = token
        usuario.token_expiracao = datetime.now(
            timezone.utc
        ) + timedelta(hours=RESET_HORAS)
        db.session.commit()
        ServicoEmail.enviar_recuperacao(
            usuario.email,
            usuario.nome,
            usuario.nome_de_usuario,
            token,
            usuario.perfil.codigo if usuario.perfil else perfil
        )
        return usuario

    @staticmethod
    def redefinir_senha(token, nova_senha):
        """Redefine senha usando token de recuperação válido."""
        usuario = Usuario.query.filter_by(
            token_recuperacao=token, ativo=True
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
        usuario.token_recuperacao = None
        usuario.token_expiracao = None
        db.session.commit()
        return usuario, None

    @staticmethod
    def alternar_ativo(id_usuario):
        """Alterna status ativo/inativo do usuário."""
        usuario = Usuario.query.get(id_usuario)
        if not usuario:
            return None
        usuario.ativo = not usuario.ativo
        db.session.commit()
        return usuario
