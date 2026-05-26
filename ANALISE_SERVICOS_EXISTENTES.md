# Análise Completa dos Serviços Existentes - SRA-PLI

## Resumo Executivo

Análise completa dos 18 serviços Python do projeto SRA-PLI para planejamento da integração do novo conceito de capítulos (distinção seção DOCX vs capítulo conceitual). A arquitetura atual é madura e bem estruturada, com serviços especializados que formam um pipeline completo de processamento de documentos DOCX.

## Mapa de Dependências entre Serviços

```
servico_relatorio (core)
├── servico_merge_docx (mescla conteúdo)
│   ├── servico_sincronizar_capitulos (sincroniza árvore)
│   └── servico_extracao_canonica (extrai estrutura)
├── servico_envio_autor (upload/autor)
│   ├── servico_captioning (legendas)
│   │   └── servico_cross_refs (referências)
│   └── servico_perfil_formatacao (perfil)
├── servico_acoes_relatorio (ações coordenador)
│   ├── servico_toc (sumário/listas)
│   ├── servico_capa (capa/folha rosto)
│   └── servico_finalizar_relatorio (finalização)
├── servico_sanitizar_docx (sanitização editor)
└── servico_email + servico_usuario (suporte)
```

## Análise Detalhada por Serviço

### 1. servico_extracao_canonica.py
**Propósito**: Extração canônica de parâmetros de formatação do DOCX modelo
**Dependências**: `servico_capa.py` (para extração detalhada)
**Integração com capítulos**: Extrai árvore hierárquica com regras de deduplicação
**Fluxo**: DOCX → seções → estilos → legendas → macro → capitulos → JSONs
**Impacto da integração**: ALTO - fonte da verdade para estrutura de capítulos
**Pontos de integração**:
- `_extrair_capitulos()`: extrai árvore hierárquica
- `_extrair_macro()`: determina tipo_elemento (pre_textual, textual, pos_textual)
- `_extrair_secoes()`: já extrai seções DOCX (w:sectPr)

### 2. servico_sincronizar_capitulos.py
**Propósito**: Sincronização de capítulos do banco com DOCX em produção
**Dependências**: `servico_extracao_canonica.py`
**Integração com capítulos**: Core - alinha banco com realidade do DOCX
**Fluxo**: extrair_capitulos(DOCX) → diff_capitulos → ressincronizar_capitulos
**Impacto da integração**: CRÍTICO - mantém consistência banco/DOCX
**Pontos de integração**:
- `diff_capitulos()`: compara banco com DOCX
- `ressincronizar_capitulos()`: aplica atualizações
- `_normalizar_titulo()`: chave de matching tolerante a renames

### 3. servico_toc.py
**Propósito**: Inserção de Sumário, Lista de Figuras, Lista de Tabelas
**Dependências**: `_ooxml_helpers.py`, `servico_perfil_formatacao.py`
**Integração com capítulos**: Ordem ABNT NBR 14724: Figuras → Tabelas → Equações → Siglas → Sumário
**Fluxo**: coletar elementos → garantir bookmarks → construir blocos → inserir pre-textual
**Impacto da integração**: ALTO - depende da estrutura completa de capítulos
**Pontos de integração**:
- `_garantir_bookmarks_em_headings()`: bookmarks para hyperlinks
- `_calcular_posicao_insercao()`: ordem ABNT
- `inserir_sumario()`: gera TOC com hyperlinks

### 4. servico_cross_refs.py
**Propósito**: Substituição OOXML-canônica de cross-references no corpo do DOCX
**Dependências**: `_ooxml_helpers.py`, `servico_captioning.py`
**Integração com capítulos**: Processa tags `{{fig:x}}`, `{{tab:x}}`, `{{eq:x}}`, `{{ref:x}}` no conteúdo textual
**Fluxo**: mapa_labels → substituição por campos REF → hyperlinks clicáveis
**Impacto da integração**: CRÍTICO - depende da numeração hierárquica baseada em capítulos
**Pontos de integração**:
- `_processar_paragrafo()`: substitui tags por campos REF
- `_resolver_info()`: obtém número e bookmark do elemento

