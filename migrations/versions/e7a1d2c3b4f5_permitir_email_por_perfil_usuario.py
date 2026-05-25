"""permitir_email_por_perfil_usuario

Revision ID: e7a1d2c3b4f5
Revises: drop_conteudo_docx
Create Date: 2026-05-25 03:15:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'e7a1d2c3b4f5'
down_revision = 'drop_conteudo_docx'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.drop_constraint('usuarios_email_key', type_='unique')
        batch_op.create_unique_constraint(
            'uq_usuarios_email_perfil',
            ['email', 'perfil_id']
        )


def downgrade():
    with op.batch_alter_table('usuarios', schema=None) as batch_op:
        batch_op.drop_constraint(
            'uq_usuarios_email_perfil',
            type_='unique'
        )
        batch_op.create_unique_constraint(
            'usuarios_email_key',
            ['email']
        )
