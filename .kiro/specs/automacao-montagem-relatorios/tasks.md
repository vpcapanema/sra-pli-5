# Implementation Plan: Automação de Montagem de Relatórios

## Overview

Implementação de pipeline de montagem de relatórios com tratamento centralizado de erros, localização robusta de capítulos com múltiplas estratégias de matching, e orquestração coordenada de etapas (merge → numeração → cross-refs → TOC).

**Escopo**: Req-1 (Logging), Req-2 (Localização), Req-4 (Classificação), Req-3 (Pipeline), Req-5/6 (Validações)

**Stack**: Python 3 + Flask 3.0 + SQLAlchemy 2.0 + python-docx + lxml

**Performance Target**: <30 segundos para pipeline completo (5 capítulos, 30 figuras, 10 tabelas)

**Estrutura de Testes**: Property-based (Hypothesis) + unit tests + integration tests validando 10 propriedades ortogonais

---

## Tasks

### Sprint 1: Infraestrutura de Logging e Tratamento de Erros (Req-1)

**Objetivo**: Implementar camada centralizada de erros com logging estruturado e padronização de dicts de retorno.

**Estimativa**: 5 dias

### Tasks

- [x] 1.1 Criar ServicoNiveladorErros com wrapper de try-except centralizado
  - **Arquivo**: `app/services/servico_nivelador_erros.py`
  - **Assinatura de código**:
    ```python
    class ServicoNiveladorErros:
        @staticmethod
        def executar_com_tratamento(
            funcao_callable,
            *args,
            relatorio_id: int = None,
            capitulo_id: int = None,
            etapa: str = None,
            usuario_id: int = None,
            **kwargs
        ) -> dict
    ```
  - **Responsabilidades**: Capturar exceções, registrar em JSON, retornar dict padrão
  - **Tratamento de erros**: Validação (captura), I/O (captura), Interno (captura + stack trace)
  - **Contexto adicionado ao log**: timestamp, nivel, relatorio_id, capitulo_id, usuario_id, etapa, mensagem, stack_trace, detalhes
  - _Requisitos: 1.1, 1.2, 1.3, NF-1_
  - _Propriedade 1: Rastreabilidade Estruturada de Erros_

- [x]* 1.2 Escrever testes property-based para rastreabilidade de erros
  - **Arquivo de teste**: `tests/test_servico_nivelador_erros.py`
  - **Property 1**: Para qualquer operação que falha, retorna dict com `sucesso=False`, `erro` não-vazio, `sugestoes` lista não-vazia
  - **Estratégia**: Gerar operações que falham (arquivo inválido, permissão negada, valor None) e validar dict retornado
  - **Ferramenta**: Hypothesis com `@given(operation_fixture(), failure_modes_fixture())`
  - **Mínimo**: 100+ iterações
  - _Requisitos: 1.2, 1.3_

- [x] 1.3 Integrar logger estruturado em JSON em todos os serviços críticos
  - **Serviços afetados**: servico_merge_docx, servico_captioning, servico_cross_refs, servico_toc, servico_sincronizar_capitulos
  - **Mudança**: Adicionar `from app.services.servico_nivelador_erros import ServicoNiveladorErros` e envolver chamadas críticas com `executar_com_tratamento()`
  - **Padrão de uso**:
    ```python
    resultado = ServicoNiveladorErros.executar_com_tratamento(
        funcao_original,
        arg1, arg2,
        relatorio_id=rel_id,
        etapa='merge'
    )
    if not resultado['sucesso']:
        return resultado  # Propagar erro
    ```
  - **Validação**: Todos os serviços chamam wrapper; logs salvos em `app.log` em JSON
  - _Requisitos: 1.1, 1.2, NF-1_

- [x] 1.4 Criar Checkpoint: Validar logging estruturado
  - **Checkpoint executado**: 26/05/2026
  - **Resultado**: ✅ VALIDAÇÃO COMPLETA
  - **Critérios validados**:
    1. ✅ Erros capturados e retornados em dict estruturado
    2. ✅ Property 9: Mensagens de erro seguras (sem caminhos absolutos/dados sensíveis)
    3. ✅ Logs estruturados em JSON com contexto completo
    4. ✅ Integração com serviços críticos (servico_merge_docx)
    5. ✅ Estrutura consistente de dicts (Property 3)
    6. ✅ Sugestões contextuais para diferentes tipos de erro
    7. ✅ Sem stack trace em respostas HTTP
  - **Documentação**: Ver `CHECKPOINT_FASE_1.md`
  - _Propriedade 9: Segurança em Mensagens de Erro_ ✅

---

## Sprint 2: Localização Robusta de Capítulos com Multi-Nível (Req-2)

**Objetivo**: Implementar estratégia de matching em cascata (exato → fuzzy → contexto) com confiança explícita.

**Estimativa**: 7 dias

**Dependências**: Sprint 1 (logging)

### Tasks

- [ ] 2.1 Criar função auxiliar de extração de range respeitando seções
  - **Arquivo**: `app/services/servico_merge_docx.py` (novo método)
  - **Assinatura**:
    ```python
    @staticmethod
    def _calcular_range_respeitando_secao(
        doc,
        indice_inicio: int,
        nivel_inicio: int
    ) -> dict
    ```
  - **Responsabilidades**: Encontrar próximo heading de nível ≤ nivel_inicio, respeitar quebras de seção (lxml)
  - **Retorno**: Dict com `inicio`, `fim`, `secao_inicio`, `secao_fim`
  - **Integração com seções**: Consultar `app/services/servico_extracao_secoes.py` para IDs de seções
  - _Requisitos: 2.1, 2.4_
  - _Propriedade 2: Determinismo e Idempotência de Localização_

