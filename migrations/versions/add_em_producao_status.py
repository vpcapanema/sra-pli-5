"""Adiciona status em_producao a dom_status_relatorios

Revision ID: add_em_producao_status
Revises: view_todos_relatorios
Create Date: 2026-05-23 15:11:00.000000

"""
from alembic import op
from sqlalchemy import text

# revision identifiers
revision = 'add_em_producao_status'
down_revision = 'view_todos_relatorios'
branch_labels = None
depends_on = None


def upgrade():
    """Adiciona status em_producao se não existir."""
    conn = op.get_bind()
    
    # Verificar se o status já existe
    result = conn.execute(text(
        "SELECT id FROM dom_status_relatorios WHERE codigo = 'em_producao'"
    )).fetchone()
    
    if not result:
        conn.execute(text("""
            INSERT INTO dom_status_relatorios (codigo, descricao, ordem, ativo, criado_em)
            VALUES ('em_producao', 'Em Produção', 1, true, NOW())
        """))
        print("Status 'em_producao' adicionado.")
    else:
        print("Status 'em_producao' já existe.")


def downgrade():
    """Remove status em_producao."""
    conn = op.get_bind()
    conn.execute(text(
        "DELETE FROM dom_status_relatorios WHERE codigo = 'em_producao'"
    ))
