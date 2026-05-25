"""Drop coluna conteudo_docx de capitulos_documento.

Revision ID: drop_conteudo_docx
Revises: add_finalizado_status
Create Date: 2026-05-24 15:50:00.000000

Pos-Fase 1 do merge in-place: o conteudo de cada capitulo agora vive
no DOCX em producao (`RelatorioProducao.caminho_template`). A coluna
`conteudo_docx` (LargeBinary) deixa de ser a fonte da verdade e e
removida para economizar espaco e evitar dessincronizacao.

Downgrade recria a coluna como nullable=True (sem dados — os bytes
historicos sao perdidos no downgrade).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'drop_conteudo_docx'
down_revision = 'add_finalizado_status'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
        'capitulos_documento', schema=None
    ) as batch_op:
        batch_op.drop_column('conteudo_docx')


def downgrade():
    with op.batch_alter_table(
        'capitulos_documento', schema=None
    ) as batch_op:
        batch_op.add_column(
            sa.Column('conteudo_docx', sa.LargeBinary(), nullable=True)
        )
