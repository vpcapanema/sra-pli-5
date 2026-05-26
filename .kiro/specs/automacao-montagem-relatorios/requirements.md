# Automação de Montagem de Relatórios

## Introduction

O Sistema de Relatório de Atividades (SRA) é uma aplicação Flask de montagem colaborativa de relatórios DOCX. Atualmente, o fluxo de submissão de capítulos pelos autores é manual, desacoplado e sem tratamento de erros explícito, resultando em 11 horas/mês de trabalho repetitivo pelo coordenador e múltiplos erros silenciosos.

Este documento formaliza requisitos para automação confiável através de três oportunidades integradas: (O7) Logging e tratamento estruturado de erros, (O1) Localização robusta de capítulos com múltiplas estratégias de match, e (O5) Pipeline orquestrador que valida pré-condições, executa etapas coordenadas com feedback claro.

Após implementação, o fluxo será reduzido para 30 minutos com zero erros silenciosos e compliance ABNT completo (TOC com páginas).

## Glossary

- **Relatório**: Documento DOCX montado a partir de conteúdo enviado por autores
- **Capítulo**: Unidade de conteúdo hierarquicamente estruturada (seção de H1)
- **Classificação**: Tipo de capítulo (textual, pré-textual, anexo, apêndice, pós-textual)
- **Seção DOCX**: Divisão OOXML de documento (próxima/contínua), pode ter numeração diferente
- **Template/Master**: DOCX-base que define estrutura canônica do relatório
- **Merge**: Operação de substituição de capítulo no template com conteúdo do autor
- **Captioning**: Numeração automática de figuras, tabelas e equações
- **Cross-refs**: Substitui tags de referência com campos REF do Word
- **TOC**: Table of Contents (Sumário/Índice)
- **Idempotência**: Propriedade de operação que pode ser executada múltiplas vezes com resultado equivalente
- **Pipeline**: Sequência automática de etapas coordenadas (merge → captioning → cross-refs → toc)

## Requirements

### Requirement 1: Structured Error Handling and Logging

**User Story**: Como coordenador, quero receber feedback claro quando uma operação falha, para não perder tempo debugando.

1. THE System SHALL implement try-except with logging.
2. WHEN an operation is executed, THE ErrorHandler SHALL return standardized dict.
3. WHEN an exception is captured, THE Logger SHALL record context.
4. WHILE an error exists, THE System SHALL not proceed with subsequent steps.
5. IF an operation would fail silently, THE System SHALL raise exception.

---

### Requirement 2: Robust Chapter Localization

**User Story**: Como coordenador, quero que a substituição de capítulos funcione mesmo com variações no formato do título.

1. WHEN coordenador faz upload, THE MergeService SHALL locate capítulo using multi-level strategy.
2. THE MergeService SHALL integrate classification and section extraction.
3. WHEN capítulo is located, THE MergeService SHALL return detailed dict with confidence.
4. IF capítulo is not located, THE MergeService SHALL return error dict with suggestions.
5. IF multiple matches exist, THE System SHALL select highest confidence or request confirmation.

---

### Requirement 3: Orchestrating Pipeline with Validation

**User Story**: Como coordenador, quero executar TODO o fluxo de montagem (merge → captioning → cross-refs → toc) em uma única ação confiável.

1. THE System SHALL provide class ServicoPipelineRelatorio with method executar(relatorio_id, uploads_dict).
2. WHEN pipeline starts, THE System SHALL validate preconditions before execution.
3. WHEN merge completes, THE Pipeline SHALL execute numeração, cross-refs, toc in sequence.
4. IF merge fails, THE Pipeline SHALL stop and return error with details.
5. WHEN all stages complete, THE Pipeline SHALL validate postconditions and return comprehensive result dict.

---

### Requirement 4: Classification Integration in Synchronization

**User Story**: Como administrador, quero que o banco de dados reflita corretamente se um capítulo é Anexo ou Apêndice.

1. WHEN servico_sincronizar_capitulos executes, THE System SHALL call classifier for each capítulo.
2. THE System SHALL update CapituloDocumento with classificacao and prefixo_indice fields.
3. WHEN synchronization occurs, THE System SHALL extract DOCX sections and map capítulos.
4. THE System SHALL update id_secao_inicio and id_secao_fim for each capítulo.
5. AFTER synchronization, THE Repository SHALL enable ordering by classificacao and prefixo_indice.

---

### Requirement 5: Pre-condition Validation

**User Story**: Como coordenador, quero evitar processar um relatório em estado inválido.

1. IF capítulos not synchronized, THE System SHALL refuse merge with clear message.
2. IF previous upload failed, THE System SHALL indicate error and suggest cleanup.
3. IF multiple pending uploads exist, THE System SHALL offer batch processing option.

---

### Requirement 6: Post-condition Validation

