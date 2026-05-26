from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime


class AuditoriaMixin:
    """Mixin de auditoria para entidades persistidas.

    Convencoes:
      - `criado_por` / `atualizado_por`: id do usuario responsavel pela
        operacao. Pode ser NULL quando a operacao foi disparada pelo
        proprio sistema (ex.: clonagem automatica de capitulos a partir
        de um relatorio finalizado, sincronizacao em background, jobs
        de migracao). Na UI, registros com `criado_por IS NULL` devem
        ser apresentados como "Sistema" em vez de "desconhecido".
      - `criado_em`: preenchido automaticamente na primeira insercao.
      - `atualizado_em`: atualizado automaticamente em qualquer UPDATE
        via `onupdate` do SQLAlchemy.

    Datas usam UTC explicitamente (steering rule: nunca `datetime.utcnow()`).
    """
    criado_por = Column(Integer, nullable=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    atualizado_por = Column(Integer, nullable=True)
    atualizado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
