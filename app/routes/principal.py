"""Rotas principais / dashboard do SRA."""

from flask import Blueprint, session, render_template
from flask_login import login_required, current_user

from app.services.servico_dashboard import obter_contexto_dashboard
from app.utils.htmx import render_conteudo

principal_bp = Blueprint('principal', __name__)


@principal_bp.route('/dev/botoes-icone')
@login_required
def dev_botoes_icone():
    """Pagina de demonstracao de estilos de botoes-icone.

    Mostra varias variacoes (peso do Phosphor, forma, cor, hover) para
    o usuario escolher qual aplicar em todas as tabelas.
    """
    return render_template('dev/botoes_icone.html')


@principal_bp.route('/')
@login_required
def index():
    """Rota principal do dashboard."""
    perfil_ativo = session.get('perfil_ativo', '')
    componentes = _resolver_componentes(perfil_ativo)
    contexto = obter_contexto_dashboard(perfil_ativo, current_user.id)

    return render_conteudo(
        componentes,
        perfil_ativo=perfil_ativo,
        **contexto,
    )


def _resolver_componentes(perfil):
    if perfil == 'admin':
        return [
            'components/paineis/painel_indicadores.html',
            'components/paineis/painel_relatorios.html',
        ]
    elif perfil == 'coordenador':
        return [
            'components/paineis/dashboard_coordenador.html',
        ]
    elif perfil == 'autor':
        return [
            'components/paineis/painel_relatorios.html',
        ]
    # Fallback: evita <main> vazio quando o perfil não casa com nenhum
    # dos conhecidos (ex.: sessão sem perfil definido).
    return ['components/paineis/painel_relatorios.html']
