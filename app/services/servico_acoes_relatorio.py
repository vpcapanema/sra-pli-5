"""Catalogo central de acoes operacionais do relatorio.

Define declarativamente todas as acoes que o coordenador pode executar
sobre um `RelatorioProducao` (inserir TOC, listas, reindexar captions,
gerar final, atualizar capa, etc.).

Cada `Acao` carrega:
- metadados de UI (label, icone, descricao, grupo)
- regras de acesso (perfis permitidos, bloqueia se finalizado)
- requisitos tecnicos (precisa de DOCX em disco?)
- o handler (callable) que executa o trabalho

A rota universal `acoes.executar` consome este catalogo, aplica TODAS
as validacoes em um unico lugar e despacha para o handler.

Para adicionar uma acao nova: bastam estas linhas no `CATALOGO` abaixo
+ a funcao handler. Nenhum template, nenhuma rota nova.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Tuple

from flask_login import current_user


# ===========================================================
# Modelo da acao
# ===========================================================

@dataclass(frozen=True)
class Acao:
    """Definicao declarativa de uma acao executavel sobre um relatorio."""

    id: str
    """Identificador unico (slug). Vai compor a URL `/acao/<id>`."""

    label: str
    """Texto do botao."""

    icone: str
    """Nome do icone Phosphor (sem o prefixo `ph-`)."""

    descricao: str
    """Tooltip e mensagem de confirmacao."""

    grupo: str
    """Agrupador visual: `pre_textuais` | `numeracao` | `finalizacao`."""

    perfis: Tuple[str, ...]
    """Perfis ativos autorizados a executar."""

    handler: Callable
    """Funcao chamada como `handler(rel, perfil)` e devolve algo
    serializavel (dict, str, int) para a mensagem de flash."""

    bloqueia_se_finalizado: bool = True
    """Se `True`, recusa a acao quando o relatorio esta bloqueado."""

    requer_template: bool = True
    """Se `True`, exige que `rel.caminho_template` exista no disco."""

    ordem: int = 0
    """Ordem dentro do grupo (menor primeiro)."""

    confirmacao: str = ''
    """Mensagem de `confirm()` exibida antes do submit. Vazio = sem
    confirmacao."""


# ===========================================================
# Resultado da execucao
# ===========================================================

@dataclass
class ResultadoAcao:
    ok: bool
    mensagem: str
    redirect_url: str = ''
    payload: dict = field(default_factory=dict)


# ===========================================================
# Handlers (delegam para os servicos)
# ===========================================================

def _h_inserir_sumario(rel, perfil):
    from app.services.servico_toc import inserir_sumario
    info = inserir_sumario(rel.caminho_template, perfil=perfil)
    return _resumo_toc('Sumário', info)


def _h_inserir_lista_figuras(rel, perfil):
    from app.services.servico_toc import inserir_lista_figuras
    info = inserir_lista_figuras(rel.caminho_template, perfil=perfil)
    return _resumo_toc('Lista de Figuras', info)


def _h_inserir_lista_tabelas(rel, perfil):
    from app.services.servico_toc import inserir_lista_tabelas
    info = inserir_lista_tabelas(rel.caminho_template, perfil=perfil)
    return _resumo_toc('Lista de Tabelas', info)


def _h_inserir_lista_equacoes(rel, perfil):
    from app.services.servico_toc import inserir_lista_equacoes
    info = inserir_lista_equacoes(rel.caminho_template, perfil=perfil)
    return _resumo_toc('Lista de Equações', info)


def _h_inserir_lista_siglas(rel, perfil):
    from app.services.servico_toc import inserir_lista_siglas
    info = inserir_lista_siglas(rel.caminho_template, perfil=perfil)
    return _resumo_toc('Lista de Siglas e Abreviaturas', info)


def _h_sincronizar_capitulos(rel, perfil):
    """Reextrai a arvore de capitulos do DOCX em producao e atualiza
    o banco — garante que a sidebar mostre exatamente o que esta
    no documento renderizado.
    """
    from app.services.servico_sincronizar_capitulos import (
        ressincronizar_capitulos,
    )
    info = ressincronizar_capitulos(rel)
    if not info.get('aplicados'):
        return info.get('erro', 'Falha desconhecida na sincronizacao.')
    return (
        f'{info.get("atualizados", 0)} atualizado(s), '
        f'{info.get("criados", 0)} criado(s), '
        f'{info.get("sumiram", 0)} sem correspondente no DOCX.'
    )


def _h_reindexar_captions(rel, perfil):
    from app.services.servico_captioning import reindexar_captions
    from app.services.servico_cross_refs import substituir_referencias

    info = reindexar_captions(rel.caminho_template, perfil=perfil)
    mapa = info.get('mapa_labels', {}) if isinstance(info, dict) else {}
    n_refs = substituir_referencias(rel.caminho_template, mapa)
    resolvidas = n_refs.get('tags_resolvidas', 0) if isinstance(n_refs, dict) else 0
    nao_resolvidas = n_refs.get('tags_nao_resolvidas', 0) if isinstance(n_refs, dict) else 0
    sufixo_nao_resolvidas = (
        f', {nao_resolvidas} não resolvida(s)' if nao_resolvidas else ''
    )
    return (
        f'{info.get("figuras", 0)} figuras, '
        f'{info.get("tabelas", 0)} tabelas, '
        f'{info.get("equacoes", 0)} equações; '
        f'{resolvidas} ref(s) atualizada(s){sufixo_nao_resolvidas}.'
    )


def _h_atualizar_capa(rel, perfil):
    """Reaplica a capa preenchendo com dados atuais do relatorio.

    Handler em modo placeholder: a logica real esta no fluxo de
    clonagem. Quando o servico dedicado existir, basta substituir
    o corpo desta funcao.
    """
    try:
        from app.services.servico_capa import atualizar_capa
    except ImportError:
        return (
            'Atualização manual de capa pendente — atualmente é feita '
            'apenas na clonagem do relatório.'
        )
    info = atualizar_capa(rel.caminho_template, rel, perfil=perfil)
    return f'Capa atualizada. {info or ""}'.strip()


def _h_atualizar_folha_rosto(rel, perfil):
    try:
        from app.services.servico_capa import atualizar_folha_rosto
    except ImportError:
        return (
            'Atualização manual da folha de rosto pendente — atualmente '
            'é feita apenas na clonagem do relatório.'
        )
    info = atualizar_folha_rosto(rel.caminho_template, rel, perfil=perfil)
    return f'Folha de rosto atualizada. {info or ""}'.strip()


def _h_validar_estrutura(rel, perfil):
    """Checa se o DOCX tem todos os elementos canonicos esperados."""
    try:
        from app.services.servico_extracao_canonica import (
            validar_estrutura_canonica,
        )
    except ImportError:
        return 'Validação de estrutura pendente de implementação.'
    info = validar_estrutura_canonica(rel.caminho_template, perfil=perfil)
    if isinstance(info, dict):
        problemas = info.get('problemas') or []
        if not problemas:
            return 'Estrutura validada — todos os elementos canônicos OK.'
        return (
            f'Estrutura com {len(problemas)} problema(s): '
            + '; '.join(str(p) for p in problemas[:5])
        )
    return str(info or 'Validação concluída.')


def _h_gerar_final(rel, perfil):
    """Delega ao servico de finalizacao. Bloqueia futuras edicoes."""
    from app.services.servico_finalizar_relatorio import finalizar
    rf = finalizar(id_relatorio=rel.id, id_usuario=current_user.id)
    checksum_curto = (rf.checksum_docx or '')[:8]
    return (
        f'Relatório finalizado: {rf.nome_arquivo} '
        f'(checksum {checksum_curto}…)'
    )


# ===========================================================
# Helpers
# ===========================================================

def _resumo_toc(nome, info):
    if not isinstance(info, dict):
        return f'{nome} inserido(a).'
    n = info.get('entradas') or info.get('itens') or 0
    return f'{nome}: {n} entrada(s).'


# ===========================================================
# CATALOGO — fonte unica da verdade
# ===========================================================

CATALOGO: tuple = (
    # --- Pre-textuais (em ordem ABNT NBR 14724 / NBR 10719) ----
    # Sequencia canonica:
    #   Capa -> Folha de Rosto -> Lista de Figuras -> Lista de Tabelas
    #   -> Lista de Equacoes -> Lista de Siglas/Abreviaturas
    #   -> Sumario (sempre o ULTIMO pre-textual, NBR 14724 6.2.10)
    Acao(
        id='atualizar_capa',
        label='Atualizar Capa',
        icone='image-square',
        descricao='Reaplica a capa com os dados atuais do relatório '
                  '(título, código, período, autor). Primeiro elemento '
                  'pré-textual (ABNT NBR 14724 5.1).',
        grupo='pre_textuais',
        perfis=('coordenador', 'admin'),
        handler=_h_atualizar_capa,
        ordem=10,
    ),
    Acao(
        id='atualizar_folha_rosto',
        label='Atualizar Folha de Rosto',
        icone='file-text',
        descricao='Reaplica a folha de rosto. Segundo elemento '
                  'pré-textual (ABNT NBR 14724 5.2).',
        grupo='pre_textuais',
        perfis=('coordenador', 'admin'),
        handler=_h_atualizar_folha_rosto,
        ordem=20,
    ),
    Acao(
        id='inserir_lista_figuras',
        label='Inserir Lista de Figuras',
        icone='image',
        descricao='Insere ou atualiza a Lista de Figuras na região '
                  'pré-textual (ABNT NBR 14724 5.7).',
        grupo='pre_textuais',
        perfis=('coordenador', 'admin'),
        handler=_h_inserir_lista_figuras,
        ordem=30,
    ),
    Acao(
        id='inserir_lista_tabelas',
        label='Inserir Lista de Tabelas',
        icone='table',
        descricao='Insere ou atualiza a Lista de Tabelas na região '
                  'pré-textual (ABNT NBR 14724 5.8).',
        grupo='pre_textuais',
        perfis=('coordenador', 'admin'),
        handler=_h_inserir_lista_tabelas,
        ordem=40,
    ),
    Acao(
        id='inserir_lista_equacoes',
        label='Inserir Lista de Equações',
        icone='function',
        descricao='Insere ou atualiza a Lista de Equações na região '
                  'pré-textual (uso opcional, NBR 14724 5.9).',
        grupo='pre_textuais',
        perfis=('coordenador', 'admin'),
        handler=_h_inserir_lista_equacoes,
        ordem=50,
    ),
    Acao(
        id='inserir_lista_siglas',
        label='Inserir Lista de Siglas',
        icone='translate',
        descricao='Detecta siglas usadas no texto e insere lista '
                  'pré-textual em ordem alfabética (ABNT NBR 14724 5.10). '
                  'O coordenador edita as descrições manualmente.',
        grupo='pre_textuais',
        perfis=('coordenador', 'admin'),
        handler=_h_inserir_lista_siglas,
        ordem=60,
    ),
    Acao(
        id='inserir_sumario',
        label='Inserir Sumário',
        icone='list-bullets',
        descricao='Insere ou atualiza o Sumário com hyperlinks para '
                  'todos os headings. ÚLTIMO elemento pré-textual, '
                  'logo antes do conteúdo (ABNT NBR 14724 6.2.10). '
                  'Execute por último, após todas as listas.',
        grupo='pre_textuais',
        perfis=('coordenador', 'admin'),
        handler=_h_inserir_sumario,
        ordem=70,
    ),

    # --- Numeracao / Refs ------------------------------------
    Acao(
        id='sincronizar_capitulos',
        label='Sincronizar Capítulos',
        icone='tree-structure',
        descricao='Reextrai a árvore de capítulos do DOCX em produção '
                  'e atualiza a sidebar (índices e títulos). Use após '
                  'editar o documento manualmente no Word.',
        grupo='numeracao',
        perfis=('coordenador', 'admin'),
        handler=_h_sincronizar_capitulos,
        ordem=5,
    ),
    Acao(
        id='reindexar_captions',
        label='Reindexar Captions + Refs',
        icone='arrows-clockwise',
        descricao='Renumera figuras, tabelas e equações e atualiza '
                  'todas as referências cruzadas.',
        grupo='numeracao',
        perfis=('coordenador', 'admin'),
        handler=_h_reindexar_captions,
        ordem=10,
    ),
    Acao(
        id='validar_estrutura',
        label='Validar Estrutura',
        icone='check-circle',
        descricao='Verifica se o DOCX tem todos os elementos canônicos '
                  'esperados pela biblioteca de formatação.',
        grupo='numeracao',
        perfis=('coordenador', 'admin'),
        handler=_h_validar_estrutura,
        ordem=20,
    ),

    # --- Finalizacao -----------------------------------------
    Acao(
        id='gerar_final',
        label='Gerar Relatório Final',
        icone='seal-check',
        descricao='Gera snapshot final do DOCX e bloqueia edições. '
                  'Execute os comandos acima antes de finalizar.',
        grupo='finalizacao',
        perfis=('coordenador', 'admin'),
        handler=_h_gerar_final,
        ordem=10,
        confirmacao='Finalizar o relatório? Após esta operação, '
                    'edições serão bloqueadas.',
    ),
)


# Indexado por id para lookup O(1) na rota
ACOES_POR_ID: dict = {a.id: a for a in CATALOGO}


# ===========================================================
# API publica
# ===========================================================

def obter_acao(acao_id: str):
    """Devolve a `Acao` ou `None`."""
    return ACOES_POR_ID.get(acao_id)


def listar_por_grupo(perfil_ativo: str, rel_bloqueado: bool):
    """Devolve dict {grupo: [Acao]} com TODAS as acoes do catalogo,
    cada uma anotada com flags `disponivel` e `motivo_indisponivel`.

    Usado pelo template do painel para renderizar todos os botoes,
    desabilitando (sem esconder) os que nao podem ser executados.
    """
    # Ordem fixa de exibicao dos grupos no painel (NAO alfabetica).
    # Pre-textuais primeiro (botoes que o coordenador usa no dia a dia),
    # depois Numeracao/Refs (manutencao), e Finalizacao por ultimo
    # (acao destrutiva, deve estar visualmente separada).
    _ORDEM_GRUPOS = {'pre_textuais': 1, 'numeracao': 2, 'finalizacao': 3}

    grupos: dict = {}
    for acao in sorted(
        CATALOGO,
        key=lambda a: (
            _ORDEM_GRUPOS.get(a.grupo, 99), a.ordem, a.label,
        ),
    ):
        item = {
            'acao': acao,
            'disponivel': True,
            'motivo': '',
        }
        if perfil_ativo not in acao.perfis:
            item['disponivel'] = False
            item['motivo'] = 'Perfil sem permissão'
        elif rel_bloqueado and acao.bloqueia_se_finalizado:
            item['disponivel'] = False
            item['motivo'] = 'Relatório finalizado'
        grupos.setdefault(acao.grupo, []).append(item)
    return grupos


def validar_pre_execucao(acao: Acao, rel, perfil_ativo: str):
    """Valida as pre-condicoes da acao. Devolve `(ok, mensagem)`.

    Centraliza TODAS as validacoes que antes estavam duplicadas em
    cada handler de rota:
      1. Perfil tem permissao
      2. Relatorio nao esta bloqueado (se a acao exige)
      3. Arquivo DOCX existe (se a acao exige)
    """
    if perfil_ativo not in acao.perfis:
        return False, (
            f'Apenas {", ".join(acao.perfis)} podem executar '
            f'"{acao.label}".'
        )

    if acao.bloqueia_se_finalizado:
        from app.services.servico_relatorio import ServicoRelatorio
        if ServicoRelatorio.esta_bloqueado(rel):
            return False, (
                f'Relatório finalizado — não é possível executar '
                f'"{acao.label}".'
            )

    if acao.requer_template:
        if not rel.caminho_template or not os.path.exists(
            rel.caminho_template
        ):
            return False, (
                'DOCX em produção indisponível. Faça upload do template '
                'primeiro.'
            )

    return True, ''
