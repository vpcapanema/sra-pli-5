#!/usr/bin/env python
"""Teste do modelo CapituloDocumento com conceito endurecido."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.capitulo_documento import CapituloDocumento

def test_capitulo_nivel_1():
    """Testa criação de capítulo de nível 1."""
    print("=== Teste: Capítulo Nível 1 ===")
    
    cap = CapituloDocumento(
        nivel_capitulo=1,
        tipo_elemento='textual',
        classificacao=None,
        indice_capitulo='1',
        titulo_capitulo='Introdução'
    )
    
    print(f"  e_capitulo: {cap.e_capitulo} (esperado: True)")
    print(f"  e_subcapitulo: {cap.e_subcapitulo} (esperado: False)")
    print(f"  e_anexo_ou_apendice: {cap.e_anexo_ou_apendice} (esperado: False)")
    print(f"  indice_completo: '{cap.indice_completo}' (esperado: '1')")
    
    erros = cap.validar_estrutura()
    print(f"  Validação: {'OK' if not erros else 'ERROS: ' + ', '.join(erros)}")
    
    return not erros

def test_subcapitulo():
    """Testa criação de subcapítulo."""
    print("\n=== Teste: Subcapítulo ===")
    
    sub = CapituloDocumento(
        nivel_capitulo=2,
        tipo_elemento='textual',
        classificacao=None,
        indice_capitulo='1.1',
        titulo_capitulo='Contexto'
    )
    
    print(f"  e_capitulo: {sub.e_capitulo} (esperado: False)")
    print(f"  e_subcapitulo: {sub.e_subcapitulo} (esperado: True)")
    print(f"  e_anexo_ou_apendice: {sub.e_anexo_ou_apendice} (esperado: False)")
    print(f"  indice_completo: '{sub.indice_completo}' (esperado: '1.1')")
    
    erros = sub.validar_estrutura()
    print(f"  Validação: {'OK' if not erros else 'ERROS: ' + ', '.join(erros)}")
    
    return not erros

def test_anexo():
    """Testa criação de anexo."""
    print("\n=== Teste: Anexo ===")
    
    anexo = CapituloDocumento(
        nivel_capitulo=1,
        tipo_elemento='pos_textual',
        classificacao='anexo',
        indice_capitulo='A',
        titulo_capitulo='Dados Brutos'
    )
    
    print(f"  e_capitulo: {anexo.e_capitulo} (esperado: False)")
    print(f"  e_subcapitulo: {anexo.e_subcapitulo} (esperado: False)")
    print(f"  e_anexo_ou_apendice: {anexo.e_anexo_ou_apendice} (esperado: True)")
    print(f"  indice_completo: '{anexo.indice_completo}' (esperado: 'ANEXO_A')")
    
    erros = anexo.validar_estrutura()
    print(f"  Validação: {'OK' if not erros else 'ERROS: ' + ', '.join(erros)}")
    
    return not erros

def test_apendice():
    """Testa criação de apêndice."""
    print("\n=== Teste: Apêndice ===")
    
    apendice = CapituloDocumento(
        nivel_capitulo=1,
        tipo_elemento='pos_textual',
        classificacao='apendice',
        indice_capitulo='I',
        titulo_capitulo='Glossário'
    )
    
    print(f"  e_capitulo: {apendice.e_capitulo} (esperado: False)")
    print(f"  e_subcapitulo: {apendice.e_subcapitulo} (esperado: False)")
    print(f"  e_anexo_ou_apendice: {apendice.e_anexo_ou_apendice} (esperado: True)")
    print(f"  indice_completo: '{apendice.indice_completo}' (esperado: 'APENDICE_I')")
    
    erros = apendice.validar_estrutura()
    print(f"  Validação: {'OK' if not erros else 'ERROS: ' + ', '.join(erros)}")
    
    return not erros

def test_validacoes_erro():
    """Testa validações que devem gerar erros."""
    print("\n=== Teste: Validações de Erro ===")
    
    testes_erro = [
        {
            'nome': 'Capítulo nível 1 com classificação',
            'obj': CapituloDocumento(nivel_capitulo=1, tipo_elemento='textual', classificacao='anexo')
        },
        {
            'nome': 'Capítulo nível 1 com tipo errado',
            'obj': CapituloDocumento(nivel_capitulo=1, tipo_elemento='pos_textual')
        },
        {
            'nome': 'Subcapítulo sem pai',
            'obj': CapituloDocumento(nivel_capitulo=2, tipo_elemento='textual')
        },
        {
            'nome': 'Subcapítulo com classificação',
            'obj': CapituloDocumento(nivel_capitulo=2, tipo_elemento='textual', classificacao='anexo')
        },
        {
            'nome': 'Anexo com classificação inválida',
            'obj': CapituloDocumento(tipo_elemento='pos_textual', classificacao='invalida')
        }
    ]
    
    todos_ok = True
    for teste in testes_erro:
        erros = teste['obj'].validar_estrutura()
        if erros:
            print(f"  ✅ {teste['nome']}: Gerou {len(erros)} erro(s) como esperado")
        else:
            print(f"  ❌ {teste['nome']}: Não gerou erros (era esperado)")
            todos_ok = False
    
    return todos_ok

def main():
    """Executa todos os testes."""
    print("=" * 60)
    print("TESTE DO MODELO CAPITULODOCUMENTO - CONCEITO ENDURECIDO")
    print("=" * 60)
    
    resultados = []
    
    resultados.append(("Capítulo Nível 1", test_capitulo_nivel_1()))
    resultados.append(("Subcapítulo", test_subcapitulo()))
    resultados.append(("Anexo", test_anexo()))
    resultados.append(("Apêndice", test_apendice()))
    resultados.append(("Validações de Erro", test_validacoes_erro()))
    
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)
    
    sucessos = 0
    for nome, resultado in resultados:
        status = "✅ PASS" if resultado else "❌ FAIL"
        print(f"  {status}: {nome}")
        if resultado:
            sucessos += 1
    
    print(f"\nTotal: {sucessos}/{len(resultados)} testes passaram")
    
    if sucessos == len(resultados):
        print("\n🎉 TODOS OS TESTES PASSARAM! Modelo implementado corretamente.")
        return 0
    else:
        print(f"\n⚠️  {len(resultados) - sucessos} teste(s) falharam.")
        return 1

if __name__ == "__main__":
    sys.exit(main())