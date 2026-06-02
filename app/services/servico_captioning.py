"""Servico de captioning automatico para o DOCX em producao.

Responsabilidades (Fase 2 — versao completa):

1. Detectar elementos numeraveis no corpo do DOCX:
   - **Figuras**: paragrafos contendo `<w:drawing>` ou `<w:pict>`.
   - **Tabelas**: elementos `<w:tbl>`.
   - **Equacoes**: paragrafos contendo `<m:oMath>` ou `<m:oMathPara>`.

2. Numerar hierarquicamente baseado no heading mais recente (qualquer
   nivel). Exemplos:
   - Documento com H1 "5 Coordenacao" + H2 "5.1 Reunioes":
     - Figura dentro do H2 → "Figura 5.1.1", "Figura 5.1.2"
   - Documento sem H2:
     - Figura dentro do H1 → "Figura 5.1", "Figura 5.2"

3. Inserir/atualizar paragrafos de legenda:
   - **Figuras**: legenda APOS o paragrafo da imagem.
   - **Tabelas**: legenda ANTES da tabela (convencao ABNT/Word).
   - **Equacoes**: numero `(N.M)` anexado ao FIM do paragrafo da
     equacao (convencao matematica), sem criar paragrafo separado.

4. Extrair labels declarados pelo autor na legenda. Sintaxe:
   `Figura ?? – {{label:meu-grafico}} Texto descritivo`
   ou
   `{{label:meu-grafico}} Texto descritivo` (qualquer posicao no
   paragrafo de legenda).
   O servico devolve um dicionario `mapa_labels` que sera usado pelo
   `servico_cross_refs` para substituir `{{fig:meu-grafico}}` no corpo
   do texto pelo numero correspondente.

Uso tipico:
    from app.services.servico_captioning import reindexar_captions
    resumo = reindexar_captions(caminho_master)
    # resumo['mapa_labels'] = {'fig:meu-grafico': '5.1.2', ...}
"""
from __future__ import annotations

import re
from typing import Optional

from docx import Document
from docx.oxml.ns import qn
import lxml.etree as etree

from app.services._ooxml_helpers import texto_paragrafo as _texto_paragrafo


W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
M_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'


# Estilos comuns de legenda no Word (pt-BR e en-US)
ESTILOS_CAPTION = {'Caption', 'caption', 'Legenda', 'legenda'}

# Tipos suportados → rotulo + prefixo de label
ROTULOS = {
    'figura': 'Figura',
    'tabela': 'Tabela',
    'equacao': 'Equação',
}
LABEL_PREFIX = {
    'figura': 'fig',
    'tabela': 'tab',
    'equacao': 'eq',
}

# Regex para detectar prefixo de legenda existente.
# Aceita numero real ("5.1.2"), placeholders curtos ("??", "XX", "X")
# ou simplesmente "Figura – Texto" (sem numerador), tudo seguido de
# separador (hifen, en-dash, em-dash, dois-pontos, ponto ou espacos).
RE_PREFIXO_LEGENDA = re.compile(
    r'^\s*(Figura|Tabela|Equa[çc]ão|Quadro)\s*'
    r'(?:\d+(?:\.\d+)*|\?+|X+|x+)?\s*'
    r'[\-\u2013\u2014\.:]\s*',
    re.IGNORECASE,
)

# Regex para detectar labels embutidos: {{label:nome-do-elemento}}
RE_LABEL = re.compile(r'\{\{\s*label\s*:\s*([\w\-_\.]+)\s*\}\}')

# Regex para o sufixo `(N.M)` que adicionamos nas equacoes — usado
# para evitar duplicar ao reprocessar.
RE_SUFIXO_EQ = re.compile(
    r'\s*\(\s*\d+(?:\.\d+)*\s*\)\s*$'
)


def _eh_heading_paragrafo(p_element) -> Optional[int]:
    """Retorna o nivel (1..9) se o paragrafo for heading, senao None."""
    pPr = p_element.find(qn('w:pPr'))
    if pPr is None:
        return None
    pStyle = pPr.find(qn('w:pStyle'))
    if pStyle is None:
        return None
    val = pStyle.get(qn('w:val'), '')
    m = re.search(r'(\d)', val)
    if m and ('eading' in val or 'tulo' in val.lower() or val.isdigit()):
        n = int(m.group(1))
        if 1 <= n <= 9:
            return n
    return None


