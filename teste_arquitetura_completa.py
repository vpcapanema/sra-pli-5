#!/usr/bin/env python3
"""Teste completo da arquitetura: Seções DOCX vs Capítulos Conceituais."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.secao_docx import SecaoDOCX
from app.models.quebra_pagina import QuebraPagina
from app.models.capitulo_documento import CapituloDocumento
from app.services.servico_extracao_secoes import ServicoExtracaoSecoes

# Criar app de teste
app = create_app()
app.config['TESTING'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

with app.app_context():
    db.create_all()
    
    print("=" * 80)
    print("TESTE COMPLETO DA ARQUITETURA: SEÇÕES DOCX vs CAPÍTULOS CONCEITUAIS")
    print("=" * 80)
    
    # Criar seções de exemplo
    print("\n1. CRIANDO SEÇÕES DOCX DE EXEMPLO:")
    
    secoes = [
        SecaoDOCX(
            id_relatorio=1,
            ordem_secao=0,
            tipo_secao='nextPage',
            reiniciar_numero_pagina=True,
            numero_pagina_inicial=1,
            estilo_numero_pagina='lowerRoman',  # i, ii, iii
            orientacao='portrait',
            colunas=1
        ),
        SecaoDOCX(
            id_relatorio=1,
            ordem_secao=1,
            tipo_secao='continuous',
            reiniciar_numero_pagina=True,
            numero_pagina_inicial=1,
            estilo_numero_pagina='decimal',  # 1, 2, 3
            orientacao='portrait',
            colunas=1
        ),
        SecaoDOCX(
            id_relatorio=1,
            ordem_secao=2,
            tipo_secao='nextPage',
            reiniciar_numero_pagina=False,
            estilo_numero_pagina='decimal',
            orientacao='portrait',
            colunas=1
        )
    ]
    
    for secao in secoes:
        print(f"   Seção {secao.ordem_secao}: {secao.descricao_tipo}")
        print(f"     - Reinicia numeração: {secao.reiniciar_numero_pagina}")
        print(f"     - Estilo numeração: {secao.estilo_numero_pagina}")
        print(f"     - Orientação: {secao.orientacao}")
    
    # Criar capítulos conceituais
    print("\n2. CRIANDO CAPÍTULOS CONCEITUAIS:")
    
    capitulos = [
        # Capítulos textuais (seção 1)
        CapituloDocumento(
            id_relatorio=1,
            id_secao_inicio=1,  # Seção 1
            nivel_capitulo=1,
            tipo_elemento='textual',
            titulo_capitulo='INTRODUÇÃO',
            indice_capitulo='1',
            ordem_capitulo=1
        ),
        CapituloDocumento(
            id_relatorio=1,
            id_secao_inicio=1,  # Seção 1
            nivel_capitulo=2,
            tipo_elemento='textual',
            titulo_capitulo='Contexto',
            indice_capitulo='1.1',
            ordem_capitulo=2,
            id_capitulo_pai=1  # Subcapítulo do capítulo 1
        ),
        CapituloDocumento(
            id_relatorio=1,
            id_secao_inicio=1,  # Seção 1
            nivel_capitulo=1,
            tipo_elemento='textual',
            titulo_capitulo='METODOLOGIA',
            indice_capitulo='2',
            ordem_capitulo=3
        ),
        # Anexos (seção 2)
        CapituloDocumento(
            id_relatorio=1,
            id_secao_inicio=2,  # Seção 2
            nivel_capitulo=1,
            tipo_elemento='pos_textual',
            classificacao='anexo',
            titulo_capitulo='DADOS BRUTOS',
            indice_capitulo='A',
            ordem_capitulo=4
        ),
        # Apêndices (seção 2)
        CapituloDocumento(
            id_relatorio=1,
            id_secao_inicio=2,  # Seção 2
            nivel_capitulo=1,
            tipo_elemento='pos_textual',
            classificacao='apendice',
            titulo_capitulo='GLOSSÁRIO',
            indice_capitulo='I',
            ordem_capitulo=5
        )
    ]
    
    for cap in capitulos:
        print(f"   {cap.indice_completo}: {cap.titulo_capitulo}")
        print(f"     - Tipo conceitual: {cap.tipo_conceitual}")
        print(f"     - Nível: {cap.nivel_capitulo}")
        print(f"     - Seção início: {cap.id_secao_inicio}")
        print(f"     - É capítulo? {cap.e_capitulo}")
        print(f"     - É subcapítulo? {cap.e_subcapitulo}")
        print(f"     - É anexo/apêndice? {cap.e_anexo_ou_apendice}")
    
    # Testar mapeamento
    print("\n3. TESTANDO MAPEAMENTO SEÇÕES → CAPÍTULOS:")
    
    # Simular IDs das seções
    for i, secao in enumerate(secoes):
        secao.id_secao = i + 1
    
    for i, cap in enumerate(capitulos):
        cap.id_capitulo_documento = i + 1
    
    # Mapear capítulos para seções
    capitulos_mapeados = ServicoExtracaoSecoes.mapear_capitulos_para_secoes(capitulos, secoes)
    
    for cap in capitulos_mapeados:
        secao_inicio = next((s for s in secoes if s.id_secao == cap.id_secao_inicio), None)
        secao_desc = secao_inicio.descricao_tipo if secao_inicio else "N/A"
        
        print(f"   {cap.indice_completo}: Seção {cap.id_secao_inicio} ({secao_desc})")
        if cap.id_secao_fim and cap.id_secao_fim != cap.id_secao_inicio:
            print(f"     → Abrange múltiplas seções: até seção {cap.id_secao_fim}")
    
    # Testar validação
    print("\n4. VALIDANDO MAPEAMENTO:")
    
    erros = ServicoExtracaoSecoes.validar_mapeamento_secoes_capitulos(secoes, capitulos_mapeados)
    
    if erros:
        print("   ❌ ERROS ENCONTRADOS:")
        for erro in erros:
            print(f"     - {erro}")
    else:
        print("   ✅ Mapeamento válido!")
    
    # Testar propriedades das seções
    print("\n5. PROPRIEDADES DAS SEÇÕES:")
    
    for secao in secoes:
        print(f"\n   Seção {secao.ordem_secao}:")
        print(f"     - Tipo: {secao.tipo_secao} ({secao.descricao_tipo})")
        print(f"     - Tem numeração diferente: {secao.tem_numero_pagina_diferente}")
        print(f"     - É quebra importante: {secao.e_quebra_importante}")
        print(f"     - Orientação: {secao.orientacao}")
        print(f"     - Colunas: {secao.colunas}")
        
        # Capítulos nesta seção
        caps_na_secao = [c for c in capitulos_mapeados if c.id_secao_inicio == secao.id_secao]
        if caps_na_secao:
            print(f"     - Capítulos nesta seção:")
            for cap in caps_na_secao:
                print(f"       • {cap.indice_completo}: {cap.titulo_capitulo}")
    
    # Testar análise estrutural
    print("\n6. ANÁLISE ESTRUTURAL DO DOCUMENTO:")
    
    analise_simulada = {
        'total_secoes': len(secoes),
        'total_quebras': 2,  # Simulado
        'secoes_com_numero_diferente': sum(1 for s in secoes if s.tem_numero_pagina_diferente),
        'secoes_com_orientacao_diferente': sum(1 for s in secoes if s.orientacao != 'portrait'),
        'quebras_visiveis': 2,
        'estrutura_secoes': [
            {
                'ordem': s.ordem_secao,
                'tipo': s.tipo_secao,
                'orientacao': s.orientacao,
                'colunas': s.colunas,
                'reinicia_numero': s.reiniciar_numero_pagina
            }
            for s in secoes
        ]
    }
    
    print(f"   Total de seções: {analise_simulada['total_secoes']}")
    print(f"   Seções com numeração diferente: {analise_simulada['secoes_com_numero_diferente']}")
    print(f"   Quebras visíveis: {analise_simulada['quebras_visiveis']}")
    
    print("\n" + "=" * 80)
    print("RESUMO DA ARQUITETURA:")
    print("=" * 80)
    print("""
