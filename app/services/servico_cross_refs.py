r"""Substituicao OOXML-CANONICA de cross-references no corpo do DOCX.

Em conjunto com `servico_captioning`, este servico transforma tags
plain-text como `{{fig:meu-grafico}}` em campos `REF` validos do Word:

    <w:r><w:fldChar w:fldCharType="begin"/></w:r>
    <w:r><w:instrText xml:space="preserve"> REF _Ref_sra_fig_meu-grafico \h </w:instrText></w:r>
    <w:r><w:fldChar w:fldCharType="separate"/></w:r>
    <w:r><w:t>5.1</w:t></w:r>
    <w:r><w:fldChar w:fldCharType="end"/></w:r>

Beneficios:
- O Word atualiza o numero automaticamente ao reabrir/recalcular campos.
- Hyperlink clicavel (`\h`) para a legenda destino.
- Bookmark target (`_Ref_sra_*`) gerenciado pelo `servico_captioning`,
  garantindo idempotencia.

Entrada esperada:
    `mapa_labels` no formato canonico:
        {'fig:nome': {'numero': '5.1', 'bookmark': '_Ref_sra_fig_nome'},
         'tab:dados': {...}, 'ref:nome': {...}}

Compatibilidade retroativa:
    Se algum item de `mapa_labels` for string pura (formato antigo),
    fazemos fallback para substituicao plain-text (sem campo REF).
"""
from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

from docx import Document
from docx.oxml.ns import qn

from app.services._ooxml_helpers import texto_paragrafo as _texto_paragrafo


W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


# Sintaxe das tags. Aceita {{fig:x}}, {{tab:x}}, {{eq:x}}, {{ref:x}}.
RE_TAG = re.compile(
    r'\{\{\s*(fig|tab|eq|ref)\s*:\s*([\w\-_\.]+)\s*\}\}',
    re.IGNORECASE,
)

# Marcador de label declarado (a ser REMOVIDO do texto da legenda
# apos o `servico_captioning` ter consumido). Restos no corpo geral
# tambem sao limpos aqui.
RE_LABEL_DECLARACAO = re.compile(
    r'\{\{\s*label\s*:\s*[\w\-_\.]+\s*\}\}\s*'
)


def _resolver_info(mapa_labels: dict, chave: str) -> Optional[dict]:
    """Retorna dict `{'numero': str, 'bookmark': str|None}` para `chave`,
    ou None se nao encontrado. Aceita `mapa_labels` no formato novo
    (dict) ou antigo (string pura — bookmark None).
    """
    if chave not in mapa_labels:
        return None
    valor = mapa_labels[chave]
    if isinstance(valor, dict):
        return valor
    # Compat retroativo
    return {'numero': str(valor), 'bookmark': None}


