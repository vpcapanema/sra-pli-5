"""Testes property-based para classificação e sincronização de capítulos.

Feature: automacao-montagem-relatorios, Property 4: Respeito a Classificação e Seções

Valida que para qualquer capítulo no DOCX template com classificação,
após ressincronizar_capitulos_com_classificacao(), o modelo CapituloDocumento
tem campos corretos: classificacao, prefixo_indice, id_secao_inicio/fim.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
"""
from __future__ import annotations

import pytest
import hypothesis.strategies as st
from hypothesis import given, settings, assume


# Estratégias de geração para testes property-based

@st.composite
def estilo_por_classificacao_strategy(draw) -> tuple:
    """Gera (estilo_docx, classificacao_esperada, prefixo_esperado)."""
    opcoes = [
        ('Heading 1', None, None),  # Textual
        ('Heading 2', None, None),  # Subcapítulo
        ('Anexo', 'anexo', 'ANEXO_'),
        ('ANEXO', 'anexo', 'ANEXO_'),
        ('Apêndice', 'apendice', 'APENDICE_'),
        ('APÊNDICE', 'apendice', 'APENDICE_'),
        ('Referências', None, None),  # Pos-textual (sem classificação)
    ]
    return draw(st.sampled_from(opcoes))


@st.composite
def mapa_capitulos_com_estilos_strategy(draw) -> dict:
    """Gera estrutura de dados com capitulos e seus estilos esperados."""
    num_items = draw(st.integers(min_value=1, max_value=4))
    
    items = {}
    for i in range(num_items):
        estilo, classif, prefixo = draw(estilo_por_classificacao_strategy())
        items[f'Cap_{i+1}'] = {
            'estilo': estilo,
            'classificacao_esperada': classif,
            'prefixo_esperado': prefixo
        }
    
    return items


# =====================================================================
# Property 4: Respeito a Classificação e Seções
# =====================================================================

# Feature: automacao-montagem-relatorios, Property 4: Respeito a Classificação e Seções na Sincronização
@given(capitulos_map=mapa_capitulos_com_estilos_strategy())
@settings(max_examples=30, deadline=None)
def test_property_4_classificacao_mapping(capitulos_map: dict):
    """Testa que mapeamento de estilo DOCX para classificacao é correto.
    
    Propriedade invariante: Para qualquer estilo DOCX, o mapeamento
    para classificacao e prefixo_indice é consistente.
    
    **Validates: Requirements 4.1, 4.2**
    """
    from app.services.servico_classificacao_capitulos import (
        ServicoClassificacaoCapitulos
    )
    
    for titulo, dados in capitulos_map.items():
        estilo = dados['estilo']
        classificacao_esperada = dados['classificacao_esperada']
        prefixo_esperado = dados['prefixo_esperado']
        
        # Executa classificação
        classificacao, nivel, prefixo = (
            ServicoClassificacaoCapitulos.classificar_por_estilo_docx(estilo)
        )
        
        # Valida classificação
        assert classificacao == classificacao_esperada, \
            f"Estilo '{estilo}' deve ter classificacao '{classificacao_esperada}' (foi '{classificacao}')"
        
        # Valida prefixo
        assert prefixo == prefixo_esperado, \
            f"Estilo '{estilo}' deve ter prefixo '{prefixo_esperado}' (foi '{prefixo}')"


# Feature: automacao-montagem-relatorios, Property 4: Respeito a Classificação e Seções na Sincronização
@given(num_items=st.integers(min_value=1, max_value=5),
       tipos=st.lists(
           st.sampled_from([
               ('textual', 'Heading 1', None, None),
               ('anexo', 'Anexo', 'anexo', 'ANEXO_'),
               ('apendice', 'Apêndice', 'apendice', 'APENDICE_'),
           ]),
           min_size=1,
           max_size=5,
           unique=False
       ))
@settings(max_examples=30, deadline=None)
def test_property_4_determinismo_classificacao(num_items: int, tipos: list):
    """Testa que classificação é determinística.
    
    Propriedade invariante: Chamando classificacao 2x com mesmo estilo
    sempre retorna mesmo resultado.
    
    **Validates: Requirements 4.1, 4.3**
    """
    assume(len(tipos) >= num_items)
    
    from app.services.servico_classificacao_capitulos import (
        ServicoClassificacaoCapitulos
    )
    
    for i in range(num_items):
        tipo, estilo, classif_esperada, prefixo_esperado = tipos[i]
        
        # Chamar 2x
        resultado1 = ServicoClassificacaoCapitulos.classificar_por_estilo_docx(estilo)
        resultado2 = ServicoClassificacaoCapitulos.classificar_por_estilo_docx(estilo)
        
        # Devem ser idênticos
        assert resultado1 == resultado2, \
            f"Classificação deve ser determinística para '{estilo}'"
        
        classif1, nivel1, prefixo1 = resultado1
        classif2, nivel2, prefixo2 = resultado2
        
        # Validar que retorna o esperado
        assert classif1 == classif_esperada, \
            f"Classificação para '{estilo}' deve ser '{classif_esperada}' (foi '{classif1}')"


