import sys
sys.path.insert(0, '.')
from app import create_app
app = create_app()
app.app_context().push()
from app import db
from sqlalchemy import text

# Verificar dados do capítulo 432
with db.engine.connect() as conn:
    result = conn.execute(
        text("SELECT id_capitulo_documento, id_relatorio, id_usuario_responsavel, indice_capitulo, nivel_capitulo, tipo_elemento, classificacao FROM capitulos_documento WHERE id_capitulo_documento = 432")
    )
    row = result.fetchone()
    if row:
        print(f"Capítulo 432 encontrado:")
        print(f"  ID: {row[0]}, Relatório: {row[1]}, Responsável: {row[2]}, Índice: {row[3]}, Nível: {row[4]}, Tipo: {row[5]}, Classificação: {row[6]}")
    else:
        print("Capítulo 432 NÃO encontrado!")

# Verificar todos os capítulos do relatório 10
    result = conn.execute(
        text("SELECT id_capitulo_documento FROM capitulos_documento WHERE id_relatorio = 10 ORDER BY id_capitulo_documento")
    )
    rows = result.fetchall()
    print(f"\nCapítulos do relatório 10: {[row[0] for row in rows]}")
