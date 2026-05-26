"""Serviço de mescla in-place de conteúdo do autor no DOCX em produção.

Fluxo principal (Fase 1 do plano):

1. `localizar_range_capitulo`: dado o DOCX em produção e um
   `CapituloDocumento`, identifica o intervalo [inicio, fim] (em
   índices relativos ao corpo do XML, NÃO a paragraphs[]) que
   corresponde ao capítulo (heading + conteúdo até antes do próximo
   heading de nível <= ao do capítulo).
2. `substituir_capitulo`: substitui o conteúdo do capítulo no DOCX
   de produção pelo conteúdo do DOCX do autor, preservando heading,
   estilos, seções e imagens (rIds remapeados).

Decisão arquitetural: a tabela `capitulos_documento` NÃO armazena
mais o conteúdo (`conteudo_docx` será removido em migração futura).
A fonte única de verdade do conteúdo é o `.docx` em produção em
`storage/relatorios_producao/<arquivo>.docx`.
"""
from __future__ import annotations

import re
import unicodedata
from io import BytesIO
from typing import Optional

from lxml import etree

from docx import Document
from docxcompose.composer import Composer

from app.services.servico_nivelador_erros import ServicoNiveladorErros


W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def _normalizar(texto: str) -> str:
    """Lowercase + sem acentos + colapsa espaços + tira numeração inicial."""
    if not texto:
        return ''
    s = unicodedata.normalize('NFD', texto)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'\s+', ' ', s).strip().lower()
    s = re.sub(r'^\s*(?:\d+(?:\.\d+)*|[ivx]+|[a-z])[\.\)]?\s+', '', s)
    return s


def _heading_nivel_de_estilo(style_name: str) -> Optional[int]:
    """Retorna nível 1..9 se o estilo for um heading, senão None.

    Aceita variações de styleId/styleName comuns:
    - Inglês: 'Heading 1', 'Heading1', 'heading 2', ...
    - Português: 'Título 1', 'Titulo 1', 'Ttulo1' (styleId Word
      sem acentos), 'Título1', ...
    - Title (estilo de título do documento) → nível 0.
    """
    if not style_name:
        return None
    # Normaliza: lowercase + sem acentos + sem espaços
    s = unicodedata.normalize('NFD', style_name)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.strip().lower().replace(' ', '')

    for prefixo in ('heading', 'titulo', 'ttulo'):
        if s.startswith(prefixo):
            sufixo = s[len(prefixo):].strip()
            if not sufixo:
                return 1
            try:
                return int(sufixo)
            except ValueError:
                return None
    if s in ('title',):
        return 0
    return None


def _eh_paragrafo_heading(p_element) -> Optional[int]:
    """Inspeciona o elemento <w:p> e retorna o nível do heading
    (1..9) se for um heading, senão None.

    Olha o `<w:pStyle w:val="Heading N"/>` dentro de `<w:pPr>`.
    """
    pPr = p_element.find(f'{{{W_NS}}}pPr')
    if pPr is None:
        return None
    pStyle = pPr.find(f'{{{W_NS}}}pStyle')
    if pStyle is None:
        return None
    val = pStyle.get(f'{{{W_NS}}}val', '')
    return _heading_nivel_de_estilo(val)


def _texto_paragrafo(p_element) -> str:
    """Extrai texto plano de um `<w:p>` (concatena todos os `<w:t>`)."""
    pedacos = []
    for t in p_element.iter(f'{{{W_NS}}}t'):
        if t.text:
            pedacos.append(t.text)
    return ''.join(pedacos).strip()


