from flask import (
    Blueprint, render_template, redirect,
    url_for, flash, request, session
)
from flask_login import login_user, logout_user, login_required
from app.services.servico_usuario import ServicoUsuario

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        perfil = request.form.get('tipo_perfil')

        usuario = ServicoUsuario.autenticar(
            email, senha, perfil
        )
        if not usuario:
            flash('Credenciais inválidas.', 'erro')
            return render_template('login.html')

        login_user(usuario)
        session['perfil_ativo'] = perfil
        return redirect(url_for('principal.index'))
    return render_template('login.html')


@auth_bp.route('/recuperar-senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if email:
            ServicoUsuario.solicitar_recuperacao(email)
        flash(
            'Se o e-mail estiver cadastrado, você '
            'receberá um link para redefinir a senha.',
            'info'
        )
        return redirect(url_for('auth.login'))
    return render_template('recuperar_senha.html')


@auth_bp.route(
    '/redefinir-senha/<token>',
    methods=['GET', 'POST']
)
def redefinir_senha(token):
    usuario = ServicoUsuario.obter_por_token(token)
    if not usuario or not usuario.ativo:
        flash('Link inválido ou expirado.', 'erro')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        senha = request.form.get('senha')
        confirma = request.form.get('confirmar_senha')
        if not senha or len(senha) < 6:
            flash(
                'A senha deve ter no mínimo '
                '6 caracteres.',
                'erro'
            )
            return render_template(
                'redefinir_senha.html',
                token=token
            )
        if senha != confirma:
            flash('As senhas não conferem.', 'erro')
            return render_template(
                'redefinir_senha.html',
                token=token
            )

        user, erro = ServicoUsuario.redefinir_senha(
            token, senha
        )
        if erro:
            flash(erro, 'erro')
            return redirect(
                url_for('auth.recuperar_senha')
            )

        flash(
            'Senha redefinida com sucesso! '
            'Faça login.',
            'sucesso'
        )
        return redirect(url_for('auth.login'))

    return render_template(
        'redefinir_senha.html',
        token=token
    )


@auth_bp.route(
    '/ativar-conta/<token>',
    methods=['GET', 'POST']
)
def ativar_conta(token):
    usuario = ServicoUsuario.obter_por_token(token)
    if not usuario:
        flash('Link inválido ou já utilizado.', 'erro')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        senha = request.form.get('senha')
        confirma = request.form.get('confirmar_senha')
        if not senha or len(senha) < 6:
            flash(
                'A senha deve ter no mínimo 6 caracteres.',
                'erro'
            )
            return render_template(
                'ativar_conta.html',
                token=token,
                usuario=usuario
            )
        if senha != confirma:
            flash('As senhas não conferem.', 'erro')
            return render_template(
                'ativar_conta.html',
                token=token,
                usuario=usuario
            )

        user, erro = ServicoUsuario.ativar_conta(
            token, senha
        )
        if erro:
            flash(erro, 'erro')
            return render_template(
                'ativar_conta.html',
                token=token,
                usuario=usuario
            )

        flash(
            'Conta ativada com sucesso! Faça login.',
            'sucesso'
        )
        return redirect(url_for('auth.login'))

    return render_template(
        'ativar_conta.html',
        token=token,
        usuario=usuario
    )


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
