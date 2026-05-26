"""Testes para o ServicoNiveladorErros (T1.1)."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.servico_nivelador_erros import ServicoNiveladorErros


def test_executar_com_tratamento_sucesso():
    """Testa execução bem-sucedida sem erros."""
    
    def funcao_soma(a, b):
        return a + b
    
    resultado = ServicoNiveladorErros.executar_com_tratamento(
        funcao_soma, 5, 3, etapa="soma"
    )
    
    assert resultado == 8, f"Esperado 8, obtido {resultado}"
    print("✓ Teste de sucesso passou")


def test_executar_com_tratamento_erro():
    """Testa execução com erro e retorno estruturado."""
    
    def funcao_erro():
        raise ValueError("Valor inválido")
    
    resultado = ServicoNiveladorErros.executar_com_tratamento(
        funcao_erro, etapa="validacao"
    )
    
    assert resultado['sucesso'] is False
    assert resultado['erro'] == "Valor inválido"
    assert resultado['tipo_erro'] == "ValueError"
    assert resultado['etapa'] == "validacao"
    assert isinstance(resultado['sugestoes'], list)
    assert len(resultado['sugestoes']) > 0
    assert 'timestamp' in resultado
    print("✓ Teste de erro passou")


def test_executar_com_tratamento_contexto():
    """Testa execução com contexto (relatorio_id, capitulo_id, usuario_id)."""
    
    def funcao_erro():
        raise FileNotFoundError("Arquivo não encontrado")
    
    resultado = ServicoNiveladorErros.executar_com_tratamento(
        funcao_erro,
        relatorio_id=123,
        capitulo_id=456,
        usuario_id=789,
        etapa="carregamento_arquivo"
    )
    
    assert resultado['sucesso'] is False
    assert resultado['relatorio_id'] == 123
    assert resultado['capitulo_id'] == 456
    assert resultado['usuario_id'] == 789
    assert resultado['etapa'] == "carregamento_arquivo"
    assert "Arquivo não encontrado. Verifique o caminho." in resultado['sugestoes']
    print("✓ Teste de contexto passou")


def test_mapeamento_sugestoes():
    """Testa mapeamento de tipos de exceção para sugestões."""
    
    # Testa FileNotFoundError
    def funcao_file_not_found():
        raise FileNotFoundError("teste.txt")
    
    resultado = ServicoNiveladorErros.executar_com_tratamento(funcao_file_not_found)
    assert "Arquivo não encontrado. Verifique o caminho." in resultado['sugestoes']
    
    # Testa PermissionError
    def funcao_permission_error():
        raise PermissionError("acesso negado")
    
    resultado = ServicoNiveladorErros.executar_com_tratamento(funcao_permission_error)
    assert "Permissão negada. Verifique as permissões do arquivo." in resultado['sugestoes']
    
    # Testa KeyError
    def funcao_key_error():
        raise KeyError("chave_inexistente")
    
    resultado = ServicoNiveladorErros.executar_com_tratamento(funcao_key_error)
    assert "Chave não encontrada no dicionário." in resultado['sugestoes']
    
    print("✓ Teste de mapeamento de sugestões passou")


def test_adicionar_sugestao_padrao():
    """Testa adição de nova sugestão padrão."""
    
    class ExcecaoCustomizada(Exception):
        pass
    
    # Adiciona sugestão para exceção customizada
    ServicoNiveladorErros.adicionar_sugestao_padrao(
        ExcecaoCustomizada,
        "Esta é uma exceção customizada. Verifique a configuração."
    )
    
    def funcao_custom_error():
        raise ExcecaoCustomizada("erro customizado")
    
    resultado = ServicoNiveladorErros.executar_com_tratamento(funcao_custom_error)
    
    assert "Esta é uma exceção customizada. Verifique a configuração." in resultado['sugestoes']
    print("✓ Teste de adição de sugestão padrão passou")


def test_preservacao_argumentos():
    """Testa que argumentos e kwargs são passados corretamente para a função."""
    
    def funcao_complexa(a, b, c=10, d=20):
        return a + b + c + d
    
    resultado = ServicoNiveladorErros.executar_com_tratamento(
        funcao_complexa, 1, 2, c=30, d=40
    )
    
    assert resultado == 1 + 2 + 30 + 40, f"Esperado {1+2+30+40}, obtido {resultado}"
    print("✓ Teste de preservação de argumentos passou")


def test_obter_sugestoes_padrao():
    """Testa obtenção de cópia do mapeamento de sugestões."""
    sugestoes = ServicoNiveladorErros.obter_sugestoes_padrao()
    
    assert isinstance(sugestoes, dict)
    assert FileNotFoundError in sugestoes
    assert sugestoes[FileNotFoundError] == "Arquivo não encontrado. Verifique o caminho."
    print("✓ Teste de obtenção de sugestões padrão passou")


def main():
    """Executa todos os testes."""
    print("Executando testes para ServicoNiveladorErros...\n")
    
    try:
        test_executar_com_tratamento_sucesso()
        test_executar_com_tratamento_erro()
        test_executar_com_tratamento_contexto()
        test_mapeamento_sugestoes()
        test_adicionar_sugestao_padrao()
        test_preservacao_argumentos()
        test_obter_sugestoes_padrao()
        
        print("\n✅ Todos os testes passaram!")
        return 0
    except AssertionError as e:
        print(f"\n❌ Teste falhou: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())