def _eh_paragrafo_de_caption(
    p_element, tipo: Optional[str] = None
) -> bool:
    """True se o paragrafo e uma legenda. Quando `tipo` e fornecido
    ('figura'|'tabela'|'equacao'|'fonte'), a verificacao e
    TIPO-ESPECIFICA: so retorna True se o prefixo casar com aquele
    tipo (ex: 'Figura 5.1...' nao casa para tipo='tabela').

    Isso evita que tabelas e figuras adjacentes "roubem" a legenda
    uma da outra durante o reindex.

    Quando `tipo` e None, mantem comportamento legado (qualquer
    legenda casa) — usado em deteccoes auxiliares.
    """
    pPr = p_element.find(qn('w:pPr'))
    estilo_caption = False
    if pPr is not None:
        pStyle = pPr.find(qn('w:pStyle'))
        if pStyle is not None:
            val = pStyle.get(qn('w:val'), '')
            if val in ESTILOS_CAPTION:
                estilo_caption = True

    texto = _texto_paragrafo(p_element)
    m = RE_PREFIXO_LEGENDA.match(texto)
    if not m and not estilo_caption:
        return False

    if tipo is None:
        return bool(m) or estilo_caption

    # Tipo-especifico: examinar o rotulo capturado pelo regex.
    if not m:
        # Tem estilo Caption mas sem prefixo reconhecivel — sem
        # informacao de tipo, assumimos que NAO casa (preserva
        # legenda generica para nao ser sobrescrita por tipo errado).
        return False
    rotulo_capturado = (m.group(1) or '').lower()
    aliases = {
        'figura': {'figura'},
        'tabela': {'tabela', 'quadro'},
        'equacao': {'equação', 'equacao'},
        'fonte': {'fonte'},
    }
    return rotulo_capturado in aliases.get(tipo, set())


def _contem_drawing_ou_pict(p_element) -> bool:
    if p_element.find(f'.//{qn("w:drawing")}') is not None:
        return True
    if p_element.find(f'.//{qn("w:pict")}') is not None:
        return True
    return False


def _contem_equacao(p_element) -> bool:
    if p_element.find(f'.//{{{M_NS}}}oMath') is not None:
        return True
    if p_element.find(f'.//{{{M_NS}}}oMathPara') is not None:
        return True
    return False


def _estilo_caption_disponivel(doc) -> Optional[str]:
    """Verifica se o documento ja tem o estilo Caption/Legenda."""
    try:
        styles_part = doc.styles.element
    except AttributeError:
        return None
    for style in styles_part.findall(qn('w:style')):
        style_id = style.get(qn('w:styleId'), '')
        if style_id in ESTILOS_CAPTION:
            return style_id
    return None


def _todos_estilos_paragrafo(doc) -> set:
    """Devolve set de styleId/styleName disponiveis no DOCX. Inclui tanto
    o `w:styleId` quanto o nome legivel `<w:name w:val=.../>`, pois a
    biblioteca canonica pode armazenar qualquer um.
    """
    nomes: set = set()
    try:
        styles_part = doc.styles.element
    except AttributeError:
        return nomes
    for style in styles_part.findall(qn('w:style')):
        sid = style.get(qn('w:styleId'))
        if sid:
            nomes.add(sid)
        name_el = style.find(qn('w:name'))
        if name_el is not None:
            nm = name_el.get(qn('w:val'))
            if nm:
                nomes.add(nm)
    return nomes


