"""Serviço de envio, extração, classificação e confirmação de conteúdo do autor.

Pipeline:
1. Receber upload do DOCX do autor (rota chama `processar_upload`).
2. Extrair elementos (parágrafos, headings, tabelas, imagens inline).
3. Classificar elementos e tentar posicioná-los nos capítulos
   (`CapituloDocumento`) da versão de trabalho, casando por:
   - Heading 1..N: bate pelo título normalizado contra capítulos.
   - Parágrafos/tabelas entre dois headings: ficam no último heading casado.
   - Conteúdo solto (sem heading): vai para o capítulo destino indicado
     (ou o primeiro capítulo, como fallback).
4. Extrair sugestões do DOCX upado (títulos, figuras, tabelas com legendas).
5. Gerar uma `PrevisualizacaoConteudo` por capítulo destino, com HTML
   básico para o autor revisar antes da confirmação.
6. Confirmação:
   - 'importar' → persiste o DOCX por capítulo em `conteudo_docx` e marca
     o envio como 'importado'.
   - 'rejeitar' → descarta o envio (status 'rejeitado') sem alterar
     capítulos.
"""

import os
import re
import unicodedata
from io import BytesIO

from docx import Document

from app import db
from app.models.envio_conteudo import EnvioConteudo
from app.models.previsualizacao_conteudo import PrevisualizacaoConteudo
from app.models.capitulo_documento import CapituloDocumento


def _normalizar(texto):
    """Lowercase + sem acentos + colapsa espaços."""
    if not texto:
        return ''
    s = unicodedata.normalize('NFD', texto)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'\s+', ' ', s).strip().lower()
    # Remover numeração inicial: "1. Introdução" → "introdução"
    s = re.sub(r'^\s*(?:\d+(?:\.\d+)*|[ivx]+|[a-z])[\.\)]\s*', '', s)
    return s


def _heading_nivel(estilo):
    """Retorna nível do heading (1..9) ou None."""
    if not estilo:
        return None
    s = estilo.strip().lower()
    if s.startswith('heading'):
        try:
            return int(s.replace('heading', '').strip() or '1')
        except ValueError:
            return None
    if s in ('title', 'titulo', 'título'):
        return 0
    return None


def gerar_docx_segmento(envio, capitulo):
    """Gera em memória um DOCX correspondente apenas ao segmento do
    envio que foi classificado para o capítulo informado.

    Estratégia: percorre os parágrafos do DOCX original, identifica
    o capítulo ativo por casamento de Heading com `titulo_capitulo`
    e acumula os parágrafos entre o heading casado e o próximo
    heading casado.

    Retorna bytes (.docx) ou None se nada foi atribuído.
    """
    if not envio.caminho_arquivo or not os.path.exists(envio.caminho_arquivo):
        return None

    capitulos = CapituloDocumento.query.filter_by(
        id_relatorio=envio.id_relatorio,
        ativo=True,
    ).order_by(CapituloDocumento.ordem_capitulo).all()
    mapa = {}
    for cap in capitulos:
        chave = _normalizar(cap.titulo_capitulo)
        if chave:
            mapa.setdefault(chave, cap)

    alvo_norm = _normalizar(capitulo.titulo_capitulo)

    doc_origem = Document(envio.caminho_arquivo)
    novo = Document()

    coletando = False
    qtd = 0
    for para in doc_origem.paragraphs:
        estilo = para.style.name or ''
        texto = para.text.strip()
        nivel = _heading_nivel(estilo)
        if nivel is not None and texto:
            norm = _normalizar(texto)
            if norm in mapa:
                coletando = (norm == alvo_norm)
                continue
        if not coletando:
            continue
        # Copia o parágrafo (preserva runs básicos)
        novo_para = novo.add_paragraph()
        for run in para.runs:
            r = novo_para.add_run(run.text)
            if run.bold:
                r.bold = True
            if run.italic:
                r.italic = True
            if run.underline:
                r.underline = True
        qtd += 1

    if qtd == 0:
        # Se nada foi coletado pelo casamento de heading, devolve
        # placeholder mínimo (1 parágrafo) para o editor abrir
        novo.add_paragraph(
            f'(Sem conteúdo classificado para "{capitulo.titulo_capitulo}")'
        )

    buf = BytesIO()
    novo.save(buf)
    return buf.getvalue()


