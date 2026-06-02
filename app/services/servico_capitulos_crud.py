"""Servicos CRUD para capitulos de relatorios."""
from __future__ import annotations

from app import db
from app.models.capitulo_documento import CapituloDocumento
from app.models.relatorio_producao import RelatorioProducao
from app.services import servico_relatorio_core as relatorio_core
from app.services.servico_merge_docx import remover_capitulo_do_docx


def validar_acesso_capitulos(rel, perfil):
    """Devolve ``(ok, mensagem_erro)`` para operacoes de capitulos."""
    if perfil not in ('coordenador', 'admin'):
        return False, 'Apenas o coordenador pode gerenciar capítulos.'
    if rel is None:
        return False, 'Relatório não encontrado.'
    if relatorio_core.esta_bloqueado(rel):
        return False, (
            'Relatório finalizado/bloqueado — capítulos não podem '
            'ser modificados. Crie uma nova versão para continuar.'
        )
    return True, ''


def criar_capitulo_relatorio(id_relatorio, dados, id_usuario):
    """Cria um capitulo na arvore de um relatorio."""
    rel = RelatorioProducao.query.get(id_relatorio)
    ok, msg = validar_acesso_capitulos(rel, dados.get('perfil_ativo') or '')
    if not ok:
        return False, msg, None

    titulo = (dados.get('titulo_capitulo') or '').strip()
    if not titulo:
        return False, 'Título do capítulo é obrigatório.', None

    ordem = dados.get('ordem_capitulo')
    if ordem is None:
        max_ordem = db.session.query(
            db.func.coalesce(db.func.max(CapituloDocumento.ordem_capitulo), 0)
        ).filter_by(id_relatorio=id_relatorio).scalar()
        ordem = (max_ordem or 0) + 10

    cap = CapituloDocumento(
        id_relatorio=id_relatorio,
        titulo_capitulo=titulo,
        nivel_capitulo=dados.get('nivel_capitulo') or 1,
        tipo_elemento=dados.get('tipo_elemento') or 'textual',
        id_capitulo_pai=dados.get('id_capitulo_pai'),
        ordem_capitulo=ordem,
        indice_capitulo=dados.get('indice_capitulo'),
        nome_capitulo=dados.get('nome_capitulo') or titulo,
        status_capitulo='em_edicao',
        criado_por=id_usuario,
    )
    db.session.add(cap)
    db.session.commit()
    return True, f'Capítulo "{titulo}" adicionado.', cap


def salvar_capitulo_relatorio(id_capitulo, dados, id_usuario):
    """Atualiza os campos editaveis de um capitulo."""
    cap = CapituloDocumento.query.get_or_404(id_capitulo)
    rel = RelatorioProducao.query.get(cap.id_relatorio)
    ok, msg = validar_acesso_capitulos(rel, dados.get('perfil_ativo') or '')
    if not ok:
        return False, msg, cap

    campos_simples = (
        'titulo_capitulo', 'nome_capitulo', 'indice_capitulo',
        'status_capitulo', 'observacao_coordenador',
    )
    for campo in campos_simples:
        if campo in dados:
            setattr(cap, campo, (dados.get(campo) or '').strip() or None)

    for campo in ('nivel_capitulo', 'ordem_capitulo'):
        if dados.get(campo) is not None:
            setattr(cap, campo, dados[campo])

    if 'id_usuario_responsavel' in dados:
        cap.id_usuario_responsavel = dados.get('id_usuario_responsavel') or None
    if 'id_capitulo_pai' in dados:
        cap.id_capitulo_pai = dados.get('id_capitulo_pai') or None
    if not cap.nome_capitulo and cap.titulo_capitulo:
        cap.nome_capitulo = cap.titulo_capitulo
    if id_usuario:
        cap.atualizado_por = id_usuario
    db.session.commit()
    return True, f'Capítulo "{cap.titulo_capitulo}" salvo.', cap


def mover_capitulo_relatorio(id_capitulo, direcao, perfil_ativo, id_usuario):
    """Move um capitulo entre irmaos diretos."""
    cap = CapituloDocumento.query.get_or_404(id_capitulo)
    rel = RelatorioProducao.query.get(cap.id_relatorio)
    ok, msg = validar_acesso_capitulos(rel, perfil_ativo)
    if not ok:
        return False, msg, cap

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
        return False, 'Capítulo já está no limite — não pode mover.', cap

    cap.ordem_capitulo, vizinho.ordem_capitulo = (
        vizinho.ordem_capitulo, cap.ordem_capitulo
    )
    if id_usuario:
        cap.atualizado_por = id_usuario
        vizinho.atualizado_por = id_usuario
    db.session.commit()
    sentido = 'cima' if direcao == 'cima' else 'baixo'
    return True, f'Capítulo "{cap.titulo_capitulo}" movido para {sentido}.', cap


def excluir_capitulo_relatorio(id_capitulo, perfil_ativo):
    """Remove capitulo e subcapitulos do banco, com limpeza DOCX best-effort."""
    cap = CapituloDocumento.query.get_or_404(id_capitulo)
    rel = RelatorioProducao.query.get(cap.id_relatorio)
    ok, msg = validar_acesso_capitulos(rel, perfil_ativo)
    if not ok:
        return False, msg, cap.id_relatorio

    id_rel = cap.id_relatorio
    titulo = cap.titulo_capitulo
    range_removido, erro_docx = _remover_range_docx(rel, cap)
    n_subcap = _remover_recursivo(cap)
    db.session.delete(cap)
    db.session.commit()

    extras = []
    if n_subcap:
        extras.append(f'{n_subcap} subcapítulo(s)')
    if range_removido:
        extras.append('range removido do DOCX')
    sufixo = f' ({"; ".join(extras)})' if extras else ''
    if erro_docx:
        sufixo = f'{sufixo}. Falha ao limpar DOCX: {erro_docx}'
    return True, f'Capítulo "{titulo}" excluído{sufixo}.', id_rel


def _remover_range_docx(rel, cap):
    if not rel.caminho_template:
        return False, ''
    try:
        remover_capitulo_do_docx(rel.caminho_template, cap)
        return True, ''
    except (OSError, ValueError, RuntimeError) as erro:
        return False, str(erro)


def _remover_recursivo(cap):
    n = 0
    filhos = CapituloDocumento.query.filter_by(
        id_capitulo_pai=cap.id_capitulo_documento
    ).all()
    for filho in filhos:
        n += 1 + _remover_recursivo(filho)
        db.session.delete(filho)
    return n