def _construir_paragrafo_legenda_canonica(
    *,
    rotulo: str,             # "Figura"
    indice_h1: str,          # "5" (texto plano — H1)
    sep_idx: str,            # "-" ou "."
    sep_leg: str,            # ": " ou " – "
    texto_descritivo: str,   # "Texto da legenda"
    label: Optional[str],    # label do autor (`{{label:x}}`) ou None
    estilo: Optional[str],   # "Caption" / "Normal"
    cache_seq: str,          # numero a aparecer antes do recalc do Word
    nome_bm: Optional[str],  # nome do bookmark (None = sem bookmark)
    id_gen,                  # GeradorIdsBookmark
):
    """Constroi um `<w:p>` de legenda usando ESTRUTURAS OOXML CANONICAS:

        <w:p>
          <w:pPr><w:pStyle w:val="Caption"/></w:pPr>
          <w:bookmarkStart w:id="X" w:name="_Ref_sra_fig_meu-grafico"/>
          <w:r><w:t xml:space="preserve">Figura </w:t></w:r>
          <w:r><w:t>5-</w:t></w:r>
          ...campo SEQ Figura...
          <w:r><w:t xml:space="preserve">: Texto da legenda</w:t></w:r>
          <w:bookmarkEnd w:id="X"/>
        </w:p>

    Garantias:
    - O campo SEQ tem nome IGUAL ao rotulo (`SEQ Figura`), permitindo
      que `TOC \\c "Figura"` capture esta legenda.
    - O bookmark envolve a legenda inteira, permitindo `REF` apontar
      para ela e o Word fazer hyperlink.
    - O texto descritivo e adicionado APOS o campo, com separador.
    """
    from app.services._ooxml_helpers import (
        criar_run_texto,
        criar_runs_campo_seq,
        criar_bookmark_par,
        aplicar_estilo_paragrafo,
    )

    w = f'{{{W_NS}}}'
    p = etree.Element(f'{w}p')
    aplicar_estilo_paragrafo(p, estilo)

    # bookmarkStart (apos pPr, antes dos runs)
    bms = bme = None
    if nome_bm:
        bms, bme = criar_bookmark_par(nome_bm, id_gen)
        p.append(bms)

    # Run "Rotulo "
    p.append(criar_run_texto(f'{rotulo} '))

    # Run "<H1><sep_idx>" — componente H1 e texto plano (resolvido no
    # nosso lado; o Word nao tem como recalcular sem STYLEREF, que
    # exige numeracao automatica de headings configurada no template).
    p.append(criar_run_texto(f'{indice_h1}{sep_idx}'))

    # Campo SEQ <Rotulo> \* ARABIC — numero recalculavel pelo Word
    for r_seq in criar_runs_campo_seq(rotulo, cache_seq):
        p.append(r_seq)

    # Texto descritivo (com separador e label preservados se houver)
    sufixo = sep_leg + (texto_descritivo or '[Sem legenda]')
    p.append(criar_run_texto(sufixo))

    # bookmarkEnd
    if bme is not None:
        p.append(bme)

    return p


def _reescrever_legenda_canonica(
    p_element,
    *,
    rotulo: str,
    indice_h1: str,
    sep_idx: str,
    sep_leg: str,
    cache_seq: str,
    nome_bm: Optional[str],
    estilo: Optional[str],
    id_gen,
) -> str:
    """Reescreve `p_element` (paragrafo de legenda existente) para a
    forma canonica OOXML, preservando:
    - O texto descritivo (apos o prefixo numerico atual).
    - O label declarado em `{{label:xyz}}` (sera removido do texto e
      retornado para o caller registrar no mapa).

    Apaga TUDO dentro do paragrafo (runs, bookmarks antigos, fields)
    e reconstroi com a estrutura canonica.

    Retorna o texto descritivo (sem prefixo numerico nem `{{label:..}}`)
    para que o caller possa extrair labels.
    """
    from app.services._ooxml_helpers import (
        criar_run_texto,
        criar_runs_campo_seq,
        criar_bookmark_par,
        aplicar_estilo_paragrafo,
    )

    w = f'{{{W_NS}}}'

    # 1. Capturar texto descritivo ANTES de apagar
    texto_completo = _texto_paragrafo(p_element)
    sem_prefixo = RE_PREFIXO_LEGENDA.sub('', texto_completo, count=1)
    # Remover declaracao `{{label:xyz}}` do texto descritivo (label
    # ja foi extraido em outro lugar pelo caller)
    sem_label = RE_LABEL.sub('', sem_prefixo).strip()
    if not sem_label:
        sem_label = '[Sem legenda]'

    # 2. Apagar TODO o conteudo do paragrafo (runs, bookmarks, fields)
    #    PRESERVANDO o pPr (estilo), pois ele sera ajustado pelo
    #    aplicar_estilo_paragrafo abaixo se necessario.
    for filho in list(p_element):
        if filho.tag != f'{w}pPr':
            p_element.remove(filho)

    # 3. Aplicar estilo correto
    aplicar_estilo_paragrafo(p_element, estilo)

    # 4. Inserir bookmarkStart (apos pPr)
    bms = bme = None
    if nome_bm:
        bms, bme = criar_bookmark_par(nome_bm, id_gen)
        p_element.append(bms)

    # 5. Run "Rotulo "
    p_element.append(criar_run_texto(f'{rotulo} '))

    # 6. Run "<H1><sep_idx>"
    p_element.append(criar_run_texto(f'{indice_h1}{sep_idx}'))

    # 7. Campo SEQ
    for r_seq in criar_runs_campo_seq(rotulo, cache_seq):
        p_element.append(r_seq)

    # 8. Texto descritivo
    p_element.append(criar_run_texto(sep_leg + sem_label))

    # 9. bookmarkEnd
    if bme is not None:
        p_element.append(bme)

    return sem_label


