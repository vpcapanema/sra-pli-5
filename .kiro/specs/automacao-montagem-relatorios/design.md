# Design: Automação de Montagem de Relatórios

## Overview

Este documento apresenta o design técnico para automação confiável do fluxo de montagem de relatórios DOCX no SRA. A solução integra três oportunidades (O7 + O1 + O5) em uma arquitetura de componentes que reduz o tempo de processamento de 11 horas/mês para 30 minutos com zero erros silenciosos.

**Escopo**: Implementar tratamento de erros centralizado, localização robusta de capítulos com múltiplas estratégias de matching, e um pipeline orquestrador que valida pré/pós-condições e fornece feedback transparente em cada etapa.

**Versão**: 1.0  
**Data**: Maio 2026  
**Critério de Sucesso**: Fluxo end-to-end (merge → captioning → cross-refs → TOC) em uma ação, com todas as operações idempotentes e erros explícitos.

---

## Architecture

### Visão Geral de Componentes

```
┌─────────────────────────────────────────────────────────────┐
│  ServicoPipelineRelatorio (novo)                            │
│  • executar(relatorio_id, uploads_dict)                     │
│  • validar_precondiciones()                                 │
│  • fazer_merge()                                            │
│  • executar_numeracao()                                     │
│  • atualizar_refs_cruzadas()                                │
│  • regenerar_indices()                                      │
│  • validar_poscondiciones()                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┼───────────────────┐
        ↓                   ↓                   ↓
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Serviço Nível    │ │ Merge Melhorado  │ │ Sync Integrado   │
│ Erros (novo)     │ │ (localização)    │ │ (classificação)  │
│                  │ │                  │ │                  │
│ • try-except     │ │ • multi-nível    │ │ • integra class  │
│ • logging struct │ │ • fuzzy match    │ │ • integra seções │
│ • dicts padrão   │ │ • validação      │ │ • pré-condições  │
│ • contexto       │ │ • confiança      │ │ • pós-condições  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
        ↑                   ↑                   ↑
        └───────────────────┼───────────────────┘
                            ↓
            ┌───────────────────────────────┐
            │  Serviços Existentes          │
            │  • extracao_canonica          │
            │  • classificacao_capitulos    │
            │  • extracao_secoes            │
            │  • captioning                 │
            │  • cross_refs                 │
            │  • toc                        │
            └───────────────────────────────┘
```

### Layers de Responsabilidade

1. **Camada de Orquestração** (novo): `ServicoPipelineRelatorio`
   - Coordena fluxo completo
   - Valida pré/pós-condições
   - Retorna resultado estruturado
   - Gerencia transações

2. **Camada de Tratamento de Erros** (novo): `ServicoNiveladorErros`
   - Centraliza try-except
   - Standardiza formato de erro
   - Implementa logging estruturado
   - Oferece contexto de diagnóstico

3. **Camada de Processamento** (melhorado): Serviços existentes + melhorias
   - `servico_merge_docx`: localização robusta
   - `servico_sincronizar_capitulos`: integração de classificação + seções
   - Retornam dicts estruturados (sucesso/erro)

4. **Camada de Dados** (existente): Models SQLAlchemy + storage DOCX
   - `CapituloDocumento` (com campos novos: `classificacao`, `prefixo_indice`, `id_secao_inicio`, `id_secao_fim`)
   - `RelatorioProducao`, `EnvioConteudo`

---

## Components and Interfaces

### 1. ServicoPipelineRelatorio (novo)

**Responsabilidade**: Orquestração completa do pipeline de montagem de relatório.

**Arquivo**: `app/services/servico_pipeline_relatorio.py`

```python
class ServicoPipelineRelatorio:
    """Orquestra fluxo completo de montagem de relatório com validação."""
    
    @staticmethod
    def executar(relatorio_id: int, uploads_dict: dict) -> dict:
        """Executa pipeline completo: merge → numeração → cross-refs → TOC."""
        # Implementação
        ...
    
    @staticmethod
    def _validar_precondiciones(relatorio_id: int, uploads_dict: dict) -> dict:
        """Valida estado antes de executar pipeline."""
        # Verifica relatório, capítulos sincronizados, uploads válidos
        ...
    
    @staticmethod
    def _fazer_merge(relatorio: RelatorioProducao, uploads_dict: dict) -> dict:
        """Executa merge de todos os uploads."""
        ...
    
    @staticmethod
    def _executar_numeracao() -> dict:
        """Executa numeração unificada."""
        ...
    
    @staticmethod
    def _atualizar_refs_cruzadas() -> dict:
        """Substitui tags {{fig:x}} por campos REF."""
        ...
    
    @staticmethod
    def _regenerar_indices() -> dict:
        """Regenera TOC com números de página."""
        ...
    
    @staticmethod
    def _validar_poscondiciones() -> dict:
        """Valida integridade e coerência."""
        ...
```

