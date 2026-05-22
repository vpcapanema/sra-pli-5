import psycopg, sys
sys.stdout.reconfigure(encoding='utf-8')
RENDER_URL = 'postgresql://sra:eJmMmQTdsNENzrKoB00RLOM2f3uzkyK8@dpg-d7ludlgg4nts739fjijg-a.virginia-postgres.render.com:5432/sra_h66q'
conn = psycopg.connect(RENDER_URL)
cur = conn.cursor()

tabelas = ['usuarios', 'relatorios_producao', 'relatorios_finalizados']
for t in tabelas:
    print(f'\n=== TABELA: sra.{t} ===')
    cur.execute(
        'SELECT column_name, data_type, is_nullable, column_default '
        'FROM information_schema.columns '
        'WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position',
        ('sra', t)
    )
    for row in cur.fetchall():
        print(f'  {row[0]} | {row[1]} | nullable={row[2]} | default={row[3]}')
    
    # Primary key
    cur.execute(
        """SELECT kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'PRIMARY KEY'
          AND tc.table_schema = %s
          AND tc.table_name = %s""",
        ('sra', t)
    )
    pks = [r[0] for r in cur.fetchall()]
    print(f'  PRIMARY KEY: {pks}')

conn.close()