- [x] 2.2 Implementar match exato em localizar_range_capitulo_robusto()
  - **Arquivo**: `app/services/servico_merge_docx.py` (novo método)
  - **Assinatura**:
    ```python
    @staticmethod
    def _match_exato(
        doc,
        capitulo,
        headings_cache: dict = None
    ) -> dict
    ```
  - **Estratégia**: Normalizar título do capítulo e buscar heading com casamento exato de (estilo + texto normalizado)
  - **Normalização**: lowercase, remover acentos, colapsar espaços, tirar numeração inicial (usar `unicodedata`)
  - **Retorno**: Dict com `encontrado`, `indice`, `confianca` (0.95 se exato), `diagnostico`
  - **Cache**: Opcionalmente cachear headings para não varrer doc 3x
  - _Requisitos: 2.1, 2.3_

- [ ] 2.3 Implementar match fuzzy com distância de edição
  - **Arquivo**: `app/services/servico_merge_docx.py` (novo método)
  - **Assinatura**:
    ```python
    @staticmethod
    def _match_fuzzy(
        doc,
        capitulo,
        max_distancia_edicao: int = 2
    ) -> dict
    ```
  - **Ferramenta**: difflib.SequenceMatcher ou fuzzywuzzy (dependência a adicionar)
  - **Estratégia**: Se match exato falha, procurar heading com distância de Levenshtein ≤ max_distancia_edicao
  - **Retorno**: Dict com `encontrado`, `indice`, `confianca` (0.5-0.9 baseado em ratio), `titulo_encontrado`, `diagnostico`
  - **Fallback**: Retornar lista de melhores 3 matches (ordenado por confiança)
  - _Requisitos: 2.1, 2.2_
  - _Propriedade 2: Determinismo de Match Multi-Nível_

- [ ] 2.4 Implementar match por contexto (índice + tipo + classificação)
  - **Arquivo**: `app/services/servico_merge_docx.py` (novo método)
  - **Assinatura**:
    ```python
    @staticmethod
    def _match_contexto(
        doc,
        capitulo,
        indice_esperado: int = None
    ) -> dict
    ```
  - **Estratégia**: Se título não found, usar número do capítulo (ex: "5") ou classificação (ex: "ANEXO") para inferir posição
  - **Integração**: Consultar classificação do capítulo (novo campo em CapituloDocumento)
  - **Retorno**: Dict com `encontrado`, `indice`, `confianca` (0.6-0.8), `diagnostico`
  - _Requisitos: 2.1, 4.2_

- [ ] 2.5 Integrar cascata de estratégias em localizar_range_capitulo_robusto()
  - **Arquivo**: `app/services/servico_merge_docx.py` (refatorar método existente)
  - **Assinatura**:
    ```python
    @staticmethod
    def localizar_range_capitulo_robusto(
        doc,
        capitulo,
        estrategia: str = 'multi_niveis'
    ) -> dict
    ```
  - **Fluxo**: Tentar exato → fuzzy → contexto; parar no primeiro sucesso
  - **Retorno padrão**: Dict com `encontrado`, `inicio`, `fim`, `secao_inicio`, `secao_fim`, `titulo_encontrado`, `confianca`, `estrategia_usada`, `alternativas`
  - **Alternativas**: Lista de melhores matches secundários (para confirmação no UI)
  - **Validação**: Todos os casos retornam dict estruturado (nunca None)
  - _Requisitos: 2.1, 2.2, 2.3, 2.4, 2.5, NF-2_
  - _Propriedade 2: Determinismo e Idempotência de Localização_
  - _Propriedade 3: Coerência de Estrutura Retornada_

- [ ] 2.6 Atualizar substituir_capitulo() para usar localizar_range_capitulo_robusto()
  - **Arquivo**: `app/services/servico_merge_docx.py` (refatorar método existente)
  - **Mudança**: Chamar novo `localizar_range_capitulo_robusto()` em vez de `localizar_range_capitulo()`
  - **Tratamento**: Se resultado['encontrado'] == False, retornar dict de erro com `sugestoes` (alternativas)
  - **Idempotência**: Antes de substituir, remover conteúdo anterior completamente (garantir sem resíduos)
  - _Requisitos: 2.1, 2.3, 2.5, NF-2_

- [ ]* 2.7 Escrever testes property-based para determinismo de localização
  - **Arquivo de teste**: `tests/test_localizacao_capitulos.py`
  - **Property 2**: Para qualquer capítulo com título consistente, múltiplas execuções de `localizar_range_capitulo_robusto()` retornam exatamente mesmo resultado
  - **Property 10**: Ordem de tentativa (exato → fuzzy → contexto) é sempre mesma
  - **Estratégia**: Gerar capítulos com variações de título (typos, espaços, acentos) e validar determinismo
  - **Ferramenta**: Hypothesis com `@given(capitulo_fixture(), template_fixture())`
  - **Mínimo**: 100+ iterações
  - _Requisitos: 2.1, 2.2, 2.3_

- [ ] 2.8 Criar Checkpoint: Validar localização robusta
  - Upload de DOCX com título ligeiramente diferente (typo)
  - Validar que sistema detecta com confiança 0.8-0.9
  - Validar que resultado contém sugestões de alternativas
  - Merge executado com sucesso
  - _Propriedade 2: Determinismo_
  - _Exemplo 1: Error Silent Becomes Visible_

---

## Sprint 3: Integração de Classificação em Sincronização (Req-4)

**Objetivo**: Integrar classificação de capítulos e seções em ressincronizar_capitulos().

**Estimativa**: 4 dias

**Dependências**: Sprint 1 (logging), Sprint 2 (seções)

### Tasks

- [ ] 3.1 Adicionar campos novos em CapituloDocumento (model)
  - **Arquivo**: `app/models/capitulo_documento.py`
  - **Campos novos**:
    ```python
    classificacao = db.Column(db.String(50), nullable=True)
    prefixo_indice = db.Column(db.String(10), nullable=True)
    id_secao_inicio = db.Column(db.Integer, db.ForeignKey('secao_docx.id'), nullable=True)
    id_secao_fim = db.Column(db.Integer, db.ForeignKey('secao_docx.id'), nullable=True)
    ```
  - **Comentários**: Classificação = textual|pre_textual|pos_textual|anexo|apendice; Prefixo = I|1|A
  - **Migration**: Criar migração Alembic para adicionar colunas
  - **Registrar em `__init__.py`**: Importar CapituloDocumento
  - _Requisitos: 4.2, 4.3, 4.4_

