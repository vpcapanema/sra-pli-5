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

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
XML_NS = 'http://www.w3.org/XML/1998/namespace'
NSMAP = {'w': W_NS}
ET.register_namespace('w', W_NS)

# Documentos típicos do Word incluem estes namespaces. Pré-registrar
# evita que o ElementTree gere prefixos genéricos (ns0, ns1, ...).
_EXTRA_NAMESPACES = {
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'm': 'http://schemas.openxmlformats.org/officeDocument/2006/math',
    'v': 'urn:schemas-microsoft-com:vml',
    'o': 'urn:schemas-microsoft-com:office:office',
    'w10': 'urn:schemas-microsoft-com:office:word',
    'w14': 'http://schemas.microsoft.com/office/word/2010/wordml',
    'w15': 'http://schemas.microsoft.com/office/word/2012/wordml',
    'mc': 'http://schemas.openxmlformats.org/markup-compatibility/2006',
}
for _prefix, _uri in _EXTRA_NAMESPACES.items():
    ET.register_namespace(_prefix, _uri)


def _qn(local: str) -> str:
    """Devolve um nome qualificado com o namespace de wordprocessingml."""
    return f'{{{W_NS}}}{local}'


def _xml_qn(local: str) -> str:
    """Devolve um nome qualificado com o namespace XML."""
    return f'{{{XML_NS}}}{local}'


# Conjunto de fontes seguras (disponíveis em todos os SOs e/ou no
# Google Fonts) que não precisam de normalização.
_FONTES_PADRAO = {
    'arial', 'calibri', 'calibri light', 'cambria', 'candara',
    'consolas', 'constantia', 'corbel', 'courier new', 'georgia',
    'helvetica', 'helvetica neue', 'lucida console',
    'lucida sans unicode', 'palatino linotype', 'segoe ui',
    'tahoma', 'times new roman', 'trebuchet ms', 'verdana',
    'symbol', 'wingdings',
}

# Mapeamento de fontes proprietárias/incomuns para equivalentes padrão.
# Chave em lowercase (sem espaços extras). Quando uma fonte não está
# em _FONTES_PADRAO nem em _MAPA_FONTES, cai para Arial.
_MAPA_FONTES = {
    'futurabt': 'Arial',
    'futura bt': 'Arial',
    'futura': 'Arial',
    'cg omega': 'Calibri',
    'zapfhumnst dm bt': 'Calibri',
    'zapfhumnst bt': 'Calibri',
    'avantgarde bk bt': 'Arial',
    'avantgarde': 'Arial',
    'humanst521 bt': 'Calibri',
    'humanst521 lt bt': 'Calibri',
    'times new roman bold': 'Times New Roman',
    'minionpro-regular': 'Times New Roman',
    'minion pro': 'Times New Roman',
    'egyptian505 lt bt': 'Times New Roman',
    'egyptian505 bt': 'Times New Roman',
    'helv': 'Helvetica',
    'helvetica-bold': 'Helvetica',
    'arial-boldmt': 'Arial',
    'arialmt': 'Arial',
    'timesnewromanpsmt': 'Times New Roman',
    'timesnewromanps-boldmt': 'Times New Roman',
}

# Atributos de <w:rFonts> que carregam nomes de fonte
_ATRIBS_FONTE = ('ascii', 'hAnsi', 'cs', 'eastAsia',
                 'asciiTheme', 'hAnsiTheme', 'csTheme', 'eastAsiaTheme')


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
    return 'Arial'


def _criar_paragrafo_valido():
    """Cria um <w:p> aceito pelo parser do editor.

    Um parágrafo totalmente vazio pode ser descartado por alguns parsers.
    Por isso usamos um run com um espaço preservado; visualmente é neutro,
    mas estruturalmente satisfaz o `block+` esperado em células de tabela.
    """
    p = ET.Element(_qn('p'))
    ET.SubElement(p, _qn('pPr'))
    r = ET.SubElement(p, _qn('r'))
    t = ET.SubElement(r, _qn('t'))
    t.set(_xml_qn('space'), 'preserve')
    t.text = '\u200B'
    return p


def _criar_celula_valida():
    """Cria uma célula Word mínima, estruturalmente válida."""
    tc = ET.Element(_qn('tc'))
    tc_pr = ET.SubElement(tc, _qn('tcPr'))
    tc_w = ET.SubElement(tc_pr, _qn('tcW'))
    tc_w.set(_qn('w'), '0')
    tc_w.set(_qn('type'), 'auto')
    tc.append(_criar_paragrafo_valido())
    return tc


def _garantir_tcpr(tc) -> bool:
    """Garante que a célula tenha <w:tcPr> como metadado estrutural."""
    for child in tc:
        if child.tag == _qn('tcPr'):
            return False

    tc_pr = ET.Element(_qn('tcPr'))
    tc_w = ET.SubElement(tc_pr, _qn('tcW'))
    tc_w.set(_qn('w'), '0')
    tc_w.set(_qn('type'), 'auto')
    tc.insert(0, tc_pr)
    return True


