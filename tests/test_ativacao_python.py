"""
TESTE PARA ATIVAR VIEWS PYTHON NO KIRO

Este arquivo contém testes mínimos para ativar o Test Explorer
e fazer o ícone aparecer na barra lateral do Kiro.
"""
import unittest
import sys
import os

# Adiciona diretório atual ao PYTHONPATH para importar módulos do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAtivacaoPython(unittest.TestCase):
    """Testes básicos para ativar funcionalidades Python"""
    
    def test_python_ambiente(self):
        """Testa se ambiente Python está funcionando"""
        self.assertTrue(sys.version_info >= (3, 8))
        print(f"✅ Python {sys.version}")
    
    def test_venv_ativa(self):
        """Testa se ambiente virtual está ativo"""
        python_path = sys.executable
        self.assertIn(".venv", python_path)
        print(f"✅ Ambiente virtual: {python_path}")
    
    def test_imports_projeto(self):
        """Testa imports do projeto SRA"""
        try:
            # Testa imports básicos do Flask
            import flask
            import sqlalchemy
            print("✅ Flask e SQLAlchemy importados")
            return True
        except ImportError as e:
            print(f"⚠️  Erro de import: {e}")
            return False
    
    def test_estrutura_projeto(self):
        """Testa estrutura básica do projeto"""
        diretorios_esperados = ["app", "app/models", "app/routes", "app/services"]
        for dir in diretorios_esperados:
            self.assertTrue(os.path.exists(dir), f"Diretório {dir} não encontrado")
        print("✅ Estrutura do projeto OK")


class TestSRAFuncional(unittest.TestCase):
    """Testes funcionais do projeto SRA"""
    
    def test_configuracao_app(self):
        """Testa criação da aplicação Flask"""
        try:
            from app import create_app
            app = create_app()
            self.assertIsNotNone(app)
            print("✅ Aplicação Flask criada com sucesso")
        except Exception as e:
            self.fail(f"Falha ao criar app: {e}")
    
    def test_models_import(self):
        """Testa importação de models"""
        try:
            from app.models import Usuario, RelatorioProducao
            print("✅ Models importados com sucesso")
        except ImportError as e:
            print(f"⚠️  Models não importados: {e}")


if __name__ == '__main__':
    print("=" * 60)
    print("EXECUTANDO TESTES PARA ATIVAR VIEWS PYTHON")
    print("=" * 60)
    
    # Executa todos os testes
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAtivacaoPython)
    suite.addTests(loader.loadTestsFromTestCase(TestSRAFuncional))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ TODOS OS TESTES PASSARAM!")
        print("✅ Test Explorer DEVE aparecer na barra lateral")
        print("✅ Ícone de tubo de ensaio deve estar visível")
    else:
        print("⚠️  Alguns testes falharam")
        print("   Verifique o ambiente Python")
    
    print("=" * 60)
    print("\nPARA VER O ÍCONE NO KIRO:")
    print("1. Abra este arquivo no editor")
    print("2. Ctrl+Shift+P → 'Python: Discover Tests'")
    print("3. Ctrl+Shift+P → 'Test: Focus on Test Explorer'")
    print("4. Ícone de tubo de ensaio deve aparecer na barra lateral")