- [ ] 3.2 Integrar servico_classificacao_capitulos em ressincronizar_capitulos_com_classificacao()
  - **Arquivo**: `app/services/servico_sincronizar_capitulos.py` (novo método)
  - **Assinatura**:
    ```python
    @staticmethod
    def ressincronizar_capitulos_com_classificacao(
        relatorio: RelatorioProducao
    ) -> dict
    ```
  - **Fluxo**:
    1. Extrair capítulos de template com `servico_extracao_canonica`
    2. Para cada capítulo, chamar `ServicoClassificacaoCapitulos.classificar()`
    3. Integrar seções: consultar `servico_extracao_secoes` e mapear id_secao_inicio/fim
    4. Atualizar CapituloDocumento com classificacao + prefixo_indice + id_secao_inicio/fim
  - **Retorno**: Dict com lista de capítulos sincronizados, erros de classificação
  - _Requisitos: 4.1, 4.2, 4.3, 4.4, 4.5_
  - _Propriedade 4: Respeito a Classificação e Seções_

- [ ] 3.3 Remover ou depreciar ressincronizar_capitulos() antigo
  - **Arquivo**: `app/services/servico_sincronizar_capitulos.py`
  - **Mudança**: Manter método antigo como `@deprecated` wrapper que chama novo; log warning
  - **Atualizar callers**: Encontrar todas as rotas/serviços que chamam antigo método, atualizar para novo
  - **Grep**: Buscar `servico_sincronizar_capitulos.ressincronizar_capitulos` em toda base
  - _Requisitos: 4.1, 4.2_

- [ ] 3.4 Adicionar validação de classificação em _validar_precondiciones()
  - **Arquivo**: `app/services/servico_pipeline_relatorio.py` (será criado em Sprint 4)
  - **Mudança futura**: Verificar que todos os capítulos têm classificacao preenchida antes de merge
  - **Aqui**: Placeholder para garantir que sync anterior preenche classificacao
  - _Requisitos: 5.1_

- [ ]* 3.5 Escrever testes property-based para classificação
  - **Arquivo de teste**: `tests/test_classificacao_sync.py`
  - **Property 4**: Para qualquer capítulo no template com classificação, após sync, CapituloDocumento tem classificacao + prefixo_indice preenchidos
  - **Estratégia**: Gerar templates com capítulos de diferentes tipos (textual, anexo, etc.) e validar sync
  - **Ferramenta**: Hypothesis com `@given(relatorio_fixture(), template_classificado_fixture())`
  - **Mínimo**: 100+ iterações
  - _Requisitos: 4.2, 4.3, 4.4_

- [ ] 3.6 Criar Checkpoint: Validar sync com classificação
  - Sync de relatório com 3 capítulos (1 pre_textual, 1 textual, 1 anexo)
  - Validar que BD reflete classificação correta
  - Validar que prefixo_indice está preenchido (I, 1, A)
  - Query `CapituloDocumento.query.filter_by(classificacao='anexo')` retorna capítulo correto
  - _Propriedade 4: Respeito a Classificação_

---

## Sprint 4: Pipeline Orquestrador com Validação (Req-3, Req-5, Req-6)

**Objetivo**: Implementar ServicoPipelineRelatorio que orquestra merge → numeração → cross-refs → TOC com validação de pré/pós-condições.

**Estimativa**: 10 dias

**Dependências**: Sprint 1 (logging), Sprint 2 (localização), Sprint 3 (classificação)

### Tasks

- [ ] 4.1 Criar struct servico_pipeline_relatorio.py com classe base
  - **Arquivo**: `app/services/servico_pipeline_relatorio.py`
  - **Assinatura de classe**:
    ```python
    class ServicoPipelineRelatorio:
        @staticmethod
        def executar(
            relatorio_id: int,
            uploads_dict: dict
        ) -> dict
    ```
  - **Estrutura inicial**: Métodos privados para cada fase (_fase_1, _fase_2, etc.)
  - **Atributos**: Armazenar estado de execução (etapa_atual, erros, avisos)
  - _Requisitos: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 4.2 Implementar _validar_precondiciones()
  - **Arquivo**: `app/services/servico_pipeline_relatorio.py` (novo método)
  - **Assinatura**:
    ```python
    @staticmethod
    def _validar_precondiciones(
        relatorio_id: int,
        uploads_dict: dict
    ) -> dict
    ```
  - **Validações**:
    1. Relatório existe e está em estado válido (RelatorioProducao)
    2. Todos os capítulos foram sincronizados (classificacao não nula)
    3. Cada upload corresponde a capítulo existente
    4. Espaço em disco suficiente (>100MB)
    5. DOCX template válido (não corrompido)
  - **Retorno**: Dict com `valido: bool`, `motivos_rejeicao: []`
  - **Parada antecipada**: Se qualquer validação falha, não proceder com pipeline
  - _Requisitos: 5.1, 5.2, 5.3, 3.2_
  - _Propriedade 7: Validação de Pré-Condições_

- [ ] 4.3 Implementar _fazer_merge() com iteração sobre uploads
  - **Arquivo**: `app/services/servico_pipeline_relatorio.py` (novo método)
  - **Assinatura**:
    ```python
    @staticmethod
    def _fazer_merge(
        relatorio: RelatorioProducao,
        uploads_dict: dict
    ) -> dict
    ```
  - **Fluxo**:
    1. Para cada (capitulo_id, docx_bytes) em uploads_dict:
       - Chamar `ServicioMergeDocx.localizar_range_capitulo_robusto()`
       - Se encontrado, fazer merge com `substituir_capitulo()`
       - Se não encontrado, registrar erro e **continuar próximo capítulo**
    2. Retornar dict com lista de capítulos processados, erros, avisos
  - **Tolerância a erros**: Merge falha para cap 3 → continuar cap 4 (não parar pipeline)
  - **Registro**: Logar cada etapa com `ServicoNiveladorErros`
  - _Requisitos: 3.1, 3.3, 3.4_
  - _Propriedade 5: Parada Segura do Pipeline em Erro (parcial)_

