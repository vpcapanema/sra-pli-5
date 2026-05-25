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
from flask_login import login_required

from app import db
from app.models.capitulo_documento import CapituloDocumento
from app.models.relatorio_producao import RelatorioProducao
from app.services.servico_relatorio import ServicoRelatorio


capitulos_bp = Blueprint(
    'capitulos', __name__, url_prefix='/relatorio/capitulo'
)


# ===========================================================
# Helpers compartilhados
# ===========================================================

def _validar_acesso(rel):
    """Devolve `(ok, mensagem_erro)`."""
    perfil = session.get('perfil_ativo') or ''
    if perfil not in ('coordenador', 'admin'):
        return False, 'Apenas o coordenador pode gerenciar capítulos.'
    if rel is None:
        return False, 'Relatório não encontrado.'
    if ServicoRelatorio.esta_bloqueado(rel):
        return False, (
            'Relatório finalizado/bloqueado — capítulos não podem '
            'ser modificados. Crie uma nova versão para continuar.'
        )
    return True, ''


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
    rel = RelatorioProducao.query.get(id_relatorio)
    ok, msg = _validar_acesso(rel)
    if not ok:
        flash(msg, 'erro')
        return _redirect_detalhe(id_relatorio)

    titulo = (request.form.get('titulo_capitulo') or '').strip()
    if not titulo:
        flash('Título do capítulo é obrigatório.', 'erro')
        return _redirect_detalhe(id_relatorio)

    # Se ordem nao fornecida, coloca no fim
    ordem = request.form.get('ordem_capitulo', type=int)
    if ordem is None:
        max_ordem = db.session.query(
            db.func.coalesce(db.func.max(CapituloDocumento.ordem_capitulo), 0)
        ).filter_by(id_relatorio=id_relatorio).scalar()
        ordem = (max_ordem or 0) + 10

    cap = CapituloDocumento(
        id_relatorio=id_relatorio,
        titulo_capitulo=titulo,
        nivel_capitulo=request.form.get(
            'nivel_capitulo', type=int, default=1
        ),
        tipo_elemento=request.form.get('tipo_elemento') or 'textual',
        id_capitulo_pai=request.form.get(
            'id_capitulo_pai', type=int
        ),
        ordem_capitulo=ordem,
        indice_capitulo=request.form.get('indice_capitulo'),
        nome_capitulo=request.form.get('nome_capitulo'),
        status_capitulo='em_edicao',
    )
    db.session.add(cap)
    db.session.commit()
    flash(f'Capítulo "{titulo}" adicionado.', 'sucesso')
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
    cap = CapituloDocumento.query.get_or_404(id_capitulo)
    rel = RelatorioProducao.query.get(cap.id_relatorio)
    ok, msg = _validar_acesso(rel)
    if not ok:
        flash(msg, 'erro')
        return _redirect_detalhe(cap.id_relatorio)

    # Aplica apenas os campos presentes no form
    campos_simples = (
        'titulo_capitulo', 'nome_capitulo', 'indice_capitulo',
        'status_capitulo', 'observacao_coordenador',
    )
    for campo in campos_simples:
        if campo in request.form:
            valor = (request.form.get(campo) or '').strip() or None
            setattr(cap, campo, valor)

    # Campos numericos
    if 'nivel_capitulo' in request.form:
        v = request.form.get('nivel_capitulo', type=int)
        if v is not None:
            cap.nivel_capitulo = v
    if 'ordem_capitulo' in request.form:
        v = request.form.get('ordem_capitulo', type=int)
        if v is not None:
            cap.ordem_capitulo = v
    if 'id_usuario_responsavel' in request.form:
        v = request.form.get('id_usuario_responsavel', type=int)
        cap.id_usuario_responsavel = v if v else None
    if 'id_capitulo_pai' in request.form:
        v = request.form.get('id_capitulo_pai', type=int)
        cap.id_capitulo_pai = v if v else None

    db.session.commit()
    flash(
        f'Capítulo "{cap.titulo_capitulo}" salvo.', 'sucesso'
    )
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
    cap = CapituloDocumento.query.get_or_404(id_capitulo)
    rel = RelatorioProducao.query.get(cap.id_relatorio)
    ok, msg = _validar_acesso(rel)
    if not ok:
        flash(msg, 'erro')
        return _redirect_detalhe(cap.id_relatorio)

    direcao = request.form.get('direcao', 'cima')
    irmaos_q = CapituloDocumento.query.filter_by(
        id_relatorio=cap.id_relatorio,
        id_capitulo_pai=cap.id_capitulo_pai,
        nivel_capitulo=cap.nivel_capitulo,
    )
    if direcao == 'cima':
        vizinho = irmaos_q.filter(
            CapituloDocumento.ordem_capitulo < cap.ordem_capitulo
        ).order_by(CapituloDocumento.ordem_capitulo.desc()).first()
    else:
        vizinho = irmaos_q.filter(
            CapituloDocumento.ordem_capitulo > cap.ordem_capitulo
        ).order_by(CapituloDocumento.ordem_capitulo.asc()).first()

    if vizinho is None:
        flash('Capítulo já está no limite — não pode mover.', 'info')
        return _redirect_detalhe(cap.id_relatorio)

    # Troca de ordens
    cap.ordem_capitulo, vizinho.ordem_capitulo = (
        vizinho.ordem_capitulo, cap.ordem_capitulo
    )
    db.session.commit()
    flash(
        f'Capítulo "{cap.titulo_capitulo}" movido para '
        f'{"cima" if direcao == "cima" else "baixo"}.',
        'sucesso',
    )
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
    cap = CapituloDocumento.query.get_or_404(id_capitulo)
    rel = RelatorioProducao.query.get(cap.id_relatorio)
    ok, msg = _validar_acesso(rel)
    if not ok:
        flash(msg, 'erro')
        return _redirect_detalhe(cap.id_relatorio)

    id_rel = cap.id_relatorio
    titulo = cap.titulo_capitulo

    # Tenta remover range do capitulo no DOCX (best-effort)
    range_removido = False
    if rel.caminho_template:
        try:
            from app.services.servico_merge_docx import (
                remover_capitulo_do_docx,
            )
            remover_capitulo_do_docx(rel.caminho_template, cap)
            range_removido = True
        except ImportError:
            # Funcao ainda nao implementada — limpeza so no banco
            pass
        except (OSError, ValueError, RuntimeError) as e:
            flash(
                f'Capítulo removido do banco, mas falha ao limpar '
                f'DOCX: {e}', 'aviso',
            )

    # Remove subcapitulos (cascade manual)
    n_subcap = _remover_recursivo(cap)
    db.session.delete(cap)
    db.session.commit()

    extras = []
    if n_subcap:
        extras.append(f'{n_subcap} subcapítulo(s)')
    if range_removido:
        extras.append('range removido do DOCX')
    sufixo = f' ({"; ".join(extras)})' if extras else ''
    flash(f'Capítulo "{titulo}" excluído{sufixo}.', 'sucesso')
    return _redirect_detalhe(id_rel)


def _remover_recursivo(cap):
    """Remove subcapitulos do capitulo recursivamente. Retorna contagem."""
    n = 0
    filhos = CapituloDocumento.query.filter_by(
        id_capitulo_pai=cap.id_capitulo_documento
    ).all()
    for f in filhos:
        n += 1 + _remover_recursivo(f)
        db.session.delete(f)
    return n


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
