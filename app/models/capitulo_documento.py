from app import db
from app.models.mixins import AuditoriaMixin
from sqlalchemy import event


# Sinonimos historicos -> valor canonico em dominios.tipo='status_capitulo'.
# Usados pelo listener abaixo para nao quebrar codigo legado que ainda
# escreve 'reprovado', 'finalizado', 'enviado_revisao' diretamente.
_SINONIMOS_STATUS_CAPITULO = {
    'reprovado': 'rejeitado',
    'enviado_revisao': 'aguardando_aprovacao',
    'finalizado': 'aprovado',
}


class CapituloDocumento(db.Model, AuditoriaMixin):
    __tablename__ = 'capitulos_documento'

    id_capitulo_documento = db.Column(db.Integer, primary_key=True)
    id_relatorio = db.Column(
        db.Integer,
        db.ForeignKey('relatorios_producao.id'),
        nullable=False
    )
    id_secao_inicio = db.Column(
        db.Integer,
        db.ForeignKey('secoes_docx.id_secao'),
        nullable=True,
        comment="ID da seção DOCX onde o capítulo começa"
    )
    id_secao_fim = db.Column(
        db.Integer,
        db.ForeignKey('secoes_docx.id_secao'),
        nullable=True,
        comment="ID da seção DOCX onde o capítulo termina (se abrange múltiplas seções)"
    )
    id_capitulo_pai = db.Column(
        db.Integer,
        db.ForeignKey('capitulos_documento.id_capitulo_documento'),
        nullable=True
    )
    id_usuario_responsavel = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id'),
        nullable=True
    )
    ordem_capitulo = db.Column(db.Integer, nullable=False)
    nome_capitulo = db.Column(db.String(200), nullable=True)
    titulo_capitulo = db.Column(db.String(300), nullable=False)
    indice_capitulo = db.Column(db.String(50), nullable=True)
    nivel_capitulo = db.Column(db.Integer, nullable=False, default=1)
    tipo_elemento = db.Column(
        db.String(50),
        nullable=False,
        default='textual',
        comment="Tipo de elemento: pre_textual, textual, pos_textual"
    )
    classificacao = db.Column(
        db.String(50),
        nullable=True,
        comment="Classificação do capítulo: textual, pre_textual, pos_textual, anexo, apendice"
    )
    prefixo_indice = db.Column(
        db.String(10),
        nullable=True,
        comment="Prefixo de numeração (ex: 'I', '1', 'A')"
    )
    indice_esperado = db.Column(
        db.Integer,
        nullable=True,
        comment="Índice esperado do capítulo para match por contexto (ex: 5 para capítulo 5)"
    )
    estilo_docx = db.Column(
        db.String(100),
        nullable=True,
        comment="Estilo DOCX do título (ex: 'Heading 1', 'Título 1')"
    )
    docx_bookmark = db.Column(
        db.String(200),
        nullable=True,
        comment="Marcador (bookmark) no DOCX para referências cruzadas"
    )
    # Status editorial do capitulo. Mantemos a coluna VARCHAR como
    # cache/legado mas a fonte de verdade passou a ser
    # `status_capitulo_id` (FK -> dominios). O setter de
    # `status_capitulo` (via property abaixo) mantem ambos sincronizados
    # quando a aplicacao escreve a string. Valores validos vivem em
    # `dominios.tipo='status_capitulo'`.
    status_capitulo = db.Column(
        db.String(50), nullable=False, default='em_edicao'
    )
    status_capitulo_id = db.Column(
        db.Integer,
        db.ForeignKey('dominios.id_dominio'),
        nullable=True,
        index=True,
    )
    # `conteudo_docx` removido pos-Fase 1 (migration drop_conteudo_docx).
    # O conteudo de cada capitulo agora vive no DOCX em producao
    # (`RelatorioProducao.caminho_template`), atualizado in-place pelo
    # `servico_merge_docx`. Use `extrair_capitulo_como_docx` para obter
    # o DOCX de um capitulo isolado.
    observacao_coordenador = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True)

    relatorio = db.relationship(
        'RelatorioProducao', back_populates='capitulos'
    )
    secao_inicio = db.relationship(
        'SecaoDOCX', foreign_keys=[id_secao_inicio], back_populates='capitulos'
    )
    secao_fim = db.relationship(
        'SecaoDOCX', foreign_keys=[id_secao_fim]
    )
    responsavel = db.relationship(
        'Usuario', foreign_keys=[id_usuario_responsavel]
    )
    capitulo_pai = db.relationship(
        'CapituloDocumento',
        remote_side=[id_capitulo_documento],
        backref='subcapitulos'
    )
    elementos = db.relationship('ElementoConteudo', back_populates='capitulo')

    # Relacionamento com a tabela `dominios` para o status editorial.
    # Conveniencia: `cap.status_dominio.descricao` para a label
    # apresentada na UI sem precisar de consulta extra.
    status_dominio = db.relationship(
        'Dominio',
        foreign_keys=[status_capitulo_id],
        lazy='joined',
    )

    @property
    def descricao_status(self):
        """Label amigavel do status, vinda de `dominios.descricao`.

        Fallback para o codigo (ou 'em edição') quando o relacionamento
        nao foi carregado / nao existe ainda.
        """
        if self.status_dominio and self.status_dominio.descricao:
            return self.status_dominio.descricao
        codigo = self.status_capitulo or 'em_edicao'
        return codigo.replace('_', ' ').capitalize()

    # ------------------------------------------------------------------
    # Propriedades calculadas para conceito endurecido de capítulos
    # ------------------------------------------------------------------

    @property
    def indice_completo(self):
        """Índice completo com prefixo quando aplicável."""
        if self.classificacao == 'anexo':
            return f"ANEXO_{self.indice_capitulo}" if self.indice_capitulo else "ANEXO"
        elif self.classificacao == 'apendice':
            return f"APENDICE_{self.indice_capitulo}" if self.indice_capitulo else "APENDICE"
        return self.indice_capitulo or ""

    @property
    def numero_capitulo_esperado(self):
        """Retorna o número do capítulo para match por contexto.

        Prioridade:
        1. indice_esperado (campo explícito)
        2. Extrair de indice_capitulo (ex: "5" de "5.1")
        3. None se não conseguir determinar
        """
        import re

        # 1. Usar indice_esperado se disponível
        if self.indice_esperado is not None:
            return self.indice_esperado

        # 2. Tentar extrair de indice_capitulo
        if self.indice_capitulo:
            match = re.match(r'^(\d+)', self.indice_capitulo)
            if match:
                return int(match.group(1))

        # 3. Não conseguiu determinar
        return None

    @property
    def e_capitulo(self):
        """Retorna True se for um capítulo de primeiro nível (textual)."""
        return (self.nivel_capitulo == 1 and
                self.tipo_elemento == 'textual' and
                self.classificacao in (None, 'textual'))

    @property
    def e_subcapitulo(self):
        """Retorna True se for um subcapítulo (textual, com pai)."""
        return (self.nivel_capitulo >= 2 and
                self.tipo_elemento == 'textual' and
                self.id_capitulo_pai is not None and
                self.classificacao in (None, 'textual'))

    @property
    def e_anexo(self):
        """Retorna True se for anexo."""
        return (self.tipo_elemento == 'pos_textual' and
                self.classificacao == 'anexo')

    @property
    def e_apendice(self):
        """Retorna True se for apêndice."""
        return (self.tipo_elemento == 'pos_textual' and
                self.classificacao == 'apendice')

    @property
    def e_anexo_ou_apendice(self):
        """Retorna True se for anexo ou apêndice."""
        return self.e_anexo or self.e_apendice

    @property
    def tipo_conceitual(self):
        """Retorna o tipo conceitual do capítulo."""
        if self.e_capitulo:
            return 'capitulo'
        elif self.e_subcapitulo:
            return 'subcapitulo'
        elif self.e_anexo:
            return 'anexo'
        elif self.e_apendice:
            return 'apendice'
        elif self.tipo_elemento == 'pre_textual':
            return 'pre_textual'
        else:
            return 'outro'

    # ------------------------------------------------------------------
    # Propriedades relacionadas a seções DOCX
    # ------------------------------------------------------------------

    @property
    def abrange_multiplas_secoes(self):
        """Retorna True se o capítulo abrange mais de uma seção DOCX."""
        return self.id_secao_fim is not None and self.id_secao_fim != self.id_secao_inicio

    @property
    def numero_secoes(self):
        """Retorna o número de seções que o capítulo abrange."""
        if not self.abrange_multiplas_secoes:
            return 1

        # Em implementação real, calcularia baseado em ordem_secao
        return 1  # Placeholder

    @property
    def tem_quebra_secao_importante(self):
        """Retorna True se o capítulo começa com quebra de seção importante."""
        if self.secao_inicio and self.secao_inicio.e_quebra_importante:
            return True
        return False

    @property
    def propriedades_secao_inicio(self):
        """Retorna propriedades da seção de início."""
        if self.secao_inicio:
            return {
                'tipo': self.secao_inicio.tipo_secao,
                'orientacao': self.secao_inicio.orientacao,
                'colunas': self.secao_inicio.colunas,
                'reinicia_numero_pagina': self.secao_inicio.reiniciar_numero_pagina
            }
        return {}

    # ------------------------------------------------------------------
    # Validações
    # ------------------------------------------------------------------

    def validar_estrutura(self):
        """Valida a estrutura conceitual do capítulo."""
        erros = []

        # Anexo/Apêndice (pós-textual) - regras especiais
        if self.tipo_elemento == 'pos_textual':
            if self.classificacao not in ('anexo', 'apendice', None):
                erros.append("Classificação inválida para conteúdo pós-textual")
            # Anexos/apêndices podem ter nível 1 e não precisam ser 'textual'
            return erros

        # Conteúdo textual (capítulos e subcapítulos)
        if self.tipo_elemento != 'textual':
            erros.append("Conteúdo textual deve ter tipo_elemento = 'textual'")

        # Capítulo (nível 1)
        if self.nivel_capitulo == 1:
            if self.id_capitulo_pai is not None:
                erros.append("Capítulo de nível 1 não pode ter pai")
            if self.classificacao not in (None, 'textual'):
                erros.append("Capítulo de nível 1 deve ter classificação 'textual' ou None")

        # Subcapítulo (nível ≥ 2)
        elif self.nivel_capitulo >= 2:
            if self.id_capitulo_pai is None:
                erros.append("Subcapítulo deve ter um capítulo pai")
            if self.classificacao not in (None, 'textual'):
                erros.append("Subcapítulo deve ter classificação 'textual' ou None")

        return erros