- [ ] 4.4 Implementar _executar_numeracao() — wrapper sobre servico_captioning
  - **Arquivo**: `app/services/servico_pipeline_relatorio.py` (novo método)
  - **Assinatura**:
    ```python
    @staticmethod
    def _executar_numeracao(
        caminho_template: str
    ) -> dict
    ```
  - **Estratégia**: Chamar `ServicoCaptioning.reindexar_captions()` com tratamento de erro
  - **Validação de pré-req**: Antes de chamar, verificar que merge foi bem-sucedido (senão, retornar erro)
  - **Retorno**: Dict com numeracao_status, figuras_numeradas, tabelas_numeradas, erros
  - **Parada**: Se numeração falha, pipeline **não continua** (cross-refs depende de numeração)
  - _Requisitos: 3.3_
  - _Propriedade 5: Parada Segura (merge OK, numeração falha → parar)_

- [ ] 4.5 Implementar _atualizar_refs_cruzadas() — wrapper sobre servico_cross_refs
  - **Arquivo**: `app/services/servico_pipeline_relatorio.py` (novo método)
  - **Assinatura**:
    ```python
    @staticmethod
    def _atualizar_refs_cruzadas(
        caminho_template: str,
        mapa_labels: dict
    ) -> dict
    ```
  - **Estratégia**: Chamar `ServicoCrossRefs.processar()` com mapa_labels da etapa anterior
  - **Validação de pré-req**: Verificar que mapa_labels não é vazio (senão, retornar aviso)
  - **Retorno**: Dict com refs_status, tags_substituidas, tags_orfas
  - **Tolerância**: Se tags orfas, incluir em avisos (não falha pipeline)
  - _Requisitos: 3.3_

- [ ] 4.6 Implementar _regenerar_indices() — wrapper sobre servico_toc
  - **Arquivo**: `app/services/servico_pipeline_relatorio.py` (novo método)
  - **Assinatura**:
    ```python
    @staticmethod
    def _regenerar_indices(
        caminho_template: str,
        perfil: ServicoPerfilFormatacao = None
    ) -> dict
    ```
  - **Estratégia**: Chamar `ServicoToc.inserir_sumario()` + `inserir_lista_figuras()` + `inserir_lista_tabelas()`
  - **Retorno**: Dict com toc_status, listas_status, erros
  - _Requisitos: 3.3_

- [ ] 4.7 Implementar _validar_poscondiciones() — verificar integridade após pipeline
  - **Arquivo**: `app/services/servico_pipeline_relatorio.py` (novo método)
  - **Assinatura**:
    ```python
    @staticmethod
    def _validar_poscondiciones(
        caminho_template: str
    ) -> dict
    ```
  - **Validações**:
    1. Nenhuma legenda duplicada (detectar por bookmark duplicado)
    2. Numeração sequencial sem gaps (figuras 1, 2, 3 sem falta de 2)
    3. TOC coerente com headings (número de entradas bate)
    4. Nenhum bookmark orfão
    5. DOCX não corrompido (validar OOXML)
  - **Retorno**: Dict com `inconsistencias: []` (array de problemas encontrados)
  - **Não bloqueia**: Se inconsistências encontradas, incluir em avisos
  - _Requisitos: 6.1, 6.2, 6.3_
  - _Propriedade 8: Validação e Reportagem de Inconsistências_

- [ ] 4.8 Integrar executar() orquestrando todas as fases
  - **Arquivo**: `app/services/servico_pipeline_relatorio.py` (refatorar método main)
  - **Fluxo**:
    ```python
    resultado = {
        'sucesso': False,
        'relatorio_id': relatorio_id,
        'etapas': [],
        'erros': [],
        'avisos': [],
        'tempo_total_ms': 0,
        'arquivo_modificado': False,
        'proximos_passos': []
    }
    
    # Fase 1: Validar pré-condições
    precond = _validar_precondiciones(...)
    if not precond['valido']:
        resultado['erros'] = precond['motivos_rejeicao']
        return resultado
    
    # Fase 2: Fazer merge
    merge_result = _fazer_merge(...)
    resultado['etapas'].append({'etapa': 'merge', 'resultado': merge_result})
    
    # Fase 3: Numeração (parar se merge falhou completamente)
    if merge_result['sucesso']:
        num_result = _executar_numeracao(...)
        resultado['etapas'].append({'etapa': 'numeracao', 'resultado': num_result})
    
    # ... continuar outros...
    
    # Validar pós-condições
    postcond = _validar_poscondiciones(...)
    if postcond['inconsistencias']:
        resultado['avisos'].extend(postcond['inconsistencias'])
    
    resultado['sucesso'] = True
    return resultado
    ```
  - **Timing**: Registrar tempo total
  - _Requisitos: 3.1, 3.2, 3.3, 3.4, 3.5, 5.1, 5.2, 5.3, 6.1, 6.2, 6.3_
  - _Propriedade 5: Parada Segura_

- [ ]* 4.9 Escrever testes property-based para pipeline idempotência
  - **Arquivo de teste**: `tests/test_pipeline_idempotencia.py`
  - **Property 6**: Executar pipeline 2x com mesma entrada → checksum DOCX idêntico, sem duplicação de legendas/bookmarks
  - **Estratégia**: Gerar relatório com uploads, executar pipeline, calcular sha256 de arquivo, repetir, comparar
  - **Ferramenta**: Hypothesis com `@given(relatorio_fixture(), uploads_dict_fixture())`
  - **Mínimo**: 50+ iterações (computacionalmente pesado)
  - _Requisitos: NF-2_
  - _Exemplo 2: Pipeline Idempotent_

- [ ]* 4.10 Escrever testes property-based para parada segura em erro
  - **Arquivo de teste**: `tests/test_pipeline_error_handling.py`
  - **Property 5**: Se merge falha para capítulo X, numeração/cross-refs/TOC não são chamados (ou são chamados mas não modificam)
  - **Estratégia**: Simular falha de merge (capítulo não encontrado) e verificar que etapas posteriores não executam
  - **Ferramenta**: Hypothesis com `@given(relatorio_com_capitulo_invalido_fixture())`
  - **Mínimo**: 50+ iterações
  - _Requisitos: 3.4, 5.1_

