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
4. Gerar uma `PrevisualizacaoConteudo` por capítulo destino, com HTML
   básico para o autor revisar antes da confirmação.
5. Confirmação:
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

    cap_atual_norm = None
    coletando = False
    qtd = 0
    for para in doc_origem.paragraphs:
        estilo = para.style.name or ''
        texto = para.text.strip()
        nivel = _heading_nivel(estilo)
        if nivel is not None and texto:
            norm = _normalizar(texto)
            if norm in mapa:
                cap_atual_norm = norm
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

        Retorna o `EnvioConteudo` criado, já com prévias associadas.
        """
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
        )
        db.session.add(envio)
        db.session.flush()

        # Extração + classificação + prévia
        cls._gerar_previas(envio, id_capitulo_destino)

        db.session.commit()
        return envio

    @classmethod
    def _gerar_previas(cls, envio, id_capitulo_destino):
        """Lê o DOCX e gera PrevisualizacaoConteudo por capítulo destino."""
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

        - acao='importar': lê o DOCX e fragmenta em DOCX-por-capítulo,
          salvando em `CapituloDocumento.conteudo_docx`.
        - acao='rejeitar': marca como rejeitado e não altera capítulos.
        """
        if acao == 'rejeitar':
            envio.status_envio = 'rejeitado'
            db.session.commit()
            return {'ok': True, 'acao': 'rejeitado'}

        if acao != 'importar':
            return {'ok': False, 'erro': 'Ação inválida'}

        # Importar: gerar um DOCX por capítulo destino
        capitulos = CapituloDocumento.query.filter_by(
            id_relatorio=envio.id_relatorio,
            ativo=True,
        ).order_by(CapituloDocumento.ordem_capitulo).all()
        mapa = {}
        for cap in capitulos:
            chave = _normalizar(cap.titulo_capitulo)
            if chave:
                mapa.setdefault(chave, cap)

        try:
            doc = Document(envio.caminho_arquivo)
        except (OSError, ValueError) as e:
            return {'ok': False, 'erro': f'Erro ao ler DOCX: {e}'}

        # Estratégia simples e segura:
        # Para cada heading que casa com um capítulo, abrir um novo
        # documento e copiar parágrafos até o próximo heading casado.
        cap_atual = None
        docs_por_cap = {}

        def _novo_doc():
            return Document()

        for para in doc.paragraphs:
            estilo = para.style.name or ''
            texto = para.text.strip()
            nivel = _heading_nivel(estilo)
            if nivel is not None and texto:
                norm = _normalizar(texto)
                if norm in mapa:
                    cap_atual = mapa[norm]
                    if (cap_atual.id_capitulo_documento
                            not in docs_por_cap):
                        docs_por_cap[
                            cap_atual.id_capitulo_documento
                        ] = _novo_doc()
                    continue
            if cap_atual is None:
                continue
            cap_id = cap_atual.id_capitulo_documento
            destino = docs_por_cap.setdefault(cap_id, _novo_doc())
            novo_para = destino.add_paragraph()
            for run in para.runs:
                r = novo_para.add_run(run.text)
                if run.bold:
                    r.bold = True
                if run.italic:
                    r.italic = True
                if run.underline:
                    r.underline = True

        # Persistir bytes nos capítulos
        atualizados = 0
        for cap_id, d in docs_por_cap.items():
            buf = BytesIO()
            d.save(buf)
            cap = CapituloDocumento.query.get(cap_id)
            if cap:
                cap.conteudo_docx = buf.getvalue()
                cap.status_capitulo = 'em_edicao'
                atualizados += 1

        envio.status_envio = 'importado'
        db.session.commit()
        return {
            'ok': True,
            'acao': 'importado',
            'capitulos_atualizados': atualizados,
        }
