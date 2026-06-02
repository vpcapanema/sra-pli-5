"""
Sanitizador de DOCX para visualização no editor eigenpal.

O @eigenpal/docx-editor-react usa um schema ProseMirror estrito e rejeita
estruturas DOCX comuns mas malformadas, como células de tabela sem
parágrafos ('Invalid content for node tableRow: <>'). Este serviço lê o
arquivo .docx, garante que toda <w:tc> tenha pelo menos um <w:p> e
devolve os bytes sanitizados, sem modificar o arquivo original.
"""

from __future__ import annotations

import io
import zipfile
from typing import Optional
from xml.etree import ElementTree as ET

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_NS = "http://www.w3.org/XML/1998/namespace"
NSMAP = {"w": W_NS}
ET.register_namespace("w", W_NS)

# Documentos típicos do Word incluem estes namespaces. Pré-registrar
# evita que o ElementTree gere prefixos genéricos (ns0, ns1, ...).
_EXTRA_NAMESPACES = {
    "wp": ("http://schemas.openxmlformats.org/drawingml/2006/" "wordprocessingDrawing"),
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "v": "urn:schemas-microsoft-com:vml",
    "o": "urn:schemas-microsoft-com:office:office",
    "w10": "urn:schemas-microsoft-com:office:word",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "w15": "http://schemas.microsoft.com/office/word/2012/wordml",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
}
for _prefix, _uri in _EXTRA_NAMESPACES.items():
    ET.register_namespace(_prefix, _uri)


def _qn(local: str) -> str:
    """Devolve um nome qualificado com o namespace de wordprocessingml."""
    return f"{{{W_NS}}}{local}"


def _xml_qn(local: str) -> str:
    """Devolve um nome qualificado com o namespace XML."""
    return f"{{{XML_NS}}}{local}"


# Conjunto de fontes seguras (disponíveis em todos os SOs e/ou no
# Google Fonts) que não precisam de normalização.
_FONTES_PADRAO = {
    "arial",
    "calibri",
    "calibri light",
    "cambria",
    "candara",
    "consolas",
    "constantia",
    "corbel",
    "courier new",
    "georgia",
    "helvetica",
    "helvetica neue",
    "lucida console",
    "lucida sans unicode",
    "palatino linotype",
    "segoe ui",
    "tahoma",
    "times new roman",
    "trebuchet ms",
    "verdana",
    "symbol",
    "wingdings",
}

# Mapeamento de fontes proprietárias/incomuns para equivalentes padrão.
# Chave em lowercase (sem espaços extras). Quando uma fonte não está
# em _FONTES_PADRAO nem em _MAPA_FONTES, cai para Arial.
_MAPA_FONTES = {
    "futurabt": "Arial",
    "futura bt": "Arial",
    "futura": "Arial",
    "cg omega": "Calibri",
    "zapfhumnst dm bt": "Calibri",
    "zapfhumnst bt": "Calibri",
    "avantgarde bk bt": "Arial",
    "avantgarde": "Arial",
    "humanst521 bt": "Calibri",
    "humanst521 lt bt": "Calibri",
    "times new roman bold": "Times New Roman",
    "minionpro-regular": "Times New Roman",
    "minion pro": "Times New Roman",
    "egyptian505 lt bt": "Times New Roman",
    "egyptian505 bt": "Times New Roman",
    "helv": "Helvetica",
    "helvetica-bold": "Helvetica",
    "arial-boldmt": "Arial",
    "arialmt": "Arial",
    "timesnewromanpsmt": "Times New Roman",
    "timesnewromanps-boldmt": "Times New Roman",
}

# Atributos de <w:rFonts> que carregam nomes de fonte
_ATRIBS_FONTE = (
    "ascii",
    "hAnsi",
    "cs",
    "eastAsia",
    "asciiTheme",
    "hAnsiTheme",
    "csTheme",
    "eastAsiaTheme",
)


def _normalizar_fonte(nome: str) -> str:
    """Devolve o nome a usar para uma fonte. Se já for padrão ou
    estiver mapeada, retorna o equivalente; caso contrário, Arial."""
    if not nome:
        return nome
    chave = nome.strip().lower()
    if chave in _FONTES_PADRAO:
        return nome  # preserva capitalização original
    if chave in _MAPA_FONTES:
        return _MAPA_FONTES[chave]
    # Fonte desconhecida → fallback genérico
    return "Arial"


