"""Modelo para representar seções técnicas do DOCX (w:sectPr)."""

from app import db
from app.models.mixins import AuditoriaMixin


class SecaoDOCX(db.Model, AuditoriaMixin):
    """Representa uma seção técnica do DOCX (elemento w:sectPr no OOXML).

    Distinção CRÍTICA:
    - SEÇÃO (DOCX): Unidade técnica de formatação (cabeçalhos, rodapés, numeração)
    - CAPÍTULO: Unidade conceitual de conteúdo (título, responsável, status editorial)

    Uma seção pode conter múltiplos capítulos, e um capítulo pode abranger múltiplas seções.
    """

    __tablename__ = "secoes_docx"

    id_secao = db.Column(db.Integer, primary_key=True)
    id_relatorio = db.Column(
        db.Integer, db.ForeignKey("relatorios_producao.id"), nullable=False
    )
    ordem_secao = db.Column(
        db.Integer, nullable=False
    )  # Ordem sequencial no documento (0-based)

    # Tipo de seção (conforme OOXML w:type)
    tipo_secao = db.Column(
        db.String(50), nullable=False, default="continuous"
    )  # 'continuous', 'nextPage', 'nextColumn', 'evenPage', 'oddPage'

    # Propriedades de numeração de páginas
    reiniciar_numero_pagina = db.Column(db.Boolean, default=False)
    numero_pagina_inicial = db.Column(db.Integer, nullable=True)
    estilo_numero_pagina = db.Column(
        db.String(50), default="decimal"
    )  # 'decimal', 'upperRoman', 'lowerRoman', 'upperLetter', 'lowerLetter'

    # Propriedades de layout
    orientacao = db.Column(db.String(20), default="portrait")  # 'portrait', 'landscape'

    colunas = db.Column(db.Integer, default=1)

    # Margens (em pontos)
    margem_superior = db.Column(db.Integer, default=1440)  # 1 polegada = 1440 twips
    margem_inferior = db.Column(db.Integer, default=1440)
    margem_esquerda = db.Column(db.Integer, default=1440)
    margem_direita = db.Column(db.Integer, default=1440)

    # Cabeçalhos e rodapés
    tem_cabecalho_diferente = db.Column(db.Boolean, default=False)
    tem_rodape_diferente = db.Column(db.Boolean, default=False)

    # Propriedades OOXML brutas (para casos complexos)
    propriedades_raw = db.Column(db.Text, nullable=True)

    # Relacionamentos
    relatorio = db.relationship("RelatorioProducao", back_populates="secoes")
    capitulos = db.relationship(
        "CapituloDocumento",
        foreign_keys="CapituloDocumento.id_secao_inicio",
        back_populates="secao_inicio",
    )
    quebras = db.relationship("QuebraPagina", back_populates="secao")

    # Propriedades calculadas
    @property
    def descricao_tipo(self):
        """Descrição amigável do tipo de seção."""
        map_tipos = {
            "continuous": "Contínua",
            "nextPage": "Nova página",
            "nextColumn": "Nova coluna",
            "evenPage": "Página par",
            "oddPage": "Página ímpar",
        }
        return map_tipos.get(self.tipo_secao, self.tipo_secao)

    @property
    def tem_numero_pagina_diferente(self):
        """Retorna True se a seção tem numeração de página diferente."""
        return self.reiniciar_numero_pagina or self.numero_pagina_inicial is not None

    @property
    def e_quebra_importante(self):
        """Retorna True se a seção representa uma quebra importante."""
        return self.tipo_secao in ("nextPage", "evenPage", "oddPage")

    def to_dict(self):
        """Converte para dicionário para serialização."""
        return {
            "id_secao": self.id_secao,
            "ordem_secao": self.ordem_secao,
            "tipo_secao": self.tipo_secao,
            "descricao_tipo": self.descricao_tipo,
            "reiniciar_numero_pagina": self.reiniciar_numero_pagina,
            "numero_pagina_inicial": self.numero_pagina_inicial,
            "estilo_numero_pagina": self.estilo_numero_pagina,
            "orientacao": self.orientacao,
            "colunas": self.colunas,
            "tem_numero_pagina_diferente": self.tem_numero_pagina_diferente,
            "e_quebra_importante": self.e_quebra_importante,
        }
