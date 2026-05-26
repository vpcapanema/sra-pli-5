import sys
sys.path.insert(0, '.')
from app import create_app
app = create_app()
app.app_context().push()
from app import db
from sqlalchemy import text

# Verificar dados da tabela capitulos_documento
with db.engine.connect() as conn:
    result = conn.execute(
        text("SELECT id_capitulo_documento, id_relatorio, id_usuario_responsavel, indice_capitulo, nivel_capitulo, tipo_elemento, classificacao FROM capitulos_documento ORDER BY id_capitulo_documento")
    )
    rows = result.fetchall()
    print(f"Total de capítulos: {len(rows)}")
    print("Capítulos no banco de dados:")
    for row in rows:
        print(f"  ID: {row[0]}, Relatório: {row[1]}, Responsável: {row[2]}, Índice: {row[3]}, Nível: {row[4]}, Tipo: {row[5]}, Classificação: {row[6]}")