def _localizar_range_capitulo_interno(doc, capitulo) -> Optional[tuple[int, int]]:
    """Implementação interna de localizar_range_capitulo."""
    body = doc.element.body
    titulo_alvo = _normalizar(capitulo.titulo_capitulo)
    indice_alvo = (capitulo.indice_capitulo or '').strip()
    nivel_alvo = capitulo.nivel_capitulo or 1

    inicio = None
    for i, child in enumerate(body):
        if child.tag != f'{{{W_NS}}}p':
            continue
        nivel = _eh_paragrafo_heading(child)
        if nivel is None:
            continue
        texto = _texto_paragrafo(child)
        texto_norm = _normalizar(texto)

        casou_titulo = bool(titulo_alvo) and texto_norm == titulo_alvo
        casou_indice = (
            bool(indice_alvo)
            and texto.lstrip().startswith(indice_alvo)
        )
        if casou_titulo or casou_indice:
            inicio = i
            nivel_alvo_real = nivel  # confia no nível encontrado
            break
    # nivel_alvo (vindo do parâmetro) é apenas dica; o nível real
    # usado para delimitar o fim é o do heading encontrado.
    _ = nivel_alvo  # silenciar warning de variável não usada

    if inicio is None:
        return None

    # Fim: último elemento antes do próximo heading com nível <=
    fim = None
    for j in range(inicio + 1, len(body)):
        child = body[j]
        if child.tag == f'{{{W_NS}}}p':
            nivel_j = _eh_paragrafo_heading(child)
            if nivel_j is not None and nivel_j <= nivel_alvo_real:
                fim = j - 1
                break
        if child.tag == f'{{{W_NS}}}sectPr':
            fim = j - 1
            break

    if fim is None:
        # Foi até o fim sem encontrar próximo heading; fim é o último
        # elemento que NÃO é sectPr.
        ultimos = list(range(inicio + 1, len(body)))
        while ultimos and body[ultimos[-1]].tag == f'{{{W_NS}}}sectPr':
            ultimos.pop()
        fim = ultimos[-1] if ultimos else inicio

    return (inicio, fim)


def localizar_range_capitulo(doc, capitulo, relatorio_id=None, capitulo_id=None) -> Optional[tuple[int, int]]:
    """Localiza o range de elementos do corpo (`body`) que pertencem
    ao capítulo informado.

    Retorna `(inicio, fim)` como índices inclusivos em
    `doc.element.body[*]`, onde `inicio` é o parágrafo do heading
    e `fim` é o último elemento (parágrafo ou tabela) antes do
    próximo heading de nível <= `capitulo.nivel_capitulo`, ou o
    último elemento do corpo (excluindo `<w:sectPr>`).

    Retorna `None` se o capítulo não for localizado.

    Estratégia de casamento:
    - Normaliza `capitulo.titulo_capitulo` e compara com texto
      normalizado de cada parágrafo que tem estilo `Heading N`.
    - Quando o `indice_capitulo` está presente, tenta também
      casar pelo prefixo `"<indice> <titulo>"` no texto do
      parágrafo (caso o DOCX traga numeração explícita).
    - Pega o primeiro match (DOCX bem formatado não duplica
      headings de capítulo no mesmo nível).
    """
    resultado = ServicoNiveladorErros.executar_com_tratamento(
        _localizar_range_capitulo_interno,
        doc, capitulo,
        relatorio_id=relatorio_id,
        capitulo_id=capitulo_id,
        etapa='localizacao_capitulo'
    )
    
    # Se o resultado é um dict de erro, retorna None
    if isinstance(resultado, dict) and not resultado.get('sucesso', True):
        return None
    
    return resultado


def _listar_subheadings_no_range_interno(
    doc, inicio: int, fim: int, nivel_pai: int
) -> list[dict]:
    """Implementação interna de listar_subheadings_no_range."""
    body = doc.element.body
    encontrados = []
    # Saltar o próprio heading do capítulo pai (em body[inicio])
    for k in range(inicio + 1, min(fim + 1, len(body))):
        child = body[k]
        if child.tag != f'{{{W_NS}}}p':
            continue
        nivel = _eh_paragrafo_heading(child)
        if nivel is None or nivel <= nivel_pai:
            continue
        texto = _texto_paragrafo(child)
        if not texto:
            continue
        # Tentar extrair prefixo numérico do título (ex.: "5.4.6.1
        # Sistema" -> indice "5.4.6.1", título "Sistema").
        indice = None
        m = re.match(
            r'^\s*(\d+(?:\.\d+)*)\s*[\.\)\-–—:]?\s+(.+?)\s*$',
            texto,
        )
        if m:
            indice = m.group(1)
            titulo_limpo = m.group(2).strip()
        else:
            titulo_limpo = texto
        encontrados.append({
            'titulo': titulo_limpo,
            'indice': indice,
            'nivel': nivel,
            'indice_no_body': k,
        })
    return encontrados