def _criar_paragrafo_valido():
    """Cria um <w:p> aceito pelo parser do editor.

    Um parágrafo totalmente vazio pode ser descartado por alguns parsers.
    Por isso usamos um run com um espaço preservado; visualmente é neutro,
    mas estruturalmente satisfaz o `block+` esperado em células de tabela.
    """
    p = ET.Element(_qn("p"))
    ET.SubElement(p, _qn("pPr"))
    r = ET.SubElement(p, _qn("r"))
    t = ET.SubElement(r, _qn("t"))
    t.set(_xml_qn("space"), "preserve")
    t.text = "\u200b"
    return p


def _criar_celula_valida():
    """Cria uma célula Word mínima, estruturalmente válida."""
    tc = ET.Element(_qn("tc"))
    tc_pr = ET.SubElement(tc, _qn("tcPr"))
    tc_w = ET.SubElement(tc_pr, _qn("tcW"))
    tc_w.set(_qn("w"), "0")
    tc_w.set(_qn("type"), "auto")
    tc.append(_criar_paragrafo_valido())
    return tc


def _garantir_tcpr(tc) -> bool:
    """Garante que a célula tenha <w:tcPr> como metadado estrutural."""
    for child in tc:
        if child.tag == _qn("tcPr"):
            return False

    tc_pr = ET.Element(_qn("tcPr"))
    tc_w = ET.SubElement(tc_pr, _qn("tcW"))
    tc_w.set(_qn("w"), "0")
    tc_w.set(_qn("type"), "auto")
    tc.insert(0, tc_pr)
    return True


def _normalizar_rfonts(root) -> bool:
    """Substitui referências de fonte em <w:rFonts> por equivalentes
    padrão. Retorna True se algo foi modificado.
    Aplica-se tanto a document.xml quanto a styles.xml/header/footer."""
    modificado = False
    rfonts_tag = _qn("rFonts")
    for rfonts in root.iter(rfonts_tag):
        for atrib in _ATRIBS_FONTE:
            chave = _qn(atrib)
            valor = rfonts.get(chave)
            if not valor:
                continue
            novo = _normalizar_fonte(valor)
            if novo != valor:
                rfonts.set(chave, novo)
                modificado = True
    return modificado


def _is_vmerge_continue(tc) -> bool:
    """Retorna True se a celula e uma continuacao de vertical merge.

    Uma celula com `<w:vMerge/>` ou `<w:vMerge w:val="continue"/>` e
    descartada pelo parser do eigenpal (porque visualmente ela faz
    parte da celula da linha de cima). Quando TODAS as celulas de
    uma <w:tr> sao continue, a row fica vazia no ProseMirror e
    dispara `Invalid content for node tableRow: <>`.
    """
    tcpr = tc.find(_qn("tcPr"))
    if tcpr is None:
        return False
    vm = tcpr.find(_qn("vMerge"))
    if vm is None:
        return False
    val = vm.get(_qn("val"))
    return val is None or val == "continue"


# =====================================================================
# Achatamento de text boxes flutuantes (capa)
# =====================================================================

# Namespaces dos shapes flutuantes — declarados localmente para
# que `_aplanar_text_boxes_flutuantes` possa procurar elementos sem
# depender de imports externos.
_WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
_WPS_NS = "http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
_MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"


# Atributos e filhos EXCLUSIVOS de <wp:anchor> que precisam ser
# removidos ao converter para <wp:inline>.
_ANCHOR_ATTRS_REMOVER = (
    "behindDoc",
    "locked",
    "layoutInCell",
    "allowOverlap",
    "simplePos",
    "relativeHeight",
    "distT",
    "distB",
    "distL",
    "distR",
)
_ANCHOR_FILHOS_REMOVER = (
    "simplePos",
    "positionH",
    "positionV",
    "wrapNone",
    "wrapSquare",
    "wrapTight",
    "wrapThrough",
    "wrapTopAndBottom",
)