### 5. servico_captioning.py
**Propósito**: Captioning automático para figuras, tabelas e equações
**Dependências**: `_ooxml_helpers.py`, `servico_perfil_formatacao.py`
**Integração com capítulos**: Numeração hierárquica baseada no heading mais recente (H1.<seq>)
**Fluxo**: Detecção elementos → numeração → legendas OOXML-canônicas → mapa_labels
**Impacto da integração**: ALTO - gera bookmarks para cross-refs e depende da estrutura de capítulos
**Pontos de integração**:
- `reindexar_captions()`: numeração hierárquica baseada em H1
- `_anexar_numero_inline_equacao()`: numeração de equações
- Geração de `mapa_labels` para cross-refs

### 6. servico_merge_docx.py
**Propósito**: Mescla in-place de conteúdo do autor no DOCX em produção
**Dependências**: `servico_sincronizar_capitulos.py`
**Integração com capítulos**: Localiza range de capítulos por heading → substitui conteúdo → sincroniza subcapítulos
**Fluxo**: DOCX autor → localizar_range_capitulo → substituir_capitulo → sincronizar_subcapitulos
**Impacto da integração**: CRÍTICO - operação central do fluxo autor/coordenador
**Pontos de integração**:
- `localizar_range_capitulo()`: encontra capítulo por heading
- `substituir_capitulo()`: mescla conteúdo
- `sincronizar_subcapitulos()`: atualiza subcapítulos

### 7. servico_relatorio.py
**Propósito**: Serviços de domínio para relatórios, modelos e capítulos
**Dependências**: Models (CapituloDocumento, RelatorioProducao, etc.)
**Integração com capítulos**: Ordenação por `tipo_elemento` (pre_textual < textual < pos_textual) + índice hierárquico
**Fluxo**: CRUD capítulos → ordenação natural → validação bloqueio
**Impacto da integração**: CORE - gerencia toda a lógica de capítulos no banco
**Pontos de integração**:
- `_criar_capitulos_da_arvore()`: criação hierárquica
- `esta_bloqueado()`: validação de edição
- Ordenação natural por tipo_elemento

### 8. servico_envio_autor.py
**Propósito**: Upload, extração, classificação e confirmação de conteúdo do autor
**Dependências**: `servico_merge_docx.py`, `servico_captioning.py`, `servico_cross_refs.py`
**Integração com capítulos**: Pipeline completo: upload → classificação → merge → captioning → cross-refs
**Fluxo**: Upload → extrair_estrutura → detectar_renomeacoes → confirmar (importar/rejeitar)
**Impacto da integração**: CRÍTICO - orquestra todo o fluxo do autor
**Pontos de integração**:
- `processar_upload()`: pipeline completo
- `gerar_docx_segmento()`: extrai conteúdo por capítulo
- `_descartar_envios_anteriores()`: regra de unicidade

### 9. servico_acoes_relatorio.py
**Propósito**: Catálogo central de ações operacionais do coordenador
**Dependências**: `servico_toc.py`, `servico_capa.py`, `servico_finalizar_relatorio.py`, `servico_captioning.py`
**Integração com capítulos**: Ações que afetam estrutura (sincronizar_capitulos, reindexar_captions)
**Fluxo**: Catálogo declarativo → validação → execução → feedback
**Impacto da integração**: ALTO - interface unificada para operações do coordenador
**Pontos de integração**:
- Catálogo de ações com regras de acesso
- Handlers que chamam outros serviços
- Validação de bloqueio e perfil

### 10. servico_finalizar_relatorio.py
**Propósito**: Finalização de relatório em produção (snapshot)
**Dependências**: `servico_captioning.py`, `servico_cross_refs.py`
**Integração com capítulos**: Aplica rotinas finais (reindexar captions) antes do snapshot
**Fluxo**: DOCX produção → aplicar_rotinas_finais → snapshot → RelatorioFinalizado
**Impacto da integração**: MODERADO - depende da estrutura finalizada de capítulos
**Pontos de integração**:
- `_aplicar_rotinas_finais()`: reindexa captions antes do snapshot
- `_nome_snapshot()`: geração de nome único
- `_checksum_sha256()`: validação de integridade

### 11. servico_sanitizar_docx.py
**Propósito**: Sanitização de DOCX para visualização no editor eigenpal
**Dependências**: Nenhuma (opera em bytes)
**Integração com capítulos**: Achatamento de text boxes flutuantes da capa
**Fluxo**: DOCX bytes → normalização células → normalização fontes → remoção elementos incompatíveis
**Impacto da integração**: BAIXO - não afeta estrutura de capítulos
**Pontos de integração**: Nenhum crítico

