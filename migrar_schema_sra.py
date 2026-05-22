"""
Migra schema e dados do banco remoto sra_h66q para o banco local sra_pli.
Substitui:
  - usuarios -> sra.usuarios (schema remoto)
  - versoes_trabalho -> sra.relatorios_producao
  - relatorios_base -> sra.relatorios_finalizados
"""
import psycopg
import sys

sys.stdout.reconfigure(encoding='utf-8')

RENDER_URL = (
    "postgresql://sra:eJmMmQTdsNENzrKoB00RLOM2f3uzkyK8"
    "@dpg-d7ludlgg4nts739fjijg-a.virginia-postgres.render.com:5432/sra_h66q"
)
LOCAL_URL = "postgresql://sra_admin:sra2026@localhost:5433/sra_pli"


def run_migration():
    render_conn = psycopg.connect(RENDER_URL)
    render_cur = render_conn.cursor()
    local_conn = psycopg.connect(LOCAL_URL)
    local_cur = local_conn.cursor()

    try:
        # ============================================================
        # 1. CRIAR TABELAS DE DOMINIO
        # ============================================================
        print("\n=== 1. Criando tabelas de dominio ===")

        local_cur.execute("""
            CREATE TABLE IF NOT EXISTS dom_perfis_usuario (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR(50) NOT NULL UNIQUE,
                descricao VARCHAR(100) NOT NULL,
                nivel_acesso INTEGER DEFAULT 0,
                ativo BOOLEAN DEFAULT TRUE NOT NULL,
                criado_em TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        local_cur.execute("""
            CREATE TABLE IF NOT EXISTS dom_status_relatorios (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR(50) NOT NULL UNIQUE,
                descricao VARCHAR(100) NOT NULL,
                ordem INTEGER DEFAULT 0,
                ativo BOOLEAN DEFAULT TRUE NOT NULL,
                criado_em TIMESTAMPTZ DEFAULT NOW()
            )
        """)

        # Popular dominios
        render_cur.execute("SELECT * FROM dominios.dom_perfis_usuario")
        perfis = render_cur.fetchall()
        for p in perfis:
            local_cur.execute(
                "INSERT INTO dom_perfis_usuario (id, codigo, descricao, nivel_acesso, ativo, criado_em) "
                "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
                (p[0], p[1], p[2], p[3], p[4], p[5])
            )

        render_cur.execute("SELECT * FROM dominios.dom_status_relatorios")
        status_rows = render_cur.fetchall()
        for s in status_rows:
            local_cur.execute(
                "INSERT INTO dom_status_relatorios (id, codigo, descricao, ordem, ativo, criado_em) "
                "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
                (s[0], s[1], s[2], s[3], s[4], s[5])
            )
        print(f"  Perfis: {len(perfis)}, Status: {len(status_rows)}")

        # ============================================================
        # 2. DROPAR FKs que apontam para tabelas antigas
        # ============================================================
        print("\n=== 2. Dropando FKs dependentes ===")

        fks_to_drop = [
            # FKs para usuarios
            ("notificacoes", "notificacoes_id_usuario_destino_fkey"),
            ("registros_auditoria", "registros_auditoria_id_usuario_fkey"),
            ("envios_conteudo", "envios_conteudo_id_usuario_fkey"),
            ("revisoes", "revisoes_id_usuario_coordenador_fkey"),
            ("capitulos_documento", "capitulos_documento_id_usuario_responsavel_fkey"),
            # FK para relatorios_base
            ("versoes_trabalho", "versoes_trabalho_id_relatorio_base_fkey"),
            # FKs para versoes_trabalho
            ("bloqueios", "bloqueios_id_versao_trabalho_fkey"),
            ("capitulos_documento", "capitulos_documento_id_versao_trabalho_fkey"),
            ("envios_conteudo", "envios_conteudo_id_versao_trabalho_fkey"),
            ("revisoes", "revisoes_id_versao_trabalho_fkey"),
        ]

        for table, fk_name in fks_to_drop:
            try:
                local_cur.execute(
                    f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {fk_name}"
                )
                print(f"  DROP FK {fk_name} from {table}")
            except Exception as e:
                print(f"  [SKIP] {fk_name}: {e}")

        # ============================================================
        # 3. DROPAR TABELAS ANTIGAS (em ordem segura)
        # ============================================================
        print("\n=== 3. Dropando tabelas antigas ===")

        tables_to_drop = [
            "usuarios",
            "relatorios_base",
            "versoes_trabalho",
        ]
        for t in tables_to_drop:
            try:
                local_cur.execute(f"DROP TABLE IF EXISTS {t} CASCADE")
                print(f"  DROP TABLE {t}")
            except Exception as e:
                print(f"  [SKIP] {t}: {e}")

        # ============================================================
        # 4. CRIAR NOVAS TABELAS
        # ============================================================
        print("\n=== 4. Criando novas tabelas ===")

        local_cur.execute("""
            CREATE TABLE usuarios (
                id SERIAL PRIMARY KEY,
                nome VARCHAR(200) NOT NULL,
                email VARCHAR(200) NOT NULL UNIQUE,
                email_secundario VARCHAR(200),
                nome_de_usuario VARCHAR(100) NOT NULL UNIQUE,
                senha_hash VARCHAR(256) NOT NULL,
                perfil_id INTEGER NOT NULL REFERENCES dom_perfis_usuario(id),
                ativo BOOLEAN DEFAULT TRUE NOT NULL,
                notificacoes_ativas BOOLEAN DEFAULT TRUE NOT NULL,
                email_verificado_em TIMESTAMPTZ,
                token_convite VARCHAR(128) UNIQUE,
                token_recuperacao VARCHAR(128) UNIQUE,
                token_expiracao TIMESTAMPTZ,
                criado_em TIMESTAMPTZ DEFAULT NOW() NOT NULL,
                atualizado_em TIMESTAMPTZ,
                desativado_em TIMESTAMPTZ
            )
        """)
        print("  CREATE TABLE usuarios")

        local_cur.execute("""
            CREATE TABLE relatorios_producao (
                id SERIAL PRIMARY KEY,
                codigo_d20 VARCHAR(20) NOT NULL DEFAULT 'D-20',
                numero_medicao INTEGER NOT NULL,
                mes_referencia DATE NOT NULL,
                periodo_inicio DATE NOT NULL,
                periodo_fim DATE NOT NULL,
                titulo_curto VARCHAR(300),
                status_id INTEGER NOT NULL REFERENCES dom_status_relatorios(id),
                criado_por INTEGER NOT NULL REFERENCES usuarios(id),
                criado_em TIMESTAMPTZ DEFAULT NOW() NOT NULL,
                atualizado_em TIMESTAMPTZ,
                ano_referencia INTEGER,
                versao_atual VARCHAR(20) NOT NULL DEFAULT 'R00',
                bloqueio_edicao BOOLEAN DEFAULT FALSE NOT NULL,
                UNIQUE (codigo_d20, numero_medicao)
            )
        """)
        print("  CREATE TABLE relatorios_producao")

        local_cur.execute("""
            CREATE TABLE relatorios_finalizados (
                id SERIAL PRIMARY KEY,
                relatorio_id INTEGER NOT NULL REFERENCES relatorios_producao(id),
                snapshot_conteudo JSONB NOT NULL,
                artefato_docx BYTEA NOT NULL,
                nome_arquivo VARCHAR(300) NOT NULL,
                finalizado_por INTEGER NOT NULL REFERENCES usuarios(id),
                data_finalizacao TIMESTAMPTZ DEFAULT NOW() NOT NULL,
                checksum_docx VARCHAR(64),
                revisao_id INTEGER,
                codigo VARCHAR(20),
                titulo VARCHAR(300),
                mes_referencia DATE,
                ano_referencia INTEGER,
                periodo_inicio DATE,
                periodo_fim DATE,
                numero_medicao INTEGER,
                versao VARCHAR(20) NOT NULL DEFAULT 'R00',
                sincronizado_em TIMESTAMPTZ DEFAULT NOW() NOT NULL
            )
        """)
        print("  CREATE TABLE relatorios_finalizados")

        # ============================================================
        # 5. MIGRAR DADOS
        # ============================================================
        print("\n=== 5. Migrando dados ===")

        # Usuarios
        render_cur.execute(
            "SELECT id, nome, email, email_secundario, senha_hash, perfil_id, "
            "ativo, notificacoes_ativas, email_verificado_em, token_convite, "
            "token_recuperacao, token_expiracao, criado_em, atualizado_em, desativado_em "
            "FROM sra.usuarios ORDER BY id"
        )
        usuarios = render_cur.fetchall()
        inseridos = 0
        ignorados = 0
        emails_vistos = set()
        for u in usuarios:
            email = u[2]
            if email in emails_vistos:
                ignorados += 1
                continue
            emails_vistos.add(email)
            # Gerar nome_de_usuario a partir do email
            nome_de_usuario = (email or f"user_{u[0]}").split('@')[0].replace('.', '_')
            try:
                local_cur.execute(
                    "INSERT INTO usuarios (id, nome, email, email_secundario, nome_de_usuario, senha_hash, "
                    "perfil_id, ativo, notificacoes_ativas, email_verificado_em, token_convite, "
                    "token_recuperacao, token_expiracao, criado_em, atualizado_em, desativado_em) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (u[0], u[1], u[2], u[3], nome_de_usuario, u[4], u[5], u[6], u[7], u[8], u[9], u[10], u[11], u[12], u[13], u[14])
                )
                inseridos += 1
            except psycopg.errors.UniqueViolation:
                local_conn.rollback()
                ignorados += 1
        print(f"  Usuarios: {inseridos} inseridos, {ignorados} ignorados")

        # Relatorios producao
        render_cur.execute(
            "SELECT id, codigo_d20, numero_medicao, mes_referencia, periodo_inicio, periodo_fim, "
            "titulo_curto, status_id, criado_por, criado_em, atualizado_em, ano_referencia, "
            "versao_atual, bloqueio_edicao FROM sra.relatorios_producao ORDER BY id"
        )
        rels = render_cur.fetchall()
        for r in rels:
            local_cur.execute(
                "INSERT INTO relatorios_producao (id, codigo_d20, numero_medicao, mes_referencia, "
                "periodo_inicio, periodo_fim, titulo_curto, status_id, criado_por, criado_em, "
                "atualizado_em, ano_referencia, versao_atual, bloqueio_edicao) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (id) DO NOTHING",
                r
            )
        print(f"  Relatorios producao: {len(rels)}")

        # Relatorios finalizados
        render_cur.execute(
            "SELECT id, relatorio_id, snapshot_conteudo, artefato_docx, nome_arquivo, "
            "finalizado_por, data_finalizacao, checksum_docx, revisao_id, codigo, titulo, "
            "mes_referencia, ano_referencia, periodo_inicio, periodo_fim, numero_medicao, "
            "versao, sincronizado_em FROM sra.relatorios_finalizados ORDER BY id"
        )
        fins = render_cur.fetchall()
        for f in fins:
            local_cur.execute(
                "INSERT INTO relatorios_finalizados (id, relatorio_id, snapshot_conteudo, "
                "artefato_docx, nome_arquivo, finalizado_por, data_finalizacao, checksum_docx, "
                "revisao_id, codigo, titulo, mes_referencia, ano_referencia, periodo_inicio, "
                "periodo_fim, numero_medicao, versao, sincronizado_em) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (id) DO NOTHING",
                f
            )
        print(f"  Relatorios finalizados: {len(fins)}")

        # ============================================================
        # 6. RESEQUENCIAR
        # ============================================================
        print("\n=== 6. Resequenciando ===")
        for seq, table, pk in [
            ("usuarios_id_seq", "usuarios", "id"),
            ("relatorios_producao_id_seq", "relatorios_producao", "id"),
            ("relatorios_finalizados_id_seq", "relatorios_finalizados", "id"),
        ]:
            try:
                local_cur.execute(
                    f"SELECT setval('{seq}', COALESCE((SELECT MAX({pk}) FROM {table}), 1), true)"
                )
                print(f"  {seq} atualizado")
            except Exception as e:
                print(f"  [SKIP] {seq}: {e}")

        # ============================================================
        # 7. RECRIAR FKs nas tabelas dependentes
        # ============================================================
        print("\n=== 7. Recriando FKs ===")

        # Mapeamento das FKs antigas para novas:
        # usuarios.id_usuario -> usuarios.id
        # versoes_trabalho.id_versao_trabalho -> relatorios_producao.id
        # relatorios_base.id_relatorio_base -> relatorios_finalizados.id (mas ninguem aponta direto agora?)

        new_fks = [
            ("notificacoes", "id_usuario_destino", "usuarios", "id"),
            ("registros_auditoria", "id_usuario", "usuarios", "id"),
            ("envios_conteudo", "id_usuario", "usuarios", "id"),
            ("revisoes", "id_usuario_coordenador", "usuarios", "id"),
            ("capitulos_documento", "id_usuario_responsavel", "usuarios", "id"),
            ("bloqueios", "id_versao_trabalho", "relatorios_producao", "id"),
            ("capitulos_documento", "id_versao_trabalho", "relatorios_producao", "id"),
            ("envios_conteudo", "id_versao_trabalho", "relatorios_producao", "id"),
            ("revisoes", "id_versao_trabalho", "relatorios_producao", "id"),
        ]

        for tbl, col, ref_tbl, ref_col in new_fks:
            fk_name = f"fk_{tbl}_{col}_{ref_tbl}"
            try:
                local_cur.execute(
                    f"ALTER TABLE {tbl} ADD CONSTRAINT {fk_name} "
                    f"FOREIGN KEY ({col}) REFERENCES {ref_tbl}({ref_col})"
                )
                print(f"  ADD FK {fk_name}")
            except Exception as e:
                print(f"  [SKIP] {fk_name}: {e}")

        local_conn.commit()
        print("\n=== MIGRACAO CONCLUIDA COM SUCESSO ===")

    except Exception as e:
        local_conn.rollback()
        print(f"\n=== ERRO NA MIGRACAO: {e} ===")
        raise

    finally:
        render_conn.close()
        local_conn.close()


if __name__ == "__main__":
    run_migration()
