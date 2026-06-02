from sqlalchemy import event

from app import db
from app.models.mixins import AuditoriaMixin


# Mapeamento da coluna VARCHAR legada `status_envio` (em_previa /
# importado / rejeitado / pendente) para os codigos canonicos do
# tipo='status_envio_conteudo' em `dominios`. Usado pelo listener
# abaixo para manter `status_envio_id` em sincronia quando codigo
# legado escrever a string.
_MAPA_STATUS_ENVIO_LEGADO = {
    'em_previa':  'em_preparacao',
    'rejeitado':  'em_preparacao',
    'importado':  'enviado',
    'pendente':   'aguardando_envio',
    # Codigos canonicos passam direto:
    'notificado':       'notificado',
    'aguardando_envio': 'aguardando_envio',
    'em_preparacao':    'em_preparacao',
    'enviado':          'enviado',
}


class EnvioConteudo(db.Model, AuditoriaMixin):
    __tablename__ = 'envios_conteudo'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    id_envio_conteudo = db.Column(db.Integer, primary_key=True)
    id_relatorio = db.Column(
        db.Integer,
        db.ForeignKey('relatorios_producao.id'),
        nullable=False
    )
    id_usuario = db.Column(
        db.Integer,
        db.ForeignKey('usuarios.id'),
        nullable=False
    )
    nome_arquivo = db.Column(db.String(300), nullable=False)
    caminho_arquivo = db.Column(db.String(500), nullable=False)

    # `status_envio` (VARCHAR) — coluna LEGADA, mantida como cache
    # para nao quebrar codigo antigo que filtra/escreve por string.
    # A fonte de verdade passou a ser `status_envio_id` (FK ->
    # `dominios.tipo='status_envio_conteudo'`), que descreve o ciclo
    # do AUTOR em relacao ao envio (notificado / aguardando_envio /
    # em_preparacao / enviado).
    status_envio = db.Column(db.String(50), nullable=False, default='pendente')
    status_envio_id = db.Column(
        db.Integer,
        db.ForeignKey('dominios.id_dominio'),
        nullable=True,
        index=True,
    )

    # Capitulo destino do upload — fixo no momento do envio (autor
    # acessa via /capitulo/<id>/upload). Usado pelo merge in-place
    # para localizar o range correto no DOCX em producao.
    id_capitulo_destino = db.Column(
        db.Integer,
        db.ForeignKey('capitulos_documento.id_capitulo_documento'),
        nullable=True,
    )
    # Espelho do estado editorial do capitulo destino
    # (FK -> `dominios.tipo='status_capitulo'`). Permite filtros e
    # dashboards sem precisar fazer JOIN com `capitulos_documento`.
    # Eh sincronizado automaticamente pelo listener abaixo quando
    # `id_capitulo_destino` e atribuido.
    status_capitulo_id = db.Column(
        db.Integer,
        db.ForeignKey('dominios.id_dominio'),
        nullable=True,
        index=True,
    )

    # Sugestoes extraidas do DOCX upado (titulos, figuras, tabelas).
    sugestoes_json = db.Column(db.Text, nullable=True)

    relatorio = db.relationship(
        'RelatorioProducao', back_populates='envios'
    )
    capitulo_destino = db.relationship(
        'CapituloDocumento', foreign_keys=[id_capitulo_destino]
    )
    criador = db.relationship(
        'Usuario', foreign_keys=[id_usuario]
    )
    previsualizacoes = db.relationship(
        'PrevisualizacaoConteudo', back_populates='envio'
    )

    # Acesso conveniente aos dominios (read-only via relationship).
    status_envio_dominio = db.relationship(
        'Dominio',
        foreign_keys=[status_envio_id],
        lazy='joined',
    )
    status_capitulo_dominio = db.relationship(
        'Dominio',
        foreign_keys=[status_capitulo_id],
        lazy='joined',
    )

    # ------------------------------------------------------------------
    # Helpers para a UI.
    # ------------------------------------------------------------------

    @property
    def descricao_status_envio(self):
        """Label amigavel para o ciclo de envio do AUTOR.

        Lida da `dominios.descricao` quando o relacionamento esta
        carregado; fallback para o codigo legado em VARCHAR.
        """
        if self.status_envio_dominio and self.status_envio_dominio.descricao:
            return self.status_envio_dominio.descricao
        codigo = self.status_envio or 'pendente'
        return codigo.replace('_', ' ').capitalize()

    @property
    def descricao_status_capitulo(self):
        """Label amigavel do estado editorial do capitulo destino."""
        if (self.status_capitulo_dominio
                and self.status_capitulo_dominio.descricao):
            return self.status_capitulo_dominio.descricao
        if self.capitulo_destino:
            return self.capitulo_destino.descricao_status
        return '—'

    # Rotulos curtos (apenas o codigo formatado), uteis em colunas
    # estreitas onde a descricao completa do dominio nao cabe.
    @property
    def rotulo_status_envio(self):
        codigo = self.codigo_status_envio
        return codigo.replace('_', ' ').capitalize() if codigo else '—'

    @property
    def rotulo_status_capitulo(self):
        codigo = self.codigo_status_capitulo
        return codigo.replace('_', ' ').capitalize() if codigo else '—'

    @property
    def codigo_status_envio(self):
        """Codigo canonico (ex.: 'aguardando_envio', 'enviado'). Util
        para gerar classes CSS de badge e checks de transicao."""
        if self.status_envio_dominio and self.status_envio_dominio.valor:
            return self.status_envio_dominio.valor
        antigo = (self.status_envio or '').strip()
        return _MAPA_STATUS_ENVIO_LEGADO.get(antigo, 'aguardando_envio')

    @property
    def codigo_status_capitulo(self):
        """Codigo canonico do capitulo destino."""
        if (self.status_capitulo_dominio
                and self.status_capitulo_dominio.valor):
            return self.status_capitulo_dominio.valor
        if self.capitulo_destino:
            return self.capitulo_destino.status_capitulo or 'em_edicao'
        return None


