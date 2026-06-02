"""Perfil de Formatacao: ponte entre `BibliotecaFormatacaoCanonica` e os
servicos de captioning/cross-refs/TOC.

Sem este modulo, os servicos `servico_captioning` e `servico_toc` usam
parametros HARD-CODED (estilo "Caption", separador en-dash, posicao
"abaixo" para figuras, etc). Esses defaults raramente coincidem com a
biblioteca canonica escolhida pelo coordenador na clonagem do
relatorio.

Este modulo:

1. Le os 3 JSONs em `storage/canonicos/<biblioteca>/`:
   - `canonico_formatacao.json`  (estilos, legendas, numeracao)
   - `canonico_capitulos.json`   (estilos de heading)
   - `canonico_estrutura_macro.json` (estrutura textual)

2. Constroi um dataclass `PerfilFormatacao` com as escolhas reais
   da biblioteca:
   - `estilo_legenda_figura`, `estilo_legenda_tabela`, `estilo_fonte`
   - `posicao_legenda_figura`, `posicao_legenda_tabela`
   - `separador_indice_seq` ('-' ou '.')
   - `separador_legenda` (':' ou '–')
   - `estilo_titulo_toc`
   - `nome_heading_por_nivel[i]` (pode ser "Heading 1" com espaco ou
     "Heading1" sem espaco — a biblioteca escolhe)

3. Expoe defaults seguros (compatible com Word generico) quando a
   biblioteca esta ausente ou nao foi extraida.

Exemplo:
    perfil = PerfilFormatacao.de_relatorio(rel)
    reindexar_captions(rel.caminho_template, perfil=perfil)
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional


# Defaults — usados quando a biblioteca nao tem dado canonico para
# o atributo. Compativeis com Word/Office generico.
_DEFAULT_ESTILO_LEGENDA = 'Caption'
_DEFAULT_POSICAO_FIGURA = 'abaixo'  # convencao cientifica
_DEFAULT_POSICAO_TABELA = 'acima'   # convencao Word/ABNT
_DEFAULT_SEP_INDICE = '.'           # "5.1.2"
_DEFAULT_SEP_LEGENDA = ' – '        # en-dash com espacos
_DEFAULT_HEADING_NOMES = [
    None,              # placeholder para nivel 0
    'Heading 1',
    'Heading 2',
    'Heading 3',
    'Heading 4',
    'Heading 5',
    'Heading 6',
    'Heading 7',
    'Heading 8',
    'Heading 9',
]


@dataclass
class PerfilFormatacao:
    """Perfil unificado para captioning + TOC + cross-refs."""

    # ===== Legendas =====
    rotulo_figura: str = 'Figura'
    rotulo_tabela: str = 'Tabela'
    rotulo_equacao: str = 'Equação'
    rotulo_fonte: str = 'Fonte'

    # Estilo de paragrafo aplicado a cada tipo de legenda. Quando o
    # estilo nao existe no DOCX em producao, a aplicacao falha
    # silenciosamente (Word usa Normal). Os servicos checam disponibili-
    # dade e fazem fallback se necessario.
    estilo_legenda_figura: str = _DEFAULT_ESTILO_LEGENDA
    estilo_legenda_tabela: str = _DEFAULT_ESTILO_LEGENDA
    estilo_legenda_equacao: str = _DEFAULT_ESTILO_LEGENDA
    estilo_fonte: str = _DEFAULT_ESTILO_LEGENDA

    # Posicao da legenda em relacao ao elemento ('acima' ou 'abaixo').
    posicao_legenda_figura: str = _DEFAULT_POSICAO_FIGURA
    posicao_legenda_tabela: str = _DEFAULT_POSICAO_TABELA

    # ===== Separadores =====
    # Usado entre indice de capitulo e numero sequencial:
    # '.' produz "Figura 4.1.2"; '-' produz "Figura 4-1-2".
    separador_indice_seq: str = _DEFAULT_SEP_INDICE
    # Usado entre numero e texto descritivo:
    # ' – ' produz "Figura 4.1 – Texto"; ': ' produz "Figura 4-1: Texto".
    separador_legenda: str = _DEFAULT_SEP_LEGENDA

    # ===== TOC =====
    # Estilo aplicado aos titulos "Sumário", "Lista de Figuras",
    # "Lista de Tabelas" inseridos pelo TOC automatico.
    estilo_titulo_toc: str = 'Heading 1'

    # ===== Headings =====
    # Mapeamento nivel -> nome do estilo. Permite que a biblioteca
    # canonica use "Heading 1" (com espaco) vs "Heading1" (sem).
    nome_heading_por_nivel: list = field(
        default_factory=lambda: list(_DEFAULT_HEADING_NOMES)
    )

    # ===== Origem (para debug/auditoria) =====
    origem: str = 'default'  # 'default', 'biblioteca:<nome>', 'parcial'
    avisos: list = field(default_factory=list)

    # ----------------------------------------------------------------
    # Construcao a partir do banco/disco
    # ----------------------------------------------------------------

    @classmethod
    def de_relatorio(cls, relatorio) -> 'PerfilFormatacao':
        """Cria perfil a partir de `RelatorioProducao.biblioteca`.

        Se o relatorio nao tem biblioteca vinculada ou os JSONs nao
        existem em disco, devolve perfil `default`.
        """
        bib = getattr(relatorio, 'biblioteca', None)
        if bib is None:
            return cls(origem='default', avisos=['sem biblioteca vinculada'])
        return cls.de_biblioteca(bib)

    @classmethod
    def de_biblioteca(cls, biblioteca) -> 'PerfilFormatacao':
        """Cria perfil a partir de `BibliotecaFormatacaoCanonica`.

        Le os JSONs em `biblioteca.caminho_arquivo` (diretorio em
        `storage/canonicos/<nome>/`) e popula os campos do perfil.
        """
        caminho_dir = getattr(biblioteca, 'caminho_arquivo', None)
        if not caminho_dir or not os.path.isdir(caminho_dir):
            return cls(
                origem='default',
                avisos=[f'biblioteca {biblioteca!r} sem caminho_arquivo'],
            )
        return cls.de_diretorio(caminho_dir, nome_biblioteca=getattr(
            biblioteca, 'nome_biblioteca', '<sem-nome>'
        ))

    @classmethod
    def de_diretorio(
        cls, caminho_dir: str, *, nome_biblioteca: str = '<dir>'
    ) -> 'PerfilFormatacao':
        """Le os 3 JSONs do diretorio e constroi o perfil.

        Tolerante a JSON parcial: campos ausentes recebem default e
        sao registrados em `perfil.avisos`.
        """
        avisos = []
        formatacao_raw = _carregar_json(
            os.path.join(caminho_dir, 'canonico_formatacao.json'),
            avisos,
        ) or {}
        capitulos_raw = _carregar_json(
            os.path.join(caminho_dir, 'canonico_capitulos.json'),
            avisos,
        ) or []
        formatacao = formatacao_raw if isinstance(formatacao_raw, dict) else {}
        capitulos = capitulos_raw if isinstance(capitulos_raw, list) else []

        perfil = cls(origem=f'biblioteca:{nome_biblioteca}', avisos=avisos)
        perfil._aplicar_legendas(formatacao.get('legendas') or {})
        perfil._aplicar_capitulos(capitulos)
        perfil._aplicar_estilos_paragrafo(
            formatacao.get('estilos_paragrafo') or []
        )
        return perfil

    # ----------------------------------------------------------------
    # Helpers internos de aplicacao
    # ----------------------------------------------------------------

    def _aplicar_legendas(self, legendas: dict) -> None:
        """Le `legendas.{figura,tabela,fonte}` do canonico_formatacao.

        Cada bloco tem `estilo_predominante`, `posicao_predominante` e
        `exemplos`. Dos exemplos, inferimos os separadores reais.
        """
        figura = legendas.get('figura') or {}
        tabela = legendas.get('tabela') or {}
        fonte = legendas.get('fonte') or {}

        if figura.get('estilo_predominante'):
            self.estilo_legenda_figura = figura['estilo_predominante']
        if figura.get('posicao_predominante') in ('acima', 'abaixo'):
            self.posicao_legenda_figura = figura['posicao_predominante']

        if tabela.get('estilo_predominante'):
            self.estilo_legenda_tabela = tabela['estilo_predominante']
        if tabela.get('posicao_predominante') in ('acima', 'abaixo'):
            self.posicao_legenda_tabela = tabela['posicao_predominante']

        if fonte.get('estilo_predominante'):
            self.estilo_fonte = fonte['estilo_predominante']

        # Inferir separadores a partir dos exemplos (preferindo
        # figuras > tabelas, pois figuras tem mais ocorrencias no
        # D20-15). Cada exemplo tem padrao
        # "Figura 4-1: Texto" ou "Figura 4.1 – Texto" etc.
        exemplos = (figura.get('exemplos') or []) + (
            tabela.get('exemplos') or []
        )
        sep_idx, sep_leg = _inferir_separadores(exemplos)
        if sep_idx is not None:
            self.separador_indice_seq = sep_idx
        if sep_leg is not None:
            self.separador_legenda = sep_leg

    def _aplicar_capitulos(self, arvore_capitulos: list) -> None:
        """Le `canonico_capitulos.json` para descobrir o nome real dos
        estilos de heading usados pela biblioteca (ex.: "Heading 1"
        vs "Heading1" vs "Titulo 1").
        """
        nivel_para_estilo: dict = {}

        def visitar(no):
            if not isinstance(no, dict):
                return
            nv = no.get('nivel')
            est = no.get('estilo')
            if isinstance(nv, int) and 1 <= nv <= 9 and est:
                # Primeiro estilo visto vence (frequencia tipicamente
                # alta para o nome canonico).
                nivel_para_estilo.setdefault(nv, est)
            for filho in (no.get('filhos') or []):
                visitar(filho)

        for raiz in arvore_capitulos or []:
            visitar(raiz)

        for nv, est in nivel_para_estilo.items():
            if 1 <= nv <= 9:
                self.nome_heading_por_nivel[nv] = est

    def _aplicar_estilos_paragrafo(self, estilos: list) -> None:
        """Procura estilos relevantes em `estilos_paragrafo[]`:
        - "TOC Heading" (titulo do sumario).
        - "Caption" / "Legenda" (legendas).
        - "Heading 1" (caso `_aplicar_capitulos` nao tenha capturado).
        """
        nomes = {(s.get('nome') or '').strip() for s in estilos if s}
        # Estilo do TOC
        if 'TOC Heading' in nomes:
            self.estilo_titulo_toc = 'TOC Heading'
        elif self.nome_heading_por_nivel[1]:
            # Fallback: mesmo estilo dos H1 do documento
            self.estilo_titulo_toc = self.nome_heading_por_nivel[1]


def _carregar_json(caminho: str, avisos: list) -> Optional[Any]:
    """Le JSON tolerando ausencia/erro. Adiciona aviso se falhar."""
    if not os.path.exists(caminho):
        avisos.append(f'arquivo ausente: {os.path.basename(caminho)}')
        return None
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        avisos.append(
            f'falha ao ler {os.path.basename(caminho)}: {e}'
        )
        return None


# Regex para inferir separadores a partir de exemplos como
# "Figura 4-1: Texto", "Tabela 5.2 – Outra coisa".
_RE_EXEMPLO = re.compile(
    r'^\s*(?:Figura|Tabela|Equa[çc]ão|Quadro)\s+'
    r'(\d+)([\-\u2013\u2014\.])(\d+)'
    r'(?:[\-\u2013\u2014\.]\d+)*'
    r'\s*([:\u2013\u2014\-])\s*',
    re.IGNORECASE,
)


def _inferir_separadores(exemplos: list) -> tuple:
    """A partir dos exemplos de legenda, infere
    `(separador_indice_seq, separador_legenda)`. Cada um pode ser None
    se nao houver consenso.

    Estrategia: votacao simples — o caractere mais frequente na
    posicao correspondente vence.
    """
    contagem_idx: dict = {}
    contagem_leg: dict = {}

    for exemplo in exemplos:
        if not isinstance(exemplo, str):
            continue
        m = _RE_EXEMPLO.match(exemplo)
        if not m:
            continue
        sep_idx = m.group(2)
        sep_leg_raw = m.group(4)
        # Normalizar separador de legenda: ':' e '-' geralmente vem
        # sem espacos no exemplo; en-dash '–' costuma vir com espacos.
        if sep_leg_raw == ':':
            sep_leg = ': '
        elif sep_leg_raw in ('\u2013', '\u2014'):
            sep_leg = f' {sep_leg_raw} '
        else:
            sep_leg = f' {sep_leg_raw} '
        contagem_idx[sep_idx] = contagem_idx.get(sep_idx, 0) + 1
        contagem_leg[sep_leg] = contagem_leg.get(sep_leg, 0) + 1

    sep_idx = (
        max(contagem_idx.items(), key=lambda item: item[1])[0]
        if contagem_idx else None
    )
    sep_leg = (
        max(contagem_leg.items(), key=lambda item: item[1])[0]
        if contagem_leg else None
    )
    return sep_idx, sep_leg
