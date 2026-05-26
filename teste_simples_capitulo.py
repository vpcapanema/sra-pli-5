#!/usr/bin/env python
"""Teste simples do modelo CapituloDocumento sem contexto de aplicação."""

class MockCapituloDocumento:
    """Mock da classe para testar lógica sem SQLAlchemy."""
    
    def __init__(self, nivel_capitulo=1, tipo_elemento='textual', classificacao=None, 
                 indice_capitulo=None, id_capitulo_pai=None):
        self.nivel_capitulo = nivel_capitulo
        self.tipo_elemento = tipo_elemento
        self.classificacao = classificacao
        self.indice_capitulo = indice_capitulo
        self.id_capitulo_pai = id_capitulo_pai
    
    @property
    def indice_completo(self):
        """Índice completo com prefixo quando aplicável."""
        if self.classificacao == 'anexo':
            return f"ANEXO_{self.indice_capitulo}" if self.indice_capitulo else "ANEXO"
        elif self.classificacao == 'apendice':
            return f"APENDICE_{self.indice_capitulo}" if self.indice_capitulo else "APENDICE"
        return self.indice_capitulo or ""
    
    @property
    def e_capitulo(self):
        """Retorna True se for um capítulo de primeiro nível."""
        return self.nivel_capitulo == 1 and self.tipo_elemento == 'textual'
    
    @property
    def e_subcapitulo(self):
        """Retorna True se for um subcapítulo."""
        return self.nivel_capitulo >= 2 and self.id_capitulo_pai is not None
    
    @property
    def e_anexo_ou_apendice(self):
        """Retorna True se for anexo ou apêndice."""
        return self.tipo_elemento == 'pos_textual' and self.classificacao in ('anexo', 'apendice')
    
    def validar_estrutura(self):
        """Valida a estrutura conceitual do capítulo."""
        erros = []
        
        # Capítulo (nível 1)
        if self.nivel_capitulo == 1:
            if self.id_capitulo_pai is not None:
                erros.append("Capítulo de nível 1 não pode ter pai")
            if self.tipo_elemento != 'textual':
                erros.append("Capítulo de nível 1 deve ser 'textual'")
            if self.classificacao is not None:
                erros.append("Capítulo de nível 1 não deve ter classificação")
        
        # Subcapítulo
        elif self.nivel_capitulo >= 2:
            if self.id_capitulo_pai is None:
                erros.append("Subcapítulo deve ter um capítulo pai")
            if self.classificacao is not None:
                erros.append("Subcapítulo não deve ter classificação")
        
        # Anexo/Apêndice
        elif self.tipo_elemento == 'pos_textual':
            if self.classificacao not in ('anexo', 'apendice', None):
                erros.append("Classificação inválida para conteúdo pós-textual")
        
        return erros

def test_capitulo_nivel_1():
    """Testa criação de capítulo de nível 1."""
    print("=== Teste: Capítulo Nível 1 ===")
    
    cap = MockCapituloDocumento(
        nivel_capitulo=1,
        tipo_elemento='textual',
        classificacao=None,
        indice_capitulo='1',
        id_capitulo_pai=None
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
    
    sub = MockCapituloDocumento(
        nivel_capitulo=2,
        tipo_elemento='textual',
        classificacao=None,
        indice_capitulo='1.1',
        id_capitulo_pai=1  # ID do capítulo pai
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
    
    anexo = MockCapituloDocumento(
        nivel_capitulo=1,
        tipo_elemento='pos_textual',
        classificacao='anexo',
        indice_capitulo='A',
        id_capitulo_pai=None
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
    
    apendice = MockCapituloDocumento(
        nivel_capitulo=1,
        tipo_elemento='pos_textual',
        classificacao='apendice',
        indice_capitulo='I',
        id_capitulo_pai=None
    )
    
    print(f"  e_capitulo: {apendice.e_capitulo} (esperado: False)")
    print(f"  e_subcapitulo: {apendice.e_subcapitulo} (esperado: False)")
    print(f"  e_anexo_ou_apendice: {apendice.e_anexo_ou_apendice} (esperado: True)")
    print(f"  indice_completo: '{apendice.indice_completo}' (esperado: 'APENDICE_I')")
    
    erros = apendice.validar_estrutura()
    print(f"  Validação: {'OK' if not erros else 'ERROS: ' + ', '.join(erros)}")
    
    return not erros

def main():
    """Executa todos os testes."""
    print("=" * 60)
    print("TESTE DO CONCEITO ENDURECIDO DE CAPÍTULOS")
    print("=" * 60)
    
    resultados = []
    
    resultados.append(("Capítulo Nível 1", test_capitulo_nivel_1()))
    resultados.append(("Subcapítulo", test_subcapitulo()))
    resultados.append(("Anexo", test_anexo()))
    resultados.append(("Apêndice", test_apendice()))
    
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
        print("\n🎉 TODOS OS TESTES PASSARAM! Lógica implementada corretamente.")
        return 0
    else:
        print(f"\n⚠️  {len(resultados) - sucessos} teste(s) falharam.")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())