def _normalizar_rfonts(root) -> bool:
    """Substitui referências de fonte em <w:rFonts> por equivalentes
    padrão. Retorna True se algo foi modificado.
    Aplica-se tanto a document.xml quanto a styles.xml/header/footer."""
    modificado = False
    rfonts_tag = _qn('rFonts')
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


def _sanitizar_xml_documento(xml_bytes: bytes) -> bytes:
    """
    Sanitiza o XML do documento Word:
    - Toda <w:tc> ganha pelo menos um <w:p> (eigenpal exige).
    - Toda <w:tr> ganha pelo menos uma <w:tc>.
    - Fontes proprietárias em <w:rFonts> são mapeadas para padrão.
    """
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return xml_bytes  # se não for parseável, devolver intacto

    modificado = False

    for tc in root.iter(_qn('tc')):
        if _garantir_tcpr(tc):
            modificado = True

        paragrafos = [child for child in tc if child.tag == _qn('p')]
        if not paragrafos:
            tc.append(_criar_paragrafo_valido())
            modificado = True
        else:
            ultimo = paragrafos[-1]
            tem_texto = any(
                (t.text or '').strip()
                for t in ultimo.iter(_qn('t'))
            )
            tem_desenho = any(
                child.tag.endswith('}drawing') or child.tag.endswith('}pict')
                for child in ultimo.iter()
            )
            if not tem_texto and not tem_desenho:
                # Alguns parsers descartam parágrafos totalmente vazios.
                # Inserir um run com espaço preservado evita tableCell vazio.
                r = ET.SubElement(ultimo, _qn('r'))
                t = ET.SubElement(r, _qn('t'))
                t.set(_xml_qn('space'), 'preserve')
                t.text = '\u200B'
                modificado = True

    for tr in root.iter(_qn('tr')):
        tem_celula = any(
            child.tag == _qn('tc') for child in tr
        )
        if not tem_celula:
            tr.append(_criar_celula_valida())
            modificado = True

    if _normalizar_rfonts(root):
        modificado = True

    if not modificado:
        return xml_bytes

    return ET.tostring(root, xml_declaration=True, encoding='UTF-8')


def _sanitizar_xml_estilos(xml_bytes: bytes) -> bytes:
    """Normaliza fontes em styles.xml (e qualquer outro XML que só
    precise de troca de fontes, sem restruturação)."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return xml_bytes
    if not _normalizar_rfonts(root):
        return xml_bytes
    return ET.tostring(root, xml_declaration=True, encoding='UTF-8')


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
    name_attr = _qn('name')
    for font_el in root.iter(_qn('font')):
        nome = font_el.get(name_attr)
        if not nome:
            continue
        novo = _normalizar_fonte(nome)
        if novo != nome:
            font_el.set(name_attr, novo)
            modificado = True
    if not modificado:
        return xml_bytes
    return ET.tostring(root, xml_declaration=True, encoding='UTF-8')


def sanitizar_docx(caminho: str) -> Optional[bytes]:
    """
    Lê um .docx do disco e devolve uma cópia em memória com células de
    tabela vazias preenchidas com um parágrafo vazio. Retorna None em
    caso de erro (caminho inexistente, arquivo corrompido, etc.).
    """
    try:
        with open(caminho, 'rb') as f:
            docx_bytes = f.read()
    except OSError:
        return None

    return sanitizar_docx_bytes(docx_bytes)


def sanitizar_docx_bytes(docx_bytes: bytes) -> Optional[bytes]:
    """Variante que opera diretamente em bytes."""
    try:
        zin = zipfile.ZipFile(io.BytesIO(docx_bytes), mode='r')
    except zipfile.BadZipFile:
        return None

    saida = io.BytesIO()
    with zipfile.ZipFile(
        saida, mode='w', compression=zipfile.ZIP_DEFLATED
    ) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            nome = item.filename

            # Todos os XMLs de conteúdo Word: estrutura + fontes.
            # Inclui document.xml, headers, footers, footnotes, endnotes,
            # comments, glossary/document.xml etc.
            if (
                nome.startswith('word/')
                and nome.endswith('.xml')
                and nome not in (
                    'word/styles.xml',
                    'word/fontTable.xml',
                    'word/settings.xml',
                    'word/webSettings.xml',
                    'word/numbering.xml',
                )
            ):
                data = _sanitizar_xml_documento(data)

            # styles.xml: apenas fontes
            elif nome == 'word/styles.xml':
                data = _sanitizar_xml_estilos(data)

            # fontTable.xml: renomeia fontes proprietárias
            elif nome == 'word/fontTable.xml':
                data = _sanitizar_font_table(data)

            zout.writestr(item, data)
    zin.close()

    return saida.getvalue()
