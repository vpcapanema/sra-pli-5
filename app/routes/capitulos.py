"""Rotas CRUD para `CapituloDocumento`.

Padroniza as operacoes que o coordenador faz na arvore de capitulos
(criar, salvar, mover, excluir). Cada rota:

  - Valida perfil ativo (coordenador/admin)
  - Valida bloqueio do relatorio (rejeita se finalizado)
  - Faz a operacao + commit
  - Devolve redirect com flash

Substituir o conteudo de um capitulo nao tem rota propria — usa o
fluxo de upload do autor (`/relatorio/envios-conteudo/upload`), que ja
faz merge in-place + sincronizacao + captioning. A UI manda o usuario
para la com `capitulo` no querystring.
"""
from __future__ import annotations

from flask import (
    Blueprint, redirect, url_for, flash, session, request,
)
from flask_login import login_required, current_user

from app.models.capitulo_documento import CapituloDocumento
from app.services.servico_capitulos_crud import (
    criar_capitulo_relatorio,
    excluir_capitulo_relatorio,
    mover_capitulo_relatorio,
    salvar_capitulo_relatorio,
)


capitulos_bp = Blueprint(
    'capitulos', __name__, url_prefix='/relatorio/capitulo'
)


def _redirect_detalhe(id_relatorio):
    return redirect(
        url_for('relatorio.detalhe_versao', id_versao=id_relatorio)
    )


# ===========================================================
# Criar
# ===========================================================

@capitulos_bp.route(
    '/novo-em/<int:id_relatorio>', methods=['POST']
)
@login_required
def criar(id_relatorio):
    """Cria um novo capitulo na posicao indicada.

    Form fields:
      - titulo_capitulo (obrigatorio)
      - nivel_capitulo (default=1)
      - tipo_elemento (default='textual')
      - id_capitulo_pai (opcional)
      - ordem_capitulo (opcional; default = ultimo + 10)
      - indice_capitulo (opcional)
    """
    dados = {
        'perfil_ativo': session.get('perfil_ativo') or '',
        'titulo_capitulo': request.form.get('titulo_capitulo'),
        'nivel_capitulo': request.form.get(
            'nivel_capitulo', type=int, default=1
        ),
        'tipo_elemento': request.form.get('tipo_elemento'),
        'id_capitulo_pai': request.form.get('id_capitulo_pai', type=int),
        'ordem_capitulo': request.form.get('ordem_capitulo', type=int),
        'indice_capitulo': request.form.get('indice_capitulo'),
        'nome_capitulo': request.form.get('nome_capitulo'),
    }
    ok, msg, _cap = criar_capitulo_relatorio(
        id_relatorio,
        dados,
        current_user.id if current_user.is_authenticated else None,
    )
    flash(msg, 'sucesso' if ok else 'erro')
    return _redirect_detalhe(id_relatorio)


# ===========================================================
# Salvar (edita TODAS as colunas)
# ===========================================================

@capitulos_bp.route('/<int:id_capitulo>/salvar', methods=['POST'])
@login_required
def salvar(id_capitulo):
    """Salva todas as edicoes do capitulo em um unico submit.

    Substitui o antigo `atribuir_responsavel` — qualquer combinacao de
    campos pode ser enviada; campos omitidos sao mantidos.
    """
    dados = {'perfil_ativo': session.get('perfil_ativo') or ''}
    for campo in (
        'titulo_capitulo', 'nome_capitulo', 'indice_capitulo',
        'status_capitulo', 'observacao_coordenador',
    ):
        if campo in request.form:
            dados[campo] = request.form.get(campo)
    for campo in (
        'nivel_capitulo', 'ordem_capitulo', 'id_usuario_responsavel',
        'id_capitulo_pai',
    ):
        if campo in request.form:
            dados[campo] = request.form.get(campo, type=int)
    ok, msg, cap = salvar_capitulo_relatorio(
        id_capitulo,
        dados,
        current_user.id if current_user.is_authenticated else None,
    )
    flash(msg, 'sucesso' if ok else 'erro')
    return _redirect_detalhe(cap.id_relatorio)


# ===========================================================
# Mover (subir / descer)
# ===========================================================

@capitulos_bp.route('/<int:id_capitulo>/mover', methods=['POST'])
@login_required
def mover(id_capitulo):
    """Troca a `ordem_capitulo` deste capitulo com o vizinho.

    Form: `direcao` = 'cima' | 'baixo'.

    Considera apenas capitulos do mesmo nivel e mesmo pai
    (irmaos diretos). Capitulos sem vizinho na direcao
    solicitada nao se movem (no-op + flash informativo).
    """
    ok, msg, cap = mover_capitulo_relatorio(
        id_capitulo,
        request.form.get('direcao', 'cima'),
        session.get('perfil_ativo') or '',
        current_user.id if current_user.is_authenticated else None,
    )
    flash(msg, 'sucesso' if ok else 'info')
    return _redirect_detalhe(cap.id_relatorio)


# ===========================================================
# Excluir (registro + tentativa de limpar range no DOCX)
# ===========================================================

@capitulos_bp.route('/<int:id_capitulo>/excluir', methods=['POST'])
@login_required
def excluir(id_capitulo):
    """Remove o capitulo do banco e tenta apagar seu range no DOCX.

    Se houver subcapitulos, eles tambem sao removidos (cascade manual
    via consulta hierarquica). O DOCX em producao tem o range do
    capitulo apagado quando o servico de merge suporta isso; caso
    contrario, a remocao e apenas no banco e o usuario precisa
    re-fazer upload depois.
    """
    ok, msg, id_rel = excluir_capitulo_relatorio(
        id_capitulo,
        session.get('perfil_ativo') or '',
    )
    flash(msg, 'sucesso' if ok else 'erro')
    return _redirect_detalhe(id_rel)


# ===========================================================
# Substituir conteudo (atalho para o fluxo de upload)
# ===========================================================

@capitulos_bp.route('/<int:id_capitulo>/substituir-conteudo')
@login_required
def substituir_conteudo(id_capitulo):
    """Redireciona para o fluxo de upload, ja com o capitulo destino
    pre-selecionado. O merge in-place + reindexacao acontecem la."""
    cap = CapituloDocumento.query.get_or_404(id_capitulo)
    return redirect(
        url_for(
            'relatorio.upload_conteudo',
            id_versao=cap.id_relatorio,
            id_capitulo=id_capitulo,
        )
    )