def _converter_anchor_para_inline(anchor) -> bool:
    """Converte um `<wp:anchor>` em `<wp:inline>` in-place.

    O renderer do eigenpal envolve cada anchor em um NodeView de
    'objeto' (moldura azul), o que polui visualmente a capa. Imagens
    inline (`<wp:inline>`) sao renderizadas como `<img>` normal,
    no fluxo do texto, sem moldura.

    Operacao:
      - Renomeia a tag de `anchor` para `inline`.
      - Remove atributos exclusivos de anchor (behindDoc, locked,
        simplePos, etc.).
      - Remove filhos exclusivos de anchor (positionH/V, wrapNone,
        simplePos, wrap*).
      - Preserva: extent, effectExtent, docPr, cNvGraphicFramePr,
        graphic — que sao validos em `<wp:inline>`.

    Retorna True se a conversao foi bem-sucedida.
    """
    # Renomeia a tag (mantem o namespace WP)
    novo_tag = f"{{{_WP_NS}}}inline"
    if anchor.tag == novo_tag:
        return False
    anchor.tag = novo_tag

    # Remove atributos exclusivos de anchor
    for attr in _ANCHOR_ATTRS_REMOVER:
        if attr in anchor.attrib:
            del anchor.attrib[attr]

    # Remove filhos exclusivos de anchor
    filhos_para_remover = []
    for filho in list(anchor):
        local = filho.tag.split("}")[-1] if "}" in filho.tag else filho.tag
        if local in _ANCHOR_FILHOS_REMOVER:
            filhos_para_remover.append(filho)
    for filho in filhos_para_remover:
        anchor.remove(filho)

    # Garantir que extent existe (obrigatorio em inline)
    if anchor.find(f"{{{_WP_NS}}}extent") is None:
        return False  # estrutura inesperada, abortar

    return True


def _remover_fallbacks_alternate_content(root) -> bool:
    """Remove blocos `<mc:Fallback>` de `<mc:AlternateContent>`.

    O Word usa `<mc:Choice>` quando entende DrawingML moderno e ignora
    o fallback VML. O eigenpal, porém, pode ler também o fallback e
    duplicar conteúdo antigo da capa. Esta limpeza é feita somente nos
    bytes em memória servidos ao editor.
    """
    modificado = False
    alt_qn = f"{{{_MC_NS}}}AlternateContent"
    fallback_qn = f"{{{_MC_NS}}}Fallback"

    for alt in root.iter(alt_qn):
        for fallback in list(alt.findall(fallback_qn)):
            alt.remove(fallback)
            modificado = True

    return modificado


def _substituir_alternate_content_por_choice(root) -> bool:
    modificado = False
    alt_qn = f"{{{_MC_NS}}}AlternateContent"
    choice_qn = f"{{{_MC_NS}}}Choice"

    def processar(parent):
        nonlocal modificado
        for child in list(parent):
            if child.tag == alt_qn:
                idx = list(parent).index(child)
                choice = child.find(choice_qn)
                if choice is not None:
                    novos = list(choice)
                    if novos:
                        parent.remove(child)
                        for offset, novo in enumerate(novos):
                            parent.insert(idx + offset, novo)
                        modificado = True
                        continue
                parent.remove(child)
                modificado = True
                continue
            processar(child)

    processar(root)
    return modificado


def _normalizar_elementos_incompativeis_preview(root) -> bool:
    modificado = False
    p_qn = _qn("p")
    r_qn = _qn("r")
    fld_simple_qn = _qn("fldSimple")
    remover_em_run = {
        _qn("commentReference"),
        _qn("annotationRef"),
    }

    for p in root.iter(p_qn):
        for child in list(p):
            if child.tag != fld_simple_qn:
                continue
            idx = list(p).index(child)
            filhos = list(child)
            p.remove(child)
            for offset, filho in enumerate(filhos):
                p.insert(idx + offset, filho)
            modificado = True

    for r in root.iter(r_qn):
        for child in list(r):
            if child.tag in remover_em_run:
                r.remove(child)
                modificado = True

    return modificado


