# Diagnóstico - Automação de Montagem de Relatórios

**Data**: 26 de maio de 2026  
**Status**: Pronto para Aprovação  
**Objetivo**: Automatizar o trabalho repetitivo do coordenador ao montar relatórios mensais

---

## 🎯 O Problema Atual (Trabalho Manual do Coordenador)

**Cada mês**:
1. Coordenador clona DOCX do mês anterior
2. Recebe ~10-20 arquivos DOCX de autores (um por capítulo)
3. **Copia/cola** manualmente conteúdo de cada DOCX do autor
4. **Renumera manualmente**:
   - Capítulos: 1, 2, 3...
   - Subcapítulos: 1.1, 1.2, 2.1...
   - Tabelas: Tabela 1, Tabela 2, Tabela 3...
   - Figuras: Figura 1, Figura 2...
   - Equações: Equação 1, Equação 2...
5. **Atualiza cross-references**: `Tabela 1` → `Tabela 2` (se foi adicionada uma tabela antes)
6. **Regenera TOC**: Sumário com novos números de página
7. **Regenera Listas**: Figuras, Tabelas com números corretos
8. **Ajusta formatação**: Estilos, quebras de página, seções

**Resultado**: 8-12 horas de trabalho repetitivo, propenso a erros, todo mês.

---

## ✅ Solução Proposta

### Fluxo Automatizado

```
Mês N:
  1. Coordenador carrega DOCX template (clone do mês N-1)
     └─ Sistema EXTRAI estrutura
        ├─ Capítulos: títulos, níveis, tipos (textual/pós-textual)
        ├─ Seções DOCX: tipos de quebra, margens, numeração
        ├─ Numeração atual: qual tabela é a última? qual figura?
        └─ Índices: como estão os números de página?

  2. Coordenador recebe 10+ DOCX de autores (entregas parciais)

  3. Sistema MESCLA automaticamente
     ├─ Detecta qual capítulo cada DOCX representa
     ├─ Localiza o range de parágrafo/seção desse capítulo no template
     └─ Substitui conteúdo in-place (merge)

  4. Sistema RENUMERA automaticamente
     ├─ Capítulos: 1, 2, 3... (ordem preservada)
     ├─ Tabelas: Tabela 1, 2, 3... (sequencial)
     ├─ Figuras: Figura 1, 2, 3... (sequencial)
     ├─ Equações: Equação 1, 2, 3... (sequencial)
     └─ Atualiza todos os cross-references

  5. Sistema REGENERA índices
     ├─ TOC (Sumário): com números de página corretos
     ├─ Lista de Figuras: com números corretos
     ├─ Lista de Tabelas: com números corretos
     └─ Validação ABNT: ordem correta

  6. Coordenador APROVA e FINALIZA
     └─ Sistema gera relatório final (PDF + DOCX)

Resultado: 30 minutos de trabalho (review + aprovação)
```

---

## 🔍 Análise Técnica do Estado Atual

### Serviços que JÁ FAZEM Parte do Trabalho

| Serviço | Função | Estado |
|---------|--------|--------|
| `servico_extracao_canonica` | Extrai estrutura do DOCX | ✅ Existe |
| `servico_sincronizar_capitulos` | Sincroniza capítulos banco↔DOCX | ✅ Existe |
| `servico_merge_docx` | Mescla conteúdo de capítulos | ✅ Existe (parcial) |
| `servico_captioning` | Numeração de figuras/tabelas | ✅ Existe (precisa integração) |
| `servico_cross_refs` | Atualiza referências cruzadas | ✅ Existe (precisa integração) |
| `servico_toc` | Gera TOC com números de página | ✅ Existe (precisa integração) |

### Gaps Identificados

**1. Detecção Automática de Capítulos**
- Sistema extrai estrutura, mas não classifica capítulos
- Não distingue: Capítulo vs Anexo vs Apêndice vs Pré-textual
- **Gap**: Algoritmo de classificação por estilo DOCX + contexto

**2. Localização Automática de Range**
- `servico_merge_docx` tenta localizar capítulo, mas falha em casos complexos
- Não considera seções DOCX (quebras de página)
- **Gap**: Algoritmo robusto de localização que respeita layout

**3. Numeração Unificada**
- Cada serviço numera isoladamente (captioning, cross_refs)
- Sem coordenação central
- Quando um elemento é adicionado/removido, todos precisam ser atualizados
- **Gap**: Sistema central de numeração com cascata de atualizações

**4. Rastreamento de Páginas**
- Sistema não rastreia números de página entre documentos
- TOC gerado manualmente com números errados
- **Gap**: Algoritmo que calcula números de página considerando seções DOCX

**5. Integração Automática**
- Serviços existem, mas não há orquestração automática
- Coordenador ainda faz manualmente: merge → captioning → cross_refs → TOC
- **Gap**: Pipeline automático que chama serviços em sequência

---

## 🛠️ Componentes Necessários

### 1. **ServicoClassificacaoCapitulos** (Novo)
```python
# Classifica capítulos automaticamente
classificacao = classificar_capitulo(
    estilo_docx='Heading 1',
    titulo='METODOLOGIA',
    tipo_elemento='textual'
)
# Retorna: {'tipo': 'capitulo', 'prefixo': '', 'nivel': 1}

classificacao = classificar_capitulo(
    estilo_docx='Título Anexo',
    titulo='ANEXO A - Formulários',
    tipo_elemento='pos_textual'
)
# Retorna: {'tipo': 'anexo', 'prefixo': 'ANEXO_', 'nivel': 1}
```

**Benefício**: Distinguir automaticamente que conteúdo é capítulo vs anexo

---

