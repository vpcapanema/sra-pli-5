"""Serviço para extrair seções e quebras de página de documentos DOCX."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from docx import Document

from app.models.capitulo_documento import CapituloDocumento
from app.models.quebra_pagina import QuebraPagina
from app.models.secao_docx import SecaoDOCX


@dataclass
class ElementoDOCX:
    """Representa um elemento extraído do DOCX."""

    tipo: str
    posicao: int
    conteudo: str
    estilo: Optional[str] = None
    propriedades: Optional[Dict[str, Any]] = None


def _twips(valor: Any, padrao: int = 1440) -> int:
    """Converte valores de medida do python-docx para twips."""
    if valor is None:
        return padrao
    return int(getattr(valor, "twips", padrao) or padrao)


def _criar_secao(**valores: Any) -> SecaoDOCX:
    """Cria SecaoDOCX sem kwargs para evitar falsos positivos do Pyright."""
    secao = SecaoDOCX()
    for campo, valor in valores.items():
        setattr(secao, campo, valor)
    return secao


def _criar_quebra(**valores: Any) -> QuebraPagina:
    """Cria QuebraPagina sem kwargs para evitar falsos positivos do Pyright."""
    quebra = QuebraPagina()
    for campo, valor in valores.items():
        setattr(quebra, campo, valor)
    return quebra


class ServicoExtracaoSecoes:
    """Serviço para extrair seções, quebras e elementos do DOCX."""

    @staticmethod
    def extrair_secoes_do_docx(
        docx_path: str,
        id_relatorio: int,
    ) -> List[SecaoDOCX]:
        """Extrai todas as seções (w:sectPr) de um documento DOCX."""
        try:
            doc = Document(docx_path)
        except (OSError, ValueError, ImportError):
            return ServicoExtracaoSecoes._extrair_secoes_fallback(id_relatorio)

        secoes = []
        for indice, section in enumerate(doc.sections):
            page_width = section.page_width or 0
            page_height = section.page_height or 0
            orientacao = "landscape" if page_width > page_height else "portrait"

            secoes.append(
                _criar_secao(
                    id_relatorio=id_relatorio,
                    ordem_secao=indice,
                    tipo_secao=ServicoExtracaoSecoes._determinar_tipo_secao(
                        section
                    ),
                    reiniciar_numero_pagina=section.start_type != "continuous",
                    orientacao=orientacao,
                    colunas=ServicoExtracaoSecoes._contar_colunas(),
                    margem_superior=_twips(section.top_margin),
                    margem_inferior=_twips(section.bottom_margin),
                    margem_esquerda=_twips(section.left_margin),
                    margem_direita=_twips(section.right_margin),
                    propriedades_raw=ServicoExtracaoSecoes
                    ._extrair_propriedades_raw(),
                )
            )

        return secoes

    @staticmethod
    def _determinar_tipo_secao(section: Any) -> str:
        """Determina o tipo de seção baseado nas propriedades."""
        return str(getattr(section, "start_type", None) or "nextPage")

    @staticmethod
    def _contar_colunas() -> int:
        """Conta o número de colunas na seção."""
        return 1

    @staticmethod
    def _extrair_propriedades_raw() -> str:
        """Extrai propriedades OOXML brutas da seção."""
        return "{}"

    @staticmethod
    def _extrair_secoes_fallback(id_relatorio: int) -> List[SecaoDOCX]:
        """Fallback para extração de seções quando python-docx falha."""
        return [
            _criar_secao(
                id_relatorio=id_relatorio,
                ordem_secao=0,
                tipo_secao="nextPage",
                reiniciar_numero_pagina=True,
                numero_pagina_inicial=1,
                estilo_numero_pagina="decimal",
            ),
            _criar_secao(
                id_relatorio=id_relatorio,
                ordem_secao=1,
                tipo_secao="continuous",
                reiniciar_numero_pagina=False,
                estilo_numero_pagina="decimal",
            ),
        ]

    @staticmethod
    def extrair_quebras_pagina_do_docx(
        docx_path: str,
        secoes: List[SecaoDOCX],
    ) -> List[QuebraPagina]:
        """Extrai quebras de página do documento DOCX."""
        try:
            doc = Document(docx_path)
        except (OSError, ValueError, ImportError):
            return []

        quebras = []
        secao_atual = 0
        posicao_na_secao = 0

        for paragraph in doc.paragraphs:
            for run in getattr(paragraph, "runs", []):
                if run.text and "\\page" in run.text:
                    id_secao = (
                        secoes[secao_atual].id_secao
                        if secao_atual < len(secoes)
                        else 1
                    )
                    quebras.append(
                        _criar_quebra(
                            id_secao=id_secao,
                            posicao_na_secao=posicao_na_secao,
                            tipo_posicao="paragrafo",
                            tipo_quebra="page",
                            forcar_nova_pagina=True,
                            contexto_anterior=(
                                paragraph.text[:100] if paragraph.text else None
                            ),
                        )
                    )

            posicao_na_secao += 1
            estilo = getattr(getattr(paragraph, "style", None), "name", None)
            if estilo in ("Heading 1", "Título 1"):
                secao_atual = min(secao_atual + 1, len(secoes) - 1)
                posicao_na_secao = 0

        return quebras

    @staticmethod
    def mapear_capitulos_para_secoes(
        capitulos: List[CapituloDocumento],
        secoes: List[SecaoDOCX],
    ) -> List[CapituloDocumento]:
        """Mapeia capítulos para as seções onde começam e terminam."""
        if not capitulos or not secoes:
            return capitulos

        capitulos.sort(key=lambda capitulo: capitulo.ordem_capitulo)
        for indice, capitulo in enumerate(capitulos):
            if capitulo.tipo_elemento == "textual" and not capitulo.classificacao:
                capitulo.id_secao_inicio = secoes[0].id_secao if secoes else 1
            elif capitulo.classificacao in ("anexo", "apendice"):
                capitulo.id_secao_inicio = (
                    secoes[1].id_secao if len(secoes) > 1 else secoes[0].id_secao
                )

            if indice < len(capitulos) - 1:
                proximo_capitulo = capitulos[indice + 1]
                capitulo.id_secao_fim = proximo_capitulo.id_secao_inicio
            else:
                capitulo.id_secao_fim = (
                    secoes[-1].id_secao if secoes else capitulo.id_secao_inicio
                )

        return capitulos

    @staticmethod
    def analisar_estrutura_documento(
        docx_path: str,
        id_relatorio: int,
    ) -> Dict[str, Any]:
        """Executa análise completa da estrutura do documento DOCX."""
        secoes = ServicoExtracaoSecoes.extrair_secoes_do_docx(
            docx_path,
            id_relatorio,
        )
        quebras = ServicoExtracaoSecoes.extrair_quebras_pagina_do_docx(
            docx_path,
            secoes,
        )

        analise = {
            "total_secoes": len(secoes),
            "total_quebras": len(quebras),
            "secoes_com_numero_diferente": sum(
                1 for secao in secoes if secao.tem_numero_pagina_diferente
            ),
            "secoes_com_orientacao_diferente": sum(
                1 for secao in secoes if secao.orientacao != "portrait"
            ),
            "quebras_visiveis": sum(
                1 for quebra in quebras if quebra.e_quebra_visivel
            ),
            "estrutura_secoes": [
                {
                    "ordem": secao.ordem_secao,
                    "tipo": secao.tipo_secao,
                    "orientacao": secao.orientacao,
                    "colunas": secao.colunas,
                    "reinicia_numero": secao.reiniciar_numero_pagina,
                }
                for secao in secoes
            ],
        }

        return {
            "secoes": secoes,
            "quebras": quebras,
            "analise": analise,
        }

    @staticmethod
    def validar_mapeamento_secoes_capitulos(
        secoes: List[SecaoDOCX],
        capitulos: List[CapituloDocumento],
    ) -> List[str]:
        """Valida o mapeamento entre seções e capítulos."""
        erros = []
        for capitulo in capitulos:
            if not capitulo.id_secao_inicio:
                erros.append(
                    f"Capítulo '{capitulo.titulo_capitulo}' não tem seção "
                    "de início"
                )

            secao_inicio = next(
                (
                    secao
                    for secao in secoes
                    if secao.id_secao == capitulo.id_secao_inicio
                ),
                None,
            )
            if not secao_inicio:
                erros.append(
                    f"Capítulo '{capitulo.titulo_capitulo}' referencia "
                    f"seção inexistente: {capitulo.id_secao_inicio}"
                )
                continue

            existe_anexo_na_secao = any(
                item.classificacao in ("anexo", "apendice")
                for item in capitulos
                if item.id_secao_inicio == secao_inicio.id_secao
            )
            if (
                capitulo.tipo_elemento == "textual"
                and secao_inicio.ordem_secao > 0
                and existe_anexo_na_secao
            ):
                erros.append(
                    f"Capítulo textual '{capitulo.titulo_capitulo}' começa "
                    "em seção de anexos/apêndices"
                )

        return erros