# ----------------------------------------------------------------------
# Listeners de sincronizacao.
# ----------------------------------------------------------------------

@event.listens_for(EnvioConteudo.status_envio, 'set', propagate=True)
def _sync_status_envio_id(target, value, _oldvalue, _initiator):
    """Quando `status_envio` (string) e escrito, mantem
    `status_envio_id` (FK -> dominios) em sincronia conforme
    `_MAPA_STATUS_ENVIO_LEGADO`.

    Tolerante: valor desconhecido nao altera o id atual.
    """
    if not value:
        return value
    canonico = _MAPA_STATUS_ENVIO_LEGADO.get(value)
    if canonico is None:
        return value
    from app.models.dominio import Dominio  # noqa: C0415
    try:
        dom = Dominio.query.filter_by(
            tipo='status_envio_conteudo', valor=canonico
        ).first()
    except Exception:  # pragma: no cover  # pylint: disable=broad-except
        dom = None
    if dom is not None:
        target.status_envio_id = dom.id_dominio
    return value


@event.listens_for(EnvioConteudo.id_capitulo_destino, 'set',
                   propagate=True)
def _sync_status_capitulo_id(target, value, _oldvalue, _initiator):
    """Quando o capitulo destino do envio e definido (ou alterado),
    espelha `status_capitulo_id` a partir do capitulo. Permite que a
    tabela `envios_conteudo` seja consultada diretamente por status
    do capitulo sem JOIN.
    """
    if not value:
        return value
    from app.models.capitulo_documento import CapituloDocumento  # noqa: C0415
    try:
        cap = CapituloDocumento.query.get(value)
    except Exception:  # pragma: no cover  # pylint: disable=broad-except
        cap = None
    if cap is not None and cap.status_capitulo_id is not None:
        target.status_capitulo_id = cap.status_capitulo_id
    return value
