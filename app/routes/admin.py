"""Rotas de administração do SRA."""

from flask import (
    Blueprint, redirect,
    url_for, flash, request, session, render_template
)
from flask_login import login_required
from app.services.servico_usuario import ServicoUsuario
from app.utils.htmx import render_conteudo

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
@login_required
def verificar_perfil_admin():
    """Verifica se o usuário tem perfil de admin ou coordenador."""
    if session.get('perfil_ativo') not in ('admin', 'coordenador'):
        flash('Acesso restrito a administradores e coordenadores.', 'erro')
        return redirect(url_for('principal.index'))


@admin_bp.route('/usuarios')
def listar_usuarios():
    """Lista todos os usuários do sistema."""
    usuarios = ServicoUsuario.listar_usuarios()
    return render_conteudo(
        ['components/configuracoes/gestao_usuarios.html'],
        perfil_ativo=session.get('perfil_ativo', ''),
        usuarios=usuarios
    )


@admin_bp.route('/usuarios/novo', methods=['POST'])
def criar_usuario():
    """Cria um novo usuário e envia convite por email."""
    usuario, link = ServicoUsuario.convidar_usuario(
        nome_completo=request.form.get('nome_completo'),
        email=request.form.get('email'),
        perfil=request.form.get('tipo_perfil')
    )
    flash(
        f'Convite enviado para {usuario.email}. '
        f'Link: {link}',
        'sucesso'
    )
    return redirect(url_for('admin.listar_usuarios'))


@admin_bp.route(
    '/usuarios/<int:id_usuario>/reenviar',
    methods=['POST']
)
def reenviar_convite(id_usuario):
    """Reenvia o convite de cadastro para um usuário."""
    link = ServicoUsuario.reenviar_convite(id_usuario)
    if link:
        flash(
            f'Convite reenviado. Link: {link}',
            'sucesso'
        )
    else:
        flash(
            'Não foi possível reenviar '
            '(conta já ativa ou não encontrada).',
            'erro'
        )
    return redirect(url_for('admin.listar_usuarios'))


@admin_bp.route(
    '/usuarios/<int:id_usuario>/editar',
    methods=['GET', 'POST']
)
def editar_usuario(id_usuario):
    """Edita os dados de um usuário."""
    usuario = ServicoUsuario.obter_por_id(id_usuario)
    if request.method == 'POST':
        ServicoUsuario.atualizar_usuario(
            id_usuario,
            nome_completo=request.form.get('nome_completo'),
            email=request.form.get('email')
        )
        flash('Usuário atualizado.', 'sucesso')
        return redirect(url_for('admin.listar_usuarios'))
    return render_template(
        'components/configuracoes/editar_usuario.html',
        usuario=usuario,
    )


@admin_bp.route(
    '/usuarios/<int:id_usuario>/ativar',
    methods=['POST']
)
def alternar_ativo(id_usuario):
    """Alterna o status ativo/inativo de um usuário."""
    ServicoUsuario.alternar_ativo(id_usuario)
    flash('Status do usuário alterado.', 'sucesso')
    return redirect(url_for('admin.listar_usuarios'))