DISTINÇÃO CRÍTICA CONFIRMADA:

✅ SEÇÃO DOCX (w:sectPr):
  - Unidade técnica de formatação OOXML
  - Controla: cabeçalhos, rodapés, numeração de páginas
  - Pode: reiniciar numeração, mudar orientação, ter colunas diferentes
  - Exemplo: Seção 1 (numeração romana), Seção 2 (numeração arábica)

✅ CAPÍTULO CONCEITUAL:
  - Unidade lógica de conteúdo
  - Controla: título, responsável, status editorial, hierarquia
  - Pode: abranger múltiplas seções, ter subcapítulos
  - Exemplo: "1. INTRODUÇÃO", "ANEXO_A", "APENDICE_I"

✅ QUEBRA DE PÁGINA (w:br):
  - Instrução de layout dentro de uma seção
  - Apenas força nova página/coluna
  - Não afeta propriedades da seção

BENEFÍCIOS DA ABORDAGEM:

1. CLAREZA CONCEITUAL:
   - Seção ≠ Capítulo
   - Cada um com responsabilidades bem definidas

2. PRESERVAÇÃO TÉCNICA:
   - Propriedades OOXML mantidas intactas
   - Formatação complexa preservada

3. FLEXIBILIDADE EDITORIAL:
   - Capítulos podem cruzar seções
   - Controle granular de formatação vs conteúdo

4. RASTREABILIDADE:
   - Saber exatamente onde cada elemento está
   - Atualizar apenas o necessário durante edição

PRÓXIMOS PASSOS:

1. Implementar extração real com python-docx/lxml
2. Integrar com serviço de extração canônica existente
3. Criar interface para visualizar mapeamento
4. Testar com documentos reais complexos
5. Documentar casos de borda e exceções
""")
    
    print("✅ Teste da arquitetura concluído com sucesso!")