def listar_subheadings_no_range(
    doc, inicio: int, fim: int, nivel_pai: int,
    relatorio_id: Optional[int] = None,
    capitulo_id: Optional[int] = None,
) -> list[dict]:
    """Varre o range [inicio..fim] do `body` (incluindo o heading do
    capítulo pai) e devolve uma lista de subheadings encontrados,
    em ordem de aparecimento.

    Cada item: {'titulo': str, 'nivel': int, 'indice_no_body': int}
    onde `nivel` é o do heading no DOCX (>= nivel_pai + 1) e
    `indice_no_body` é a posição do parágrafo dentro de `body`.

    Inclui subheadings de TODOS os níveis abaixo de `nivel_pai`
    (não só nivel_pai+1) — a hierarquia entre eles é resolvida na
    montagem da árvore (sincronizar_subcapitulos).
    """
    resultado = ServicoNiveladorErros.executar_com_tratamento(
        _listar_subheadings_no_range_interno,
        doc, inicio, fim, nivel_pai,
        relatorio_id=relatorio_id,
        capitulo_id=capitulo_id,
        etapa='listagem_subheadings'
    )
    
    # Se o resultado é um dict de erro, retorna lista vazia
    if isinstance(resultado, dict) and not resultado.get('sucesso', True):
        return []
    
    return resultado


def _sincronizar_subcapitulos_interno(
    db_session,
    capitulo_pai,
    caminho_docx: str,
) -> dict:
    """Implementação interna de sincronizar_subcapitulos."""
    from app.models.capitulo_documento import CapituloDocumento

    doc = Document(caminho_docx)
    rng = localizar_range_capitulo(doc, capitulo_pai)
    if rng is None:
        return {'inseridos': 0, 'atualizados': 0, 'desativados': 0,
                'erro': 'capitulo_pai não localizado no DOCX'}
    inicio, fim = rng

    nivel_pai = capitulo_pai.nivel_capitulo or 1
    detectados = listar_subheadings_no_range(doc, inicio, fim, nivel_pai)

    # Filhos atuais do capítulo pai no banco
    filhos_db = (
        CapituloDocumento.query
        .filter_by(
            id_relatorio=capitulo_pai.id_relatorio,
            id_capitulo_pai=capitulo_pai.id_capitulo_documento,
        )
        .all()
    )
    filhos_por_titulo = {
        _normalizar(f.titulo_capitulo): f for f in filhos_db
    }
    titulos_detectados = set()

    inseridos = atualizados = 0
    indice_pai = (capitulo_pai.indice_capitulo or '').strip()
    for ordem, item in enumerate(detectados, start=1):
        chave = _normalizar(item['titulo'])
        titulos_detectados.add(chave)
        if chave in filhos_por_titulo:
            f = filhos_por_titulo[chave]
            f.ordem_capitulo = ordem
            f.ativo = True
            atualizados += 1
        else:
            indice_filho = item.get('indice')
            if not indice_filho and indice_pai:
                indice_filho = f'{indice_pai}.{ordem}'
            elif not indice_filho:
                indice_filho = str(ordem)
            from app.utils.auditoria import usuario_atual_id  # noqa: C0415
            novo = CapituloDocumento(
                id_relatorio=capitulo_pai.id_relatorio,
                id_capitulo_pai=capitulo_pai.id_capitulo_documento,
                titulo_capitulo=item['titulo'],
                # `nome_capitulo` espelha o titulo na criacao automatica.
                nome_capitulo=item['titulo'],
                ordem_capitulo=ordem,
                nivel_capitulo=nivel_pai + 1,
                tipo_elemento=capitulo_pai.tipo_elemento or 'textual',
                indice_capitulo=indice_filho,
                status_capitulo='em_edicao',
                ativo=True,
                # Subcapitulo detectado a partir do upload do autor —
                # preenche com o usuario logado (autor) se houver
                # request context; senao fica como sistema.
                criado_por=usuario_atual_id(),
            )
            db_session.add(novo)
            inseridos += 1

    # Desativar filhos que sumiram do DOCX
    desativados = 0
    for chave, f in filhos_por_titulo.items():
        if chave not in titulos_detectados and f.ativo:
            f.ativo = False
            desativados += 1

    db_session.flush()
    return {
        'inseridos': inseridos,
        'atualizados': atualizados,
        'desativados': desativados,
    }


