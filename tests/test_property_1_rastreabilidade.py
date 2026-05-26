"""Testes property-based para rastreabilidade de erros.

Feature: automacao-montagem-relatorios, Property 1: Rastreabilidade Estruturada de Erros

Valida que qualquer operação que falha retorna dict estruturado com:
- sucesso=False
- erro não vazio (string)
- sugestões lista não vazia
- timestamp presente
- tipo_erro identificado
"""
from __future__ import annotations

import hypothesis.strategies as st
from hypothesis import given, settings, assume
from datetime import datetime, timezone
from typing import Any, Callable

from app.services.servico_nivelador_erros import ServicoNiveladorErros


# Estratégias de geração de dados para testes property-based
def funcao_que_falha(error_type: type, error_message: str) -> Callable:
    """Cria uma função que sempre falha com o tipo e mensagem especificados."""
    def funcao_falha(*args, **kwargs):
        raise error_type(error_message)
    return funcao_falha


def funcao_que_funciona(resultado: Any) -> Callable:
    """Cria uma função que sempre retorna o resultado especificado."""
    def funcao_sucesso(*args, **kwargs):
        return resultado
    return funcao_sucesso


# Feature: automacao-montagem-relatorios, Property 1: Rastreabilidade Estruturada de Erros
@given(
    error_type=st.sampled_from([FileNotFoundError, PermissionError, ValueError, RuntimeError, KeyError]),
    error_message=st.text(min_size=1, max_size=100),
    relatorio_id=st.integers(min_value=1, max_value=1000) | st.none(),
    capitulo_id=st.integers(min_value=1, max_value=100) | st.none(),
    etapa=st.sampled_from(['merge', 'numeracao', 'cross_refs', 'toc', 'validacao'])
)
@settings(max_examples=100)
def test_property_1_rastreabilidade_estruturada(
    error_type: type,
    error_message: str,
    relatorio_id: int | None,
    capitulo_id: int | None,
    etapa: str
):
    """Testa que qualquer operação que falha retorna dict estruturado.
    
    Propriedade invariante: Para qualquer função que falha, o resultado
    sempre contém estrutura de erro padronizada.
    """
    # Cria função que sempre falha
    funcao = funcao_que_falha(error_type, error_message)
    
    # Executa com tratamento de erros
    resultado = ServicoNiveladorErros.executar_com_tratamento(
        funcao,
        relatorio_id=relatorio_id,
        capitulo_id=capitulo_id,
        etapa=etapa
    )
    
    # Valida propriedade 1: sucesso=False
    assert resultado['sucesso'] is False, "Resultado deve ter sucesso=False"
    
    # Valida propriedade 2: erro não vazio
    assert isinstance(resultado['erro'], str), "Erro deve ser string"
    assert len(resultado['erro']) > 0, "Erro não pode ser vazio"
    # Para KeyError, a mensagem pode ser repr da chave, então comparamos representações
    if error_type == KeyError:
        # KeyError usa repr() para mostrar a chave, então comparamos repr
        assert repr(error_message) in resultado['erro'], f"Erro KeyError deve conter repr da chave"
    else:
        # Para outros tipos, a mensagem deve estar contida no erro
        assert error_message in resultado['erro'], f"Mensagem de erro deve conter '{error_message}'"
    
    # Valida propriedade 3: tipo_erro identificado
    assert 'tipo_erro' in resultado, "Resultado deve conter tipo_erro"
    assert resultado['tipo_erro'] == error_type.__name__, f"tipo_erro deve ser {error_type.__name__}"
    
    # Valida propriedade 4: sugestões lista não vazia
    assert 'sugestoes' in resultado, "Resultado deve conter sugestoes"
    assert isinstance(resultado['sugestoes'], list), "sugestoes deve ser lista"
    assert len(resultado['sugestoes']) > 0, "sugestoes não pode ser lista vazia"
    
    # Valida propriedade 5: timestamp presente
    assert 'timestamp' in resultado, "Resultado deve conter timestamp"
    assert isinstance(resultado['timestamp'], str), "timestamp deve ser string"
    
    # Valida propriedade 6: contexto preservado
    assert resultado['etapa'] == etapa, f"etapa deve ser '{etapa}'"
    assert resultado['relatorio_id'] == relatorio_id, f"relatorio_id deve ser {relatorio_id}"
    assert resultado['capitulo_id'] == capitulo_id, f"capitulo_id deve ser {capitulo_id}"
    
    # Valida propriedade 7: estrutura completa
    campos_esperados = ['sucesso', 'erro', 'tipo_erro', 'etapa', 'relatorio_id', 
                       'capitulo_id', 'sugestoes', 'timestamp']
    for campo in campos_esperados:
        assert campo in resultado, f"Campo '{campo}' deve estar presente"