- [ ] 4.11 Criar Checkpoint: Validar pipeline end-to-end
  - Upload de 3 capítulos em relatório sincronizado
  - Validar que pipeline executa todas as fases
  - Validar que resultado contém array de etapas + tempo total
  - Validar que DOCX final é coerente (sem erros de estrutura)
  - Executar pipeline 2x com mesmo input → verificar checksum idêntico
  - _Propriedade 5: Parada Segura_
  - _Propriedade 6: Idempotência_
  - _Exemplo 4: Merge Fails → Pipeline Stops_

---

## Sprint 5: Validações de Pré/Pós-Condições e Refinamento (Req-5, Req-6)

**Objetivo**: Refinar validações de pré/pós-condições, integrar com UI, adicionar feedback detalhado.

**Estimativa**: 5 dias

**Dependências**: Sprint 4 (pipeline)

### Tasks

- [ ] 5.1 Expandir _validar_precondiciones() com mensagens amigáveis
  - **Arquivo**: `app/services/servico_pipeline_relatorio.py` (refatorar método)
  - **Mudança**: Para cada falha de validação, adicionar mensagem detalhada e sugestões
  - **Exemplos**:
    - "Capítulos não sincronizados. Execute 'Sincronizar' antes de prosseguir."
    - "Espaço em disco insuficiente. Libere >100MB e tente novamente."
    - "Arquivo DOCX corrompido. Verifique integridade."
  - **Integração com UI**: Retornar `proximos_passos: ['sincronizar', 'liberar_disco', ...]`
  - _Requisitos: 5.1, 5.2, 5.3_

- [ ] 5.2 Expandir _validar_poscondiciones() com diagnóstico detalhado
  - **Arquivo**: `app/services/servico_pipeline_relatorio.py` (refatorar método)
  - **Mudança**: Para cada inconsistência detectada, adicionar remediação sugerida
  - **Exemplos**:
    - "Legenda duplicada 'Figura 1.1' detectada. Execute 'Limpar legendas' e reprocessar."
    - "Gap na numeração de tabelas (falta 'Tabela 2.3'). Revisar conteúdo do Capítulo 2."
  - **Integração**: Retornar array com cada inconsistência: `{'tipo': 'legenda_duplicada', 'elemento': 'Figura 1.1', 'remediacao': '...'}`
  - _Requisitos: 6.1, 6.2, 6.3_
  - _Propriedade 8: Validação e Reportagem_

- [ ] 5.3 Integrar pipeline em rota de envio de capítulo
  - **Arquivo**: `app/routes/relatorio.py` (ou novo endpoint em `api.py`)
  - **Rota**: POST `/relatorio/{relatorio_id}/processar-pipeline`
  - **Payload**: `{'uploads': {capitulo_id: docx_bytes_base64, ...}}`
  - **Tratamento**: Chamar `ServicoPipelineRelatorio.executar()` e retornar resultado estruturado
  - **Resposta HTTP**: Status 200 com dict de resultado (sucesso/erros/avisos)
  - **CSRF/Rate limit**: Aplicar proteções conforme convenção
  - _Requisitos: 3.1, 5.1, 5.2_

- [ ] 5.4 Adicionar persistência de resultado de pipeline em EnvioConteudo
  - **Arquivo**: `app/models/envio_conteudo.py` (adicionar campos)
  - **Campos novos**:
    ```python
    resultado_pipeline = db.Column(db.JSON, nullable=True)  # Armazenar dict de resultado
    processado_em = db.Column(db.DateTime, nullable=True)   # Timestamp de processamento
    ```
  - **Integração**: Após executar pipeline, salvar resultado em BD para auditoria
  - _Requisitos: 1.2, NF-1_

- [ ] 5.5 Criar Checkpoint: Validar pré/pós-condições
  - Validar pré-condição: Upload sem sync anterior → rejeição clara
  - Validar pré-condição: Capítulo inexistente → erro específico
  - Validar pós-condição: Legendas duplicadas detectadas → aviso em resultado
  - Validar pós-condição: Numeração consistente → sem avisos
  - _Propriedade 7: Validação de Pré-Condições_
  - _Propriedade 8: Validação de Pós-Condições_

---

## Sprint 6: Testes Property-Based, Integração e Finalizações

**Objetivo**: Implementar suite completa de testes property-based validando 10 propriedades; testes de integração; documentação.

**Estimativa**: 8 dias

**Dependências**: Sprints 1-5

### Tasks

- [ ] 6.1 Implementar fixture de Hypothesis: relatorio_fixture()
  - **Arquivo**: `tests/conftest.py` (criar ou estender)
  - **Estratégia**: Gerar RelatorioProducao com capítulos, uploads válidos
  - **Variações**: Diferentes números de capítulos, diferentes classificações
  - ```python
    @st.composite
    def relatorio_fixture(draw):
        # ... gerar relatório com 1-5 capítulos, cada um com classificação aleatória
  - _Requisitos: NF-3_

- [ ] 6.2 Implementar fixture de Hypothesis: capitulo_fixture()
  - **Arquivo**: `tests/conftest.py`
  - **Estratégia**: Gerar CapituloDocumento com títulos variados (typos, espaços, acentos)
  - ```python
    @st.composite
    def capitulo_fixture(draw):
        # ... gerar títulos com variações controladas
  - _Requisitos: NF-2_