def _remover_imagens_header_footer(xml_bytes: bytes) -> bytes:
    """Remove `<w:drawing>` e `<w:pict>` em header*.xml/footer*.xml.

    O renderer browser nao consegue resolver `r:embed` em parts
    auxiliares e renderiza um `<img>` quebrado em todo rodape/cabecalho.
    Removemos so os elementos visuais; o texto do rodape (numero de
    pagina, datas, codigo) continua aparecendo. Aplicado apenas em
    memoria, o DOCX em disco mantem a logo no rodape.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return xml_bytes

    drawing_qn = _qn("drawing")
    pict_qn = _qn("pict")
    modificado = False

    def limpar(parent):
        nonlocal modificado
        for filho in list(parent):
            if filho.tag in (drawing_qn, pict_qn):
                parent.remove(filho)
                modificado = True
            else:
                limpar(filho)

    limpar(root)
    if not modificado:
        return xml_bytes
    return ET.tostring(root, xml_declaration=True, encoding="UTF-8")


def _espelhar_headers_footers_em_sectpr(root) -> bool:
    """Garante simetria de headerReference/footerReference por tipo.

    Renderers DOCX em browser (incluindo o usado pelo eigenpal) tentam
    resolver `footerReference type="even"` quando existe um
    `headerReference type="even"` no mesmo `<w:sectPr>`. Se o footer
    correspondente nao existir, eles caem em um `<img>` sem `src` e
    mostram o icone de imagem quebrada em paginas pares.

    Esta funcao clona a referencia padrao (`type="default"`) para os
    tipos faltantes (`first`, `even`) - somente no XML em memoria
    servido ao editor. O DOCX em disco nao e modificado.
    """
    modificado = False
    sectpr_qn = _qn("sectPr")
    href_qn = _qn("headerReference")
    fref_qn = _qn("footerReference")
    type_qn = _qn("type")
    rid_qn = (
        "{http://schemas.openxmlformats.org/officeDocument/"
        "2006/relationships}id"
    )

    for sect in root.iter(sectpr_qn):
        for ref_qn in (href_qn, fref_qn):
            par_qn = fref_qn if ref_qn == href_qn else href_qn
            tipos_aqui = {el.get(type_qn) or "default" for el in sect.findall(ref_qn)}
            par_default = next(
                (el for el in sect.findall(par_qn) if (el.get(type_qn) or "default") == "default"),
                None,
            )
            if par_default is None:
                continue
            tipos_par = {el.get(type_qn) or "default" for el in sect.findall(par_qn)}
            for tipo in tipos_aqui:
                if tipo == "default" or tipo in tipos_par:
                    continue
                clone = ET.SubElement(sect, par_qn)
                clone.set(type_qn, tipo)
                rid = par_default.get(rid_qn)
                if rid:
                    clone.set(rid_qn, rid)
                modificado = True

    return modificado


def _aplanar_text_boxes_flutuantes(root) -> bool:
    """Achata elementos flutuantes da capa para que o editor eigenpal
    consiga renderiza-los sem encapsular em molduras de 'objeto'.

    Duas operacoes em sequencia:

    (1) **Text boxes flutuantes (`<wps:wsp>` dentro de `<wp:anchor>`)**:
        Extrai os paragrafos do `<w:txbxContent>` e os insere como
        paragrafos comuns no body, ANTES do paragrafo do anchor.
        Remove o run/AlternateContent que continha o anchor.

        Sem isto, o titulo dinamico da capa "RELATORIO MENSAL - MES X"
        desaparece na visualizacao do editor (eigenpal nao desenha
        shapes flutuantes — so imagens).

    (2) **Imagens flutuantes (`<wp:anchor>` com `<pic:pic>`)**:
        Converte o anchor para `<wp:inline>`. Inline images sao
        renderizadas como `<img>` no fluxo do texto, sem moldura.
        Sem isto, o renderer envolve a imagem da capa em um bloco
        de 'objeto' azul que captura todo o paragrafo body[1].

    O DOCX em disco NAO e alterado: este passo e parte da pipeline
    de sanitizacao em memoria executada apenas ao servir o arquivo
    para o editor. O download do DOCX final preserva o text box e
    a imagem flutuantes originais (visual fiel no Word).

    Retorna True se algo foi modificado.
    """
    body = root.find(_qn("body"))
    if body is None:
        return False

    modificado = False
    p_qn = _qn("p")
    r_qn = _qn("r")
    anchor_qn = f"{{{_WP_NS}}}anchor"
    txbx_qn = _qn("txbxContent")
    alt_qn = f"{{{_MC_NS}}}AlternateContent"

    # Localizar paragrafos do body que contem anchors com text boxes
    for paragrafo in list(body):
        if paragrafo.tag != p_qn:
            continue

        anchors = list(paragrafo.iter(anchor_qn))
        if not anchors:
            continue

        # Coletar paragrafos a inserir e elementos a remover
        paragrafos_a_inserir = []
        elementos_a_remover = []  # tuplas (parent, child)

        for anchor in anchors:
            # Procura txbxContent dentro do anchor (pode estar em
            # <a:graphic>/<a:graphicData>/<wps:wsp>/<wps:txbx>/<w:txbxContent>)
            txbx_content = None
            for elem in anchor.iter(txbx_qn):
                txbx_content = elem
                break
            if txbx_content is None:
                continue  # anchor sem text box (provavelmente imagem)

            # Extrai os paragrafos de dentro do text box
            for p_interno in txbx_content.findall(p_qn):
                # Clona o paragrafo (deepcopy via tostring/fromstring)
                clonado = ET.fromstring(ET.tostring(p_interno))
                paragrafos_a_inserir.append(clonado)

            # Marca o ancestral imediato do anchor para remocao.
            # Tipicamente: <w:r> -> <mc:AlternateContent> -> ... -> <wp:anchor>
            # Subimos ate encontrar o <w:r> filho do paragrafo.
            run_pai = None
            # ElementTree nao tem getparent — fazemos varredura
            for r in paragrafo.findall(r_qn):
                # se este run contem o anchor, ele e o que removeremos
                if anchor in list(r.iter()):
                    run_pai = r
                    break
            if run_pai is not None:
                elementos_a_remover.append((paragrafo, run_pai))
            else:
                # Se nao e um run direto, pode ser um AlternateContent
                # filho direto do paragrafo
                for alt in paragrafo.findall(alt_qn):
                    if anchor in list(alt.iter()):
                        elementos_a_remover.append((paragrafo, alt))
                        break

        if not paragrafos_a_inserir:
            continue

        # Inserir paragrafos extraidos ANTES do paragrafo atual no body
        idx_no_body = list(body).index(paragrafo)
        for offset, p_novo in enumerate(paragrafos_a_inserir):
            body.insert(idx_no_body + offset, p_novo)
        modificado = True

        # Remover elementos do paragrafo original que continham anchors
        for parent, child in elementos_a_remover:
            try:
                parent.remove(child)
            except ValueError:
                pass

    # ===== Passo (2): converter imagens flutuantes para inline =====
    # Apos achatar text boxes, varrer o body inteiro e converter os
    # anchors REMANESCENTES (que sao imagens, nao text boxes) para
    # inline. Isso retira a moldura azul de 'objeto' que o renderer
    # do eigenpal envolve em volta de cada anchor.
    for anchor in list(body.iter(anchor_qn)):
        # So converte anchors com pic:pic dentro (= imagens reais).
        # Anchors com text box ja foram removidos no passo 1.
        pic_qn_local = (
            "{http://schemas.openxmlformats.org/drawingml/"
            "2006/picture}pic"
        )
        if anchor.find(f".//{pic_qn_local}") is None:
            continue
        if _converter_anchor_para_inline(anchor):
            modificado = True

    return modificado


def _sanitizar_xml_documento(xml_bytes: bytes) -> bytes:
    """
    Sanitiza o XML do documento Word:
    - Toda <w:tc> ganha pelo menos um <w:p> (eigenpal exige).
    - Toda <w:tr> ganha pelo menos uma <w:tc>.
    - <w:tr> em que TODAS as celulas sao vMerge=continue: promove a
      primeira celula a inicio de merge (remove o vMerge) para que a
      row tenha pelo menos uma celula visivel ao parser do eigenpal.
    - Fontes proprietarias em <w:rFonts> sao mapeadas para padrao.
    - Text boxes flutuantes da capa (<wp:anchor> + <wps:wsp>) tem seu
      conteudo extraido para paragrafos comuns no body — o renderer
      do eigenpal nao desenha shapes flutuantes, e sem este ajuste o
      titulo dinamico da capa "RELATORIO MENSAL - MES X" sumiria.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return xml_bytes  # se não for parseável, devolver intacto

    modificado = False

    if _substituir_alternate_content_por_choice(root):
        modificado = True

    if _remover_fallbacks_alternate_content(root):
        modificado = True

    if _normalizar_elementos_incompativeis_preview(root):
        modificado = True

    if _espelhar_headers_footers_em_sectpr(root):
        modificado = True

    if _aplanar_text_boxes_flutuantes(root):
        modificado = True

    for tc in root.iter(_qn("tc")):
        if _garantir_tcpr(tc):
            modificado = True

        paragrafos = [child for child in tc if child.tag == _qn("p")]
        if not paragrafos:
            tc.append(_criar_paragrafo_valido())
            modificado = True
        else:
            ultimo = paragrafos[-1]
            tem_texto = any((t.text or "").strip() for t in ultimo.iter(_qn("t")))
            tem_desenho = any(
                child.tag.endswith("}drawing") or child.tag.endswith("}pict")
                for child in ultimo.iter()
            )
            if not tem_texto and not tem_desenho:
                # Alguns parsers descartam parágrafos totalmente vazios.
                # Inserir um run com espaço preservado evita tableCell vazio.
                r = ET.SubElement(ultimo, _qn("r"))
                t = ET.SubElement(r, _qn("t"))
                t.set(_xml_qn("space"), "preserve")
                t.text = "\u200b"
                modificado = True

    for tr in root.iter(_qn("tr")):
        tcs_diretos = [c for c in tr if c.tag == _qn("tc")]

        if not tcs_diretos:
            tr.append(_criar_celula_valida())
            modificado = True
            continue

        # Se TODAS as cells sao vMerge=continue, o parser descarta
        # tudo e a row fica vazia. Promove a primeira a inicio de
        # merge removendo o <w:vMerge> dela.
        if all(_is_vmerge_continue(tc) for tc in tcs_diretos):
            primeira = tcs_diretos[0]
            tcpr = primeira.find(_qn("tcPr"))
            if tcpr is not None:
                vm = tcpr.find(_qn("vMerge"))
                if vm is not None:
                    tcpr.remove(vm)
                    modificado = True

    if _normalizar_rfonts(root):
        modificado = True

    if not modificado:
        return xml_bytes

    return ET.tostring(root, xml_declaration=True, encoding="UTF-8")