@given(
    resultado_valor=st.one_of(
        st.integers(min_value=-1000, max_value=1000),
        st.text(min_size=1, max_size=50),
        st.booleans(),
        st.none(),
        st.dictionaries(keys=st.text(min_size=1, max_size=10), 
                       values=st.text(min_size=1, max_size=20))
    ),
    relatorio_id=st.integers(min_value=1, max_value=1000) | st.none(),
    capitulo_id=st.integers(min_value=1, max_value=100) | st.none(),
    etapa=st.sampled_from(['merge', 'numeracao', 'cross_refs', 'toc', 'validacao'])
)
@settings(max_examples=50)
def test_property_1_sucesso_preserva_resultado(
    resultado_valor: Any,
    relatorio_id: int | None,
    capitulo_id: int | None,
    etapa: str
):
    """Testa que operações bem-sucedidas retornam resultado original.
    
    Propriedade invariante: Para qualquer função que funciona, o resultado
    é exatamente o valor retornado pela função, sem modificação.
    """
    # Cria função que sempre funciona
    funcao = funcao_que_funciona(resultado_valor)
    
    # Executa com tratamento de erros
    resultado = ServicoNiveladorErros.executar_com_tratamento(
        funcao,
        relatorio_id=relatorio_id,
        capitulo_id=capitulo_id,
        etapa=etapa
    )
    
    # Valida que resultado é exatamente o valor original
    assert resultado == resultado_valor, "Resultado deve ser igual ao valor original"


@given(
    error_type=st.sampled_from([FileNotFoundError, PermissionError, ValueError, RuntimeError, KeyError]),
    error_message=st.text(min_size=1, max_size=100),
    etapa=st.sampled_from(['merge', 'numeracao', 'cross_refs', 'toc', 'validacao'])
)
@settings(max_examples=50)
def test_property_1_sugestoes_adequadas_ao_tipo_erro(
    error_type: type,
    error_message: str,
    etapa: str
):
    """Testa que sugestões são adequadas ao tipo de erro.
    
    Propriedade invariante: Para cada tipo de exceção, as sugestões
    devem ser relevantes e específicas para aquele tipo.
    """
    # Cria função que sempre falha
    funcao = funcao_que_falha(error_type, error_message)
    
    # Executa com tratamento de erros
    resultado = ServicoNiveladorErros.executar_com_tratamento(
        funcao,
        etapa=etapa
    )
    
    # Valida que sugestões não são vazias
    assert len(resultado['sugestoes']) > 0, "sugestoes não pode ser lista vazia"
    
    # Valida que sugestões são strings
    for sugestao in resultado['sugestoes']:
        assert isinstance(sugestao, str), "Cada sugestão deve ser string"
        assert len(sugestao) > 0, "Sugestão não pode ser string vazia"
    
    # Valida mapeamento específico para tipos conhecidos
    if error_type == FileNotFoundError:
        assert any("arquivo" in sugestao.lower() or "caminho" in sugestao.lower() 
                  for sugestao in resultado['sugestoes']), \
               "FileNotFoundError deve ter sugestão sobre arquivo/caminho"
    
    elif error_type == PermissionError:
        assert any("permissão" in sugestao.lower() or "acesso" in sugestao.lower()
                  for sugestao in resultado['sugestoes']), \
               "PermissionError deve ter sugestão sobre permissão/acesso"
    
    elif error_type == ValueError:
        assert any("valor" in sugestao.lower() or "inválido" in sugestao.lower()
                  for sugestao in resultado['sugestoes']), \
               "ValueError deve ter sugestão sobre valor inválido"
    
    elif error_type == KeyError:
        assert any("chave" in sugestao.lower() or "dicionário" in sugestao.lower()
                  for sugestao in resultado['sugestoes']), \
               "KeyError deve ter sugestão sobre chave/dicionário"


