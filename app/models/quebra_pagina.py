"""Modelo para representar quebras de página dentro de seções DOCX."""

from app import db
from app.models.mixins import AuditoriaMixin


class QuebraPagina(db.Model, AuditoriaMixin):
    """Representa uma quebra de página ou coluna dentro de uma seção DOCX."""

    __tablename__ = "quebras_pagina"
    id_quebra = db.Column(db.Integer, primary_key=True)
    id_secao = db.Column(db.Integer, db.ForeignKey("secoes_docx.id_secao"), nullable=False)
    posicao_na_secao = db.Column(db.Integer, nullable=False)
    tipo_posicao = db.Column(db.String(20), default="paragrafo")
    tipo_quebra = db.Column(db.String(50), nullable=False, default="page")
    forcar_nova_pagina = db.Column(db.Boolean, default=True)
    limpar_formatacao = db.Column(db.Boolean, default=False)
    contexto_anterior = db.Column(db.Text, nullable=True)
    contexto_posterior = db.Column(db.Text, nullable=True)
    secao = db.relationship("SecaoDOCX", back_populates="quebras")

    @property
    def descricao_tipo(self):
        """Descrição amigável do tipo de quebra."""
        map_tipos = {
            "page": "Quebra de página",
            "column": "Quebra de coluna",
            "textWrapping": "Quebra de texto",
        }
        return map_tipos.get(self.tipo_quebra, self.tipo_quebra)

    @property
    def e_quebra_visivel(self):
        """Retorna True se a quebra é visível no documento."""
        return self.tipo_quebra in ("page", "column")

    @property
    def posicao_relativa(self):
        """Retorna posição relativa formatada."""
        if self.tipo_posicao == "paragrafo":
            return f"Parágrafo {self.posicao_na_secao}"
        if self.tipo_posicao == "caractere":
            return f"Caractere {self.posicao_na_secao}"
        return f"Posição {self.posicao_na_secao}"

    def to_dict(self):
        """Converte para dicionário para serialização."""
        return {
            "id_quebra": self.id_quebra,
            "id_secao": self.id_secao,
            "posicao_na_secao": self.posicao_na_secao,
            "posicao_relativa": self.posicao_relativa,
            "tipo_quebra": self.tipo_quebra,
            "descricao_tipo": self.descricao_tipo,
            "forcar_nova_pagina": self.forcar_nova_pagina,
            "e_quebra_visivel": self.e_quebra_visivel,
        }