def _sanitizar_xml_estilos(xml_bytes: bytes) -> bytes:
    """Normaliza fontes em styles.xml (e qualquer outro XML que só
    precise de troca de fontes, sem restruturação)."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return xml_bytes
    if not _normalizar_rfonts(root):
        return xml_bytes
    return ET.tostring(root, xml_declaration=True, encoding="UTF-8")


def _sanitizar_font_table(xml_bytes: bytes) -> bytes:
    """Reescreve fontTable.xml: cada <w:font w:name="..."> que usa
    fonte proprietária recebe o nome do equivalente padrão. Isso
    impede o editor de tentar carregar a fonte original do Google
    Fonts."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return xml_bytes
    modificado = False
    name_attr = _qn("name")
    for font_el in root.iter(_qn("font")):
        nome = font_el.get(name_attr)
        if not nome:
            continue
        novo = _normalizar_fonte(nome)
        if novo != nome:
            font_el.set(name_attr, novo)
            modificado = True
    if not modificado:
        return xml_bytes
    return ET.tostring(root, xml_declaration=True, encoding="UTF-8")


def sanitizar_docx(caminho: str) -> Optional[bytes]:
    """
    Lê um .docx do disco e devolve uma cópia em memória com células de
    tabela vazias preenchidas com um parágrafo vazio. Retorna None em
    caso de erro (caminho inexistente, arquivo corrompido, etc.).
    """
    try:
        with open(caminho, "rb") as f:
            docx_bytes = f.read()
    except OSError:
        return None

    return sanitizar_docx_bytes(docx_bytes)