### 12. servico_perfil_formatacao.py
**Propósito**: Ponte entre BibliotecaFormatacaoCanonica e serviços de captioning/TOC
**Dependências**: JSONs canônicos (formatacao, capitulos, estrutura_macro)
**Integração com capítulos**: Mapeamento nível → nome_heading_por_nivel da biblioteca
**Fluxo**: Biblioteca → perfil → separadores/estilos/posições → serviços
**Impacto da integração**: ALTO - unifica parâmetros visuais com estrutura de capítulos
**Pontos de integração**:
- `de_relatorio()`: obtém perfil do relatório
- `nome_heading_por_nivel`: mapeamento da biblioteca
- Parâmetros de legendas e separadores

### 13. servico_capa.py
**Propósito**: Manipulação da CAPA, folha de rosto e controle de versões
**Dependências**: Nenhuma direta
**Integração com capítulos**: Extrai estrutura detalhada da capa (shapes, tabelas)
**Fluxo**: extrair_estrutura_capa → atualizar_capa → atualizar_folha_rosto → atualizar_controle_versoes
**Impacto da integração**: BAIXO - opera na região pré-textual
**Pontos de integração**:
- `extrair_estrutura_capa()`: inventário da capa
- `atualizar_capa()`: atualiza texto do shape

### 14. servico_email.py
**Propósito**: Integração com Brevo para e-mails transacionais
**Dependências**: Configuração (BREVO_API_KEY)
**Integração com capítulos**: Nenhuma
**Fluxo**: Convites → recuperação senha → templates HTML
**Impacto da integração**: NENHUM - serviço de suporte

### 15. servico_usuario.py
**Propósito**: Gestão de usuários, autenticação, convites
**Dependências**: `servico_email.py`
**Integração com capítulos**: Nenhuma
**Fluxo**: Autenticação → convites → ativação → recuperação
**Impacto da integração**: NENHUM - serviço de suporte

### 16. _ooxml_helpers.py
**Propósito**: Helpers para construir estruturas OOXML canônicas
**Dependências**: Nenhuma (biblioteca utilitária)
**Integração com capítulos**: Geração de bookmarks `_Ref_sra_*` e campos SEQ/REF
**Fluxo**: criação runs → campos → bookmarks → estilos
**Impacto da integração**: CRÍTICO - infraestrutura OOXML para todos os serviços
**Pontos de integração**:
- `criar_runs_campo()`: campos do Word
- `nome_bookmark()`: geração de bookmarks
- `criar_run_texto()`: texto com preservação de espaço

### 17. servico_classificacao_capitulos.py
**Propósito**: Classificação e validação de capítulos com conceito endurecido
**Dependências**: Models (CapituloDocumento)
**Integração com capítulos**: Core - mapeamento entre tipos conceituais e estilos DOCX
**Fluxo**: classificar_por_estilo → classificar_por_titulo → determinar_tipo_elemento → validar
**Impacto da integração**: CRÍTICO - implementa o conceito endurecido de capítulos
**Pontos de integração**:
- `classificar_por_estilo_docx()`: mapeamento estilos→tipos
- `classificar_por_titulo()`: classificação por conteúdo
- `determinar_tipo_elemento()`: pre_textual/textual/pos_textual

### 18. servico_extracao_secoes.py
**Propósito**: Extração de seções e quebras de página de documentos DOCX
**Dependências**: Models (SecaoDOCX, QuebraPagina)
**Integração com capítulos**: Mapeamento capítulos → seções
**Fluxo**: extrair_secoes → extrair_quebras → mapear_capitulos_para_secoes
**Impacto da integração**: MODERADO - gerencia numeração de páginas por seção
**Pontos de integração**:
- `extrair_secoes_do_docx()`: extração de seções DOCX
- `extrair_quebras_pagina()`: detecção de quebras
- `mapear_capitulos_secoes()`: associação capítulo→seção

## Pontos de Integração Críticos com Novo Conceito

### 1. **Numeração Hierárquica Baseada em Estrutura de Capítulos**
- **Serviços afetados**: `servico_captioning`, `servico_cross_refs`, `servico_toc`
- **Problema**: Atualmente baseado em `indice_h1_atual` (heading mais recente)
- **Solução**: Migrar para sistema de numeração unificada baseado em estrutura conceitual

