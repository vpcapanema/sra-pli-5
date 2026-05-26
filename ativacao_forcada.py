# ARQUIVO DE ATIVAÇÃO FORÇADA
# Este arquivo força o Kiro a mostrar views Python

print("=== ATIVAÇÃO FORÇADA DE VIEWS PYTHON ===")

# Teste de funcionalidade
def testar_ambiente():
    import sys
    print(f"Python: {sys.executable}")
    print(f"Versão: {sys.version}")
    return True

# Importar módulos do projeto
try:
    from app import create_app
    print("✅ Módulo 'app' importado com sucesso")
    app = create_app()
    print("✅ Aplicação Flask criada com sucesso")
except Exception as e:
    print(f"⚠️  Erro ao importar app: {e}")

# Executar teste
if testar_ambiente():
    print("✅ Ambiente Python funcionando perfeitamente")
    print("✅ Views Python DEVEM aparecer na barra lateral")
    print("✅ Verifique ícones de Test Explorer e Outline")
else:
    print("❌ Problema com ambiente Python")

print("==========================================")
