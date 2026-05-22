"""Rotas principais / dashboard do SRA."""

import os
from flask import Blueprint, session
from flask_login import login_required

from app.models.relatorio_producao import RelatorioProducao
from app.models.relatorio_finalizado import RelatorioFinalizado
from app.utils.htmx import render_conteudo

principal_bp = Blueprint('principal', __name__)


@principal_bp.route('/')
@login_required
def index():
    perfil_ativo = session.get('perfil_ativo', '')
    componentes = _resolver_componentes(perfil_ativo)

    relatorios_producao = RelatorioProducao.query.all()
    relatorios_finalizados = RelatorioFinalizado.query.all()

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
        arquivos_relatorios_base=arquivos_relatorios_base
    )


def _resolver_componentes(perfil):
    if perfil == 'administrador':
        return [
            'components/paineis/painel_indicadores.html',
            'components/paineis/painel_relatorios.html',
        ]
    elif perfil == 'coordenador':
        return [
            'components/paineis/painel_relatorios.html',
            'components/paineis/painel_criar_relatorio_producao.html',
        ]
    elif perfil == 'autor':
        return [
            'components/paineis/painel_relatorios.html',
        ]
    return []
