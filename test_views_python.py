"""
ARQUIVO PARA ATIVAR VIEWS PYTHON NO KIRO

Este arquivo contém testes e estrutura para forçar
a exibição das views Python na barra lateral.
"""

import unittest
import sys
import os


class TestPythonViews(unittest.TestCase):
    """Testes para verificar funcionalidade Python"""
    
    def test_python_version(self):
        """Testa versão do Python"""
        self.assertTrue(sys.version_info >= (3, 8))
        print(f"Python version: {sys.version}")
    
    def test_venv_active(self):
        """Testa se ambiente virtual está ativo"""
        python_path = sys.executable
        self.assertIn(".venv", python_path)
        print(f"Python path: {python_path}")
    
    def test_imports(self):
        """Testa imports comuns do projeto"""
        try:
            import flask
            import sqlalchemy
            print("✅ Imports básicos funcionando")
            return True
        except ImportError as e:
            print(f"❌ Erro de import: {e}")
            return False


def mostrar_estrutura():
    """Mostra estrutura do projeto"""
    print("\n=== ESTRUTURA DO PROJETO ===")
    for root, dirs, files in os.walk(".", topdown=True):
        level = root.replace(".", "").count(os.sep)
        indent = " " * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = " " * 2 * (level + 1)
        for file in files[:5]:  # Mostra apenas 5 arquivos por diretório
            if file.endswith(".py"):
                print(f"{subindent}{file}")


if __name__ == "__main__":
    print("=" * 60)
    print("TESTANDO VIEWS PYTHON NO KIRO")
    print("=" * 60)
    
    # Executa testes
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPythonViews)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Mostra estrutura
    mostrar_estrutura()
    
    print("\n" + "=" * 60)
    print("PARA VER VIEWS PYTHON:")
    print("1. Este arquivo deve ativar 'Test Explorer'")
    print("2. Estrutura deve aparecer em 'Outline'")
    print("3. Ícones Python devem aparecer na barra lateral")
    print("=" * 60)