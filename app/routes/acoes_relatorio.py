"""Router universal para todas as acoes do catalogo.

Substitui as ~5 rotas duplicadas (inserir_sumario, inserir_lista_*,
reindexar_captions, etc.) por uma rota unica que:

  1. Recebe `POST /relatorio/<id>/acao/<acao_id>`
  2. Busca a `Acao` no catalogo
  3. Aplica `validar_pre_execucao` (perfil, bloqueio, DOCX existe)
  4. Executa o handler com tratamento de erro uniforme
  5. Devolve `flash` + redirect (configuravel via form)

Adicionar uma acao nova = 1 entrada no catalogo. Esta rota nao precisa
ser tocada.
"""
from __future__ import annotations

from flask import (
    Blueprint, redirect, url_for, flash, session, request,
)
from flask_login import login_required

from app.models.relatorio_producao import RelatorioProducao
from app.services.servico_acoes_relatorio import (
    obter_acao, validar_pre_execucao,
)
from app.services.servico_perfil_formatacao import PerfilFormatacao


acoes_bp = Blueprint('acoes', __name__, url_prefix='/relatorio')


@acoes_bp.route('/<int:id_rel>/acao/<acao_id>', methods=['POST'])
@login_required
def executar(id_rel, acao_id):
    """Executa a acao identificada por `acao_id` no relatorio `id_rel`."""
    # Redirect destino: por padrao, volta ao editor coordenador.
    # Pode ser sobrescrito por hidden field `redirect_to` no form.
    redirect_to = request.form.get('redirect_to') or url_for(
        'relatorio.editor_coordenador', id_versao=id_rel
    )

    acao = obter_acao(acao_id)
    if acao is None:
        flash(f'Ação desconhecida: "{acao_id}".', 'erro')
        return redirect(redirect_to)

    rel = RelatorioProducao.query.get(id_rel)
    if rel is None:
        flash('Relatório não encontrado.', 'erro')
        return redirect(url_for('relatorio.relatorios_producao'))

    perfil_ativo = session.get('perfil_ativo') or ''
    ok, msg = validar_pre_execucao(acao, rel, perfil_ativo)
    if not ok:
        flash(msg, 'erro')
        return redirect(redirect_to)

    try:
        perfil = PerfilFormatacao.de_relatorio(rel)
        resultado = acao.handler(rel, perfil)
        mensagem = (
            f'{acao.label}: {resultado}' if resultado else acao.label
        )
        flash(mensagem, 'sucesso')
    except (OSError, ValueError, RuntimeError, ImportError) as e:
        flash(f'Erro em "{acao.label}": {e}', 'erro')

    return redirect(redirect_to)
