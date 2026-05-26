"""Helpers para preencher colunas de auditoria (criado_por / atualizado_por).

Convencao do sistema (ver `app.models.mixins.AuditoriaMixin`):
- `criado_por` / `atualizado_por` recebem o id do usuario logado quando
  a operacao foi disparada por um request HTTP autenticado.
- Quando a operacao roda fora de request (jobs, scripts, sincronizacao
  automatica, clonagem em background), o valor cai para `None` —
  registros assim representam acoes do "sistema".
"""
from __future__ import annotations

from typing import Optional

from flask import has_request_context
from flask_login import current_user


def usuario_atual_id() -> Optional[int]:
    """Devolve o id do usuario logado ou `None` se nao houver request
    autenticado.

    Tolerante: qualquer falha em ler o `current_user` (proxy fora de
    contexto, sessao corrompida) cai silenciosamente para `None`,
    permitindo que o servico continue mesmo em execucoes em background.
    """
    try:
        if not has_request_context():
            return None
        if not current_user or not current_user.is_authenticated:
            return None
        return int(current_user.id)
    except Exception:  # pragma: no cover  # pylint: disable=broad-except
        return None
