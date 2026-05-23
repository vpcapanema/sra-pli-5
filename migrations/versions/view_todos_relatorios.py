"""Cria VIEW para consolidar todos os relatórios do sistema."""

from alembic import op
from sqlalchemy import text

# revision identifiers
revision = 'view_todos_relatorios'
down_revision = 'make_relatorio_id_nullable'
branch_labels = None
depends_on = None


def upgrade():
    """Cria VIEW vw_todos_relatorios consolidando relatórios de produção e finalizados."""
    conn = op.get_bind()

    conn.execute(text("""
        CREATE OR REPLACE VIEW vw_todos_relatorios AS
        SELECT
            rp.id,
            'producao' as tipo_relatorio,
            rp.codigo_d20 as codigo,
            rp.titulo_curto as titulo,
            rp.numero_medicao,
            rp.mes_referencia,
            rp.ano_referencia,
            rp.periodo_inicio,
            rp.periodo_fim,
            rp.status_id,
            rp.criado_em as data_criacao,
            rp.versao_atual as versao,
            rp.criado_por,
            u.nome as criador_nome,
            ds.codigo as status_codigo,
            ds.descricao as status_descricao
        FROM relatorios_producao rp
        LEFT JOIN usuarios u ON rp.criado_por = u.id
        LEFT JOIN dom_status_relatorios ds ON rp.status_id = ds.id

        UNION ALL

        SELECT
            rf.id,
            'finalizado' as tipo_relatorio,
            rf.codigo,
            rf.titulo,
            rf.numero_medicao,
            rf.mes_referencia,
            rf.ano_referencia,
            rf.periodo_inicio,
            rf.periodo_fim,
            rf.status_id,
            rf.data_finalizacao as data_criacao,
            rf.versao,
            rf.finalizado_por as criado_por,
            u.nome as criador_nome,
            ds.codigo as status_codigo,
            ds.descricao as status_descricao
        FROM relatorios_finalizados rf
        LEFT JOIN usuarios u ON rf.finalizado_por = u.id
        LEFT JOIN dom_status_relatorios ds ON rf.status_id = ds.id

        ORDER BY data_criacao DESC;
    """))


def downgrade():
    """Remove VIEW vw_todos_relatorios."""
    conn = op.get_bind()
    conn.execute(text("DROP VIEW IF EXISTS vw_todos_relatorios;"))
