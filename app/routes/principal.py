"""Rotas principais / dashboard do SRA."""

import os
from flask import Blueprint, session, render_template
from flask_login import login_required

from app.models.relatorio_producao import RelatorioProducao
from app.models.relatorio_finalizado import RelatorioFinalizado
from app.models.biblioteca_formatacao import BibliotecaFormatacaoCanonica
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

    relatorios_producao = RelatorioProducao.query.all()
    relatorios_finalizados = RelatorioFinalizado.query.all()
    bibliotecas_formatacao = BibliotecaFormatacaoCanonica.query.filter_by(
        ativa=True
    ).all()

    # Listar arquivos de storage/relatorios_base
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    dir_relatorios_base = os.path.join(base_dir, 'storage', 'relatorios_base')
    arquivos_relatorios_base = []
    if os.path.exists(dir_relatorios_base):
        arquivos_relatorios_base = [
            f for f in os.listdir(dir_relatorios_base)
            if f.endswith('.docx')
        ]

    return render_conteudo(
        componentes,
        perfil_ativo=perfil_ativo,
        relatorios_producao=relatorios_producao,
        relatorios_finalizados=relatorios_finalizados,
        arquivos_relatorios_base=arquivos_relatorios_base,
        bibliotecas_formatacao=bibliotecas_formatacao
    )


def _resolver_componentes(perfil):
    if perfil == 'administrador':
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
    return []