def sincronizar_subcapitulos(
    db_session,
    capitulo_pai,
    caminho_docx: str,
    relatorio_id: Optional[int] = None,
    capitulo_id: Optional[int] = None,
) -> dict:
    """Após um merge no DOCX em produção, sincroniza os subcapítulos
    no banco a partir dos subheadings detectados dentro do range do
    `capitulo_pai` no DOCX.

    Política:
    - Subheadings novos (não presentes no banco) → INSERT como filhos
      diretos de `capitulo_pai` (nivel = nivel_pai + 1, idependente do
      nivel real no heading — uma vez que o autor pode ter usado um
      Heading 4 onde devia ser Heading 3).
    - Subheadings existentes (mesmo título normalizado, mesmo pai) →
      atualizam ordem_capitulo para refletir nova ordem de aparecimento.
      Mantêm `id_usuario_responsavel`, `status_capitulo`, `id`, etc.
    - Subheadings que sumiram do DOCX → marcados ativo=False (não
      excluídos: preserva histórico e referências).

    Retorna dict com contadores: {'inseridos': N, 'atualizados': N,
    'desativados': N}.
    """
    resultado = ServicoNiveladorErros.executar_com_tratamento(
        _sincronizar_subcapitulos_interno,
        db_session, capitulo_pai, caminho_docx,
        relatorio_id=relatorio_id,
        capitulo_id=capitulo_id,
        etapa='sincronizacao_subcapitulos'
    )
    
    # Se o resultado é um dict de erro, retorna dict de erro
    if isinstance(resultado, dict) and not resultado.get('sucesso', True):
        return resultado
    
    return resultado


def _filhos_corpo_doc(doc) -> list:
    """Retorna lista dos elementos filhos diretos do `<w:body>`,
    excluindo `<w:sectPr>` final (configuração da seção)."""
    body = doc.element.body
    return [c for c in body if c.tag != f'{{{W_NS}}}sectPr']


def _extrair_capitulo_como_docx_interno(
    caminho_master: str,
    capitulo,
    *,
    incluir_heading: bool = True,
) -> Optional[bytes]:
    """Implementação interna de extrair_capitulo_como_docx."""
    doc = Document(caminho_master)
    rng = localizar_range_capitulo(doc, capitulo)
    if rng is None:
        return None
    inicio, fim = rng

    body = doc.element.body
    primeiro_manter = inicio if incluir_heading else inicio + 1
    ultimo_manter = fim  # inclusivo

    # Coletar referências a remover: tudo fora do range, exceto
    # sectPr (configuração da seção). Capturar ANTES para evitar
    # shift de índices durante o loop de remoção.
    a_remover = []
    for k, child in enumerate(list(body)):
        if child.tag == f'{{{W_NS}}}sectPr':
            continue
        if k < primeiro_manter or k > ultimo_manter:
            a_remover.append(child)
    for el in a_remover:
        body.remove(el)

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def extrair_capitulo_como_docx(
    caminho_master: str,
    capitulo,
    *,
    incluir_heading: bool = True,
    relatorio_id: Optional[int] = None,
    capitulo_id: Optional[int] = None,
) -> Optional[bytes]:
    """Extrai o range do `capitulo` do DOCX em `caminho_master` e
    retorna um DOCX autônomo (em bytes) contendo apenas aquele
    capítulo.

    Útil para o endpoint `/api/capitulos/<id>/conteudo` (usado pelo
    eigenpal modal e pelos editores legados) — substitui o antigo
    `cap.conteudo_docx` agora que o DOCX em produção é a fonte
    única.

    Estratégia minimalista: clona o master, identifica o range
    `[inicio..fim]`, remove TODO o resto do body (preservando
    `<w:sectPr>` para que o DOCX final continue válido) e salva
    em memória.

    Retorna `None` se o capítulo não for localizado.
    """
    resultado = ServicoNiveladorErros.executar_com_tratamento(
        _extrair_capitulo_como_docx_interno,
        caminho_master, capitulo,
        incluir_heading=incluir_heading,
        relatorio_id=relatorio_id,
        capitulo_id=capitulo_id,
        etapa='extracao_capitulo_docx'
    )
    
    # Se o resultado é um dict de erro, retorna None
    if isinstance(resultado, dict) and not resultado.get('sucesso', True):
        return None
    
    return resultado


