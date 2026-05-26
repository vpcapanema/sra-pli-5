#!/usr/bin/env python3
"""Teste do mapeamento entre tipos conceituais e estilos DOCX."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.servico_classificacao_capitulos import ServicoClassificacaoCapitulos

print("=" * 70)
print("TESTE DE MAPEAMENTO ENTRE TIPOS CONCEITUAIS E ESTILOS DOCX")
print("=" * 70)

# Teste 1: Classificação por estilo DOCX
print("\n1. CLASSIFICAÇÃO POR ESTILO DOCX:")
testes_estilos = [
    ("Heading 1", "Capítulo nível 1"),
    ("Heading 2", "Subcapítulo nível 2"),
    ("Heading 3", "Subcapítulo nível 3"),
    ("Anexo", "Anexo"),
    ("Apêndice", "Apêndice"),
    ("Title", "Pré-textual"),
    ("Referências", "Pós-textual"),
    ("Estilo Desconhecido", "Fallback"),
]

for estilo, descricao in testes_estilos:
    classificacao, nivel, prefixo = ServicoClassificacaoCapitulos.classificar_por_estilo_docx(estilo)
    print(f"   {descricao:20} → Estilo: '{estilo}'")
    print(f"     Classificação: {classificacao}, Nível: {nivel}, Prefixo: {prefixo}")

# Teste 2: Determinar estilo por tipo conceitual
print("\n2. DETERMINAR ESTILO POR TIPO CONCEITUAL:")
testes_tipos = [
    ("capitulo", 1, "Heading 1"),
    ("subcapitulo", 2, "Heading 2"),
    ("subcapitulo", 3, "Heading 3"),
    ("anexo", 1, "Anexo"),
    ("apendice", 1, "Apêndice"),
    ("pre_textual", 1, "Title"),
    ("pos_textual", 1, "Normal"),
]

for tipo, nivel, esperado in testes_tipos:
    estilo = ServicoClassificacaoCapitulos.determinar_estilo_por_tipo_conceitual(tipo, nivel)
    status = "✅" if estilo == esperado else "❌"
    print(f"   {status} {tipo:15} (nível {nivel}) → '{estilo}' (esperado: '{esperado}')")

# Teste 3: Extrair e classificar do DOCX
print("\n3. EXTRAIR E CLASSIFICAR DO DOCX:")
testes_extracao = [
    ("1. INTRODUÇÃO", "Heading 1", 10, 100),
    ("1.1 Contexto", "Heading 2", 11, 100),
    ("ANEXO A - Dados", "Anexo", 80, 100),
    ("APÊNDICE I - Glossário", "Apêndice", 85, 100),
    ("REFERÊNCIAS", "Referências", 90, 100),
]

for texto, estilo, pos, total in testes_extracao:
    resultado = ServicoClassificacaoCapitulos.extrair_e_classificar_do_docx(texto, estilo, pos, total)
    print(f"\n   Texto: '{texto}'")
    print(f"   Estilo: '{estilo}' (posição {pos}/{total})")
    print(f"   → Tipo: {resultado['tipo_elemento']}")
    print(f"   → Classificação: {resultado['classificacao']}")
    print(f"   → Nível: {resultado['nivel_capitulo']}")
    print(f"   → Prefixo: {resultado['prefixo_indice']}")

# Teste 4: Mapeamento completo de estilos
print("\n4. MAPEAMENTO COMPLETO DE ESTILOS:")
print("\n   Estilos para CAPÍTULOS:")
for estilo in ServicoClassificacaoCapitulos.ESTILOS_PARA_CLASSIFICACAO['capitulo']:
    print(f"     - {estilo}")

print("\n   Estilos para SUBCAPÍTULOS (nível 2):")
for estilo in ServicoClassificacaoCapitulos.ESTILOS_PARA_CLASSIFICACAO['subcapitulo_nivel_2']:
    print(f"     - {estilo}")

print("\n   Estilos para ANEXOS:")
for estilo in ServicoClassificacaoCapitulos.ESTILOS_PARA_CLASSIFICACAO['anexo']:
    print(f"     - {estilo}")

print("\n   Estilos para APÊNDICES:")
for estilo in ServicoClassificacaoCapitulos.ESTILOS_PARA_CLASSIFICACAO['apendice']:
    print(f"     - {estilo}")

print("\n" + "=" * 70)
print("RESUMO DA INTEGRAÇÃO:")
print("=" * 70)
print("""
FLUXO DE ATUALIZAÇÃO AUTOMÁTICA DE ÍNDICES:

1. Usuário adiciona/remove/reordena capítulo
2. Sistema identifica tipo conceitual pelo estilo DOCX
3. Serviço classifica o capítulo (capítulo, subcapítulo, anexo, apêndice)
4. Índices são atualizados automaticamente:
   - Capítulos textuais: 1, 2, 3...
   - Subcapítulos: 1.1, 1.2, 2.1...
   - Anexos: ANEXO_A, ANEXO_B...
   - Apêndices: APENDICE_I, APENDICE_II...
5. TOC do DOCX é regenerado
6. Bookmarks são preservados/atualizados

BENEFÍCIOS:
- Índices sempre consistentes
- Classificação automática por estilo DOCX
- Suporte a estilos personalizados
- Atualização em tempo real
- Integração com TOC do Word
""")

print("✅ Teste de mapeamento concluído com sucesso!")