- [ ] 6.3 Implementar fixture de Hypothesis: uploads_dict_fixture()
  - **Arquivo**: `tests/conftest.py`
  - **Estratégia**: Gerar dicts com capitulo_id → docx_bytes
  - **Casos**: 0-5 capítulos, DOCX válido/inválido, vazios
  - ```python
    @st.composite
    def uploads_dict_fixture(draw):
        # ... gerar {cap_id: docx_bytes, ...}
  - _Requisitos: NF-3_

- [ ] 6.4 Implementar teste de Property 1: Rastreabilidade de Erros
  - **Arquivo**: `tests/test_propriedade_1_rastreabilidade.py`
  - **Teste**:
    ```python
    @given(operation_que_falha=st.sampled_from([...]), modo_falha=failure_modes())
    def test_erro_sempre_estruturado(operation_que_falha, modo_falha):
        resultado = executar_operacao_com_falha(operation_que_falha, modo_falha)
        assert resultado['sucesso'] == False
        assert len(resultado['erro']) > 0
        assert len(resultado['sugestoes']) > 0
        assert 'timestamp' in resultado
    ```
  - **Mínimo**: 100+ iterações
  - _Propriedade 1_

- [ ] 6.5 Implementar teste de Property 2: Determinismo de Localização
  - **Arquivo**: `tests/test_propriedade_2_determinismo.py`
  - **Teste**:
    ```python
    @given(capitulo=capitulo_fixture(), doc=template_fixture())
    def test_localizacao_deterministica(capitulo, doc):
        resultado1 = localizar_range_capitulo_robusto(doc, capitulo)
        resultado2 = localizar_range_capitulo_robusto(doc, capitulo)
        assert resultado1 == resultado2
    ```
  - **Mínimo**: 100+ iterações
  - _Propriedade 2_

- [ ] 6.6 Implementar teste de Property 3: Coerência de Estrutura
  - **Arquivo**: `tests/test_propriedade_3_coerencia.py`
  - **Teste**:
    ```python
    @given(operacao=operacao_fixture())
    def test_estrutura_dict_sempre_completa(operacao):
        resultado = executar_operacao(operacao)
        campos_obrigatorios = ['sucesso', 'erro', 'etapa', 'relatorio_id', 'sugestoes', 'timestamp']
        for campo in campos_obrigatorios:
            assert campo in resultado, f"Campo '{campo}' faltando"
    ```
  - **Mínimo**: 100+ iterações
  - _Propriedade 3_

- [ ] 6.7 Implementar teste de Property 4: Classificação + Seções
  - **Arquivo**: `tests/test_propriedade_4_classificacao.py`
  - **Teste**:
    ```python
    @given(rel=relatorio_com_multiplos_tipos_fixture())
    def test_sync_integra_classificacao(rel):
        resultado = ressincronizar_capitulos_com_classificacao(rel)
        for cap in resultado['capitulos']:
            assert cap.classificacao in ['textual', 'pre_textual', 'pos_textual', 'anexo', 'apendice']
            assert cap.prefixo_indice is not None
    ```
  - **Mínimo**: 100+ iterações
  - _Propriedade 4_

- [ ] 6.8 Implementar teste de Property 5: Parada Segura em Erro
  - **Arquivo**: `tests/test_propriedade_5_parada_segura.py`
  - **Teste**:
    ```python
    @given(rel=relatorio_fixture(), uploads_com_falha=uploads_com_merge_invalido_fixture())
    def test_pipeline_para_em_erro_merge(rel, uploads_com_falha):
        resultado = ServicoPipelineRelatorio.executar(rel.id, uploads_com_falha)
        assert resultado['sucesso'] == False
        etapas_executadas = [e['etapa'] for e in resultado['etapas']]
        assert 'numeracao' not in etapas_executadas or resultado['etapas'][1]['resultado']['sucesso'] == False
    ```
  - **Mínimo**: 50+ iterações
  - _Propriedade 5_

- [ ] 6.9 Implementar teste de Property 6: Idempotência Completa
  - **Arquivo**: `tests/test_propriedade_6_idempotencia.py`
  - **Teste**:
    ```python
    @given(rel=relatorio_fixture(), uploads=uploads_dict_fixture())
    def test_pipeline_idempotente(rel, uploads):
        resultado1 = ServicoPipelineRelatorio.executar(rel.id, uploads)
        hash1 = sha256(open(rel.caminho_template, 'rb').read())
        
        resultado2 = ServicoPipelineRelatorio.executar(rel.id, uploads)
        hash2 = sha256(open(rel.caminho_template, 'rb').read())
        
        assert hash1 == hash2, "Execução 2x produziu arquivos diferentes"
    ```
  - **Mínimo**: 50+ iterações (computacionalmente pesado)
  - _Propriedade 6_
  - _Exemplo 2: Pipeline Idempotent_

- [ ] 6.10 Implementar teste de Property 7: Validação Pré-Condições
  - **Arquivo**: `tests/test_propriedade_7_precondiciones.py`
  - **Teste**:
    ```python
    @given(rel_invalido=relatorio_nao_sincronizado_fixture())
    def test_precondicion_rejeita_invalido(rel_invalido):
        resultado = ServicoPipelineRelatorio._validar_precondiciones(rel_invalido.id, {})
        assert resultado['valido'] == False
        assert len(resultado['motivos_rejeicao']) > 0
    ```
  - **Mínimo**: 100+ iterações
  - _Propriedade 7_

- [ ] 6.11 Implementar teste de Property 8: Validação Pós-Condições
  - **Arquivo**: `tests/test_propriedade_8_poscondiciones.py`
  - **Teste**:
    ```python
    @given(rel=relatorio_fixture(), uploads=uploads_dict_fixture())
    def test_poscondicion_detecta_inconsistencias(rel, uploads):
        ServicoPipelineRelatorio.executar(rel.id, uploads)
        inconsistencias = ServicoPipelineRelatorio._validar_poscondiciones(rel.caminho_template)
        # Se legendas duplicadas, devem ser reportadas
        if inconsistencias['inconsistencias']:
            assert any('legenda' in inc['tipo'] for inc in inconsistencias['inconsistencias'])
    ```
  - **Mínimo**: 50+ iterações
  - _Propriedade 8_

- [ ] 6.12 Implementar teste de Property 9: Segurança em Mensagens
  - **Arquivo**: `tests/test_propriedade_9_seguranca.py`
  - **Teste**:
    ```python
    @given(erros_diversos=erro_fixture())
    def test_erro_sem_caminhos_absolutos(erros_diversos):
        resultado = ServicoNiveladorErros.executar_com_tratamento(
            operacao_que_falha, falha=erros_diversos
        )
        assert resultado['sucesso'] == False
        assert '/' not in resultado['erro'] or 'C:\\' not in resultado['erro']
        assert 'File' not in resultado['erro']  # Sem "File '/usr/...' line 123"
    ```
  - **Mínimo**: 100+ iterações
  - _Propriedade 9_

- [ ] 6.13 Implementar teste de Property 10: Determinismo de Multi-Nível
  - **Arquivo**: `tests/test_propriedade_10_determinismo_multinivel.py`
  - **Teste**:
    ```python
    @given(cap=capitulo_fixture(), doc=template_fixture())
    def test_ordem_match_deterministica(cap, doc):
        resultado1 = localizar_range_capitulo_robusto(doc, cap, estrategia='multi_niveis')
        resultado2 = localizar_range_capitulo_robusto(doc, cap, estrategia='multi_niveis')
        assert resultado1['estrategia_usada'] == resultado2['estrategia_usada']
        # Se tentou exato primeiro, sempre tentará exato primeiro
    ```
  - **Mínimo**: 100+ iterações
  - _Propriedade 10_

- [ ] 6.14 Criar testes de integração end-to-end
  - **Arquivo**: `tests/test_integracao_end_to_end.py`
  - **Cenários**:
    1. Upload de 3 capítulos validamente → Pipeline OK
    2. Upload de capítulo com typo → Detectado, merge com fuzzy, OK
    3. Upload de DOCX corrompido → Erro capturado, mensagem clara
    4. Upload com capítulo não encontrado → Erro, sugestões, próximos capítulos continuam
    5. Pipeline 2x → Idempotente (mesmo checksum)
  - **Validação**: Cada cenário validar estrutura de resultado + conteúdo do DOCX final
  - _Requisitos: Todos_

- [ ] 6.15 Documentar API de pipeline em docstring
  - **Arquivo**: `app/services/servico_pipeline_relatorio.py`
  - **Conteúdo**: Docstring de classe + cada método com:
    - O quê: Responsabilidade
    - Parâmetros: Tipo, descrição, intervalo válido
    - Retorno: Estrutura dict com exemplos
    - Exceções: Quais podem ser levantadas (se aplicável)
    - Exemplos: Código de uso
  - ```python
    def executar(relatorio_id: int, uploads_dict: dict) -> dict:
        """Executa pipeline completo de montagem de relatório.
        
        Args:
            relatorio_id: ID do relatório em produção
            uploads_dict: Dict {capitulo_id: docx_bytes_base64}
        
        Returns:
            {
                'sucesso': bool,
                'relatorio_id': int,
                'etapas': [...],
                'erros': [...],
                'avisos': [...]
            }
        
        Example:
            resultado = ServicoPipelineRelatorio.executar(
                relatorio_id=123,
                uploads_dict={1: b'...', 2: b'...'}
            )
            if resultado['sucesso']:
                print(f"Pipeline concluído em {resultado['tempo_total_ms']}ms")
        """
  - _Requisitos: Todos_