def sanitizar_docx_bytes(docx_bytes: bytes) -> Optional[bytes]:
    """Variante que opera diretamente em bytes."""
    try:
        zin = zipfile.ZipFile(io.BytesIO(docx_bytes), mode="r")
    except zipfile.BadZipFile:
        return None

    saida = io.BytesIO()
    with zipfile.ZipFile(saida, mode="w", compression=zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            nome = item.filename

            # Todos os XMLs de conteúdo Word: estrutura + fontes.
            # Inclui document.xml, headers, footers, footnotes, endnotes,
            # comments, glossary/document.xml etc.
            if (
                nome.startswith("word/")
                and nome.endswith(".xml")
                and nome
                not in (
                    "word/styles.xml",
                    "word/fontTable.xml",
                    "word/settings.xml",
                    "word/webSettings.xml",
                    "word/numbering.xml",
                )
            ):
                data = _sanitizar_xml_documento(data)
                # Para header*.xml/footer*.xml, remover imagens que o
                # renderer browser nao consegue resolver e mostraria
                # como `<img>` quebrado.
                base = nome.split("/")[-1]
                if base.startswith("header") or base.startswith("footer"):
                    data = _remover_imagens_header_footer(data)

            # styles.xml: apenas fontes
            elif nome == "word/styles.xml":
                data = _sanitizar_xml_estilos(data)

            # fontTable.xml: renomeia fontes proprietárias
            elif nome == "word/fontTable.xml":
                data = _sanitizar_font_table(data)

            zout.writestr(item, data)
    zin.close()

    return saida.getvalue()