@event.listens_for(CapituloDocumento.status_capitulo, 'set',
                   propagate=True)
def _sync_status_capitulo_id(target, value, _oldvalue, _initiator):
    """Sincroniza `status_capitulo_id` quando o codigo string e escrito.

    Idempotente e tolerante: se o valor nao for um dos canonicos nem
    um sinonimo conhecido, mantem o id atual e devolve o valor sem
    interferir (deixa o backend rejeitar via outras validacoes).

    Tambem propaga a mudanca para `envios_conteudo.status_capitulo_id`
    de todos os envios que apontam para este capitulo, mantendo o
    espelho consistente sem precisar de trigger de banco.
    """
    if not value:
        return value
    canonico = _SINONIMOS_STATUS_CAPITULO.get(value, value)
    # Importacao tardia para evitar ciclo no carregamento dos modelos.
    from app.models.dominio import Dominio  # noqa: C0415
    try:
        dom = Dominio.query.filter_by(
            tipo='status_capitulo', valor=canonico
        ).first()
    except Exception:  # pragma: no cover  # pylint: disable=broad-except
        dom = None
    if dom is None:
        return value

    target.status_capitulo_id = dom.id_dominio

    # Espelhar para envios que tenham este capitulo como destino.
    # Tolerante: ignora se a sessao/banco nao estiver disponivel
    # (ex.: durante criacao em memoria sem flush ainda).
    try:
        from app.models.envio_conteudo import EnvioConteudo  # noqa: C0415

        if target.id_capitulo_documento:
            EnvioConteudo.query.filter_by(
                id_capitulo_destino=target.id_capitulo_documento
            ).update(
                {'status_capitulo_id': dom.id_dominio},
                synchronize_session=False,
            )
    except Exception:  # pragma: no cover  # pylint: disable=broad-except
        pass

    return value
