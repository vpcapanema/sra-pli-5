from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime


class AuditoriaMixin:
    criado_por = Column(Integer, nullable=True)
    criado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    atualizado_por = Column(Integer, nullable=True)
    atualizado_em = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