### 2. **ServicoLocalizacaoCapitulos** (Novo)
```python
# Encontra onde um capítulo está no DOCX
range_capitulo = localizar_capitulo(
    doc=docx_producao,
    titulo_capitulo='RESULTADOS',
    estilo_esperado='Heading 1'
)
# Retorna: {'paragrafo_inicio': 150, 'paragrafo_fim': 250, 'secao': 2}

# Valida se é o range certo
assert range_capitulo['titulo_inicio'] == 'RESULTADOS'
assert range_capitulo['secao_tipo'] == 'nextPage'  # Começa em nova página
```

**Benefício**: Merge robusto mesmo com reordenações/renomeações

---

### 3. **ServicoNumeracaoUnificada** (Novo)
```python
# Coordena numeração de todos os elementos
numeracao = ServicoNumeracaoUnificada(docx_producao)

# Após adicionar novo capítulo
numeracao.atualizar_capitulos()  # 1,2,3,4... (renumera se necessário)
numeracao.atualizar_tabelas()    # Tabela 1, 2, 3... (sequencial)
numeracao.atualizar_figuras()    # Figura 1, 2, 3... (sequencial)
numeracao.atualizar_equacoes()   # Equação 1, 2, 3... (sequencial)

# Obtém números atualizados para qualquer elemento
numero_tabela_nova = numeracao.obter_numero('tabela', id=42)
# Retorna: 5 (é a 5ª tabela do documento)
```

**Benefício**: Única fonte de verdade para numeração; evita inconsistências

---

### 4. **ServicoRastreamentoPaginas** (Novo)
```python
# Calcula números de página considerando seções DOCX
rastreamento = ServicoRastreamentoPaginas(docx_producao)

# Detecta onde cada capítulo começa
paginas = rastreamento.calcular_paginas_capitulos()
# Retorna: {cap1: 1, cap2: 15, cap3: 32, ...}

# Detecta onde cada figura/tabela está
paginas_tabelas = rastreamento.calcular_paginas_por_tipo('tabela')
# Retorna: {tabela1: 5, tabela2: 8, tabela3: 25, ...}

# TOC pode usar isto para números corretos
```

**Benefício**: TOC e listas com números de página precisos

---

### 5. **ServicoPipelineRelatorio** (Novo - Orquestrador)
```python
# Automatiza o fluxo completo
pipeline = ServicoPipelineRelatorio(docx_template, docx_autores=[...])

# Executa todas as etapas automaticamente
resultado = pipeline.executar()
# Internamente:
#   1. Classifica capítulos
#   2. Localiza cada capítulo
#   3. Mescla conteúdo
#   4. Renumera tudo
#   5. Atualiza cross-refs
#   6. Regenera TOC/listas
#   7. Retorna DOCX pronto

# Coordenador só precisa validar
assert resultado['status'] == 'sucesso'
resultado['docx'].save('relatorio_completo.docx')
```

**Benefício**: Uma linha de código para fazer o que demorava horas

---

## 📊 Impacto Esperado

| Atividade | Antes | Depois | Ganho |
|-----------|-------|--------|-------|
| Merge conteúdo | 3h manual | 10min automático | 94% ↓ |
| Renumerar capítulos | 1h | 1min | 98% ↓ |
| Renumerar tabelas/figuras | 2h | 2min | 98% ↓ |
| Atualizar cross-refs | 2h | 1min | 99% ↓ |
| Regenerar TOC/listas | 2h | 2min | 98% ↓ |
| Review + aprovação | 1h | 30min | 50% ↓ |
| **TOTAL** | **11h** | **30min** | **95% ↓** |

**Resultado**: De 11 horas para 30 minutos. Coordenador foca em review, não em tarefas repetitivas.

---

## 🔄 Fluxo de Implementação

### Fase 1: Classificação (1 semana)
- Implementar `ServicoClassificacaoCapitulos`
- Testar com 5+ documentos reais
- Testes: 15+ casos (Heading 1, Anexo, Pré-textual, etc.)

### Fase 2: Localização (1 semana)
- Implementar `ServicoLocalizacaoCapitulos`
- Testar com documentos com capítulos reordenados
- Testes: 20+ casos (renomeações, reordenações, fusões)

### Fase 3: Numeração (1-2 semanas)
- Implementar `ServicoNumeracaoUnificada`
- Integrar com `servico_captioning` + `servico_cross_refs`
- Testes: 25+ casos (adição, remoção, reordenação)

### Fase 4: Rastreamento (1 semana)
- Implementar `ServicoRastreamentoPaginas`
- Integrar com `servico_toc`
- Testes: 15+ casos (múltiplas seções, numeração diferente)

### Fase 5: Orquestração (1 semana)
- Implementar `ServicoPipelineRelatorio`
- Teste end-to-end com fluxo completo
- Testes: 10+ cenários reais

### Fase 6: Validação (1-2 semanas)
- Testes de regressão (todos os 18 serviços)
- Testes com 20+ documentos reais
- Performance: <2min para DOCX com 500 páginas

**Total**: 6-8 semanas com 1 pessoa fulltime

---

## ✅ Critérios de Sucesso

- [ ] Merge automático funciona 100% das vezes
- [ ] Numeração sem inconsistências (0 tabelas duplicadas)
- [ ] Cross-refs atualizadas automaticamente
- [ ] TOC com números de página corretos
- [ ] Coordenador economiza 10+ horas/mês
- [ ] Documentação completa
- [ ] >80% cobertura de testes
- [ ] 0 bugs críticos em produção

---

## 📝 Próximos Passos

1. **Sua aprovação** desta visão
2. **Detalhamento de tasks** focado em codificação prática
3. **Delegação para agente de execução** com escopo claro
4. **Implementação faseada** com validação contínua

---

**Pronto para prosseguir com plano de tasks detalhado?**