class ServicoEnvioAutor:
    """Orquestra upload, extração, classificação e confirmação de envios."""

    @staticmethod
    def diretorio_uploads(base_dir, id_relatorio):
        """Diretório onde os uploads são salvos: storage/uploads/{id}/."""
        return os.path.join(
            base_dir, 'storage', 'uploads', str(id_relatorio)
        )

    @classmethod
    def processar_upload(cls, *, id_relatorio, id_usuario,
                         arquivo_storage, base_dir,
                         id_capitulo_destino=None):
        """Persiste o arquivo e gera registros de envio + prévias.

        O `id_capitulo_destino` é OBRIGATÓRIO no novo fluxo: o
        autor sempre acessa o upload via uma URL específica de
        capítulo (`/capitulo/<id>/upload`), e todo o conteúdo do
        DOCX upado será mesclado naquele capítulo (preservando o
        heading e sobrescrevendo o conteúdo antigo) na confirmação.

        Retorna o `EnvioConteudo` criado, já com prévias associadas.
        """
        if not id_capitulo_destino:
            raise ValueError(
                'id_capitulo_destino é obrigatório no fluxo atual de '
                'envio do autor — o destino do conteúdo é fixado pela '
                'URL de upload.'
            )
        dir_destino = cls.diretorio_uploads(base_dir, id_relatorio)
        os.makedirs(dir_destino, exist_ok=True)

        from werkzeug.utils import secure_filename
        nome = secure_filename(arquivo_storage.filename or 'envio.docx')
        # Evitar colisão preservando histórico
        timestamp = __import__('datetime').datetime.now().strftime(
            '%Y%m%d%H%M%S'
        )
        nome_final = f'{timestamp}_{nome}'
        caminho_final = os.path.join(dir_destino, nome_final)
        arquivo_storage.save(caminho_final)

        envio = EnvioConteudo(
            id_relatorio=id_relatorio,
            id_usuario=id_usuario,
            nome_arquivo=nome,
            caminho_arquivo=caminho_final,
            status_envio='em_previa',
            id_capitulo_destino=id_capitulo_destino,
        )
        db.session.add(envio)
        db.session.flush()

        # Extração + classificação + prévia
        cls._gerar_previas(envio, id_capitulo_destino)

        db.session.commit()
        return envio

    @classmethod
    def _gerar_previas(cls, envio, id_capitulo_destino):
        """Lê o DOCX e gera PrevisualizacaoConteudo por capítulo destino.

        Extrai também a estrutura completa do DOCX:
        - Árvore hierárquica de capítulos e subcapítulos
        - Figuras com legendas organizadas por capítulo
        - Tabelas com legendas organizadas por capítulo
        """
        capitulos = CapituloDocumento.query.filter_by(
            id_relatorio=envio.id_relatorio,
            ativo=True,
        ).order_by(CapituloDocumento.ordem_capitulo).all()

        # Mapa de capítulos por título normalizado
        mapa = {}
        for cap in capitulos:
            chave = _normalizar(cap.titulo_capitulo)
            if chave:
                mapa.setdefault(chave, cap)

        try:
            doc = Document(envio.caminho_arquivo)
        except (OSError, ValueError) as e:
            prev = PrevisualizacaoConteudo(
                id_envio_conteudo=envio.id_envio_conteudo,
                tipo_previsualizacao='erro',
                resultado_html=(
                    f'<div class="ew__erro">Erro ao ler DOCX: {e}</div>'
                ),
            )
            db.session.add(prev)
            return

        # Extrair estrutura completa do DOCX usando ServicoExtracaoCanonica
        estrutura = cls._extrair_estrutura_completa(doc)

        # Armazenar estrutura no envio para uso na prévia
        import json  # noqa: C0415
        envio.sugestoes_json = json.dumps(estrutura)

        # Particionar conteúdo: header (antes do primeiro heading casado)
        # + listas de "segmentos" por capítulo destino.
        cap_atual = None
        if id_capitulo_destino:
            cap_atual = CapituloDocumento.query.get(id_capitulo_destino)

        segmentos_por_cap = {}
        # Se há destino fixo, todo conteúdo vai para ele.
        forcar_destino = cap_atual is not None and not mapa

        # Iterar parágrafos
        for para in doc.paragraphs:
            estilo = para.style.name or ''
            texto = para.text.strip()
            nivel = _heading_nivel(estilo)

            if nivel is not None and texto:
                norm = _normalizar(texto)
                if norm in mapa:
                    cap_atual = mapa[norm]
                    # Heading que casa com capítulo: marca início,
                    # não duplica o título no conteúdo do capítulo
                    continue
                # Heading que não casa — se já temos cap_atual, segue
                # incluindo o heading como subseção; caso contrário,
                # mantém como conteúdo solto.

            destino = cap_atual
            if destino is None and id_capitulo_destino:
                destino = CapituloDocumento.query.get(
                    id_capitulo_destino
                )
            if destino is None and capitulos:
                destino = capitulos[0]
            if destino is None:
                continue  # sem capítulos: nada a fazer

            chave = destino.id_capitulo_documento
            segmentos_por_cap.setdefault(chave, []).append({
                'tipo': 'paragrafo',
                'estilo': estilo,
                'nivel': nivel,
                'texto': texto,
            })

        # Tabelas vão integralmente para o capítulo ativo no momento
        # da leitura — como python-docx não preserva ordenação mista
        # entre paragraphs/tables sem iterar pelo body, fazemos a
        # aproximação: cada tabela do DOCX vai para o último cap_atual
        # (ou destino solicitado).
        cap_destino_tabelas = (
            cap_atual
            or (CapituloDocumento.query.get(id_capitulo_destino)
                if id_capitulo_destino else None)
            or (capitulos[0] if capitulos else None)
        )
        if cap_destino_tabelas is not None:
            for table in doc.tables:
                segmentos_por_cap.setdefault(
                    cap_destino_tabelas.id_capitulo_documento, []
                ).append({
                    'tipo': 'tabela',
                    'linhas': [
                        [c.text for c in row.cells]
                        for row in table.rows
                    ],
                })

        if forcar_destino:
            # Compatibilidade: já feito acima através de cap_atual.
            pass

        # Gerar prévia HTML por capítulo destino
        for id_cap, segmentos in segmentos_por_cap.items():
            cap = CapituloDocumento.query.get(id_cap)
            html_parts = [
                f'<section class="ew__previa-cap" data-cap="{id_cap}">',
                (
                    f'<h2>{cap.indice_capitulo or ""} '
                    f'{cap.titulo_capitulo}</h2>'
                ),
            ]
            for seg in segmentos:
                if seg['tipo'] == 'paragrafo':
                    nivel = seg['nivel']
                    texto_html = (
                        seg['texto']
                        .replace('&', '&amp;')
                        .replace('<', '&lt;')
                        .replace('>', '&gt;')
                    )
                    if nivel and nivel >= 1:
                        tag = f'h{min(max(nivel + 1, 2), 6)}'
                        html_parts.append(
                            f'<{tag}>{texto_html}</{tag}>'
                        )
                    else:
                        html_parts.append(f'<p>{texto_html}</p>')
                elif seg['tipo'] == 'tabela':
                    html_parts.append('<table class="ew__previa-tbl">')
                    for linha in seg['linhas']:
                        html_parts.append('<tr>')
                        for celula in linha:
                            celula_html = (
                                celula
                                .replace('&', '&amp;')
                                .replace('<', '&lt;')
                                .replace('>', '&gt;')
                            )
                            html_parts.append(f'<td>{celula_html}</td>')
                        html_parts.append('</tr>')
                    html_parts.append('</table>')
            html_parts.append('</section>')

            prev = PrevisualizacaoConteudo(
                id_envio_conteudo=envio.id_envio_conteudo,
                tipo_previsualizacao='parcial',
                resultado_html='\n'.join(html_parts),
                caminho_saida=str(id_cap),
            )
            db.session.add(prev)

        # Caso nada tenha sido classificado, registrar uma prévia geral
        if not segmentos_por_cap:
            prev = PrevisualizacaoConteudo(
                id_envio_conteudo=envio.id_envio_conteudo,
                tipo_previsualizacao='vazio',
                resultado_html=(
                    '<div class="ew__erro">Nenhum conteúdo identificável '
                    'foi extraído do DOCX (verifique se há texto e '
                    'cabeçalhos compatíveis com a estrutura do relatório).'
                    '</div>'
                ),
            )
            db.session.add(prev)

    @classmethod
    def confirmar(cls, *, envio, acao):
        """Aplica a decisão do autor sobre o envio.

        - acao='importar': mescla o DOCX do autor IN-PLACE no DOCX
          em produção (caminho_template do relatório), substituindo
          o conteúdo do capítulo destino preservando o heading.
        - acao='rejeitar': marca como rejeitado e não altera DOCX.

        Implementação: delega para `servico_merge_docx.substituir_capitulo`,
        que usa docxcompose para preservar imagens, estilos e numeração.
        """
        if acao == 'rejeitar':
            envio.status_envio = 'rejeitado'
            db.session.commit()
            return {'ok': True, 'acao': 'rejeitado'}

        if acao != 'importar':
            return {'ok': False, 'erro': 'Ação inválida'}

        if not envio.id_capitulo_destino:
            return {
                'ok': False,
                'erro': (
                    'Envio sem capítulo destino — não é possível '
                    'identificar onde mesclar o conteúdo.'
                ),
            }

        cap_destino = CapituloDocumento.query.get(
            envio.id_capitulo_destino
        )
        if not cap_destino:
            return {'ok': False, 'erro': 'Capítulo destino não encontrado.'}

        from app.models.relatorio_producao import RelatorioProducao
        from app.services.servico_merge_docx import (
            substituir_capitulo,
            sincronizar_subcapitulos,
        )

        rel = RelatorioProducao.query.get(envio.id_relatorio)
        # Gate de bloqueio: relatório finalizado não aceita merge.
        from app.services.servico_relatorio import ServicoRelatorio
        if ServicoRelatorio.esta_bloqueado(rel):
            return {
                'ok': False,
                'erro': (
                    'Relatório finalizado/bloqueado — não é possível '
                    'mesclar novos conteúdos. Crie uma nova versão para '
                    'continuar a edição.'
                ),
            }
        if not rel or not rel.caminho_template:
            return {
                'ok': False,
                'erro': (
                    'Relatório de produção sem DOCX em '
                    'caminho_template — não é possível mesclar.'
                ),
            }

        if not os.path.exists(rel.caminho_template):
            return {
                'ok': False,
                'erro': (
                    f'DOCX de produção não encontrado em '
                    f'{rel.caminho_template}'
                ),
            }

        try:
            ok = substituir_capitulo(
                caminho_master=rel.caminho_template,
                capitulo=cap_destino,
                caminho_autor=envio.caminho_arquivo,
                preservar_heading=True,
            )
        except (OSError, ValueError, RuntimeError) as e:
            return {
                'ok': False,
                'erro': f'Falha ao mesclar no DOCX em produção: {e}',
            }

        if not ok:
            return {
                'ok': False,
                'erro': (
                    f'Capítulo "{cap_destino.titulo_capitulo}" não foi '
                    f'localizado no DOCX em produção. Verifique se o '
                    f'heading correspondente existe no arquivo.'
                ),
            }

        cap_destino.status_capitulo = 'em_edicao'
        envio.status_envio = 'importado'

        # Sincronizar subcapítulos no banco a partir dos subheadings
        # que o autor enviou no DOCX. Isso garante que a árvore na UI
        # reflita a estrutura recém-mesclada (cada Heading 2/3/4 do
        # upload vira CapituloDocumento filho de cap_destino).
        try:
            sync = sincronizar_subcapitulos(
                db.session, cap_destino, rel.caminho_template
            )
        except (OSError, ValueError, RuntimeError) as e:
            # Merge já foi escrito em disco — falha de sincronização
            # não deve reverter o conteúdo. Logamos e seguimos.
            sync = {'erro': str(e)}

        # Fase 2 — Captioning + cross-references:
        # 1) reindexar_captions: numera figuras/tabelas/equações
        #    hierarquicamente e devolve mapa_labels.
        # 2) substituir_referencias: troca {{fig:x}}, {{tab:x}},
        #    {{eq:x}}, {{ref:x}} no corpo pelos números.
        captions = {}
        cross_refs = {}
        try:
            from app.services.servico_captioning import reindexar_captions
            from app.services.servico_cross_refs import substituir_referencias
            from app.services.servico_perfil_formatacao import (
                PerfilFormatacao,
            )
            perfil = PerfilFormatacao.de_relatorio(rel)
            captions = reindexar_captions(
                rel.caminho_template, perfil=perfil
            )
            mapa = captions.get('mapa_labels', {}) if isinstance(
                captions, dict
            ) else {}
            cross_refs = substituir_referencias(
                rel.caminho_template, mapa
            )
        except (OSError, ValueError, RuntimeError) as e:
            captions = captions or {'erro': str(e)}
            cross_refs = {'erro': str(e)}

        db.session.commit()
        return {
            'ok': True,
            'acao': 'importado',
            'capitulos_atualizados': 1,
            'capitulo_destino_id': cap_destino.id_capitulo_documento,
            'subcapitulos_sync': sync,
            'captions': captions,
            'cross_refs': cross_refs,
        }

    @classmethod
    def _extrair_estrutura_completa(cls, doc):
        """Extrai estrutura completa do DOCX usando ServicoExtracaoCanonica.

        Retorna dict com:
        - capitulos: árvore hierárquica de capítulos e subcapítulos
        - legendas: figuras e tabelas com legendas
        """
        from app.services.servico_extracao_canonica import (  # noqa: C0415
            ServicoExtracaoCanonica,
        )

        # Extrair árvore de capítulos
        capitulos_arvore = ServicoExtracaoCanonica._extrair_capitulos(  # noqa: SLF001, E501
            doc
        )

        # Se não encontrou capítulos via Heading, tentar detecção por padrão
        if not capitulos_arvore:
            capitulos_arvore = cls._extrair_capitulos_por_padrao(doc)

        # Extrair legendas (figuras e tabelas)
        legendas = ServicoExtracaoCanonica._extrair_legendas(doc)  # noqa: SLF001, E501

        # Organizar figuras e tabelas por capítulo
        estrutura = {
            'capitulos': capitulos_arvore,
            'legendas': legendas,
        }

        return estrutura

    @staticmethod
    def _extrair_capitulos_por_padrao(doc):
        """Extrai capítulos baseados em padrões de numeração hierárquica.

        Detecta títulos que começam com numeração como "1.", "1.1", "1.1.1"
        mesmo sem estilo Heading.
        """
        import re  # noqa: C0415

        # Padrão para numeração hierárquica: 1, 1.1, 1.1.1, etc.
        padrao_numeracao = re.compile(r'^\s*(\d+(?:\.\d+)*)\s+(.+)')

        capitulos = []
        for para in doc.paragraphs:
            texto = para.text.strip()
            if not texto:
                continue

            match = padrao_numeracao.match(texto)
            if match:
                indice = match.group(1)
                titulo = match.group(2)
                nivel = indice.count('.') + 1

                capitulos.append({
                    'titulo': titulo,
                    'indice': indice,
                    'nivel': nivel,
                    'estilo': para.style.name or 'Normal',
                    'tipo_elemento': 'textual',
                    'filhos': [],
                })

        # Montar árvore hierárquica
        raiz = []
        pilha = []

        for item in capitulos:
            nv = item['nivel']
            while pilha and pilha[-1][0] >= nv:
                pilha.pop()

            destino = pilha[-1][1]['filhos'] if pilha else raiz
            destino.append(item)
            pilha.append((nv, item))

        return raiz

    @staticmethod
    def _extrair_sugestoes(doc):
        """Extrai sugestões do DOCX upado de forma inteligente.

        Detecta padrões que sugerem títulos, figuras e tabelas,
        mesmo que não estejam formatados perfeitamente.

        Retorna dict com:
        - titulos: lista de headings encontrados (texto, nivel, confianca)
        - figuras: lista de figuras com/sem legendas
        - tabelas: lista de tabelas com/sem legendas
        """
        sugestoes = {
            'titulos': [],
            'figuras': [],
            'tabelas': [],
        }

        # Padrões para detecção inteligente de títulos
        padrao_numeracao = re.compile(  # noqa: E501
            r'^\s*(\d+(?:\.\d+)*|[ivx]+|[a-z])[\.\)]\s+',
            re.IGNORECASE
        )
        padrao_caixa_alta = re.compile(r'^[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ\s]{5,}$')

        # Extrair títulos (headings + padrões inteligentes)
        for para in doc.paragraphs:
            estilo = para.style.name or ''
            texto = para.text.strip()
            if not texto:
                continue

            nivel = _heading_nivel(estilo)
            confianca = 'alta'

            # Detecção por estilo Heading
            if nivel is not None:
                sugestoes['titulos'].append({
                    'texto': texto,
                    'nivel': nivel,
                    'estilo': estilo,
                    'confianca': confianca,
                })
                continue

            # Detecção por padrões de formatação
            # 1. Numeração no início (1., 1.1, 2., etc.)
            if padrao_numeracao.match(texto):
                # Inferir nível pela profundidade da numeração
                partes = texto.split('.')[0].split()
                if partes:
                    try:
                        nivel_inferido = len(partes[0].split('.'))
                    except Exception:  # noqa: E722
                        nivel_inferido = 1
                else:
                    nivel_inferido = 1
                sugestoes['titulos'].append({
                    'texto': texto,
                    'nivel': nivel_inferido,
                    'estilo': estilo,
                    'confianca': 'media',
                })
                continue

            # 2. Texto em caixa alta (sugere título)
            if padrao_caixa_alta.match(texto) and len(texto) < 100:
                sugestoes['titulos'].append({
                    'texto': texto,
                    'nivel': 1,
                    'estilo': estilo,
                    'confianca': 'baixa',
                })
                continue

            # 3. Texto em negrito e tamanho maior que o normal
            if para.runs:
                tem_negrito = any(run.bold for run in para.runs if run.bold)
                if tem_negrito and len(texto) < 80:
                    sugestoes['titulos'].append({
                        'texto': texto,
                        'nivel': 1,
                        'estilo': estilo,
                        'confianca': 'baixa',
                    })

        # Extrair figuras (imagens inline e flutuantes)
        # python-docx não detecta facilmente imagens flutuantes,
        # então focamos em imagens inline em parágrafos
        for para in doc.paragraphs:
            if para._element.xpath('.//pic:pic'):
                # Parágrafo contém imagem
                texto_legenda = para.text.strip()
                if texto_legenda:
                    sugestoes['figuras'].append({
                        'legenda': texto_legenda,
                        'tipo': 'inline',
                        'tem_legenda': True,
                    })
                else:
                    # Imagem sem legenda - sugerir adicionar
                    sugestoes['figuras'].append({  # noqa: E501
                        'legenda': None,
                        'tipo': 'inline',
                        'tem_legenda': False,
                        'sugestao': (
                            'Adicione uma legenda descritiva '
                            'para esta figura.'
                        ),
                    })
            else:
                # Detectar parágrafos que mencionam figuras
                texto_lower = para.text.lower()
                if any(palavra in texto_lower for palavra in [  # noqa: E501
                    'figura', 'fig.', 'imagem', 'img.'
                ]):
                    sugestoes['figuras'].append({
                        'legenda': para.text.strip(),
                        'tipo': 'referencia_texto',
                        'tem_legenda': True,
                    })

        # Extrair tabelas e suas legendas
        for i, table in enumerate(doc.tables):
            # Tenta encontrar legenda no parágrafo anterior à tabela
            # ou no primeiro parágrafo após a tabela
            legenda = None
            # Busca parágrafo anterior
            for para in doc.paragraphs:
                if table._element in para._element.xpath(  # noqa: E501
                    'following-sibling::w:p'
                ):
                    if para.text.strip():
                        legenda = para.text.strip()
                        break
            if not legenda:
                # Busca parágrafo seguinte
                for para in doc.paragraphs:
                    if table._element in para._element.xpath(  # noqa: E501
                        'preceding-sibling::w:p'
                    ):
                        if para.text.strip():
                            legenda = para.text.strip()
                            break

            tabela_info = {
                'indice': i + 1,
                'linhas': len(table.rows),
                'colunas': len(table.columns) if table.rows else 0,
                'legenda': legenda,
                'tem_legenda': legenda is not None,
            }

            if not legenda:
                tabela_info['sugestao'] = (  # noqa: E501
                    'Adicione uma legenda descritiva '
                    'para esta tabela.'
                )

            sugestoes['tabelas'].append(tabela_info)

        # Detectar referências a tabelas no texto
        for para in doc.paragraphs:
            texto_lower = para.text.lower()
            if any(palavra in texto_lower for palavra in [  # noqa: E501
                'tabela', 'tab.', 'quadro'
            ]):
                # Verificar se não é uma tabela já detectada
                if not any(  # noqa: E501
                    t.get('legenda') == para.text.strip()
                    for t in sugestoes['tabelas']
                ):
                    sugestoes['tabelas'].append({
                        'indice': len(sugestoes['tabelas']) + 1,
                        'linhas': 0,
                        'colunas': 0,
                        'legenda': para.text.strip(),
                        'tem_legenda': True,
                        'tipo': 'referencia_texto',
                    })

        return sugestoes