def _extrair_indice_capitulo(p_element) -> Optional[str]:
    """Extrai indice numerico (ex: '5', '5.1') do heading."""
    nivel = _eh_heading_paragrafo(p_element)
    if nivel is None:
        return None
    texto = _texto_paragrafo(p_element).strip()
    m = re.match(r'^(\d+(?:\.\d+)*)\b', texto)
    if m:
        return m.group(1)
    return None


def _extrair_label_da_legenda(texto_legenda: str) -> Optional[str]:
    """Procura `{{label:xyz}}` no texto da legenda. Retorna o nome do
    label (sem prefixo) ou None.
    """
    m = RE_LABEL.search(texto_legenda)
    if m:
        return m.group(1).strip()
    return None


def _anexar_numero_inline_equacao(p_element, numero_str: str) -> None:
    """Anexa ` (N.M)` ao final do paragrafo da equacao, alinhado a
    direita via tab. Remove sufixo previo se ja existir.

    Modificacoes:
    - Remove qualquer sufixo `(...)` numerico do final do ultimo run.
    - Adiciona um novo run com `\\t(N.M)` ao final do paragrafo.
    """
    w = f'{{{W_NS}}}'

    # Remover sufixo previo do ultimo run (idempotencia)
    todos_t = list(p_element.iter(qn('w:t')))
    if todos_t:
        ultimo_t = todos_t[-1]
        texto_atual = ultimo_t.text or ''
        ultimo_t.text = RE_SUFIXO_EQ.sub('', texto_atual)

    # Adicionar tab + (numero) como novo run
    r = etree.SubElement(p_element, f'{w}r')
    etree.SubElement(r, f'{w}tab')
    t = etree.SubElement(r, f'{w}t')
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    t.text = f'({numero_str})'