---

### 2. ServicoNiveladorErros (novo)

**Responsabilidade**: Centralizar tratamento de exceções, logging estruturado e padronizar formato de erro.

**Arquivo**: `app/services/servico_nivelador_erros.py`

```python
class ServicoNiveladorErros:
    """Centraliza tratamento de erros com logging e formatação padrão."""
    
    @staticmethod
    def executar_com_tratamento(
        funcao_callable,
        *args,
        relatorio_id: int = None,
        capitulo_id: int = None,
        etapa: str = None,
        usuario_id: int = None,
        **kwargs
    ) -> dict:
        """Executa função com try-except e logging estruturado."""
        # Implementação com tratamento de diferentes tipos de erro
        ...
    
    @staticmethod
    def logger_estruturado(mensagem: str, nivel: str = 'INFO', **contexto):
        """Log estruturado em JSON para análise posterior."""
        ...
```

---

### 3. Melhoria em servico_merge_docx

**Responsabilidade**: Localizar capítulo usando múltiplas estratégias de matching com confiança.

```python
class ServicioMergeDocx:
    
    @staticmethod
    def localizar_range_capitulo_robusto(
        doc,
        capitulo,
        estrategia: str = 'multi_niveis'
    ) -> dict:
        """Localiza range com múltiplas estratégias e contexto."""
        # Implementação com exata → fuzzy → contexto
        ...
    
    @staticmethod
    def _match_exato(doc, capitulo) -> dict:
        """Match por casamento exato de estilo + título + nível."""
        ...
    
    @staticmethod
    def _match_fuzzy(doc, capitulo) -> dict:
        """Match por fuzzy (distância de edição)."""
        ...
    
    @staticmethod
    def _match_contexto(doc, capitulo) -> dict:
        """Match por contexto: indice + tipo + classificacao."""
        ...
    
    @staticmethod
    def _calcular_range_respeitando_secao(doc, indice_inicio, nivel_inicio) -> tuple:
        """Calcula range respeitando limites de seção."""
        ...
```

---

### 4. Melhoria em servico_sincronizar_capitulos

```python
class ServicoSincronizarCapitulos:
    
    @staticmethod
    def ressincronizar_capitulos_com_classificacao(relatorio: RelatorioProducao) -> dict:
        """Ressincroniza integrando classificação + seções."""
        # Implementação que integra todos os dados
        ...
```

---

## Data Models

### Modelos Existentes Melhorados

**`CapituloDocumento`** (modificação):
```python
class CapituloDocumento(db.Model, AuditoriaMixin):
    # ... campos existentes ...
    
    # Novos campos:
    classificacao = db.Column(
        db.String(50),
        nullable=True,
        comment="Tipo: textual, pre_textual, pos_textual, anexo, apendice"
    )
    prefixo_indice = db.Column(
        db.String(10),
        nullable=True,
        comment="Prefixo de numeração"
    )
    id_secao_inicio = db.Column(
        db.Integer,
        db.ForeignKey('secao_docx.id'),
        nullable=True
    )
    id_secao_fim = db.Column(
        db.Integer,
        db.ForeignKey('secao_docx.id'),
        nullable=True
    )
```

### Dicts de Retorno Padronizados

#### Resultado de Pipeline
```python
{
    'sucesso': bool,
    'relatorio_id': int,
    'etapas': [...],
    'erros': [...],
    'avisos': [...],
    'tempo_total_ms': float,
    'arquivo_modificado': bool,
    'proximos_passos': [...]
}
```

#### Resultado de Merge
```python
{
    'encontrado': bool,
    'inicio': int,
    'fim': int,
    'secao_inicio': int,
    'secao_fim': int,
    'titulo_encontrado': str,
    'confianca': float,
    'diagnostico': str,
    'estrategia_usada': str,
    'alternativas': [...]
}
```