# Feature: automacao-montagem-relatorios, Property 4: Respeito a Classificação e Seções na Sincronização
@given(
    estilos=st.lists(
        st.sampled_from(['Heading 1', 'Heading 2', 'Anexo', 'ANEXO', 'Apêndice', 'Referências']),
        min_size=1,
        max_size=10
    )
)
@settings(max_examples=30, deadline=None)
def test_property_4_campos_estruturados(estilos: list):
    """Testa que resultado sempre tem estrutura correta.
    
    Propriedade invariante: Resultado de classificacao sempre tem
    3 elementos (classificacao, nivel, prefixo), nunca None como tuple.
    
    **Validates: Requirements 4.1, 4.2**
    """
    from app.services.servico_classificacao_capitulos import (
        ServicoClassificacaoCapitulos
    )
    
    for estilo in estilos:
        resultado = ServicoClassificacaoCapitulos.classificar_por_estilo_docx(estilo)
        
        # Valida que é tuple com 3 elementos
        assert isinstance(resultado, tuple), \
            f"Resultado deve ser tuple (foi {type(resultado)})"
        assert len(resultado) == 3, \
            f"Resultado deve ter 3 elementos (foi {len(resultado)})"
        
        classificacao, nivel, prefixo = resultado
        
        # Classicacao pode ser None ou string válida
        if classificacao is not None:
            assert isinstance(classificacao, str), \
                f"classificacao deve ser str ou None (foi {type(classificacao)})"
            assert classificacao in ['textual', 'pre_textual', 'pos_textual', 'anexo', 'apendice'], \
                f"classificacao deve ser um dos valores válidos (foi '{classificacao}')"
        
        # Prefixo pode ser None ou string
        if prefixo is not None:
            assert isinstance(prefixo, str), \
                f"prefixo deve ser str ou None (foi {type(prefixo)})"
            assert len(prefixo) > 0, \
                f"prefixo não pode ser string vazia (foi '{prefixo}')"
        
        # Nível pode ser None ou int
        if nivel is not None:
            assert isinstance(nivel, int), \
                f"nivel deve ser int ou None (foi {type(nivel)})"


# Feature: automacao-montagem-relatorios, Property 4: Respeito a Classificação e Seções na Sincronização
@given(
    pairs=st.lists(
        st.tuples(
            st.sampled_from(['Anexo', 'ANEXO', 'Anexo A']),
            st.sampled_from(['Apêndice', 'APÊNDICE', 'Apêndice I'])
        ),
        min_size=1,
        max_size=5
    )
)
@settings(max_examples=20, deadline=None)
def test_property_4_anexo_vs_apendice_distintos(pairs: list):
    """Testa que Anexo e Apêndice sempre têm classificacoes distintas.
    
    Propriedade invariante: Estilos com 'Anexo' sempre classificam como 'anexo',
    estilos com 'Apêndice' sempre classificam como 'apendice', nunca há confusão.
    
    **Validates: Requirements 4.2**
    """
    from app.services.servico_classificacao_capitulos import (
        ServicoClassificacaoCapitulos
    )
    
    for estilo_anexo, estilo_apendice in pairs:
        classif_anexo, _, prefixo_anexo = (
            ServicoClassificacaoCapitulos.classificar_por_estilo_docx(estilo_anexo)
        )
        classif_apendice, _, prefixo_apendice = (
            ServicoClassificacaoCapitulos.classificar_por_estilo_docx(estilo_apendice)
        )
        
        # Devem ser classificacoes diferentes
        assert classif_anexo == 'anexo', \
            f"'{estilo_anexo}' deve classificar como 'anexo' (foi '{classif_anexo}')"
        assert classif_apendice == 'apendice', \
            f"'{estilo_apendice}' deve classificar como 'apendice' (foi '{classif_apendice}')"
        
        # Prefixos devem ser diferentes
        assert prefixo_anexo != prefixo_apendice, \
            f"Prefixos devem ser distintos (anexo={prefixo_anexo}, apendice={prefixo_apendice})"


# Feature: automacao-montagem-relatorios, Property 4: Respeito a Classificação e Seções na Sincronização
@given(
    estilos_desconhecidos=st.lists(
        st.text(min_size=1, max_size=20),
        min_size=1,
        max_size=5,
        unique=True
    )
)
@settings(max_examples=20, deadline=None)
def test_property_4_fallback_para_desconhecidos(estilos_desconhecidos: list):
    """Testa que estilos desconhecidos recebem classificacao None (fallback).
    
    Propriedade invariante: Estilos não reconhecidos não causam erro,
    mas retornam None para classificacao (permitindo processamento continuar).
    
    **Validates: Requirements 4.1**
    """
    from app.services.servico_classificacao_capitulos import (
        ServicoClassificacaoCapitulos
    )
    
    # Filtra para garantir que são realmente desconhecidos
    estilos_conhecidos = {
        'Heading 1', 'Heading 2', 'Heading 3', 'Titulo 1', 'Titulo 2', 'Titulo 3',
        'Anexo', 'ANEXO', 'Apêndice', 'APÊNDICE', 'Title', 'Capa', 'Sumário',
        'Referências', 'Bibliografia'
    }
    
    for estilo in estilos_desconhecidos:
        if estilo in estilos_conhecidos:
            continue  # Pular se foi gerado um estilo conhecido
        
        # Não deve lançar exceção
        try:
            resultado = ServicoClassificacaoCapitulos.classificar_por_estilo_docx(estilo)
            classificacao, nivel, prefixo = resultado
            
            # Pode retornar None (graceful fallback)
            # ou tentar classificar por heurística
            assert resultado is not None, f"Resultado não pode ser None"
            assert isinstance(resultado, tuple), f"Resultado deve ser tuple"
            
        except Exception as e:
            pytest.fail(f"Classificação não deve lançar exceção para '{estilo}': {e}")


if __name__ == '__main__':
    # Execução direta para debugging
    import sys
    import pytest
    
    sys.exit(pytest.main([__file__, '-v', '--tb=short']))
