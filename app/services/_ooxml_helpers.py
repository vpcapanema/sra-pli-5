"""Helpers para construir estruturas OOXML canonicas.

Ponto unico para criacao de campos do Word (`<w:fldChar>` + `<w:instrText>`),
bookmarks (`<w:bookmarkStart>`/`<w:bookmarkEnd>`) e runs com texto formatado.
Usado por `servico_captioning` e `servico_cross_refs` para garantir 100%
compatibilidade DOCX.

Decisoes:
- IDs de bookmark gerados sequencialmente a partir de 100000+ (alto o
  bastante para nao colidir com bookmarks pre-existentes do template).
- Prefixo de bookmark `_Ref_sra_` identifica bookmarks gerados por
  nos — facilita limpeza/regeneracao idempotente.
- Campo `SEQ <rotulo> \\* ARABIC`: o `<rotulo>` deve casar EXATAMENTE
  com o usado no `TOC \\c "<rotulo>"` para que a Lista de Figuras/
  Tabelas seja preenchida pelo Word.
"""
from __future__ import annotations

from typing import Optional

from docx.oxml.ns import qn
from lxml import etree


W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
XML_SPACE_PRESERVE = (
    '{http://www.w3.org/XML/1998/namespace}space',
    'preserve',
)

# Prefixo dos bookmarks que GERAMOS (para distinguir dos pre-existentes
# no template e permitir limpeza segura).
PREFIXO_BOOKMARK = '_Ref_sra_'


class GeradorIdsBookmark:
    """Contador monotonico para w:id de bookmarks. IDs comecam em
    100000 para nao colidir com IDs ja presentes no template."""

    def __init__(self, inicio: int = 100000):
        self._proximo = inicio

    def proximo(self) -> int:
        valor = self._proximo
        self._proximo += 1
        return valor


def nome_bookmark(tipo: str, identificador: str) -> str:
    """Constroi o nome do bookmark para um elemento numerado.

    `tipo` deve ser 'fig' | 'tab' | 'eq'.
    `identificador` pode ser o label do autor (preferido, estavel) ou
    um indice numerico (`h{H1}_n{seq}`) quando nao ha label.

    Retorno: `_Ref_sra_<tipo>_<identificador>`.
    """
    # Sanear identificador para ser valido em w:name (alfanumerico,
    # underscore, hifen, ponto). Substitui qualquer outra coisa por '_'.
    safe = ''.join(
        c if (c.isalnum() or c in '_-.') else '_'
        for c in identificador
    )
    return f'{PREFIXO_BOOKMARK}{tipo}_{safe}'


def criar_run_texto(texto: str, preservar_espaco: bool = True):
    """Cria um `<w:r><w:t>` com `xml:space="preserve"` quando o texto
    tem espacos significativos.
    """
    w = f'{{{W_NS}}}'
    r = etree.Element(f'{w}r')
    t = etree.SubElement(r, f'{w}t')
    if preservar_espaco:
        t.set(*XML_SPACE_PRESERVE)
    t.text = texto
    return r


def criar_runs_campo(
    instrucao: str,
    cache_resultado: str,
) -> list:
    """Constroi a sequencia de runs que compoe um campo do Word:

        <w:r><w:fldChar w:fldCharType="begin"/></w:r>
        <w:r><w:instrText xml:space="preserve">{instrucao}</w:instrText></w:r>
        <w:r><w:fldChar w:fldCharType="separate"/></w:r>
        <w:r><w:t>{cache_resultado}</w:t></w:r>
        <w:r><w:fldChar w:fldCharType="end"/></w:r>

    Retorna lista de elementos `<w:r>`. O cache e o que aparece quando
    o documento e aberto antes do Word recalcular o campo.
    """
    w = f'{{{W_NS}}}'
    runs = []

    # begin
    r1 = etree.Element(f'{w}r')
    fld1 = etree.SubElement(r1, f'{w}fldChar')
    fld1.set(f'{w}fldCharType', 'begin')
    runs.append(r1)

    # instrText
    r2 = etree.Element(f'{w}r')
    instr = etree.SubElement(r2, f'{w}instrText')
    instr.set(*XML_SPACE_PRESERVE)
    instr.text = instrucao
    runs.append(r2)

    # separate
    r3 = etree.Element(f'{w}r')
    fld3 = etree.SubElement(r3, f'{w}fldChar')
    fld3.set(f'{w}fldCharType', 'separate')
    runs.append(r3)

    # cache
    r4 = etree.Element(f'{w}r')
    t4 = etree.SubElement(r4, f'{w}t')
    t4.set(*XML_SPACE_PRESERVE)
    t4.text = cache_resultado
    runs.append(r4)

    # end
    r5 = etree.Element(f'{w}r')
    fld5 = etree.SubElement(r5, f'{w}fldChar')
    fld5.set(f'{w}fldCharType', 'end')
    runs.append(r5)

    return runs


