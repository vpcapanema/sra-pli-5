# Exemplo para mostrar output no Kiro
import sys
import datetime

print("=" * 50)
print("SAÍDA DO PYTHON NO KIRO")
print("=" * 50)
print(f"Python version: {sys.version}")
print(f"Data/hora: {datetime.datetime.now()}")
print(f"Diretório: {sys.executable}")
print()

# Teste de funcionalidade
def calcular_soma(a, b):
    resultado = a + b
    print(f"Soma de {a} + {b} = {resultado}")
    return resultado

# Executar testes
print("Testes matemáticos:")
calcular_soma(10, 20)
calcular_soma(100, 250)
print()

# Lista de itens
frutas = ["maçã", "banana", "laranja", "uva"]
print("Lista de frutas:")
for i, fruta in enumerate(frutas, 1):
    print(f"  {i}. {fruta}")

print()
print("=" * 50)
print("FIM DO OUTPUT")
print("=" * 50)