#### Resultado de Erro
```python
{
    'sucesso': False,
    'erro': str,
    'tipo_erro': str,
    'etapa': str,
    'relatorio_id': int,
    'capitulo_id': int or None,
    'usuario_id': int or None,
    'sugestoes': [...],
    'timestamp': datetime
}
```

---

## Correctness Properties

*A property é uma característica ou comportamento que deve ser verdadeiro em todas as execuções válidas do sistema — uma afirmação formal sobre o que o sistema deve fazer. Properties são a ponte entre especificações legíveis e garantias de correção verificáveis por máquina.*

### Avaliação de Aplicabilidade PBT

Este feature combina orquestração de pipeline com tratamento de erros estruturado. As operações críticas (merge, numeração, cross-refs, TOC) contêm lógica determinística sobre transformações de dados que é apropriada para property-based testing.

### Propriedades Identificadas (após Prework Analysis)

Na prework analysis foram identificadas **35+ critérios testáveis**, dos quais 30+ são apropriados para PBT. Após **property reflection** para eliminar redundâncias, as seguintes 10 propriedades ortogonais foram selecionadas:

---

### Property 1: Rastreabilidade Estruturada de Erros

*For any* operação que falha (arquivo corrompido, capítulo não encontrado, permissão negada, validação inválida), o resultado retorna dict estruturado com `sucesso=False`, campo `erro` com mensagem explícita, `etapa` identificada e `sugestoes` lista não-vazia com ações concretas.

**Valida**: Requisitos 1.1, 1.2, 1.3, 1.5, NF-1, Exemplo 5

---

### Property 2: Determinismo e Idempotência de Localização

*For any* capítulo com título consistente no template e qualquer combinação de estratégias de matching (exata, fuzzy, contexto), `localizar_range_capitulo_robusto()` sempre retorna exatamente o mesmo resultado. Múltiplas execuções com mesma entrada → mesma saída.

**Valida**: Requisitos 2.1, 2.3, 2.5, Determinismo

---

### Property 3: Coerência de Estrutura Retornada

*For any* operação no pipeline (merge, numeração, cross-refs, TOC), o dict retornado contém TODOS os campos esperados conforme contrato: `sucesso`, `erro`, `etapa`, `relatorio_id`, `capitulo_id`, `sugestoes`, `timestamp`.

**Valida**: Requisitos 1.2, 3.5

---

### Property 4: Respeito a Classificação e Seções na Sincronização

*For any* capítulo no DOCX template com um tipo de classificação (textual, pré_textual, pos_textual, anexo, apendice), após `ressincronizar_capitulos_com_classificacao()`, o modelo `CapituloDocumento` correspondente terá campos `classificacao` e `prefixo_indice` populados corretamente e seções respeitadas.

**Valida**: Requisitos 4.1, 4.2, 4.3, 4.4, 4.5, Exemplo 3

---

### Property 5: Parada Segura do Pipeline em Erro

*For any* falha em uma etapa do pipeline (merge falha para capítulo X, numeração falha, etc.), o pipeline NÃO executa etapas subsequentes. Se merge falha, numeração/cross-refs/TOC não são chamados. Resultado retorna array `erros` com todos os problemas.

**Valida**: Requisitos 1.4, 3.4, Exemplo 4

---

### Property 6: Idempotência Completa do Pipeline

*For any* relatório válido com uploads de capítulos, executar `ServicoPipelineRelatorio.executar(relatorio_id, uploads_dict)` duas vezes com EXATAMENTE mesma entrada produz documentos DOCX com checksum idêntico. Nenhuma duplicação de legendas, nenhuma duplicação de bookmarks.

**Valida**: Requisito NF-2, Exemplo 2

---

### Property 7: Validação de Pré-Condições Rejeita Estados Inválidos

*For any* estado inválido do relatório (capítulos não sincronizados, upload não corresponde a capítulo existente, espaço em disco insuficiente), `_validar_precondiciones()` retorna `valido=False` com `motivos_rejeicao` explícitos. Pipeline é recusado ANTES de qualquer operação destrutiva.

**Valida**: Requisitos 5.1, 5.2, 5.3, 3.2

---

### Property 8: Validação e Reportagem de Inconsistências Pós-Pipeline