def _processar_paragrafo(
    p_element, mapa_labels: Dict[str, dict]
) -> Tuple[int, int]:
    """Processa um paragrafo:
    - Remove `{{label:xyz}}` declaracoes residuais (se sobraram).
    - Substitui `{{fig:x}}`/`{{tab:x}}`/`{{eq:x}}`/`{{ref:x}}` por
      campo REF apontando para o bookmark correspondente. Se nao ha
      bookmark (ex: equacao inline), faz fallback para texto plano.
    - Tags nao resolvidas viram `??`.

    Retorna `(resolvidas, nao_resolvidas)`.

    Estrategia: agrega o texto inteiro do paragrafo, divide em segmentos
    `[texto, tag, texto, tag, ...]`, depois reconstroi o paragrafo
    com runs e campos REF intercalados. Perde formatacao inline pre-
    existente do paragrafo, mas e o preco para gerar OOXML correto.
    """
    from app.services._ooxml_helpers import (
        criar_run_texto,
        criar_runs_campo_ref,
    )

    resolvidas = 0
    nao_resolvidas = 0

    texto_agregado = _texto_paragrafo(p_element)
    # Remover declaracoes residuais de label
    texto_agregado = RE_LABEL_DECLARACAO.sub('', texto_agregado)

    if not RE_TAG.search(texto_agregado):
        # Nada a fazer (mas escreva texto_agregado se a regex de label
        # removeu algo).
        if texto_agregado != _texto_paragrafo(p_element):
            _consolidar_em_unico_run(p_element, texto_agregado)
        return 0, 0

    # Dividir em segmentos: lista de tuplas (kind, valor) onde kind e
    # 'texto' ou 'tag' (com info {tipo, nome, info_resolvida_ou_None}).
    segmentos = []
    pos = 0
    for m in RE_TAG.finditer(texto_agregado):
        if m.start() > pos:
            segmentos.append(('texto', texto_agregado[pos:m.start()]))
        tipo = m.group(1).lower()
        nome = m.group(2)
        chave = f'{tipo}:{nome}'
        info = _resolver_info(mapa_labels, chave)
        if info is None:
            nao_resolvidas += 1
            segmentos.append(('texto', '??'))
        else:
            resolvidas += 1
            segmentos.append(('tag', info))
        pos = m.end()
    if pos < len(texto_agregado):
        segmentos.append(('texto', texto_agregado[pos:]))

    # Reconstruir paragrafo: limpa runs e bookmarks (NAO mexe em pPr).
    w = f'{{{W_NS}}}'
    for filho in list(p_element):
        tag = filho.tag
        if tag in (
            f'{w}r', f'{w}bookmarkStart', f'{w}bookmarkEnd',
            f'{w}hyperlink',
        ):
            p_element.remove(filho)

    for kind, valor in segmentos:
        if kind == 'texto':
            if valor:
                p_element.append(criar_run_texto(valor))
        else:  # tag
            info = valor
            cache = info['numero']
            bookmark = info.get('bookmark')
            if bookmark:
                # Campo REF canonico
                for r in criar_runs_campo_ref(bookmark, cache):
                    p_element.append(r)
            else:
                # Fallback plain-text (ex: equacao sem bookmark)
                p_element.append(criar_run_texto(cache))

    return resolvidas, nao_resolvidas


def _consolidar_em_unico_run(p_element, novo_texto: str):
    """Apaga todos os runs e cria um unico com `novo_texto` (preserva pPr).
    """
    from app.services._ooxml_helpers import criar_run_texto
    w = f'{{{W_NS}}}'
    for filho in list(p_element):
        if filho.tag in (f'{w}r', f'{w}hyperlink'):
            p_element.remove(filho)
    p_element.append(criar_run_texto(novo_texto))


def substituir_referencias(
    caminho_master: str, mapa_labels: Dict[str, dict]
) -> dict:
    """Varre o DOCX em `caminho_master` substituindo cross-refs.

    Salva em `caminho_master`. Retorna:
        {'tags_resolvidas': N, 'tags_nao_resolvidas': N,
         'paragrafos_modificados': N}
    """
    doc = Document(caminho_master)
    body = doc.element.body

    total_resolvidas = 0
    total_nao_resolvidas = 0
    paragrafos_modificados = 0

    # Iteramos sobre todos os paragrafos do body, INCLUSIVE dentro de
    # tabelas (uma tag pode estar em uma celula).
    # IMPORTANTE: pulamos paragrafos que ja sao legendas (estilo
    # Caption ou prefixo conhecido) — eles foram processados pelo
    # `servico_captioning` e nao devem ter cross-refs no texto.
    from app.services.servico_captioning import (
        _eh_heading_paragrafo,
        _eh_paragrafo_de_caption,
    )

    em_regiao_textual = False
    for child in list(body):
        if child.tag == qn('w:p'):
            if not em_regiao_textual:
                nivel = _eh_heading_paragrafo(child)
                if nivel == 1:
                    em_regiao_textual = True
                else:
                    continue
            paragrafos = [child]
        elif em_regiao_textual:
            paragrafos = list(child.iter(qn('w:p')))
        else:
            continue

        for p in paragrafos:
            if _eh_paragrafo_de_caption(p):
                continue
            antes = _texto_paragrafo(p)
            r, nr = _processar_paragrafo(p, mapa_labels)
            if r > 0 or nr > 0 or _texto_paragrafo(p) != antes:
                paragrafos_modificados += 1
            total_resolvidas += r
            total_nao_resolvidas += nr

    if paragrafos_modificados > 0:
        doc.save(caminho_master)

    return {
        'tags_resolvidas': total_resolvidas,
        'tags_nao_resolvidas': total_nao_resolvidas,
        'paragrafos_modificados': paragrafos_modificados,
    }
