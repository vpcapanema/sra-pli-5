import psycopg, sys
sys.stdout.reconfigure(encoding='utf-8')
RENDER_URL = 'postgresql://sra:eJmMmQTdsNENzrKoB00RLOM2f3uzkyK8@dpg-d7ludlgg4nts739fjijg-a.virginia-postgres.render.com:5432/sra_h66q'
conn = psycopg.connect(RENDER_URL)
cur = conn.cursor()
cur.execute("""SELECT table_schema, table_name FROM information_schema.tables WHERE table_name IN ('dom_perfis_usuario', 'dom_status_relatorios') ORDER BY table_schema, table_name""")
for row in cur.fetchall():
    print(f'{row[0]}.{row[1]}')
conn.close()
