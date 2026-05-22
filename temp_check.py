import psycopg, sys
sys.stdout.reconfigure(encoding='utf-8')
RENDER_URL = 'postgresql://sra:eJmMmQTdsNENzrKoB00RLOM2f3uzkyK8@dpg-d7ludlgg4nts739fjijg-a.virginia-postgres.render.com:5432/sra_h66q'
conn = psycopg.connect(RENDER_URL)
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='dominios' AND table_name='dom_perfis_usuario' ORDER BY ordinal_position")
for row in cur.fetchall():
    print(row)
conn.close()