- [ ] 6.16 Criar Checkpoint Final: Suite Completa de Testes
  - Executar todos os testes property-based (100+ iterações cada)
  - Executar testes de integração (5 cenários)
  - Validar coverage: >90% em servico_pipeline_relatorio.py
  - Validar que todas as 10 propriedades estão coberta
  - Gerar relatório de cobertura
  - _Propriedades: 1-10_

---

## Notas de Implementação

### Convenções de Código (PT-BR)

- Todas as classes: `ServicoX`, `PipelineY`, nomes em português
- Todas as funções/variáveis: snake_case em português (`localizar_range_capitulo_robusto`)
- Comentários e docstrings: português do Brasil
- Sem nomes em inglês em domínios de negócio

### Regras de Integração com Serviços Existentes

1. **servico_merge_docx**: Estender `localizar_range_capitulo()` → novo `localizar_range_capitulo_robusto()`
2. **servico_sincronizar_capitulos**: Integrar `servico_classificacao_capitulos` + `servico_extracao_secoes`
3. **servico_captioning**: Sem mudanças estruturais (apenas envolver com tratamento de erro)
4. **servico_cross_refs**: Sem mudanças estruturais (apenas envolver com tratamento de erro)
5. **servico_toc**: Sem mudanças estruturais (apenas envolver com tratamento de erro)

### Rollback Strategies

| Sprint | Rollback | Comando |
|--------|----------|---------|
| 1 | Remover servico_nivelador_erros.py | `git rm app/services/servico_nivelador_erros.py` |
| 2 | Remover localizar_range_capitulo_robusto() | `git checkout app/services/servico_merge_docx.py` |
| 3 | Remover campos de CapituloDocumento | `flask db downgrade` + `git checkout app/models/capitulo_documento.py` |
| 4 | Remover servico_pipeline_relatorio.py | `git rm app/services/servico_pipeline_relatorio.py` |
| 5 | Remover rota de pipeline | `git checkout app/routes/relatorio.py` |
| 6 | Remover testes | `git rm tests/test_propriedade_*.py` |

### Performance Targets

| Operação | Alvo | Método de Validação |
|----------|------|---------------------|
| Localização robusta | <500ms | Timer em teste unit |
| Merge de 1 capítulo | <2s | Timer em teste unit |
| Numeração de 30 figuras | <5s | Timer em teste unit |
| Cross-refs de 20 tags | <2s | Timer em teste unit |
| TOC gen com 5 capítulos | <1s | Timer em teste unit |
| **Pipeline completo (5 caps)** | **<30s** | Timer em teste integração |

### Arquivos Modificados / Criados