def reindexar_captions(caminho_master: str, perfil=None) -> dict:
    """Percorre o DOCX, numera elementos hierarquicamente, atualiza
    legendas e devolve mapa de labels para uso em cross-references.

    Quando `perfil` (instancia de `PerfilFormatacao`) e fornecido, usa
    seus parametros (estilos, separadores, posicoes) — extraidos da
    biblioteca canonica vinculada ao relatorio. Caso contrario, usa
    defaults compativeis com Word generico.

    Salva o resultado em `caminho_master`.

    Retorna:
        {'figuras': N, 'tabelas': N, 'equacoes': N,
         'capitulos_processados': N, 'mapa_labels': {...},
         'perfil_origem': str}

    O `mapa_labels` mapeia `'fig:nome'`/`'tab:nome'`/`'eq:nome'` para
    a string numerica (ex: '5.1.2'), incluindo tambem
    `'ref:nome'` que e uma referencia generica (mesmo numero).
    """
    # Lazy default — evita ciclo de import
    if perfil is None:
        from app.services.servico_perfil_formatacao import PerfilFormatacao
        perfil = PerfilFormatacao()

    # Helpers OOXML — gerador de IDs de bookmark + limpeza idempotente
    from app.services._ooxml_helpers import (
        GeradorIdsBookmark,
        remover_bookmarks_sra,
    )

    doc = Document(caminho_master)
    body = doc.element.body

    # Limpeza idempotente: remove bookmarks `_Ref_sra_*` antigos antes
    # de regerar (evita acumulo a cada execucao do reindex).
    remover_bookmarks_sra(body)

    id_gen = GeradorIdsBookmark(inicio=100000)

    # Resolver estilo de caption por TIPO via perfil. Verificamos
    # disponibilidade no DOCX em producao — se o estilo declarado no
    # perfil nao existe, caimos no fallback do estilo generico
    # (`Caption`/`Legenda` que ja exista) ou None.
    estilo_caption_fallback = _estilo_caption_disponivel(doc)
    estilos_disponiveis = _todos_estilos_paragrafo(doc)

    def resolver(estilo_desejado: str):
        if estilo_desejado in estilos_disponiveis:
            return estilo_desejado
        return estilo_caption_fallback

    estilo_por_tipo = {
        'figura': resolver(perfil.estilo_legenda_figura),
        'tabela': resolver(perfil.estilo_legenda_tabela),
        'equacao': resolver(perfil.estilo_legenda_equacao),
    }
    posicao_por_tipo = {
        'figura': perfil.posicao_legenda_figura,
        'tabela': perfil.posicao_legenda_tabela,
        # Equacao usa numeracao inline; posicao nao se aplica.
    }
    rotulo_por_tipo = {
        'figura': perfil.rotulo_figura,
        'tabela': perfil.rotulo_tabela,
        'equacao': perfil.rotulo_equacao,
    }
    sep_idx = perfil.separador_indice_seq
    sep_leg = perfil.separador_legenda

    # `indice_capitulo_atual` representa a hierarquia COMPLETA do
    # heading mais recente (qualquer nivel). Mantida para diagnostico
    # e para o set `capitulos_vistos`. NAO e usada na numeracao das
    # legendas — para isso usamos apenas `indice_h1_atual`.
    indice_capitulo_atual: str = '0'

    # `indice_h1_atual` e o componente fixo do indice das legendas:
    # SEMPRE corresponde ao capitulo de nivel 1 corrente. Headings de
    # nivel 2+ NAO alteram esse indice (vide regra de negocio).
    # `0` indica "antes do primeiro H1" (figuras/tabelas pre-textuais).
    indice_h1_atual: str = '0'

    contadores: dict = {}
    mapa_labels: dict = {}

    # Contador para gerar indices automaticos quando o heading nao tem
    # prefixo numerico (Word usa campos SEQ para numeracao automatica
    # — entao o texto fica "Coordenacao" em vez de "5 Coordenacao").
    # Mantemos uma stack [N1, N2, N3, ...] que cresce/encolhe conforme
    # o nivel dos headings vistos. Idx final = ".".join(stack).
    pilha_niveis: list = []

    figuras_total = tabelas_total = equacoes_total = 0
    capitulos_vistos: set = set()

    def computar_indice_auto(nivel: int) -> str:
        """Atualiza pilha_niveis para o `nivel` informado e devolve a
        string de indice resultante. Heading novo no mesmo nivel
        incrementa o contador desse nivel; subir em nivel reseta os
        niveis filhos.
        """
        # Cresce ate o nivel desejado
        while len(pilha_niveis) < nivel:
            pilha_niveis.append(0)
        # Encolhe se necessario
        while len(pilha_niveis) > nivel:
            pilha_niveis.pop()
        pilha_niveis[nivel - 1] += 1
        return '.'.join(str(n) for n in pilha_niveis)

    # `mapa_labels` agora armazena para cada chave um dict com:
    #   {'numero': '5.1', 'bookmark': '_Ref_sra_fig_meu-grafico'}
    # Mantemos compatibilidade com o formato antigo (string pura) via
    # legenda fallback no servico_cross_refs.

    def registrar_label(
        label: Optional[str],
        tipo: str,
        numero_str: str,
        nome_bm: Optional[str],
    ):
        """Adiciona o label ao mapa com numero + bookmark name.

        Sempre registra (mesmo sem label do autor) usando o nome de
        bookmark fallback como chave secundaria — assim cross-refs
        sem label declarado podem usar `{{fig:h5_n1}}` ou similar.
        """
        info = {'numero': numero_str, 'bookmark': nome_bm}
        if label:
            prefixo = LABEL_PREFIX[tipo]
            mapa_labels[f'{prefixo}:{label}'] = info
            # Alias generico — `{{ref:x}}` sem precisar saber o tipo.
            mapa_labels[f'ref:{label}'] = info

    i = 0
    while i < len(body):
        child = body[i]
        tag = child.tag

        if tag == f'{{{W_NS}}}p':
            # Atualizacao do indice de capitulo a cada heading.
            # Estrategia:
            # - Se o heading tem prefixo numerico explicito ("5.1 Foo"),
            #   usamos esse prefixo (autoritativo).
            # - Senao, geramos sequencialmente baseado no nivel via
            #   `computar_indice_auto` (Word numera via campo SEQ; o
            #   texto chega "limpo" aqui).
            nivel = _eh_heading_paragrafo(child)
            if nivel is not None:
                idx_explicito = _extrair_indice_capitulo(child)
                if idx_explicito is not None:
                    indice_capitulo_atual = idx_explicito
                    # Sincronizar a pilha com o indice explicito para
                    # que headings subsequentes sem prefixo continuem
                    # a sequencia correta.
                    partes = idx_explicito.split('.')
                    pilha_niveis[:] = [int(p) for p in partes]
                else:
                    indice_capitulo_atual = computar_indice_auto(nivel)
                capitulos_vistos.add(indice_capitulo_atual)

                # Regra de negocio: o indice das figuras/tabelas/equacoes
                # e SEMPRE composto por dois componentes — <H1>.<seq>.
                # Logo, atualizamos `indice_h1_atual` SOMENTE quando
                # encontramos heading de nivel 1. Quando isso acontece,
                # tambem zeramos os contadores do H1 anterior (na pratica,
                # um novo H1 inaugura um espaco de numeracao novo, entao
                # nao precisamos limpar — basta que as proximas insercoes
                # usem a nova chave `(indice_h1_atual, tipo)`).
                if nivel == 1:
                    if idx_explicito is not None:
                        # Pega so o primeiro componente do indice
                        # explicito (ex: '5.1' -> '5').
                        indice_h1_atual = idx_explicito.split('.')[0]
                    else:
                        # No modo automatico, pilha[0] e o contador de H1.
                        indice_h1_atual = str(pilha_niveis[0])
                i += 1
                continue

            em_regiao_textual = indice_h1_atual != '0'

            # Equacao inline
            if em_regiao_textual and _contem_equacao(child):
                contadores.setdefault(
                    (indice_h1_atual, 'equacao'), 0
                )
                contadores[(indice_h1_atual, 'equacao')] += 1
                num = contadores[(indice_h1_atual, 'equacao')]
                numero_str = f'{indice_h1_atual}{sep_idx}{num}'

                # Para equacoes: tentamos extrair label do paragrafo
                # adjacente (legenda) se houver. Verificacao tipo-
                # especifica para nao remover legenda de figura/tabela
                # que esteja por acaso adjacente a equacao.
                label = None
                proximo_idx = i + 1
                if proximo_idx < len(body):
                    prox = body[proximo_idx]
                    if (prox.tag == f'{{{W_NS}}}p'
                            and _eh_paragrafo_de_caption(
                                prox, tipo='equacao')):
                        label = _extrair_label_da_legenda(
                            _texto_paragrafo(prox)
                        )
                        # Remover a legenda — equacao usa numeracao
                        # inline, nao paragrafo separado
                        body.remove(prox)

                _anexar_numero_inline_equacao(child, numero_str)
                # Equacoes inline NAO tem bookmark associado (o numero
                # esta no fim do paragrafo da equacao, sem wrap em
                # bookmark — REF nao se aplica facilmente). Registramos
                # somente o numero.
                registrar_label(label, 'equacao', numero_str, None)
                equacoes_total += 1
                i += 1
                continue

            # Figura
            if em_regiao_textual and _contem_drawing_ou_pict(child):
                contadores.setdefault(
                    (indice_h1_atual, 'figura'), 0
                )
                contadores[(indice_h1_atual, 'figura')] += 1
                num = contadores[(indice_h1_atual, 'figura')]
                numero_str = f'{indice_h1_atual}{sep_idx}{num}'
                if posicao_por_tipo['figura'] == 'acima':
                    novo_i, label, nome_bm = (
                        _inserir_ou_atualizar_caption_antes(
                            body,
                            i,
                            'figura',
                            indice_h1=indice_h1_atual,
                            sep_idx=sep_idx,
                            sep_leg=sep_leg,
                            seq_num=num,
                            estilo_caption=estilo_por_tipo['figura'],
                            rotulo=rotulo_por_tipo['figura'],
                            id_gen=id_gen,
                        )
                    )
                    i = novo_i + 1
                else:
                    label, nome_bm = _inserir_ou_atualizar_caption_apos(
                        body,
                        i,
                        'figura',
                        indice_h1=indice_h1_atual,
                        sep_idx=sep_idx,
                        sep_leg=sep_leg,
                        seq_num=num,
                        estilo_caption=estilo_por_tipo['figura'],
                        rotulo=rotulo_por_tipo['figura'],
                        id_gen=id_gen,
                    )
                    i += 2
                registrar_label(
                    label, 'figura', numero_str, nome_bm
                )
                figuras_total += 1
                continue

        elif tag == f'{{{W_NS}}}tbl' and indice_h1_atual != '0':
            contadores.setdefault(
                (indice_h1_atual, 'tabela'), 0
            )
            contadores[(indice_h1_atual, 'tabela')] += 1
            num = contadores[(indice_h1_atual, 'tabela')]
            numero_str = f'{indice_h1_atual}{sep_idx}{num}'
            if posicao_por_tipo['tabela'] == 'acima':
                novo_i, label, nome_bm = (
                    _inserir_ou_atualizar_caption_antes(
                        body,
                        i,
                        'tabela',
                        indice_h1=indice_h1_atual,
                        sep_idx=sep_idx,
                        sep_leg=sep_leg,
                        seq_num=num,
                        estilo_caption=estilo_por_tipo['tabela'],
                        rotulo=rotulo_por_tipo['tabela'],
                        id_gen=id_gen,
                    )
                )
                i = novo_i
            else:
                label, nome_bm = _inserir_ou_atualizar_caption_apos(
                    body,
                    i,
                    'tabela',
                    indice_h1=indice_h1_atual,
                    sep_idx=sep_idx,
                    sep_leg=sep_leg,
                    seq_num=num,
                    estilo_caption=estilo_por_tipo['tabela'],
                    rotulo=rotulo_por_tipo['tabela'],
                    id_gen=id_gen,
                )
            registrar_label(label, 'tabela', numero_str, nome_bm)
            tabelas_total += 1
            i += 1
            continue

        i += 1

    doc.save(caminho_master)
    return {
        'figuras': figuras_total,
        'tabelas': tabelas_total,
        'equacoes': equacoes_total,
        'capitulos_processados': len(capitulos_vistos),
        'mapa_labels': mapa_labels,
        'perfil_origem': perfil.origem,
    }