*For any* conclusão bem-sucedida do pipeline, pós-condições são validadas: nenhuma legenda duplicada, numeração sequencial sem gaps, TOC coerente com estrutura. Se inconsistências são detectadas, resultado contém `inconsistencias` array com detalhes.

**Valida**: Requisitos 6.1, 6.2, 6.3, 3.5

---

### Property 9: Segurança em Mensagens de Erro

*For any* operação que retorna erro (sucesso=False), a mensagem em campo `erro` NÃO contém caminhos de arquivo absolutos, dados sensíveis (senhas, tokens), ou informações internas de stack trace. Mensagens são amigáveis ao usuário.

**Valida**: Requisito NF-5

---

### Property 10: Determinismo de Match Multi-Nível

*For any* capítulo no template e várias estratégias de localização tentadas em sequência (exata → fuzzy → contexto), o sistema sempre tenta na MESMA ordem com MESMA lógica de decisão. Ordem determinística, sem aleatoriedade.

**Valida**: Requisito 2.1, Determinismo

---

### Property Reflection (Eliminação de Redundâncias)

Análise das 10 propriedades:
- **Properties 1, 2, 3**: Rastreabilidade + Determinismo + Coerência são **independentes** (cobertura diferente) → Manter todas
- **Properties 4, 7**: Classificação + Pré-condições em pontos diferentes → Não redundantes → Manter ambas
- **Properties 5, 8**: Parada em Erro + Validação Pós complementares → Manter ambas
- **Property 6**: Idempotência de nível alto, não redundante → Manter
- **Properties 9, 10**: Segurança + Determinismo ortogonais → Manter ambas

**Resultado**: Todas as 10 propriedades são **não-redundantes**. Cada uma valida aspecto diferente do sistema.

---

## Error Handling

### Estratégia Geral

1. **Captura em Cada Camada**: Serviços de baixo nível (merge, captioning) capturam e retornam dict com erro
2. **Propagação Controlada**: Pipeline agrega erros e decide se para ou continua
3. **Log Estruturado**: Sempre registrar em JSON com contexto (relatorio_id, capitulo_id, usuario_id, etapa)
4. **Feedback Imediato**: Retornar ao coordenador dict com sugestões actionáveis

### Taxonomia de Erros

| Categoria | Exemplos | Ação | Prosseguir? |
|-----------|----------|------|------------|
| **Validação** | Capítulo não encontrado, entrada inválida | Log + retornar sugestões | Próximo upload |
| **I/O** | DOCX corrompido, permissão negada | Log + retornar ação | Não |
| **Interno** | Exception inesperada, lxml crash | Log + stack trace | Não |
| **Integração** | Serviço externo falha | Log + fallback se possível | Próximo upload |

---

## Testing Strategy

### Approach Dual: Unit + Property Tests

#### Unit Tests (Example-Based)

Casos específicos e edge cases em:
1. **Setup**: Validação de pré-condições (relatório não sincronizado, uploads inválidos)
2. **Merge**: Capítulo encontrado, typo detectado, inexistente, DOCX corrompido
3. **Numeração**: Figuras sequenciais, idempotência
4. **Cross-refs**: Tags substituídas, tags orfãs reportadas
5. **Índices**: TOC com páginas, listas incluídas
6. **Pós-condições**: Sem legendas duplicadas, numeração coerente

#### Property-Based Tests (Generators - Hypothesis)

```python
@given(relatorio_fixture(), uploads_dict_fixture())
def test_pipeline_idempotence(rel, uploads):
    """Property 6: Executar 2x → checksum idêntico"""
    resultado1 = pipeline.executar(rel.id, uploads)
    hash1 = sha256(rel.documento)
    resultado2 = pipeline.executar(rel.id, uploads)
    hash2 = sha256(rel.documento)
    assert hash1 == hash2

@given(operation_fixture(), failure_modes_fixture())
def test_error_always_structured(operacao, modo_falha):
    """Property 1: Erro sempre retorna dict estruturado"""
    resultado = executar_operacao(operacao, falhar_como=modo_falha)
    assert resultado['sucesso'] == False
    assert 'erro' in resultado
    assert 'sugestoes' in resultado and len(resultado['sugestoes']) > 0

@given(capitulo_fixture(), template_fixture())
def test_localization_deterministic(cap, template):
    """Property 2: Localização sempre determinística"""
    resultado1 = localizar_robusto(template, cap)
    resultado2 = localizar_robusto(template, cap)
    assert resultado1 == resultado2

@given(relatorio_fixture(), partial_uploads_fixture())
def test_non_processed_chapters_unchanged(rel, uploads):
    """Property: Capítulos não processados permanecem iguais"""
    capitulos_sem_merge = set(cap.id for cap in rel.capitulos) - set(uploads.keys())
    estado_antes = {cap_id: sha256(rel.get_content(cap_id)) for cap_id in capitulos_sem_merge}
    pipeline.executar(rel.id, uploads)
    estado_depois = {cap_id: sha256(rel.get_content(cap_id)) for cap_id in capitulos_sem_merge}
    assert estado_antes == estado_depois
```

