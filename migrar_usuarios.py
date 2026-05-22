"""Migra usuários do banco Render (sra_h66q, esquema sra) para o PostgreSQL local."""
import psycopg

RENDER_URL = (
    "postgresql://sra:eJmMmQTdsNENzrKoB00RLOM2f3uzkyK8"
    "@dpg-d7ludlgg4nts739fjijg-a.virginia-postgres.render.com:5432/sra_h66q"
)
LOCAL_URL = "postgresql://sra_admin:sra2026@localhost:5433/sra_pli"

# 1. Ler usuários do Render
print("Conectando ao Render...")
render_conn = psycopg.connect(RENDER_URL)
render_cur = render_conn.cursor()

# Listar tabelas do esquema sra para referência
render_cur.execute(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema = 'sra' ORDER BY table_name"
)
print("Tabelas no esquema sra:")
for row in render_cur.fetchall():
    print(f"  - {row[0]}")

# Ler colunas da tabela usuarios
render_cur.execute(
    "SELECT column_name FROM information_schema.columns "
    "WHERE table_schema = 'sra' AND table_name = 'usuarios' "
    "ORDER BY ordinal_position"
)
colunas = [r[0] for r in render_cur.fetchall()]
print(f"\nColunas de sra.usuarios: {colunas}")

# Ler dados
render_cur.execute("SELECT * FROM sra.usuarios ORDER BY 1")
usuarios_render = render_cur.fetchall()
print(f"Usuários encontrados no Render: {len(usuarios_render)}")
for u in usuarios_render:
    dados = dict(zip(colunas, u))
    print(f"  - {dados.get('email', '?')} | {dados.get('nome_completo', '?')}")

render_conn.close()

# 2. Inserir no banco local
print("\nConectando ao PostgreSQL local...")
local_conn = psycopg.connect(LOCAL_URL)
local_cur = local_conn.cursor()

# Mapeamento: Render (nome) → Local (nome_completo)
# Render não tem nome_de_usuario, gerar a partir do email
emails_vistos = set()
inseridos = 0
ignorados = 0

for u in usuarios_render:
    dados = dict(zip(colunas, u))
    email = dados.get("email")
    if not email:
        continue

    # Pular duplicados do próprio Render
    if email in emails_vistos:
        print(f"  [DUP] {email} duplicado no Render")
        ignorados += 1
        continue
    emails_vistos.add(email)

    # Verificar se já existe no local
    local_cur.execute(
        "SELECT 1 FROM usuarios WHERE email = %s", (email,)
    )
    if local_cur.fetchone():
        print(f"  [SKIP] {email} já existe")
        ignorados += 1
        continue

    nome = dados.get("nome", email.split("@")[0])
    usuario = email.split("@")[0].replace(".", "_")
    senha = dados.get("senha_hash", "")
    ativo = dados.get("ativo", True)

    # Garantir nome_de_usuario único
    base_usuario = usuario
    sufixo = 1
    while True:
        local_cur.execute(
            "SELECT 1 FROM usuarios "
            "WHERE nome_de_usuario = %s",
            (usuario,),
        )
        if not local_cur.fetchone():
            break
        usuario = f"{base_usuario}_{sufixo}"
        sufixo += 1

    local_cur.execute(
        "INSERT INTO usuarios "
        "(nome_completo, nome_de_usuario, email, "
        "senha_hash, ativo) "
        "VALUES (%s, %s, %s, %s, %s)",
        (nome, usuario, email, senha, ativo),
    )
    inseridos += 1
    print(f"  [OK] {email} -> {usuario}")

local_conn.commit()
local_conn.close()
print(
    f"\nMigração concluída: "
    f"{inseridos} inseridos, {ignorados} ignorados."
)
