"""Serviço para classificação e validação de capítulos com conceito endurecido.
Inclui mapeamento entre tipos conceituais e estilos DOCX para atualização automática de índices."""

from typing import List, Dict, Optional, Tuple
from app.models.capitulo_documento import CapituloDocumento


class ServicoClassificacaoCapitulos:
    """Serviço para classificar e validar capítulos segundo o conceito endurecido.
    Inclui mapeamento entre tipos conceituais e estilos DOCX."""

    # Mapeamento entre estilos DOCX e tipos conceituais
    ESTILOS_PARA_CLASSIFICACAO = {
        # Capítulos (nível 1)
        "capitulo": ["Heading 1", "Título 1", "Titulo 1", "TÍTULO 1", "Titulo1", "Heading1", "Title 1", "Titulo 1º"],
        # Subcapítulos nível 2
        "subcapitulo_nivel_2": ["Heading 2", "Título 2", "Titulo 2", "TÍTULO 2", "Titulo2", "Heading2", "Title 2", "Titulo 2º"],
        # Subcapítulos nível 3
        "subcapitulo_nivel_3": ["Heading 3", "Título 3", "Titulo 3", "TÍTULO 3", "Titulo3", "Heading3", "Title 3", "Titulo 3º"],
        # Anexos
        "anexo": ["Anexo", "ANEXO", "Anexo A", "Anexo_A", "Anexo Heading", "Anexo Title", "Anexo 1"],
        # Apêndices
        "apendice": ["Apêndice", "APÊNDICE", "Apêndice I", "Apêndice_I", "Apêndice Heading", "Apêndice Title", "Apêndice 1"],
        # Pré-textuais
        "pre_textual": [
            "Title",
            "Capa",
            "Folha de Rosto",
            "Resumo",
            "Abstract",
            "Sumário",
            "Sumario",
            "Lista de Figuras",
            "Lista de Tabelas",
            "Lista de Abreviaturas",
        ],
        # Pós-textuais (não anexo/apêndice)
        "pos_textual": ["Referências", "Referencias", "Bibliografia", "Glossário", "Glossario", "Índice", "Indice"],
    }

    @staticmethod
    def classificar_por_estilo_docx(estilo_docx: str) -> Tuple[Optional[str], Optional[int], Optional[str]]:
        """Classifica um capítulo baseado no estilo DOCX.

        Retorna: (classificacao, nivel, prefixo_indice)
        """
        if not estilo_docx:
            return None, None, None

        estilo = estilo_docx.strip()

        # Verificar em cada categoria
        for tipo, estilos in ServicoClassificacaoCapitulos.ESTILOS_PARA_CLASSIFICACAO.items():
            if estilo in estilos:
                if tipo == "capitulo":
                    return None, 1, None  # Capítulo textual
                elif tipo == "subcapitulo_nivel_2":
                    return None, 2, None  # Subcapítulo nível 2
                elif tipo == "subcapitulo_nivel_3":
                    return None, 3, None  # Subcapítulo nível 3
                elif tipo == "anexo":
                    return "anexo", 1, "ANEXO_"
                elif tipo == "apendice":
                    return "apendice", 1, "APENDICE_"
                elif tipo == "pre_textual":
                    return None, 1, None  # Pré-textual
                elif tipo == "pos_textual":
                    return None, 1, None  # Pós-textual (não classificado)

        # Fallback: tentar classificar por padrões no nome do estilo
        estilo_lower = estilo.lower()
        if "anexo" in estilo_lower:
            return "anexo", 1, "ANEXO_"
        elif "apendice" in estilo_lower or "apêndice" in estilo_lower:
            return "apendice", 1, "APENDICE_"
        elif "heading 1" in estilo_lower or "título 1" in estilo_lower:
            return None, 1, None
        elif "heading 2" in estilo_lower or "título 2" in estilo_lower:
            return None, 2, None
        elif "heading 3" in estilo_lower or "título 3" in estilo_lower:
            return None, 3, None

        return None, None, None

    @staticmethod
    def classificar_por_titulo(titulo: str, indice: str, nivel: int) -> Tuple[Optional[str], Optional[str]]:
        """Classifica um capítulo baseado no título, índice e nível.

        Retorna: (classificacao, prefixo_indice)
        """
        titulo_lower = titulo.lower()
        indice_upper = indice.upper() if indice else ""

        # Verificar se é anexo
        if (
            "anexo" in titulo_lower
            or indice_upper.startswith("ANEXO")
            or (indice_upper and indice_upper[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" and len(indice_upper) == 1)
        ):
            return "anexo", "ANEXO_"

        # Verificar se é apêndice
        if (
            "apendice" in titulo_lower
            or "apêndice" in titulo_lower
            or indice_upper.startswith("APENDICE")
            or indice_upper in ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")
        ):
            return "apendice", "APENDICE_"

        # Conteúdo textual (capítulo ou subcapítulo)
        return None, None

    @staticmethod
    def determinar_tipo_elemento(titulo: str, posicao_relativa: int, total_secoes: int) -> str:
        """Determina o tipo de elemento baseado no título e posição.

        Args:
            titulo: Título da seção
            posicao_relativa: Posição relativa no documento (0-based)
            total_secoes: Total de seções no documento

        Returns:
            'pre_textual', 'textual' ou 'pos_textual'
        """
        titulo_lower = titulo.lower()

        # Seções pré-textuais (primeiras 20% do documento)
        if posicao_relativa < total_secoes * 0.2:
            # Verificar títulos comuns de pré-textuais
            pre_textuais = [
                "capa",
                "folha de rosto",
                "resumo",
                "abstract",
                "sumário",
                "sumario",
                "lista de figuras",
                "lista de tabelas",
                "lista de abreviaturas",
                "lista de símbolos",
            ]

            for pre in pre_textuais:
                if pre in titulo_lower:
                    return "pre_textual"

        # Seções pós-textuais (últimas 30% do documento)
        if posicao_relativa > total_secoes * 0.7:
            # Verificar títulos comuns de pós-textuais
            pos_textuais = [
                "referências",
                "referencias",
                "bibliografia",
                "anexo",
                "apêndice",
                "apendice",
                "glossário",
                "glossario",
                "índice",
                "indice",
            ]

            for pos in pos_textuais:
                if pos in titulo_lower:
                    return "pos_textual"

        # Padrão: textual
        return "textual"

    @staticmethod
    def extrair_indice_puro(indice_com_prefixo: str) -> str:
        """Extrai o índice puro removendo prefixos.

        Exemplos:
            'ANEXO_A' → 'A'
            'APENDICE_I' → 'I'
            '1.1' → '1.1'
        """
        if not indice_com_prefixo:
            return ""

        indice = indice_com_prefixo.upper()

        if indice.startswith("ANEXO_"):
            return indice[6:]  # Remove 'ANEXO_'
        elif indice.startswith("APENDICE_"):
            return indice[9:]  # Remove 'APENDICE_'

        return indice_com_prefixo

    @staticmethod
    def gerar_indice_hierarquico(nivel: int, indice_pai: str = None, sequencia: int = 1) -> str:
        """Gera índice hierárquico baseado no nível e índice do pai.

        Args:
            nivel: Nível do capítulo (1=capítulo, ≥2=subcapítulo)
            indice_pai: Índice do capítulo pai (para subcapítulos)
            sequencia: Sequência dentro do nível

        Returns:
            Índice hierárquico formatado
        """
        if nivel == 1:
            return str(sequencia)
        elif nivel >= 2 and indice_pai:
            return f"{indice_pai}.{sequencia}"
        else:
            return str(sequencia)

    @staticmethod
    def validar_capitulo(capitulo: CapituloDocumento) -> Dict[str, any]:
        """Valida um capítulo completo e retorna diagnóstico.

        Returns:
            Dict com:
                - valido: bool
                - erros: List[str]
                - avisos: List[str]
                - tipo_conceitual: str
        """
        resultado = {"valido": True, "erros": [], "avisos": [], "tipo_conceitual": capitulo.tipo_conceitual}

        # Validar estrutura básica
        erros_validacao = capitulo.validar_estrutura()
        if erros_validacao:
            resultado["valido"] = False
            resultado["erros"].extend(erros_validacao)

        # Validações adicionais
        if capitulo.e_capitulo:
            # Capítulo deve ter índice numérico simples
            if capitulo.indice_capitulo and not capitulo.indice_capitulo.isdigit():
                resultado["avisos"].append(f"Capítulo de nível 1 tem índice não numérico: {capitulo.indice_capitulo}")

        elif capitulo.e_subcapitulo:
            # Subcapítulo deve ter índice hierárquico
            if capitulo.indice_capitulo and "." not in capitulo.indice_capitulo:
                resultado["avisos"].append(f"Subcapítulo tem índice não hierárquico: {capitulo.indice_capitulo}")

        elif capitulo.e_anexo:
            # Anexo deve ter índice alfabético
            if capitulo.indice_capitulo and not capitulo.indice_capitulo.isalpha():
                resultado["avisos"].append(f"Anexo tem índice não alfabético: {capitulo.indice_capitulo}")

        elif capitulo.e_apendice:
            # Apêndice deve ter índice romano ou alfabético
            if capitulo.indice_capitulo:
                indice = capitulo.indice_capitulo.upper()
                romanos = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
                if not (indice.isalpha() or indice in romanos):
                    resultado["avisos"].append(f"Apêndice tem índice inválido: {capitulo.indice_capitulo}")

        return resultado

    @staticmethod
    def normalizar_capitulo(capitulo: CapituloDocumento) -> CapituloDocumento:
        """Normaliza um capítulo aplicando regras do conceito endurecido.

        Ajusta automaticamente:
        - classificacao baseada no título/índice
        - prefixo_indice quando aplicável
        - tipo_elemento quando inconsistente
        """
        # Determinar classificação se não definida
        if not capitulo.classificacao:
            classificacao, prefixo = ServicoClassificacaoCapitulos.classificar_por_titulo(
                capitulo.titulo_capitulo, capitulo.indice_capitulo, capitulo.nivel_capitulo
            )
            if classificacao:
                capitulo.classificacao = classificacao
                capitulo.prefixo_indice = prefixo

        # Ajustar tipo_elemento para anexos/apêndices
        if capitulo.classificacao in ("anexo", "apendice"):
            capitulo.tipo_elemento = "pos_textual"

        # Garantir que capítulos textuais tenham tipo correto
        if capitulo.nivel_capitulo == 1 and not capitulo.classificacao:
            capitulo.tipo_elemento = "textual"

        return capitulo

    @staticmethod
    def criar_arvore_capitulos(capitulos: List[CapituloDocumento]) -> List[Dict]:
        """Cria uma árvore hierárquica de capítulos.

        Returns:
            Lista de dicionários com estrutura hierárquica
        """
        # Encontrar raízes (capítulos sem pai)
        raizes = []
        for cap in capitulos:
            if cap.id_capitulo_pai is None:
                raizes.append(cap)

        # Ordenar raízes por ordem_capitulo
        raizes.sort(key=lambda x: x.ordem_capitulo)

        # Construir árvore recursivamente
        def construir_no(capitulo: CapituloDocumento) -> Dict:
            no = {
                "id": capitulo.id_capitulo_documento,
                "titulo": capitulo.titulo_capitulo,
                "indice": capitulo.indice_completo,
                "tipo_conceitual": capitulo.tipo_conceitual,
                "nivel": capitulo.nivel_capitulo,
                "responsavel": capitulo.responsavel.nome if capitulo.responsavel else None,
                "status": capitulo.descricao_status,
                "filhos": [],
            }

            # Encontrar filhos
            filhos = [cap for cap in capitulos if cap.id_capitulo_pai == capitulo.id_capitulo_documento]
            filhos.sort(key=lambda x: x.ordem_capitulo)

            for filho in filhos:
                no["filhos"].append(construir_no(filho))

            return no

        # Construir árvore a partir das raízes
        arvore = []
        for raiz in raizes:
            arvore.append(construir_no(raiz))

        return arvore

    @staticmethod
    def atualizar_indices_apos_operacao(
        capitulos: List[CapituloDocumento], tipo_operacao: str, capitulo_afetado: Optional[CapituloDocumento] = None
    ) -> List[CapituloDocumento]:
        """Atualiza índices após adição, remoção ou reordenação de capítulos.

        Args:
            capitulos: Lista de todos os capítulos do relatório
            tipo_operacao: 'adicao', 'remocao', 'reordenacao'
            capitulo_afetado: Capítulo que foi adicionado/removido/reordenado

        Returns:
            Lista de capítulos com índices atualizados
        """
        del tipo_operacao, capitulo_afetado

        # Separar por tipo conceitual
        capitulos_textuais = [c for c in capitulos if c.tipo_elemento == "textual" and not c.classificacao]
        anexos = [c for c in capitulos if c.classificacao == "anexo"]
        apendices = [c for c in capitulos if c.classificacao == "apendice"]

        # Ordenar por ordem_capitulo
        capitulos_textuais.sort(key=lambda x: x.ordem_capitulo)
        anexos.sort(key=lambda x: x.ordem_capitulo)
        apendices.sort(key=lambda x: x.ordem_capitulo)

        # 1. Atualizar índices de capítulos textuais (nível 1)
        for i, cap in enumerate(capitulos_textuais, 1):
            if cap.nivel_capitulo == 1:
                cap.indice_capitulo = str(i)

        # 2. Atualizar índices de subcapítulos
        for cap in capitulos_textuais:
            if cap.nivel_capitulo >= 2 and cap.capitulo_pai:
                # Encontrar subcapítulos do mesmo pai
                subcapitulos = [c for c in capitulos_textuais if c.id_capitulo_pai == cap.capitulo_pai.id_capitulo_documento]
                subcapitulos.sort(key=lambda x: x.ordem_capitulo)

                # Atribuir índices hierárquicos
                for j, subcap in enumerate(subcapitulos, 1):
                    subcap.indice_capitulo = f"{cap.capitulo_pai.indice_capitulo}.{j}"

        # 3. Atualizar índices de anexos (A, B, C...)
        for i, anexo in enumerate(anexos, 1):
            letra = chr(64 + i)  # A=65, B=66, etc.
            anexo.indice_capitulo = letra

        # 4. Atualizar índices de apêndices (I, II, III... ou A, B, C...)
        romanos = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
        for i, apendice in enumerate(apendices, 1):
            if i <= len(romanos):
                apendice.indice_capitulo = romanos[i - 1]
            else:
                # Fallback para alfabético após X
                apendice.indice_capitulo = chr(64 + i - 10)

        return capitulos

    @staticmethod
    def determinar_estilo_por_tipo_conceitual(tipo_conceitual: str, nivel: int = 1) -> Optional[str]:
        """Determina o estilo DOCX apropriado para um tipo conceitual.

        Args:
            tipo_conceitual: 'capitulo', 'subcapitulo', 'anexo', 'apendice', etc.
            nivel: Nível hierárquico (1, 2, 3...)

        Returns:
            Nome do estilo DOCX recomendado
        """
        if tipo_conceitual == "capitulo":
            return "Heading 1"
        elif tipo_conceitual == "subcapitulo":
            if nivel == 2:
                return "Heading 2"
            elif nivel == 3:
                return "Heading 3"
            else:
                return f"Heading {nivel}"
        elif tipo_conceitual == "anexo":
            return "Anexo"
        elif tipo_conceitual == "apendice":
            return "Apêndice"
        elif tipo_conceitual == "pre_textual":
            return "Title"
        elif tipo_conceitual == "pos_textual":
            return "Normal"  # Estilo padrão para conteúdo pós-textual

        return None

    @staticmethod
    def extrair_e_classificar_do_docx(paragrafo_texto: str, estilo_docx: str, posicao: int, total_paragrafos: int) -> Dict:
        """Extrai e classifica um capítulo a partir de um parágrafo DOCX.

        Args:
            paragrafo_texto: Texto do parágrafo
            estilo_docx: Estilo DOCX do parágrafo
            posicao: Posição no documento (0-based)
            total_paragrafos: Total de parágrafos no documento

        Returns:
            Dicionário com propriedades do capítulo
        """
        # Classificar por estilo DOCX
        classificacao, nivel, prefixo = ServicoClassificacaoCapitulos.classificar_por_estilo_docx(estilo_docx)

        # Determinar tipo_elemento baseado na posição e classificação
        if classificacao in ("anexo", "apendice"):
            tipo_elemento = "pos_textual"
        elif posicao < total_paragrafos * 0.2:
            tipo_elemento = "pre_textual"
        elif posicao > total_paragrafos * 0.7:
            tipo_elemento = "pos_textual"
        else:
            tipo_elemento = "textual"

        # Se não classificou por estilo, tentar por título
        if not classificacao:
            classificacao, prefixo = ServicoClassificacaoCapitulos.classificar_por_titulo(paragrafo_texto, "", nivel or 1)

        return {
            "titulo_capitulo": paragrafo_texto,
            "estilo_docx": estilo_docx,
            "tipo_elemento": tipo_elemento,
            "classificacao": classificacao,
            "prefixo_indice": prefixo,
            "nivel_capitulo": nivel or 1,
            "ordem_capitulo": posicao + 1,
        }
