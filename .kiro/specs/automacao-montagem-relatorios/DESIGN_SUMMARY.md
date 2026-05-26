# Design Summary: Automação de Montagem de Relatórios

**Data**: 26 de maio de 2026  
**Workflow**: Requirements-First (Requirements → Design → Tasks)  
**Status**: ✅ Design Completo e Pronto para Revisão

---

## O que foi Entregue

### 1. Documento design.md Completo

**Localização**: `.kiro/specs/automacao-montagem-relatorios/design.md`

**Seções incluídas** (todas as obrigatórias):
- ✅ **Overview**: Contexto, escopo, critérios de sucesso
- ✅ **Architecture**: Visão de componentes, layers de responsabilidade
- ✅ **Components and Interfaces**: 4 novos/melhorados serviços com contratos de API
- ✅ **Data Models**: Modelos SQLAlchemy melhorados, dicts de retorno padronizados
- ✅ **Correctness Properties**: 10 propriedades ortogonais para PBT (após prework + reflection)
- ✅ **Error Handling**: Estratégia centralizada, taxonomia de erros
- ✅ **Testing Strategy**: Unit + Property-Based Tests com Hypothesis
- ✅ **Decision Rationale**: 5 decisões de design justificadas
- ✅ **Key Assumptions and Constraints**: 5 assunções críticas
- ✅ **Future Enhancements**: 5 melhorias futuras

**Total**: ~900 linhas, estrutura completa de design

---

### 2. Config File

**Arquivo**: `.kiro/specs/automacao-montagem-relatorios/.config.kiro`

```json
{"specId": "51f73c22-8594-4324-9e83-667b2d3414b5", "workflowType": "requirements-first", "specType": "feature"}
```

---

### 3. Prework Analysis Completo

**Análise de Testabilidade**:
- ✅ 35+ critérios de aceitação analisados
- ✅ Cada um classificado como: PROPERTY | EXAMPLE | EDGE_CASE | INTEGRATION | SMOKE | NOT_TESTABLE
- ✅ 30+ critérios são apropriados para PBT (Property-Based Testing)

**Classificação por Tipo**:
| Tipo | Count | Descrição |
|------|-------|-----------|
| PROPERTY | 25+ | Testáveis via PBT (universal quantification) |
| EXAMPLE | 5+ | Cenários específicos (example-based) |
| INTEGRATION | 2 | Testes com serviços externos |
| NOT_TESTABLE | 3 | Não computáveis (performance, compatibilidade UI) |

---

### 4. Properties Após Prework + Reflection

**10 Propriedades Ortogonais**:

1. **Rastreabilidade Estruturada de Erros** — Req 1.1-1.5, NF-1
2. **Determinismo e Idempotência de Localização** — Req 2.1, 2.3, 2.5
3. **Coerência de Estrutura Retornada** — Req 1.2, 3.5
4. **Respeito a Classificação e Seções na Sync** — Req 4.1-4.5, Ex-3
5. **Parada Segura do Pipeline em Erro** — Req 1.4, 3.4, Ex-4
6. **Idempotência Completa do Pipeline** — NF-2, Ex-2
7. **Validação de Pré-Condições Rejeita Estados Inválidos** — Req 5.1-5.3, 3.2
8. **Validação e Reportagem de Inconsistências Pós-Pipeline** — Req 6.1-6.3, 3.5
9. **Segurança em Mensagens de Erro** — NF-5
10. **Determinismo de Match Multi-Nível** — Req 2.1, Determinismo

**Property Reflection**: Todas as 10 são não-redundantes (ortogonais)

---

## Cobertura de Requisitos

### Requirement 1: Structured Error Handling and Logging ✅

**Abordado por**:
- ServicoNiveladorErros (novo): Try-except centralizado + logging JSON
- Property 1: Rastreabilidade
- Error Handling section: Taxonomia de erros
- Testing section: Unit tests para captura de erros

**Détail**:
- Dict estruturado com `sucesso`, `erro`, `sugestoes`, `contexto`
- Logging em JSON com relatorio_id, capitulo_id, usuario_id, etapa
- Log ocorre ANTES de qualquer operação destrutiva
- Nenhuma operação falha silenciosamente (retorna erro explícito)

---

### Requirement 2: Robust Chapter Localization ✅

**Abordado por**:
- LocalizarRangeCapituloRobusto (melhorado): Multi-nível + fuzzy + contexto
- Property 2: Determinismo
- Property 3: Coerência de estrutura retornada
- Components section: API com confiança explícita

**Détail**:
- Estratégia cascata: exata → fuzzy (dist ≤ 2) → contexto (índice + tipo + classificacao)
- Retorna dict com `encontrado`, `confianca` (0.0-1.0), `diagnostico`, `alternativas`
- Integra `servico_classificacao_capitulos` para validar tipo
- Integra `servico_extracao_secoes` para respeitar limites de seção

