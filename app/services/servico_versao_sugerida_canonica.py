"""Geração da versão DOCX sugerida a partir da biblioteca canônica."""

import json
import os
import re
import shutil

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Mm, Pt, RGBColor

from app.services.servico_captioning import reindexar_captions
from app.services.servico_sanitizar_docx import sanitizar_docx


VERSAO_DOCX_SUGERIDO = 'analise_upload_v2'


class ServicoVersaoSugeridaCanonica:
    """Aplica métricas canônicas completas ao DOCX enviado pelo autor."""

    METRICAS_OBRIGATORIAS = {
        'sanitizacao_compatibilidade_editor',
        'aplicacao_estilos_heading_do_perfil',
        'normalizacao_visual_de_paragrafos',
        'aplicacao_metricas_canonicas_reais',
        'numeracao_hierarquica_subcapitulos',
        'reindexacao_captions_quando_possivel',
    }

    @classmethod
    def gerar(cls, *, envio, relatorio, perfil, caminho_saida):
        """Gera e salva o DOCX sugerido apenas se todas as métricas passarem."""
        os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
        caminho_temp = f'{caminho_saida}.tmp'
        metricas_aplicadas = []

        bytes_sanitizados = sanitizar_docx(envio.caminho_arquivo)
        if bytes_sanitizados is None:
            shutil.copy2(envio.caminho_arquivo, caminho_temp)
        else:
            with open(caminho_temp, 'wb') as arquivo:
                arquivo.write(bytes_sanitizados)
        metricas_aplicadas.append('sanitizacao_compatibilidade_editor')

        metricas = cls.carregar_biblioteca_canonica(relatorio)
        try:
            cls.aplicar_biblioteca_canonica(caminho_temp, perfil, metricas)
            metricas_aplicadas.extend([
                'aplicacao_estilos_heading_do_perfil',
                'normalizacao_visual_de_paragrafos',
                'aplicacao_metricas_canonicas_reais',
                'numeracao_hierarquica_subcapitulos',
            ])
            reindexar_captions(caminho_temp, perfil=perfil)
            metricas_aplicadas.append('reindexacao_captions_quando_possivel')
            cls.validar_docx_sugerido(caminho_temp, metricas_aplicadas)
        except Exception:
            if os.path.exists(caminho_temp):
                os.remove(caminho_temp)
            raise

        os.replace(caminho_temp, caminho_saida)
        return metricas_aplicadas, metricas

    @classmethod
    def carregar_biblioteca_canonica(cls, relatorio):
        """Carrega formatação, capítulos e macroestrutura da base canônica."""
        caminho_dir = cls._resolver_diretorio_canonico(relatorio)
        if not caminho_dir:
            return {}
        return {
            'diretorio': caminho_dir,
            'formatacao': cls._ler_json(caminho_dir, 'canonico_formatacao.json'),
            'capitulos': cls._ler_json(caminho_dir, 'canonico_capitulos.json'),
            'macro': cls._ler_json(caminho_dir, 'canonico_estrutura_macro.json'),
            'docx_base': cls._localizar_docx_base(caminho_dir),
        }

    @staticmethod
    def _resolver_diretorio_canonico(relatorio):
        biblioteca = getattr(relatorio, 'biblioteca', None) if relatorio else None
        caminho = getattr(biblioteca, 'caminho_arquivo', None)
        if caminho and os.path.isdir(caminho):
            return caminho
        if relatorio is None:
            return None
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        )
        candidatos = [
            relatorio.codigo_d20,
            (relatorio.codigo_d20 or '').replace('-', ''),
        ]
        for nome in candidatos:
            if not nome:
                continue
            caminho = os.path.join(base_dir, 'storage', 'canonicos', nome)
            if os.path.isdir(caminho):
                return caminho
        return None

    @staticmethod
    def _ler_json(caminho_dir, nome_arquivo):
        caminho = os.path.join(caminho_dir, nome_arquivo)
        if not os.path.exists(caminho):
            return None
        with open(caminho, encoding='utf-8') as arquivo:
            return json.load(arquivo)

    @staticmethod
    def _localizar_docx_base(caminho_dir):
        for nome in os.listdir(caminho_dir):
            if nome.lower().endswith('.docx'):
                return os.path.join(caminho_dir, nome)
        return None

    @classmethod
    def aplicar_biblioteca_canonica(cls, caminho_docx, perfil, metricas):
        """Classifica elementos e aplica métricas visuais canônicas."""
        doc = Document(caminho_docx)
        estilos = cls._mapear_estilos_canonicos(metricas)
        cls._aplicar_secoes_canonicas(doc, metricas)
        cls._aplicar_estilos_base(doc, estilos)
        cls._classificar_e_formatar_blocos(doc, perfil, estilos)
        doc.save(caminho_docx)

    @staticmethod
    def _mapear_estilos_canonicos(metricas):
        formatacao = metricas.get('formatacao') or {}
        return {
            (estilo.get('nome') or '').lower(): estilo
            for estilo in formatacao.get('estilos_paragrafo') or []
            if estilo.get('nome')
        }

    @staticmethod
    def _aplicar_secoes_canonicas(doc, metricas):
        formatacao = metricas.get('formatacao') or {}
        secoes = formatacao.get('secoes') or []
        secao_canonica = (
            secoes[min(1, len(secoes) - 1)]
            if secoes
            else {
                'margem_top_mm': 25,
                'margem_right_mm': 20,
                'margem_bottom_mm': 25,
                'margem_left_mm': 20,
            }
        )
        for secao in doc.sections:
            secao.top_margin = Mm(secao_canonica.get('margem_top_mm') or 25)
            secao.right_margin = Mm(secao_canonica.get('margem_right_mm') or 20)
            secao.bottom_margin = Mm(secao_canonica.get('margem_bottom_mm') or 25)
            secao.left_margin = Mm(secao_canonica.get('margem_left_mm') or 20)

    @classmethod
    def _aplicar_estilos_base(cls, doc, estilos):
        if 'Normal' in doc.styles:
            spec = cls._spec_texto(estilos)
            cls._aplicar_spec_fonte(doc.styles['Normal'].font, spec)
        for nivel in range(1, 10):
            nome = f'Heading {nivel}'
            if nome not in doc.styles:
                continue
            spec = cls._spec_heading(estilos, nivel)
            cls._aplicar_spec_fonte(doc.styles[nome].font, spec)

    @classmethod
    def _classificar_e_formatar_blocos(cls, doc, perfil, estilos):
        contadores = []
        for paragrafo in doc.paragraphs:
            nivel = cls._heading_nivel(paragrafo.style.name or '')
            if nivel:
                cls._formatar_heading(paragrafo, nivel, perfil, estilos, contadores)
            elif cls._parece_legenda(paragrafo.text):
                cls._aplicar_spec_paragrafo(paragrafo, cls._spec_legenda(estilos))
            elif paragrafo.text.strip():
                cls._aplicar_spec_paragrafo(paragrafo, cls._spec_texto(estilos))

    @staticmethod
    def _heading_nivel(estilo):
        match = re.match(r'heading\s*(\d+)', (estilo or '').strip().lower())
        return int(match.group(1)) if match else None

    @staticmethod
    def _parece_legenda(texto):
        return bool(re.match(r'^\s*(figura|tabela|quadro|equação)\b', texto or '', re.I))

    @classmethod
    def _formatar_heading(cls, paragrafo, nivel, perfil, estilos, contadores):
        nomes = getattr(perfil, 'nome_heading_por_nivel', []) or []
        estilo_destino = nomes[nivel] if nivel < len(nomes) else None
        if estilo_destino:
            try:
                paragrafo.style = estilo_destino
            except (KeyError, ValueError):
                pass
        cls._prefixar_heading(paragrafo, nivel, contadores)
        cls._aplicar_spec_paragrafo(paragrafo, cls._spec_heading(estilos, nivel))

    @staticmethod
    def _prefixar_heading(paragrafo, nivel, contadores):
        texto = paragrafo.text.strip()
        if re.match(r'^\d+(?:\.\d+)*\s+', texto):
            return
        while len(contadores) < nivel:
            contadores.append(0)
        while len(contadores) > nivel:
            contadores.pop()
        contadores[nivel - 1] += 1
        indice = '.'.join(str(num) for num in contadores)
        if paragrafo.runs:
            paragrafo.runs[0].text = f'{indice} {paragrafo.runs[0].text}'
        else:
            paragrafo.add_run(f'{indice} {texto}')

    @staticmethod
    def _spec_texto(estilos):
        return estilos.get('texto normal') or {
            'alinhamento': 'JUSTIFY (3)',
            'espacamento_depois_pt': 11.25,
            'fonte_nome': 'Verdana',
            'fonte_tamanho_pt': 10,
            'cor_rgb': '000000',
        }

    @staticmethod
    def _spec_legenda(estilos):
        return estilos.get('figura') or estilos.get('caption') or {
            'alinhamento': 'CENTER (1)',
            'espacamento_depois_pt': 11.25,
            'fonte_nome': 'Verdana',
            'fonte_tamanho_pt': 9,
            'cor_rgb': '000000',
        }

    @staticmethod
    def _spec_heading(estilos, nivel):
        chaves = {
            1: 'nível 1',
            2: 'nível 1.1',
            3: 'nível 1.1.1',
        }
        return estilos.get(chaves.get(nivel, f'heading {nivel}')) or {
            'fonte_nome': 'Verdana',
            'fonte_tamanho_pt': max(10, 16 - (nivel * 2)),
            'negrito': True,
            'cor_rgb': '0F1E3D' if nivel == 1 else '000000',
        }

    @classmethod
    def _aplicar_spec_paragrafo(cls, paragrafo, spec):
        alinhamento = spec.get('alinhamento') or ''
        if 'JUSTIFY' in alinhamento:
            paragrafo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        elif 'CENTER' in alinhamento:
            paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fmt = paragrafo.paragraph_format
        if spec.get('espacamento_antes_pt') is not None:
            fmt.space_before = Pt(spec['espacamento_antes_pt'])
        if spec.get('espacamento_depois_pt') is not None:
            fmt.space_after = Pt(spec['espacamento_depois_pt'])
        if spec.get('entre_linhas') is not None:
            fmt.line_spacing = spec['entre_linhas']
        if spec.get('recuo_primeira_linha_cm') is not None:
            fmt.first_line_indent = Cm(spec['recuo_primeira_linha_cm'])
        if spec.get('recuo_esquerda_cm') is not None:
            fmt.left_indent = Cm(spec['recuo_esquerda_cm'])
        if spec.get('recuo_direita_cm') is not None:
            fmt.right_indent = Cm(spec['recuo_direita_cm'])
        for run in paragrafo.runs:
            cls._aplicar_spec_fonte(run.font, spec)

    @staticmethod
    def _aplicar_spec_fonte(fonte, spec):
        if spec.get('fonte_nome'):
            fonte.name = spec['fonte_nome']
        if spec.get('fonte_tamanho_pt') is not None:
            fonte.size = Pt(spec['fonte_tamanho_pt'])
        if spec.get('negrito') is not None:
            fonte.bold = spec['negrito']
        if spec.get('italico') is not None:
            fonte.italic = spec['italico']
        if spec.get('sublinhado') is not None:
            fonte.underline = spec['sublinhado']
        cor = spec.get('cor_rgb')
        if cor and re.match(r'^[0-9A-Fa-f]{6}$', cor):
            fonte.color.rgb = RGBColor.from_string(cor)

    @classmethod
    def validar_docx_sugerido(cls, caminho_docx, metricas_aplicadas):
        """Valida condicionantes obrigatórias antes de persistir o DOCX final."""
        faltantes = cls.METRICAS_OBRIGATORIAS.difference(metricas_aplicadas)
        if faltantes:
            raise RuntimeError(
                'Métricas obrigatórias não aplicadas: '
                + ', '.join(sorted(faltantes))
            )
        if not os.path.exists(caminho_docx):
            raise RuntimeError('DOCX sugerido temporário não foi gerado.')
        Document(caminho_docx)
