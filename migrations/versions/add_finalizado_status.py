"""Adiciona status em_revisao e finalizado a dom_status_relatorios.

Revision ID: add_finalizado_status
Revises: 05ad77248612
Create Date: 2026-05-24 15:30:00.000000

Necessário para o fluxo de finalização do relatório (Fase 1 do merge
in-place): após a geração do DOCX final, o RelatorioProducao migra
para 'em_revisao' (durante revisão) ou 'finalizado' (após bloqueio).
Inserção idempotente — não falha se algum dos códigos já existir.
"""
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'add_finalizado_status'
down_revision = '05ad77248612'
branch_labels = None
depends_on = None


_NOVOS_STATUS = [
    ('em_revisao', 'Em Revisão', 2),
    ('finalizado', 'Finalizado', 3),
]


def upgrade():
    conn = op.get_bind()
    for codigo, descricao, ordem in _NOVOS_STATUS:
        existe = conn.execute(text(
            'SELECT id FROM dom_status_relatorios WHERE codigo = :codigo'
        ), {'codigo': codigo}).fetchone()
        if existe:
            continue
        conn.execute(text(
            'INSERT INTO dom_status_relatorios '
            '(codigo, descricao, ordem, ativo, criado_em) '
            'VALUES (:codigo, :descricao, :ordem, true, NOW())'
        ), {'codigo': codigo, 'descricao': descricao, 'ordem': ordem})


def downgrade():
    conn = op.get_bind()
    for codigo, _, _ in _NOVOS_STATUS:
        conn.execute(text(
            'DELETE FROM dom_status_relatorios WHERE codigo = :codigo'
        ), {'codigo': codigo})
