"""
Teste simples com pytest para ativar Test Explorer
"""
import sys
import os

# Adiciona diretório atual ao PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_python_version():
    """Testa versão do Python"""
    assert sys.version_info >= (3, 8)
    print(f"✅ Python {sys.version}")


def test_venv_active():
    """Testa se ambiente virtual está ativo"""
    python_path = sys.executable
    assert ".venv" in python_path
    print(f"✅ Ambiente virtual: {python_path}")


def test_imports_basicos():
    """Testa imports básicos"""
    try:
        import flask
        import sqlalchemy
        print("✅ Flask e SQLAlchemy importados")
        assert True
    except ImportError as e:
        print(f"⚠️  Erro de import: {e}")
        assert False


def test_app_import():
    """Testa importação do app Flask"""
    try:
        from app import create_app
        app = create_app()
        assert app is not None
        print("✅ Aplicação Flask criada")
    except Exception as e:
        print(f"⚠️  Erro ao criar app: {e}")
        assert False


def test_estrutura_projeto():
    """Testa estrutura do projeto"""
    diretorios = ["app", "app/models", "app/routes", "app/services"]
    for dir in diretorios:
        assert os.path.exists(dir), f"Diretório {dir} não encontrado"
    print("✅ Estrutura do projeto OK")


if __name__ == "__main__":
    # Executa como script também
    print("=" * 60)
    print("EXECUTANDO TESTES PYTEST")
    print("=" * 60)
    
    # Executa testes
    import pytest
    pytest.main([__file__, "-v"])