---

### Requirement 3: Orchestrating Pipeline with Validation ✅

**Abordado por**:
- ServicoPipelineRelatorio (novo): Orquestrador completo
- Property 5: Parada em erro
- Property 6: Idempotência
- Property 7: Pré-condições
- Property 8: Pós-condições

**Détail**:
- `executar(relatorio_id, uploads_dict)` é ponto de entrada único
- Valida pré-condições antes de iniciar (Req 5)
- Executa em sequência: merge → numeração → cross-refs → TOC
- Para em primeiro erro (não executa etapas seguintes)
- Valida pós-condições ao fim (Req 6)
- Retorna resultado estruturado com todas as etapas

---

### Requirement 4: Classification Integration in Synchronization ✅

**Abordado por**:
- RessincronizarCapitulosComClassificacao (novo): Integra classificação + seções
- Property 4: Respeito a classificação
- Data Models: Novos campos em CapituloDocumento

**Détail**:
- Chama `ServicoClassificacaoCapitulos.classificar_por_titulo()` para cada capítulo
- Preenche `classificacao` (textual, anexo, apendice, etc.)
- Preenche `prefixo_indice` (A, I, 1, etc.)
- Integra `ServicoExtracaoSecoes` para preencher `id_secao_inicio` e `id_secao_fim`
- Banco fica alinhado com DOCX; queries por `classificacao` funcionam

---

### Requirement 5: Pre-condition Validation ✅

**Abordado por**:
- _ValidarPrecondiciones (novo): Valida antes de executar
- Property 7: Rejeita estados inválidos
- Testing section: Unit tests para pré-condições

**Détail**:
- Verifica: relatório existe?, capítulos sincronizados?, uploads válidos?
- Verifica: espaço em disco ok?, não há processamento em andamento?
- Retorna dict com `valido`, `motivos_rejeicao`, `avisos`
- Pipeline é recusado ANTES de qualquer operação

---

### Requirement 6: Post-condition Validation ✅

**Abordado por**:
- _ValidarPoscondiciones (novo): Valida após pipeline
- Property 8: Reporta inconsistências
- Testing section: Unit tests para pós-condições

**Détail**:
- Verifica: nenhuma legenda duplicada, numeração sequencial, TOC coerente
- Reporta: capítulos com inconsistências, avisos para coordenador
- Indica qual capítulo precisa de atenção
- Sugestões de ação para coordenador

---

## Modelos de Dados Novos/Melhorados

### CapituloDocumento

**Novos campos**:
```python
classificacao: str  # textual, pre_textual, pos_textual, anexo, apendice
prefixo_indice: str  # A, I, 1, etc.
id_secao_inicio: int (FK SecaoDOCX)
id_secao_fim: int (FK SecaoDOCX)
```

### Dicts Padronizados Retornados

1. **Resultado de Pipeline**: 10+ campos estruturados
2. **Resultado de Merge**: 8+ campos com confiança
3. **Resultado de Erro**: 9+ campos com sugestões
4. **Resultado de Sync**: Capitulos sincronizados + atualizações

---

## Estratégia de Testes

### Unit Tests (Example-Based)

**Cobertura**:
- ✅ Setup: Pré-condições (relatório não sincronizado, uploads inválidos)
- ✅ Merge: Exata, fuzzy, contexto, não encontrado, corrompido
- ✅ Numeração: Sequencial, idempotência
- ✅ Cross-refs: Tags substituídas, orfãs reportadas
- ✅ Índices: TOC com páginas, listas
- ✅ Pós-condições: Sem duplicatas, coerência

**Meta**: >90% linhas em `servico_pipeline_relatorio.py`

### Property-Based Tests (Hypothesis)

**10 Propriedades** com 100+ iterações cada:
1. Rastreabilidade (erros sempre estruturados)
2. Determinismo de localização
3. Coerência de estrutura
4. Classificação + seções
5. Parada em erro
6. Idempotência completa
7. Pré-condições validam
8. Pós-condições reportam
9. Segurança em mensagens
10. Match multi-nível determinístico

**Exemplos de generators**:
- `relatorio_fixture()`: Relatório aleatório com N capítulos
- `uploads_dict_fixture()`: Dict aleatório de uploads DOCX
- `failure_modes_fixture()`: Modos de falha aleatórios (corrompido, permissão, etc.)

---

## Decisões de Design Justificadas

### 1. Strategy Pattern em Localização (Multi-Nível)

**Problema**: Match exato frágil. Se coordenador edita "METODOLOGIA" → "METODO" (typo), merge falha silenciosamente.

**Solução**: Três estratégias em cascata
- Nível 1: Match exato (rápido, confiável)
- Nível 2: Fuzzy (detecta typos, edit distance ≤ 2)
- Nível 3: Contexto (índice + tipo + classificacao)