### 2. **Sincronização Banco ↔ DOCX com Nova Classificação**
- **Serviços afetados**: `servico_sincronizar_capitulos`, `servico_extracao_canonica`
- **Problema**: Matching atual por `titulo_normalizado + tipo + nivel`
- **Solução**: Incluir `classificacao` e `prefixo_indice` no matching

### 3. **Ordenação Natural com Novos Tipos de Elementos**
- **Serviços afetados**: `servico_relatorio`, `servico_toc`
- **Problema**: `chave_ordem_indice` atual: (bucket_tipo, índice_hierárquico, ordem)
- **Solução**: Expandir bucket system para incluir anexos/apêndices

### 4. **Cross-References Dependentes de Estrutura de Capítulos**
- **Serviços afetados**: `servico_cross_refs`, `servico_captioning`
- **Problema**: Bookmarks `_Ref_sra_*` gerados com prefixo baseado em H1
- **Solução**: Atualizar geração de bookmarks para nova estrutura

### 5. **Perfil de Formatação e Mapeamento de Estilos**
- **Serviços afetados**: `servico_perfil_formatacao`, `servico_classificacao_capitulos`
- **Problema**: `nome_heading_por_nivel` da biblioteca vs nova classificação
- **Solução**: Extender perfil para incluir mapeamento estilos→classificação

## Estratégia de Integração Faseada

### Fase 1: Análise e Planejamento (2 semanas)
1. **Auditoria de Dependências**: Mapear todos os usos de `nivel_capitulo`, `tipo_elemento`, `indice_capitulo`
2. **Modelo de Dados Extendido**: Definir schema com novos campos (`classificacao`, `prefixo_indice`, `estilo_docx`, etc.)
3. **Scripts de Migração**: Preparar migração de dados existentes

### Fase 2: Serviços Core (3 semanas)
1. **servico_classificacao_capitulos**: Implementar novo algoritmo de classificação
2. **servico_relatorio**: Atualizar ordenação natural para nova estrutura
3. **servico_sincronizar_capitulos**: Ajustar algoritmos de matching
4. **servico_extracao_canonica**: Integrar nova classificação na extração

### Fase 3: Serviços Dependentes (3 semanas)
1. **servico_captioning**: Ajustar numeração hierárquica
2. **servico_cross_refs**: Garantir compatibilidade com bookmarks
3. **servico_toc**: Validar ordem ABNT com novos tipos
4. **servico_merge_docx**: Ajustar localização de capítulos

### Fase 4: Fluxos de Trabalho (2 semanas)
1. **servico_envio_autor**: Ajustar pipeline de classificação
2. **servico_acoes_relatorio**: Adicionar ações para novo conceito
3. **servico_finalizar_relatorio**: Validar rotinas finais

### Fase 5: Validação e Rollout (2 semanas)
1. **Testes Regressivos**: Validar todos os fluxos existentes
2. **Migração Dados**: Executar em ambiente controlado
3. **Documentação**: Atualizar documentação conceitual e técnica

## Riscos e Mitigações

### 1. Breaking Changes em Ordenação
- **Risco**: Alterações em `tipo_elemento` quebram ordenação existente
- **Mitigação**: Manter compatibilidade retroativa, campos opcionais inicialmente

### 2. Incompatibilidade com Dados Existentes
- **Risco**: Dados existentes não mapeiam para novo conceito
- **Mitigação**: Script de migração com validação e rollback

### 3. Performance de Sincronização
- **Risco**: Algoritmos de sincronização mais complexos
- **Mitigação**: Otimização incremental, cache de resultados

### 4. Complexidade de Testes
- **Risco**: Validação requer cenários completos de DOCX reais
- **Mitigação**: Testes com documentos de referência, validação faseada

## Conclusão

A arquitetura de serviços do SRA-PLI é robusta e bem estruturada, com separação clara de responsabilidades. A integração do novo conceito de capítulos requer cuidado especial nos serviços core devido às dependências em cascata. A abordagem faseada com foco primeiro no modelo de dados e serviços core minimiza riscos e permite validação incremental.

**Próximos passos**:
1. Criar spec detalhado para Fase 1 (Análise e Planejamento)
2. Implementar modelos extendidos (`SecaoDOCX`, `QuebraPagina`, campos adicionais em `CapituloDocumento`)
3. Desenvolver `ServicoNumeracaoUnificada` e `ServicoRastreamentoPaginas`
4. Iniciar integração com `servico_extracao_canonica` e `servico_sincronizar_capitulos`