_TIPO_PARA_PREFIXO_BM = {
    'figura': 'fig',
    'tabela': 'tab',
    'equacao': 'eq',
}


def _resolver_nome_bookmark(
    tipo: str, label: Optional[str], indice_h1: str, seq_num: int
) -> str:
    """Decide o nome do bookmark da legenda.

    - Se autor declarou label (`{{label:xyz}}`): preferir
      `_Ref_sra_<prefixo>_<label>` (estavel ao reordenar/reindexar).
    - Senao: fallback baseado no indice → `_Ref_sra_<prefixo>_h<H1>_n<seq>`.
      Cross-refs sem label declarado podem usar esse nome derivavel.
    """
    from app.services._ooxml_helpers import nome_bookmark
    prefixo = _TIPO_PARA_PREFIXO_BM[tipo]
    if label:
        return nome_bookmark(prefixo, label)
    return nome_bookmark(prefixo, f'h{indice_h1}_n{seq_num}')


def _inserir_ou_atualizar_caption_apos(
    body,
    indice_elemento: int,
    tipo: str,
    *,
    indice_h1: str,
    sep_idx: str,
    sep_leg: str,
    seq_num: int,
    estilo_caption: Optional[str],
    rotulo: str,
    id_gen,
) -> tuple:
    """Insere ou atualiza legenda OOXML-canonica APOS
    `body[indice_elemento]`. Retorna `(label, nome_bm)` para que o
    caller registre tanto o numero quanto o nome do bookmark no mapa.

    Estrutura gerada (campo SEQ + bookmark) garante:
    - Numero recalculavel pelo Word (campo SEQ)
    - Captura por `TOC \\c "<rotulo>"` (Lista de Figuras/Tabelas)
    - Alvo para `REF` em cross-references
    """
    cache_seq = str(seq_num)
    proximo_idx = indice_elemento + 1
    label = None
    if proximo_idx < len(body):
        proximo = body[proximo_idx]
        if (proximo.tag == f'{{{W_NS}}}p'
                and _eh_paragrafo_de_caption(proximo, tipo=tipo)):
            label = _extrair_label_da_legenda(_texto_paragrafo(proximo))
            nome_bm = _resolver_nome_bookmark(
                tipo, label, indice_h1, seq_num
            )
            _reescrever_legenda_canonica(
                proximo,
                rotulo=rotulo,
                indice_h1=indice_h1,
                sep_idx=sep_idx,
                sep_leg=sep_leg,
                cache_seq=cache_seq,
                nome_bm=nome_bm,
                estilo=estilo_caption,
                id_gen=id_gen,
            )
            return label, nome_bm

    nome_bm = _resolver_nome_bookmark(tipo, None, indice_h1, seq_num)
    novo_p = _construir_paragrafo_legenda_canonica(
        rotulo=rotulo,
        indice_h1=indice_h1,
        sep_idx=sep_idx,
        sep_leg=sep_leg,
        texto_descritivo='[Sem legenda]',
        label=None,
        estilo=estilo_caption,
        cache_seq=cache_seq,
        nome_bm=nome_bm,
        id_gen=id_gen,
    )
    body.insert(proximo_idx, novo_p)
    return None, nome_bm