**User Story**: Como coordenador, quero saber se o documento gerado está completo e coerente.

1. WHILE pipeline completes, THE System SHALL validate all postconditions.
2. IF inconsistency detected, THE System SHALL return warnings with details.
3. THE System SHALL indicate in UI which capítulos need attention.

---

## Non-Functional Requirements

### NF-1: Structured Logging

THE System SHALL implement JSON-structured logging with context: timestamp, nivel, relatorio_id, capitulo_id, usuario_id, etapa, mensagem, stack_trace, detalhes.

### NF-2: Idempotency

All critical operations (merge, captioning, toc) SHALL be idempotent: executing 2x produces equivalent result, no duplicates (legenda, bookmark, heading), no performance degradation.

### NF-3: Performance

Pipeline complete (5 capítulos, 30 figuras, 10 tabelas) SHALL complete in < 30 seconds.

### NF-4: DOCX Compatibility

Code SHALL work with: Microsoft Word 2019+, LibreOffice 7.0+, multiple OOXML sections, custom styles.

### NF-5: Security

Não expor caminhos de arquivo em mensagens públicas, não logar dados sensíveis, validar permissões antes de modificar DOCX.

---

## Acceptance Test Examples

### Example 1: Error Silent Becomes Visible

**Cenário**: Upload com typo em título (METOLOGIA vs METODOLOGIA).

**Esperado (com Req-1 + Req-2 + Req-3)**:
- Match fuzzy detecta typo (distância edit = 1)
- Pipeline oferece confirmação "Confirmar merge de 'METOLOGIA' → 'METODOLOGIA'?"
- Log registra: `[INFO] Fuzzy match (confianca=0.85, estrategia=fuzzy)`
- Coordenador recebe feedback (UI alert)

### Example 2: Pipeline Idempotent

**Propriedade**: Executar pipeline 2x com mesma entrada produz arquivo idêntico.

**Teste**:
```
resultado_1 = ServiçoPipelineRelatorio.executar(entrada)
hash_1 = sha256(arquivo)
resultado_2 = ServiçoPipelineRelatorio.executar(entrada)
hash_2 = sha256(arquivo)
assert hash_1 == hash_2
```

### Example 3: Multiple Sections Respected

**Cenário**: Template com pré-textual (romano), textual (arábico), apêndices.

**Esperado**:
- Merge respeita limites de seção
- Captioning gera "Figura I.1" em pré-textual, "Figura 1.1" em textual, "Figura A.1" em apêndice
- TOC mostra numeração correta de página

### Example 4: Merge Fails → Pipeline Stops

**Cenário**: Capítulo 2 não encontrado.

**Esperado**:
- Merge Cap1: OK
- Merge Cap2: ERRO (capítulo não localizado)
- Pipeline PARAR (não executa numeração/cross-refs/toc)
- Retorna: erro estruturado com sugestões
- Arquivo não modificado além de Cap1

### Example 5: DOCX Corrupted → Graceful Error

**Cenário**: Upload de arquivo ZIP inválido.

**Esperado**:
- Não crash (500 error)
- Retorna erro: "Arquivo DOCX inválido (erro ao descompactar ZIP)"
- Log registra stack trace
- Coordenador vê mensagem: "Arquivo corrompido. Tente fazer upload novamente."

---

## Dependencies Between Requirements

```
Req-1 (Logging) — Fundação
    ↓
Req-2 (Localização) + Req-4 (Classificação)
    ↓
Req-3 (Pipeline)
    ↓
Req-5 (Pré-condições) + Req-6 (Pós-condições)
```

**Ordem de Implementação**:
1. Req-1 (Logging — fundacional para todas as outras)
2. Req-2 (Localização — bloqueia merge)
3. Req-4 (Classificação — enriquece dados de sync)
4. Req-3 (Pipeline — orquestra tudo com feedback)
5. Req-5 + Req-6 (Validações — finaliza confiabilidade)

---

## Success Metrics

| Métrica | Atual | Alvo |
|---------|-------|------|
| Tempo fluxo montagem | 11 horas/mês | 30 min |
| Erros silenciosos | Múltiplos | 0 |
| Taxa idempotência | 60% | 100% |
| ABNT compliance | Não | Sim |
| Cobertura testes | ~40% | >90% |

---

## Implementation Notes

- **Escopo limitado** a O7 + O1 + O5 para MVP
- **Não incluir** O2 (numeração centralizada), O4 (rastreamento páginas) nesta fase
- **Stack**: Python 3, Flask 3.0, SQLAlchemy 2.0, python-docx, lxml
- **Idioma**: Português do Brasil em código, comentários, logs
- **Banco**: PostgreSQL 16 (produção), SQLite (desenvolvimento)
- **Validar** com coordenador após Req-2 implementado