| Arquivo | Tipo | Sprint |
|---------|------|--------|
| `app/services/servico_nivelador_erros.py` | Novo | 1 |
| `app/services/servico_pipeline_relatorio.py` | Novo | 4 |
| `app/services/servico_merge_docx.py` | Mod | 2 |
| `app/services/servico_sincronizar_capitulos.py` | Mod | 3 |
| `app/models/capitulo_documento.py` | Mod | 3 |
| `migrations/versions/XXXX_adicionar_campos_capitulo.py` | Novo | 3 |
| `tests/conftest.py` | Mod | 6 |
| `tests/test_propriedade_*.py` | Novo | 6 |
| `tests/test_integracao_end_to_end.py` | Novo | 6 |

---

## Task Dependency Graph

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1.1", "1.3"],
      "descricao": "Infraestrutura de logging e tratamento de erros"
    },
    {
      "id": 1,
      "tasks": ["1.2", "2.1", "2.2"],
      "descricao": "Testes de logging + primeiras estratégias de localização"
    },
    {
      "id": 2,
      "tasks": ["2.3", "2.4", "3.1"],
      "descricao": "Fuzzy match + contexto + model updates"
    },
    {
      "id": 3,
      "tasks": ["2.5", "2.6", "3.2"],
      "descricao": "Integração de estratégias de localização + sync com classificação"
    },
    {
      "id": 4,
      "tasks": ["2.7", "2.8", "3.3"],
      "descricao": "Testes de localização + deprecação de método antigo"
    },
    {
      "id": 5,
      "tasks": ["3.4", "3.5", "3.6", "4.1"],
      "descricao": "Validações de sync + início do pipeline"
    },
    {
      "id": 6,
      "tasks": ["4.2", "4.3", "4.4"],
      "descricao": "Fases de validação pré-condições, merge e numeração"
    },
    {
      "id": 7,
      "tasks": ["4.5", "4.6", "4.7"],
      "descricao": "Fases de cross-refs, índices e validação pós-condições"
    },
    {
      "id": 8,
      "tasks": ["4.8", "4.9", "4.10"],
      "descricao": "Orquestração completa do pipeline + testes de idempotência e erro"
    },
    {
      "id": 9,
      "tasks": ["4.11", "5.1", "5.2"],
      "descricao": "Checkpoint de pipeline + refinamento de validações"
    },
    {
      "id": 10,
      "tasks": ["5.3", "5.4", "5.5"],
      "descricao": "Integração com rotas + persistência + checkpoint final Sprint 5"
    },
    {
      "id": 11,
      "tasks": ["6.1", "6.2", "6.3"],
      "descricao": "Fixtures de Hypothesis para testes"
    },
    {
      "id": 12,
      "tasks": ["6.4", "6.5", "6.6", "6.7"],
      "descricao": "Testes property 1-4 (rastreabilidade, determinismo, coerência, classificação)"
    },
    {
      "id": 13,
      "tasks": ["6.8", "6.9", "6.10"],
      "descricao": "Testes property 5-7 (parada segura, idempotência, pré-condições)"
    },
    {
      "id": 14,
      "tasks": ["6.11", "6.12", "6.13"],
      "descricao": "Testes property 8-10 (pós-condições, segurança, determinismo multi-nível)"
    },
    {
      "id": 15,
      "tasks": ["6.14", "6.15"],
      "descricao": "Testes de integração end-to-end + documentação de API"
    },
    {
      "id": 16,
      "tasks": ["6.16"],
      "descricao": "Checkpoint final: suite completa de testes"
    }
  ]
}
```

---

## Métricas de Sucesso

### Por Sprint

| Sprint | Métrica | Alvo | Validação |
|--------|---------|------|-----------|
| 1 | Logging estruturado funcional | 100% de serviços críticos com tratamento | Arquivo .log em JSON para erro |
| 2 | Localização robusta | 95%+ taxa de acerto (typos, espaços, acentos) | Test suite com 100+ casos |
| 3 | Sync com classificação | 100% de capítulos com classificacao preenchida | Query BD com filtro por classificacao |
| 4 | Pipeline orquestrador | Executa 5 fases com validações | 1 teste end-to-end com 3 capítulos |
| 5 | Validações pré/pós | Rejeita 100% de estados inválidos | Testes com 50+ casos de rejeição |
| 6 | Testes property-based | 10 propriedades, 100+ iterações cada | Coverage >90% em pipeline |

### Globais

| Métrica | Alvo | Validação |
|---------|------|-----------|
| **Tempo pipeline** | <30s (5 caps, 30 figs) | Cronometer em teste integração |
| **Idempotência** | 100% (execução 2x = checksum igual) | Property test 6 |
| **Taxa de erro detectada** | 100% (nenhum erro silencioso) | Property test 1 |
| **Cobertura de teste** | >90% em `servico_pipeline_relatorio.py` | `pytest --cov` |
| **ABNT compliance** | TOC com páginas, numeração correta | Validação manual de PDF |

---

## Critérios de Aceição

- ✅ Todos os 10 requisitos implementados (Req-1 a Req-6, NF-1 a NF-5)
- ✅ 10 propriedades ortogonais validadas com PBT (100+ iterações cada)
- ✅ Suite de testes integração (end-to-end com 5+ cenários)
- ✅ Logging estruturado em JSON com contexto completo
- ✅ Zero erros silenciosos (pipeline com feedback explícito)
- ✅ Idempotência confirmada (execução 2x = resultado equivalente)
- ✅ Performance <30s atendo
- ✅ Documentação API (docstrings, exemplos)
- ✅ Código em português do Brasil
- ✅ Sem breaking changes em serviços existentes (backward compatible)


## Notes

Este plano de implementação segue as convenções do projeto SRA-PLI:
- Código em português do Brasil
- Estrutura de serviços em `app/services/`
- Tratamento centralizado de erros via `ServicoNiveladorErros`
- Pipeline orquestrado com validações de pré/pós-condições
- Testes property-based com Hypothesis para validação de propriedades

As dependências principais são:
- Flask 3.0 + SQLAlchemy 2.0
- python-docx + lxml para manipulação de DOCX
- Hypothesis para testes property-based
- WeasyPrint para exportação PDF (opcional)

O pipeline foi projetado para ser tolerante a falhas e idempotente, garantindo que execuções repetidas com os mesmos inputs produzam resultados idênticos.