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
    if session.get('perfil_ativo') not in ('admin', 'coordenador'):
        flash('Acesso restrito a administradores e coordenadores.', 'erro')
        return redirect(url_for('principal.index'))


@admin_bp.route('/usuarios')
def listar_usuarios():
    usuarios = ServicoUsuario.listar_usuarios()
    return render_conteudo(
        ['components/configuracoes/gestao_usuarios.html'],
        perfil_ativo=session.get('perfil_ativo', ''),
        usuarios=usuarios
    )


@admin_bp.route('/usuarios/novo', methods=['POST'])
def criar_usuario():
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
    '/usuarios/<int:id>/reenviar',
    methods=['POST']
)
def reenviar_convite(id):
    link = ServicoUsuario.reenviar_convite(id)
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
    '/usuarios/<int:id>/editar',
    methods=['GET', 'POST']
)
def editar_usuario(id):
    usuario = ServicoUsuario.obter_usuario(id)
    if request.method == 'POST':
        ServicoUsuario.atualizar_usuario(
            id,
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
    '/usuarios/<int:id>/ativar',
    methods=['POST']
)
def alternar_ativo(id):
    ServicoUsuario.alternar_ativo(id)
    flash('Status do usuário alterado.', 'sucesso')
    return redirect(url_for('admin.listar_usuarios'))