def _substituir_texto_heading(p_element, novo_texto: str) -> None:
    """Substitui o texto visível de um `<w:p>` heading preservando
    pPr (estilo, numeração) e os bookmarks anchor de cross-refs.

    Estratégia:
    - Mantém o primeiro `<w:r>` (cópia das propriedades de run) e
      substitui o texto do primeiro `<w:t>` por `novo_texto`.
    - Remove os demais `<w:r>` (que carregavam o restante do título
      antigo) sem mexer em `<w:bookmarkStart/>` `<w:bookmarkEnd/>`
      `<w:pPr>` (filhos diretos do `<w:p>` que NÃO são `<w:r>`).
    - Se o heading não tinha nenhum `<w:r>`, cria um novo.
    """
    runs = p_element.findall(f'{{{W_NS}}}r')
    if runs:
        primeiro = runs[0]
        # Localiza o primeiro <w:t> dentro do primeiro run
        t_primeiro = primeiro.find(f'{{{W_NS}}}t')
        if t_primeiro is None:
            t_primeiro = etree.SubElement(primeiro, f'{{{W_NS}}}t')
        t_primeiro.text = novo_texto
        # Limpa demais <w:t> dentro do primeiro run para não duplicar
        for t in primeiro.findall(f'{{{W_NS}}}t')[1:]:
            primeiro.remove(t)
        # Remove os runs subsequentes (carregavam o resto do título)
        for r in runs[1:]:
            p_element.remove(r)
    else:
        novo_run = etree.SubElement(p_element, f'{{{W_NS}}}r')
        novo_t = etree.SubElement(novo_run, f'{{{W_NS}}}t')
        novo_t.text = novo_texto


def _atualizar_titulo_capitulo_interno(
    caminho_master: str,
    capitulo,
    novo_titulo: str,
) -> bool:
    """Implementação interna de atualizar_titulo_capitulo."""
    if not novo_titulo or not novo_titulo.strip():
        return False
    master = Document(caminho_master)
    rng = localizar_range_capitulo(master, capitulo)
    if rng is None:
        return False
    inicio, _ = rng
    body = master.element.body
    p_heading = body[inicio]
    if p_heading.tag != f'{{{W_NS}}}p':
        return False
    _substituir_texto_heading(p_heading, novo_titulo.strip())
    master.save(caminho_master)
    return True


def atualizar_titulo_capitulo(
    caminho_master: str,
    capitulo,
    novo_titulo: str,
    relatorio_id: Optional[int] = None,
    capitulo_id: Optional[int] = None,
) -> bool:
    """Atualiza apenas o texto do parágrafo de heading do capítulo
    no DOCX em produção, preservando estilo, numeração automática,
    bookmarks de cross-reference e demais marcadores.

    Retorna True se o heading foi localizado e atualizado.
    """
    resultado = ServicoNiveladorErros.executar_com_tratamento(
        _atualizar_titulo_capitulo_interno,
        caminho_master, capitulo, novo_titulo,
        relatorio_id=relatorio_id,
        capitulo_id=capitulo_id,
        etapa='atualizacao_titulo_capitulo'
    )
    
    # Se o resultado é um dict de erro, retorna False
    if isinstance(resultado, dict) and not resultado.get('sucesso', True):
        return False
    
    return resultado