**Benefício**: Cobertura ampla; confiança explícita retornada

---

### 2. Dicts em Vez de Exceptions

**Problema**: Exceptions com stack traces assustam coordenador. Hard to aggregate erros de múltiplos capítulos.

**Solução**: Retornar `{'sucesso': bool, 'erro': str, 'sugestoes': [...]}`

**Benefício**: Coordenador vê quais capítulos falharam; pipeline continua processando

---

### 3. Centralizar Erros em ServicoNiveladorErros

**Problema**: Cada serviço tem try-except diferente; logging inconsistente

**Solução**: Wrapper `executar_com_tratamento()` com try-except centralizado

**Benefício**: Auditoria centralizada; menos código duplicado

---

### 4. Integrar Classificação em Sync

**Problema**: Campo `classificacao` em CapituloDocumento nunca é preenchido. Sistema não consegue diferenciar Anexo de Apêndice.

**Solução**: `ressincronizar_capitulos_com_classificacao()` chama classificador

**Benefício**: Banco alinhado com DOCX; ordenação por classificacao possível

---

### 5. Validar Pré-Condições Antes de Pipeline

**Problema**: Pipeline executa mesmo se relatório não sincronizado. Merge falha silenciosamente.

**Solução**: `_validar_precondiciones()` valida antes de iniciar

**Benefício**: Early failure; feedback claro ao coordenador

---

## PBT Applicability Assessment

### Por que PBT é Apropriado

✅ **Pure Functions com Input/Output Claro**: Localização de capítulo, validação, merge retornam dicts estruturados

✅ **Universal Properties que Valem para Todos os Inputs**: Idempotência, determinismo, rastreabilidade não dependem de valores específicos

✅ **Input Space Grande**: Capítulos com muitas variações (typos, estilos, ordem, seções)

✅ **Determinismo Necessário**: Executar 2x deve produzir mesmo resultado

### Por que PBT NÃO é Apropriado Para

❌ **Performance (NF-3)**: "< 30 segundos" é métrica, não property. Requer integration test + benchmark.

❌ **Compatibilidade (NF-4)**: "Word 2019+, LibreOffice 7.0+" requer testes com ferramentas reais, não PBT.

❌ **UI (Ex: Confirmação de Fuzzy Match)**: Comportamento visual, não testável por PBT.

---

## Próximos Passos (Phase 3: Tasks)

Após aprovação do design, próximo passo é criar `tasks.md` com:

1. **Sprint 1: Foundation** (Req-1)
   - Implementar `ServicoNiveladorErros`
   - Adicionar try-except + logging em serviços críticos
   - Unit tests para erro estruturado

2. **Sprint 2: Localização** (Req-2)
   - Implementar `localizar_range_capitulo_robusto()`
   - Multi-nível matching (exata → fuzzy → contexto)
   - Property tests para determinismo

3. **Sprint 3: Integração** (Req-4 + Req-5 + Req-6)
   - `ressincronizar_capitulos_com_classificacao()`
   - `ServicoPipelineRelatorio` orquestrador
   - Validações pré/pós

4. **Sprint 4: Testing**
   - Property tests com Hypothesis (100+ iterações)
   - Integration tests end-to-end
   - Coverage >90%

---

## Approval Checklist

- ✅ Design cobre TODOS os 6 requisitos
- ✅ Integração com serviços existentes é clara
- ✅ Contratos de API explícitos (método, parâmetros, retorno)
- ✅ Modelos de dados bem definidos
- ✅ Estratégia de testes viável (unit + property)
- ✅ Decisões de design justificadas (5 pontos críticos)
- ✅ 10 properties ortogonais após prework + reflection
- ✅ Error handling cobre casos principais (validação, I/O, interno, integração)
- ✅ Nenhuma ambiguidade em fluxos críticos
- ✅ Performance targets (<30s) realistas

---

## Referências

### Requisitos
- `requirements.md`: 6 requisitos funcionais + 5 não-funcionais + 5 exemplos de aceitação

### Análise de Contexto
- `ANALISE_CRITICA_FLUXOS_EXISTENTES.md`: Identificação de 6 gaps críticos e 5 oportunidades
- `ANALISE_SERVICOS_EXISTENTES.md`: Avaliação dos 18 serviços existentes

### Código Existente
- `servico_extracao_canonica.py`: Base para extração de estrutura
- `servico_classificacao_capitulos.py`: Classificador de capítulos
- `servico_extracao_secoes.py`: Extração de seções DOCX
- `servico_merge_docx.py`: Base para melhorias de localização
- `servico_sincronizar_capitulos.py`: Base para integração

---

**Design Completo e Pronto para Revisão do Coordenador/Arquiteto**