@given(
    error_type=st.sampled_from([FileNotFoundError, PermissionError, ValueError, RuntimeError, KeyError]),
    error_message=st.text(min_size=1, max_size=100),
    etapa=st.sampled_from(['merge', 'numeracao', 'cross_refs', 'toc', 'validacao'])
)
@settings(max_examples=30)
def test_property_1_timestamp_valido(
    error_type: type,
    error_message: str,
    etapa: str
):
    """Testa que timestamp é válido e recente.
    
    Propriedade invariante: timestamp deve ser string ISO 8601 válida
    e representar um momento próximo ao da execução.
    """
    # Cria função que sempre falha
    funcao = funcao_que_falha(error_type, error_message)
    
    # Executa com tratamento de erros
    resultado = ServicoNiveladorErros.executar_com_tratamento(
        funcao,
        etapa=etapa
    )
    
    # Valida formato ISO 8601
    timestamp_str = resultado['timestamp']
    assert 'T' in timestamp_str, "timestamp deve conter 'T' (formato ISO 8601)"
    assert timestamp_str.endswith('+00:00') or 'Z' in timestamp_str, \
           "timestamp deve indicar UTC (Z ou +00:00)"
    
    # Tenta parsear como datetime
    try:
        timestamp_dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except ValueError:
        # Para versões mais antigas do Python
        timestamp_dt = datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%f%z')
    
    # Valida que timestamp é recente (dentro de 5 segundos)
    agora = datetime.now(timezone.utc)
    diferenca = abs((agora - timestamp_dt).total_seconds())
    assert diferenca < 5, f"timestamp deve ser recente (diferença: {diferenca}s)"


@given(
    error_type=st.sampled_from([FileNotFoundError, PermissionError, ValueError, RuntimeError, KeyError]),
    error_message=st.text(min_size=1, max_size=100),
    etapa=st.sampled_from(['merge', 'numeracao', 'cross_refs', 'toc', 'validacao']),
    usuario_id=st.integers(min_value=1, max_value=100) | st.none()
)
@settings(max_examples=30)
def test_property_1_contexto_completo(
    error_type: type,
    error_message: str,
    etapa: str,
    usuario_id: int | None
):
    """Testa que contexto completo é preservado.
    
    Propriedade invariante: Todos os parâmetros de contexto fornecidos
    devem estar presentes no resultado.
    """
    # Cria função que sempre falha
    funcao = funcao_que_falha(error_type, error_message)
    
    # Executa com tratamento de erros
    resultado = ServicoNiveladorErros.executar_com_tratamento(
        funcao,
        etapa=etapa,
        usuario_id=usuario_id
    )
    
    # Valida que todos os campos de contexto estão presentes
    assert resultado['etapa'] == etapa, f"etapa deve ser '{etapa}'"
    assert resultado['usuario_id'] == usuario_id, f"usuario_id deve ser {usuario_id}"
    
    # Valida que campos opcionais podem ser None
    assert resultado['relatorio_id'] is None, "relatorio_id deve ser None quando não fornecido"
    assert resultado['capitulo_id'] is None, "capitulo_id deve ser None quando não fornecido"


if __name__ == '__main__':
    # Execução direta para debugging
    import sys
    import pytest
    
    sys.exit(pytest.main([__file__, '-v']))