def criar_runs_campo_seq(
    rotulo: str, cache_numero: str
) -> list:
    """Atalho: campo `SEQ <rotulo> \\* ARABIC` com cache."""
    return criar_runs_campo(
        f' SEQ {rotulo} \\* ARABIC ',
        cache_numero,
    )


def criar_runs_campo_ref(
    nome_bookmark: str,
    cache_resultado: str,
    *,
    hyperlink: bool = True,
) -> list:
    """Atalho: campo `REF <nome_bookmark> \\h` (com hyperlink por padrao).

    `cache_resultado` e o texto que aparece antes do Word recalcular
    (tipicamente o numero, ex: "5.1").
    """
    flags = ' \\h' if hyperlink else ''
    return criar_runs_campo(
        f' REF {nome_bookmark}{flags} ',
        cache_resultado,
    )


def criar_bookmark_par(
    nome_bm: str, id_gen: GeradorIdsBookmark
) -> tuple:
    """Cria o par `(<w:bookmarkStart>, <w:bookmarkEnd>)` com IDs
    coordenados (mesmo `w:id`). Retorna a tupla; o caller insere os
    elementos nas posicoes apropriadas do paragrafo.
    """
    w = f'{{{W_NS}}}'
    bm_id = id_gen.proximo()

    bms = etree.Element(f'{w}bookmarkStart')
    bms.set(f'{w}id', str(bm_id))
    bms.set(f'{w}name', nome_bm)

    bme = etree.Element(f'{w}bookmarkEnd')
    bme.set(f'{w}id', str(bm_id))

    return bms, bme


def remover_bookmarks_sra(body) -> int:
    """Remove TODOS os `<w:bookmarkStart>` e `<w:bookmarkEnd>` do body
    cujo nome comeca com `_Ref_sra_`. Retorna a quantidade removida.

    Idempotencia: chamado antes de regerar legendas, evita acumulo
    de bookmarks duplicados a cada reindex.
    """
    removidos = 0
    bms_tag = qn('w:bookmarkStart')
    bme_tag = qn('w:bookmarkEnd')
    name_attr = qn('w:name')
    id_attr = qn('w:id')

    # Coletar IDs de bookmarkStart com nosso prefixo
    ids_a_remover: set = set()
    elementos_a_remover: list = []
    for bm in list(body.iter(bms_tag)):
        nome = bm.get(name_attr) or ''
        if nome.startswith(PREFIXO_BOOKMARK):
            bm_id = bm.get(id_attr)
            if bm_id:
                ids_a_remover.add(bm_id)
            elementos_a_remover.append(bm)

    # bookmarkEnd correspondentes (por id)
    for bme in list(body.iter(bme_tag)):
        if bme.get(id_attr) in ids_a_remover:
            elementos_a_remover.append(bme)

    for elem in elementos_a_remover:
        parent = elem.getparent()
        if parent is not None:
            parent.remove(elem)
            removidos += 1
    return removidos


def aplicar_estilo_paragrafo(p_element, estilo: Optional[str]) -> None:
    """Define `<w:pStyle w:val="estilo"/>` no `<w:pPr>` do paragrafo.
    Se `estilo` for None, nao faz nada (paragrafo herda Normal).
    Substitui pStyle existente.
    """
    if not estilo:
        return
    w = f'{{{W_NS}}}'
    pPr = p_element.find(f'{w}pPr')
    if pPr is None:
        # pPr deve ser o PRIMEIRO filho do <w:p>
        pPr = etree.Element(f'{w}pPr')
        p_element.insert(0, pPr)
    pStyle = pPr.find(f'{w}pStyle')
    if pStyle is None:
        pStyle = etree.SubElement(pPr, f'{w}pStyle')
    pStyle.set(f'{w}val', estilo)
