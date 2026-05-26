#!/usr/bin/env python3
"""Teste do conceito endurecido de capítulos."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.capitulo_documento import CapituloDocumento

# Criar app de teste
app = create_app()
app.config['TESTING'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

with app.app_context():
    db.create_all()
    
    print("=" * 60)
    print("TESTE DO CONCEITO DE CAPÍTULOS ENDURECIDO")
    print("=" * 60)
    
    # Teste 1: Capítulo de nível 1 (textual)
    print("\n1. Testando CAPÍTULO (nível 1, textual):")
    cap1 = CapituloDocumento(
        nivel_capitulo=1,
        tipo_elemento='textual',
        titulo_capitulo='Introdução',
        indice_capitulo='1',
        ordem_capitulo=1
    )
    erros = cap1.validar_estrutura()
    print(f"   Título: {cap1.titulo_capitulo}")
    print(f"   É capítulo? {cap1.e_capitulo}")
    print(f"   É subcapítulo? {cap1.e_subcapitulo}")
    print(f"   É anexo/apêndice? {cap1.e_anexo_ou_apendice}")
    print(f"   Índice completo: {cap1.indice_completo}")
    print(f"   Erros: {erros}")
    
    # Teste 2: Subcapítulo
    print("\n2. Testando SUBCAPÍTULO (nível 2):")
    subcap = CapituloDocumento(
        nivel_capitulo=2,
        tipo_elemento='textual',
        titulo_capitulo='Contexto',
        indice_capitulo='1.1',
        ordem_capitulo=2,
        id_capitulo_pai=1  # Simulando pai
    )
    erros = subcap.validar_estrutura()
    print(f"   Título: {subcap.titulo_capitulo}")
    print(f"   É capítulo? {subcap.e_capitulo}")
    print(f"   É subcapítulo? {subcap.e_subcapitulo}")
    print(f"   Índice completo: {subcap.indice_completo}")
    print(f"   Erros: {erros}")
    
    # Teste 3: Anexo
    print("\n3. Testando ANEXO (pós-textual):")
    anexo = CapituloDocumento(
        nivel_capitulo=1,
        tipo_elemento='pos_textual',
        classificacao='anexo',
        titulo_capitulo='Planilhas de Dados',
        indice_capitulo='A',
        ordem_capitulo=10
    )
    erros = anexo.validar_estrutura()
    print(f"   Título: {anexo.titulo_capitulo}")
    print(f"   É capítulo? {anexo.e_capitulo}")
    print(f"   É subcapítulo? {anexo.e_subcapitulo}")
    print(f"   É anexo/apêndice? {anexo.e_anexo_ou_apendice}")
    print(f"   Índice completo: {anexo.indice_completo}")
    print(f"   Erros: {erros}")
    
    # Teste 4: Apêndice
    print("\n4. Testando APÊNDICE (pós-textual):")
    apendice = CapituloDocumento(
        nivel_capitulo=1,
        tipo_elemento='pos_textual',
        classificacao='apendice',
        titulo_capitulo='Glossário de Termos',
        indice_capitulo='I',
        ordem_capitulo=11
    )
    erros = apendice.validar_estrutura()
    print(f"   Título: {apendice.titulo_capitulo}")
    print(f"   É capítulo? {apendice.e_capitulo}")
    print(f"   É subcapítulo? {apendice.e_subcapitulo}")
    print(f"   É anexo/apêndice? {apendice.e_anexo_ou_apendice}")
    print(f"   Índice completo: {apendice.indice_completo}")
    print(f"   Erros: {erros}")
    
    # Teste 5: Casos inválidos
    print("\n5. Testando CASOS INVÁLIDOS:")
    
    # Capítulo com classificação
    cap_invalido1 = CapituloDocumento(
        nivel_capitulo=1,
        tipo_elemento='textual',
        classificacao='anexo',  # Inválido
        titulo_capitulo='Capítulo Inválido',
        indice_capitulo='2',
        ordem_capitulo=3
    )
    erros = cap_invalido1.validar_estrutura()
    print(f"   Capítulo com classificação: {erros}")
    
    # Subcapítulo sem pai
    subcap_invalido = CapituloDocumento(
        nivel_capitulo=2,
        tipo_elemento='textual',
        titulo_capitulo='Subcapítulo Inválido',
        indice_capitulo='2.1',
        ordem_capitulo=4
    )
    erros = subcap_invalido.validar_estrutura()
    print(f"   Subcapítulo sem pai: {erros}")
    
    print("\n" + "=" * 60)
    print("RESUMO DO CONCEITO:")
    print("=" * 60)
    print("""
CAPÍTULO (nível 1):
  - nivel_capitulo = 1
  - tipo_elemento = 'textual'
  - classificacao = None
  - id_capitulo_pai = None
  - Índice: 1, 2, 3...

SUBCAPÍTULO (nível ≥ 2):
  - nivel_capitulo ≥ 2
  - tipo_elemento = 'textual' (herda do pai)
  - classificacao = None
  - id_capitulo_pai = NOT NULL
  - Índice: 1.1, 1.2, 2.1...

ANEXO (pós-textual):
  - tipo_elemento = 'pos_textual'
  - classificacao = 'anexo'
  - Índice: ANEXO_A, ANEXO_B...

APÊNDICE (pós-textual):
  - tipo_elemento = 'pos_textual'
  - classificacao = 'apendice'
  - Índice: APENDICE_I, APENDICE_II...
    """)
    
    print("✅ Teste concluído com sucesso!")