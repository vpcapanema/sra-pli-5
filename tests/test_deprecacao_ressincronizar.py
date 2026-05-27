"""
Testes para validar deprecação do método ressincronizar_capitulos() antigo.

Este teste verifica que:
1. O método antigo ainda funciona (compatibilidade)
2. Emite DeprecationWarning
3. Chama o novo método internamente
4. Retorna estrutura compatível com callers antigos
"""

import warnings
import pytest
from unittest.mock import patch, MagicMock

from app.services.servico_sincronizar_capitulos import ressincronizar_capitulos


def test_ressincronizar_capitulos_deprecado_emite_warning():
    """Valida que ressincronizar_capitulos() emite DeprecationWarning."""
    rel_mock = MagicMock()
    rel_mock.id_relatorio_producao = 1
    rel_mock.caminho_template = None  # Vai falhar rapidamente
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        with patch('app.services.servico_sincronizar_capitulos.ressincronizar_capitulos_com_classificacao') as mock_new:
            mock_new.return_value = {
                'sucesso': False,
                'total_atualizados': 0,
                'total_criados': 0,
                'capitulos_sincronizados': [],
                'erros_classificacao': []
            }
            
            # Chamar método deprecado
            ressincronizar_capitulos(rel_mock)
            
            # Verificar que DeprecationWarning foi emitido
            deprecation_warnings = [
                warning for warning in w
                if issubclass(warning.category, DeprecationWarning)
            ]
            
            assert len(deprecation_warnings) > 0, \
                "Nenhum DeprecationWarning foi emitido"
            
            msg = str(deprecation_warnings[0].message)
            assert "ressincronizar_capitulos_com_classificacao" in msg, \
                f"Mensagem não sugere novo método: {msg}"


def test_ressincronizar_capitulos_deprecado_chama_novo():
    """Valida que ressincronizar_capitulos() chama novo método."""
    rel_mock = MagicMock()
    rel_mock.id_relatorio_producao = 1
    
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        
        with patch('app.services.servico_sincronizar_capitulos.ressincronizar_capitulos_com_classificacao') as mock_new:
            mock_new.return_value = {
                'sucesso': True,
                'total_atualizados': 2,
                'total_criados': 1,
                'capitulos_sincronizados': [
                    {'id': 1, 'titulo': 'Cap 1', 'acao': 'atualizado'},
                    {'id': 2, 'titulo': 'Cap 2', 'acao': 'atualizado'},
                    {'titulo': 'Cap 3', 'acao': 'criado'},
                ],
                'erros_classificacao': []
            }
            
            # Chamar método deprecado
            resultado = ressincronizar_capitulos(rel_mock)
            
            # Verificar que novo método foi chamado
            mock_new.assert_called_once_with(rel_mock)
            
            # Verificar que resultado é compatível com API antiga
            assert 'aplicados' in resultado
            assert resultado['aplicados'] is True
            assert resultado['atualizados'] == 2
            assert resultado['criados'] == 1


def test_ressincronizar_capitulos_deprecado_compatibilidade():
    """Valida que retorno é compatível com API antiga."""
    rel_mock = MagicMock()
    
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        
        with patch('app.services.servico_sincronizar_capitulos.ressincronizar_capitulos_com_classificacao') as mock_new:
            mock_new.return_value = {
                'sucesso': True,
                'total_atualizados': 5,
                'total_criados': 3,
                'capitulos_sincronizados': [],
                'erros_classificacao': [
                    {'tipo': 'classificacao', 'titulo': 'Test', 'mensagem': 'Erro'}
                ]
            }
            
            resultado = ressincronizar_capitulos(rel_mock)
            
            # Estrutura antiga deve estar presente
            campos_obrigatorios = ['aplicados', 'atualizados', 'criados', 'removidos', 'sumiram', 'detalhes']
            for campo in campos_obrigatorios:
                assert campo in resultado, f"Campo '{campo}' faltando no resultado"
            
            # Valores devem estar corretos
            assert resultado['aplicados'] is True
            assert resultado['atualizados'] == 5
            assert resultado['criados'] == 3
            assert resultado['removidos'] == 0
            
            # Detalhes deve conter informações do novo método
            assert 'capitulos_sincronizados' in resultado['detalhes']
            assert 'erros_classificacao' in resultado['detalhes']


def test_logging_deprecacao():
    """Valida que log warning é registrado."""
    import logging
    from app.services.servico_sincronizar_capitulos import logger
    
    rel_mock = MagicMock()
    rel_mock.id_relatorio_producao = 1
    
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        
        with patch('app.services.servico_sincronizar_capitulos.ressincronizar_capitulos_com_classificacao') as mock_new:
            mock_new.return_value = {
                'sucesso': False,
                'total_atualizados': 0,
                'total_criados': 0,
                'capitulos_sincronizados': [],
                'erros_classificacao': []
            }
            
            with patch.object(logger, 'warning') as mock_log_warning:
                ressincronizar_capitulos(rel_mock)
                
                # Verificar que logger.warning foi chamado
                mock_log_warning.assert_called_once()
                
                # Verificar que mensagem menciona deprecação
                args, kwargs = mock_log_warning.call_args
                assert 'DEPRECATION' in args[0]
                assert 'ressincronizar_capitulos_com_classificacao' in args[0]