def _inserir_ou_atualizar_caption_antes(
    body,
    indice_elemento: int,
    tipo: str,
    *,
    indice_h1: str,
    sep_idx: str,
    sep_leg: str,
    seq_num: int,
    estilo_caption: Optional[str],
    rotulo: str,
    id_gen,
) -> tuple:
    """Insere ou atualiza legenda OOXML-canonica ANTES de
    `body[indice_elemento]`. Retorna `(novo_indice, label, nome_bm)`.
    """
    cache_seq = str(seq_num)
    anterior_idx = indice_elemento - 1
    if anterior_idx >= 0:
        anterior = body[anterior_idx]
        if (anterior.tag == f'{{{W_NS}}}p'
                and _eh_paragrafo_de_caption(anterior, tipo=tipo)):
            label = _extrair_label_da_legenda(_texto_paragrafo(anterior))
            nome_bm = _resolver_nome_bookmark(
                tipo, label, indice_h1, seq_num
            )
            _reescrever_legenda_canonica(
                anterior,
                rotulo=rotulo,
                indice_h1=indice_h1,
                sep_idx=sep_idx,
                sep_leg=sep_leg,
                cache_seq=cache_seq,
                nome_bm=nome_bm,
                estilo=estilo_caption,
                id_gen=id_gen,
            )
            return indice_elemento, label, nome_bm

    nome_bm = _resolver_nome_bookmark(tipo, None, indice_h1, seq_num)
    novo_p = _construir_paragrafo_legenda_canonica(
        rotulo=rotulo,
        indice_h1=indice_h1,
        sep_idx=sep_idx,
        sep_leg=sep_leg,
        texto_descritivo='[Sem legenda]',
        label=None,
        estilo=estilo_caption,
        cache_seq=cache_seq,
        nome_bm=nome_bm,
        id_gen=id_gen,
    )
    body.insert(indice_elemento, novo_p)
    return indice_elemento + 1, None, nome_bm