### Configuration PBT

- **Mínimo de iterações**: 100+ por propriedade
- **Timeout**: 30s por teste
- **Tag no teste**:
  ```python
  # Feature: automacao-montagem-relatorios, Property 1: Rastreabilidade Estruturada de Erros
  ```

### Coverage Goals

| Categoria | Meta |
|-----------|------|
| Unit tests | >90% linhas em servico_pipeline_relatorio |
| Property tests | 10 propriedades com 100+ iterações cada |
| Integration tests | End-to-end com 5 capítulos reais |
| Edge cases | Docx corrompido, múltiplas seções, typo, upload vazio |

---

## Decision Rationale

### 1. Strategy Pattern em Localização (multi_niveis)

**Problema**: Match exato frágil → erros silenciosos

**Solução**: Três estratégias em cascata (exata → fuzzy → contexto) com confiança explícita

**Benefício**: Cobertura ampla de cenários

### 2. Dicts em vez de Exceptions

**Problema**: Exceptions assustam coordenador; hard to aggregate múltiplos erros

**Solução**: Retornar `{'sucesso': bool, 'erro': str, 'sugestoes': [...]}`

**Benefício**: Coordenador vê quais capítulos falharam; pipeline continua processando

### 3. Centralizar Erros em ServicoNiveladorErros

**Problema**: Cada serviço tem try-except diferente

**Solução**: Wrapper `executar_com_tratamento()` com try-except e logging JSON

**Benefício**: Auditoria centralizada; menos código duplicado

### 4. Integrar Classificação em Sync

**Problema**: Campo `classificacao` nunca é preenchido

**Solução**: Chamar `ServicoClassificacaoCapitulos` em sync

**Benefício**: Banco alinhado com DOCX; ordenação por classificacao possível

### 5. Validar Pré-Condições Antes de Pipeline

**Problema**: Pipeline executa mesmo se relatório não sincronizado

**Solução**: `_validar_precondiciones()` valida estado antes de iniciar

**Benefício**: Early failure; feedback claro

---

## Key Assumptions and Constraints

1. **Template DOCX válido**: Estrutura OOXML válida e headings bem-formados
2. **Capítulos Sincronizados**: Pipeline exige sync anterior
3. **Idempotência via Bookmarks**: Captioning usa bookmarks para detectar legendas
4. **Tolerância a Erros Parciais**: Se merge cap 3 falha, continue cap 4
5. **Performance < 30s**: Até 5 capítulos, 30 figuras, 10 tabelas

---

## Future Enhancements

1. **Rastreamento de Páginas (O4)**: Implementar `ServicoRastreamentoPaginas`
2. **Numeração Centralizada (O2)**: Refatorar em `ServicoNumeracaoUnificada`
3. **Batch Processing**: Upload múltiplo e processamento paralelo
4. **UI de Confirmação**: Modal para confirmar fuzzy match
5. **Undo/Rollback**: Snapshot para rollback em caso de erro

---

## Approval Checklist

- [x] Design cobre todos os requisitos (Req-1 a Req-6)
- [x] Integração com serviços existentes é clara
- [x] Contratos de API são explícitos
- [x] Modelos de dados estão bem definidos
- [x] Estratégia de testes (unit + property) é viável
- [x] Decisões de design estão justificadas
- [x] 10 properties ortogonais após prework + reflection
- [x] Error handling cobre cenários principais
- [x] Nenhuma ambiguidade em fluxos críticos
- [x] Performance targets (<30s) são realistas