def _substituir_capitulo_interno(
    caminho_master: str,
    capitulo,
    caminho_autor: str,
    *,
    preservar_heading: bool = True,
) -> bool:
    """Implementação interna de substituir_capitulo."""
    master = Document(caminho_master)
    autor = Document(caminho_autor)

    rng = localizar_range_capitulo(master, capitulo)
    if rng is None:
        return False
    inicio, fim = rng

    body = master.element.body
    # NOTA sobre lxml: `id(elemento)` NÃO é estável entre iterações
    # (cada acesso retorna um proxy Python novo). Por isso usamos
    # contagem de filhos (estável) para identificar os elementos
    # apendados pelo Composer.
    n_pre_append = len(body)

    composer = Composer(master)
    composer.append(autor)

    n_pos_append = len(body)
    # Os apendados ficam no FINAL do body, normalmente antes do
    # `<w:sectPr>` (que continua sendo o último elemento da seção
    # original) — docxcompose insere `body.insert(len(body)-1, …)`.
    # Por segurança, filtramos elementos sectPr da janela apendada.
    inicio_apendados = n_pre_append
    fim_apendados = n_pos_append  # exclusivo
    novos = []
    for k in range(inicio_apendados, fim_apendados):
        el = body[k]
        if el.tag == f'{{{W_NS}}}sectPr':
            continue
        novos.append(el)

    # Remover o range do capítulo. inicio/fim foram capturados ANTES
    # do append; como o append acrescenta SOMENTE no fim do body,
    # esses índices continuam válidos para os elementos originais.
    if preservar_heading:
        primeiro_remover = inicio + 1
    else:
        primeiro_remover = inicio
    fim_remover = fim + 1  # exclusivo

    # Coletar referências (lxml.Element) aos elementos a remover
    # ANTES de remover qualquer um — assim a iteração não shifta
    # índices durante o loop.
    a_remover = [body[k] for k in range(primeiro_remover, fim_remover)]
    for elem in a_remover:
        body.remove(elem)

    # Posição final de inserção (após remoção):
    pos_insercao = (inicio + 1) if preservar_heading else inicio

    # Mover os apendados (que estão no fim do body) para a posição
    # correta. Removemos do fim e re-inserimos preservando ordem.
    for elem in novos:
        body.remove(elem)
    for offset, elem in enumerate(novos):
        body.insert(pos_insercao + offset, elem)

    master.save(caminho_master)
    return True


def substituir_capitulo(
    caminho_master: str,
    capitulo,
    caminho_autor: str,
    *,
    preservar_heading: bool = True,
    relatorio_id: Optional[int] = None,
    capitulo_id: Optional[int] = None,
) -> bool:
    """Substitui o conteúdo do `capitulo` no DOCX em
    `caminho_master` pelo conteúdo do DOCX do autor em
    `caminho_autor`. Salva o resultado em `caminho_master`.

    Quando `preservar_heading=True` (padrão), o parágrafo de heading
    do capítulo no master é MANTIDO; só os elementos seguintes (até
    antes do próximo heading <= nível) são substituídos.

    Estratégia:
    1. `Composer(master).append(autor_doc)` → docxcompose copia
       todos os elementos do autor para o final do master,
       remapeando rIds de imagens, estilos numerados, etc. Isso
       é o que garante que figuras/numerações cheguem íntegras.
    2. Identificamos os elementos APENDADOS (novos) localizando
       a posição que era o último elemento antes do append.
    3. Removemos o range do capítulo (preservando heading conforme
       parâmetro).
    4. Movemos os elementos apendados para a posição correta.
    5. Salvamos.

    Retorna `True` em sucesso, `False` se o capítulo não for
    localizado no master.
    """
    resultado = ServicoNiveladorErros.executar_com_tratamento(
        _substituir_capitulo_interno,
        caminho_master, capitulo, caminho_autor,
        preservar_heading=preservar_heading,
        relatorio_id=relatorio_id,
        capitulo_id=capitulo_id,
        etapa='substituicao_capitulo'
    )
    
    # Se o resultado é um dict de erro, retorna False
    if isinstance(resultado, dict) and not resultado.get('sucesso', True):
        return False
    
    return resultado
