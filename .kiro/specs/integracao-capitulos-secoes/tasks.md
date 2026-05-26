# Tasks Document - Integração do Conceito de Capítulos com Seções DOCX

## Visão Geral das Tarefas

Este documento lista as tarefas necessárias para implementar a integração do novo conceito de capítulos com os serviços existentes do SRA-PLI. As tarefas são organizadas por fases conforme definido no documento de design.

## Fase 1: Análise e Planejamento

### Tarefa 1.1: Análise Completa dos Serviços Existentes
**Status**: Pending  
**Estimativa**: 4 horas  
**Dependências**: Nenhuma  
**Responsável**: Kiro

**Descrição**: Ler e analisar todos os 18 serviços existentes para entender fluxos, dependências e pontos de integração.

**Subtarefas**:
1. Ler `servico_extracao_canonica.py` - serviço central de extração
2. Ler `servico_sincronizar_capitulos.py` - sincronização capítulos↔DOCX
3. Ler `servico_toc.py` - geração de sumário
4. Ler `servico_cross_refs.py` - referências cruzadas
5. Ler `servico_captioning.py` - legendas de figuras/tabelas
6. Ler `servico_merge_docx.py` - montagem de documentos
7. Ler `servico_relatorio.py` - gestão de relatórios
8. Ler `servico_envio_autor.py` - fluxo de envio/autor
9. Ler `servico_acoes_relatorio.py` - ações sobre relatórios
10. Ler `servico_finalizar_relatorio.py` - finalização de relatórios
11. Ler `servico_sanitizar_docx.py` - sanitização DOCX
12. Ler `servico_perfil_formatacao.py` - perfis de formatação
13. Ler `servico_capa.py` - geração de capa
14. Ler `servico_email.py` - envio de e-mails
15. Ler `servico_usuario.py` - gestão de usuários
16. Ler `_ooxml_helpers.py` - helpers OOXML
17. Documentar dependências entre serviços
18. Identificar pontos de integração críticos
19. Criar relatório de análise técnica

**Entregáveis**:
- Documento de análise com mapeamento de serviços
- Diagrama de dependências
- Lista de pontos de integração prioritários

### Tarefa 1.2: Planejamento Estratégico de Integração
**Status**: Pending  
**Estimativa**: 2 horas  
**Dependências**: Tarefa 1.1  
**Responsável**: Kiro

**Descrição**: Criar plano detalhado de migração faseada com compatibilidade retroativa.

**Subtarefas**:
1. Definir ordem de implementação das fases
2. Estabelecer critérios de aceitação para cada fase
3. Identificar riscos e mitigações
4. Planejar testes de regressão
5. Definir estratégia de rollback

**Entregáveis**:
- Plano de migração faseada
- Cronograma estimado
- Matriz de riscos

## Fase 2: Implementação de Modelos e Serviços Base

### Tarefa 2.1: Criar Modelo `SecaoDOCX`
**Status**: Pending  
**Estimativa**: 1 hora  
**Dependências**: Nenhuma  
**Responsável**: Kiro

**Descrição**: Implementar modelo SQLAlchemy para representar seções DOCX.

**Subtarefas**:
1. Criar arquivo `app/models/secao_docx.py`
2. Definir campos conforme design
3. Adicionar relacionamentos
4. Adicionar métodos utilitários
5. Registrar modelo em `app/models/__init__.py`

**Entregáveis**:
- Modelo `SecaoDOCX` funcional
- Migração Alembic para tabela `secoes_docx`

### Tarefa 2.2: Criar Modelo `QuebraPagina`
**Status**: Pending  
**Estimativa**: 1 hora  
**Dependências**: Nenhuma  
**Responsável**: Kiro

**Descrição**: Implementar modelo SQLAlchemy para representar quebras de página.

**Subtarefas**:
1. Criar arquivo `app/models/quebra_pagina.py`
2. Definir campos conforme design
3. Adicionar relacionamento com `SecaoDOCX`
4. Adicionar métodos utilitários
5. Registrar modelo em `app/models/__init__.py`

**Entregáveis**:
- Modelo `QuebraPagina` funcional
- Migração Alembic para tabela `quebras_pagina`

### Tarefa 2.3: Atualizar Modelo `CapituloDocumento`
**Status**: Pending  
**Estimativa**: 2 horas  
**Dependências**: Tarefas 2.1, 2.2  
**Responsável**: Kiro

**Descrição**: Adicionar novos campos ao modelo existente de capítulos.

**Subtarefas**:
1. Atualizar `app/models/capitulo_documento.py`
2. Adicionar campos `classificacao`, `prefixo_indice`, `estilo_docx`
3. Adicionar campos `id_secao_inicio`, `id_secao_fim`
4. Adicionar campos `numero_unificado`, `ordem_global`
5. Adicionar relacionamentos com `SecaoDOCX`
6. Atualizar métodos existentes
7. Criar migração Alembic

**Entregáveis**:
- Modelo `CapituloDocumento` atualizado
- Migração Alembic para novos campos

### Tarefa 2.4: Criar Tabela de Associação `capitulo_secao`
**Status**: Pending  
**Estimativa**: 1 hora  
**Dependências**: Tarefas 2.1, 2.3  
**Responsável**: Kiro

**Descrição**: Criar tabela de associação muitos-para-muitos entre capítulos e seções.

**Subtarefas**:
1. Definir tabela de associação em `app/models/capitulo_documento.py`
2. Adicionar relacionamento `secoes` em `CapituloDocumento`
3. Adicionar relacionamento `capitulos` em `SecaoDOCX`
4. Criar migração Alembic

**Entregáveis**:
- Tabela de associação `capitulo_secao`
- Relacionamentos configurados

### Tarefa 2.5: Implementar `ServicoClassificacaoCapitulos`
**Status**: Pending  
**Estimativa**: 3 horas  
**Dependências**: Nenhuma  
**Responsável**: Kiro

**Descrição**: Implementar serviço para classificar capítulos por estilo DOCX.

**Subtarefas**:
1. Criar arquivo `app/services/servico_classificacao_capitulos.py`
2. Implementar método `classificar_por_estilo()`
3. Implementar método `mapear_estilos_documento()`
4. Definir mapeamento padrão de estilos→classificações
5. Adicionar tratamento para anexos/apêndices
6. Criar testes unitários

**Entregáveis**:
- Serviço `ServicoClassificacaoCapitulos` funcional
- Testes unitários com cobertura > 80%

### Tarefa 2.6: Implementar `ServicoExtracaoSecoes`
**Status**: Pending  
**Estimativa**: 4 horas  
**Dependências**: Nenhuma  
**Responsável**: Kiro

**Descrição**: Implementar serviço para extrair seções DOCX e quebras de página.

**Subtarefas**:
1. Criar arquivo `app/services/servico_extracao_secoes.py`
2. Implementar método `extrair_secoes()`
3. Implementar método `extrair_quebras_pagina()`
4. Implementar método `mapear_capitulos_secoes()`
5. Adicionar parsing de propriedades de seção
6. Criar testes unitários com documentos de exemplo

**Entregáveis**:
- Serviço `ServicoExtracaoSecoes` funcional
- Testes unitários com documentos reais

## Fase 3: Integração com Extração Canônica

### Tarefa 3.1: Atualizar `ServicoExtracaoCanonica`
**Status**: Pending  
**Estimativa**: 3 horas  
**Dependências**: Tarefas 2.5, 2.6  
**Responsável**: Kiro

**Descrição**: Integrar novos serviços na extração canônica existente.

**Subtarefas**:
1. Atualizar `app/services/servico_extracao_canonica.py`
2. Adicionar import dos novos serviços
3. Modificar método `extrair()` para incluir classificação
4. Adicionar extração de seções e quebras
5. Salvar novo arquivo `canonico_secoes.json`
6. Atualizar retorno do método
7. Testar com documentos existentes

**Entregáveis**:
- `ServicoExtracaoCanonica` atualizado
- Extração completa com classificação e seções
- Arquivo `canonico_secoes.json` gerado

### Tarefa 3.2: Testar Extração com Documentos Reais
**Status**: Pending  
**Estimativa**: 2 horas  
**Dependências**: Tarefa 3.1  
**Responsável**: Kiro

**Descrição**: Validar a extração atualizada com diferentes tipos de documentos.

**Subtarefas**:
1. Criar script de teste `teste_extracao_completa.py`
2. Testar com documento simples (apenas capítulos)
3. Testar com documento complexo (anexos, apêndices)
4. Testar com documento com múltiplas seções
5. Validar classificação correta
6. Validar extração de seções
7. Corrigir bugs identificados

**Entregáveis**:
- Script de teste funcional
- Relatório de validação
- Correções de bugs identificados

## Fase 4: Integração com Sincronização

### Tarefa 4.1: Atualizar `ServicoSincronizarCapitulos`
**Status**: Pending  
**Estimativa**: 4 horas  
**Dependências**: Tarefas 2.1-2.6, 3.1  
**Responsável**: Kiro

**Descrição**: Integrar novos conceitos no serviço de sincronização.

**Subtarefas**:
1. Atualizar `app/services/servico_sincronizar_capitulos.py`
2. Modificar `diff_capitulos()` para incluir classificação
3. Modificar `ressincronizar_capitulos()` para:
   - Extrair seções e quebras
   - Classificar capítulos
   - Mapear capítulos para seções
   - Persistir seções e quebras
   - Atualizar campos de classificação
4. Adicionar tratamento para anexos/apêndices
5. Manter compatibilidade com dados existentes

**Entregáveis**:
- `ServicoSincronizarCapitulos` atualizado
- Sincronização com classificação e mapeamento de seções

### Tarefa 4.2: Testar Sincronização com Documentos Editados
**Status**: Pending  
**Estimativa**: 2 horas  
**Dependências**: Tarefa 4.1  
**Responsável**: Kiro

**Descrição**: Validar sincronização com documentos modificados.

**Subtarefas**:
1. Criar script `teste_sincronizacao_editada.py`
2. Testar adição de novo capítulo
3. Testar remoção de capítulo existente
4. Testar reordenação de capítulos
5. Testar conversão de capítulo para anexo
6. Validar mapeamento de seções
7. Validar persistência de quebras

**Entregáveis**:
- Script de teste de sincronização
- Validação de cenários de edição
- Correções de bugs

## Fase 5: Sistema de Numeração e Rastreamento

### Tarefa 5.1: Implementar `ServicoNumeracaoUnificada`
**Status**: Pending  
**Estimativa**: 5 horas  
**Dependências**: Tarefas 2.1-2.3  
**Responsável**: Kiro

**Descrição**: Implementar sistema de numeração unificada para todos os elementos.

**Subtarefas**:
1. Criar arquivo `app/services/servico_numeracao_unificada.py`
2. Implementar classe `ServicoNumeracaoUnificada`
3. Implementar método `calcular_numeracao()`
4. Implementar método `atualizar_numeracao()`
5. Implementar método `obter_numero()`
6. Adicionar suporte a:
   - Capítulos e subcapítulos
   - Anexos (ANEXO A, B, C...)
   - Apêndices (APÊNDICE A, B, C...)
   - Tabelas, figuras, equações
7. Criar testes unitários

**Entregáveis**:
- `ServicoNumeracaoUnificada` funcional
- Sistema de numeração completo
- Testes unitários abrangentes

### Tarefa 5.2: Implementar `ServicoRastreamentoPaginas`
**Status**: Pending  
**Estimativa**: 5 horas  
**Dependências**: Tarefas 2.1, 2.2, 5.1  
**Responsável**: Kiro

**Descrição**: Implementar sistema de rastreamento de números de página.

**Subtarefas**:
1. Criar arquivo `app/services/servico_rastreamento_paginas.py`
2. Implementar classe `ServicoRastreamentoPaginas`
3. Implementar método `calcular_paginas()`
4. Implementar método `obter_pagina_elemento()`
5. Considerar:
   - Seções com diferentes formatos de numeração
   - Quebras de página
   - Elementos flutuantes
   - Páginas em branco
6. Integrar com `ServicoExtracaoSecoes`
7. Criar testes unitários

**Entregáveis**:
- `ServicoRastreamentoPaginas` funcional
- Rastreamento preciso de páginas
- Testes com documentos complexos

### Tarefa 5.3: Integrar Numeração na Sincronização
**Status**: Pending  
**Estimativa**: 2 horas  
**Dependências**: Tarefas 4.1, 5.1, 5.2  
**Responsável**: Kiro

**Descrição**: Integrar sistemas de numeração e rastreamento na sincronização.

**Subtarefas**:
1. Atualizar `ServicoSincronizarCapitulos`
2. Chamar `ServicoNumeracaoUnificada` após sincronização
3. Chamar `ServicoRastreamentoPaginas` após sincronização
4. Atualizar campos `numero_unificado` e `ordem_global`
5. Testar numeração automática após edições

**Entregáveis**:
- Sincronização com numeração automática
- Atualização automática de números de página

## Fase 6: Integração com Serviços Dependentes

### Tarefa 6.1: Atualizar `ServicoTOC`
**Status**: Pending  
**Estimativa**: 3 horas  
**Dependências**: Tarefas 5.1, 5.2  
**Responsável**: Kiro

**Descrição**: Atualizar geração de sumário para usar nova classificação e numeração.

**Subtarefas**:
1. Atualizar `app/services/servico_toc.py`
2. Modificar `gerar_toc()` para:
   - Usar classificação de capítulos
   - Usar números unificados
   - Usar números de página rastreados
   - Formatar anexos/apêndices corretamente
3. Adicionar suporte a subcapítulos hierárquicos
4. Testar com documentos classificados

**Entregáveis**:
- `ServicoTOC` atualizado
- TOC com classificação e numeração corretas

### Tarefa 6.2: Atualizar `ServicoCrossRefs`
**Status**: Pending  
**Estimativa**: 3 horas  
**Dependências**: Tarefa 5.1  
**Responsável**: Kiro

**Descrição**: Atualizar referências cruzadas para usar nova numeração.

**Subtarefas**:
1. Atualizar `app/services/servico_cross_refs.py`
2. Modificar `resolver_referencias()` para:
   - Usar números unificados
   - Atualizar referências automaticamente
   - Tratar referências a anexos/apêndices
3. Adicionar suporte a referências a subcapítulos
4. Testar atualização automática

**Entregáveis**:
- `ServicoCrossRefs` atualizado
- Referências cruzadas com numeração unificada

### Tarefa 6.3: Atualizar `ServicoCaptioning`
**Status**: Pending  
**Estimativa**: 3 horas  
**Dependências**: Tarefa 5.1  
**Responsável**: Kiro

**Descrição**: Atualizar legendas para usar nova numeração.

**Subtarefas**:
1. Atualizar `app/services/servico_captioning.py`
2. Modificar `anexar_legenda()` para:
   - Usar números unificados
   - Atualizar números automaticamente
   - Tratar legendas em anexos/apêndices
3. Adicionar suporte a legendas hierárquicas
4. Testar com documentos complexos

**Entregáveis**:
- `ServicoCaptioning` atualizado
- Legendas com numeração unificada

### Tarefa 6.4: Atualizar `ServicoMergeDOCX`
**Status**: Pending  
**Estimativa**: 4 horas  
**Dependências**: Tarefas 5.1, 5.2, 6.1  
**Responsável**: Kiro

**Descrição**: Atualizar merge de documentos para considerar novas estruturas.

**Subtarefas**:
1. Atualizar `app/services/servico_merge_docx.py`
2. Modificar `mesclar()` para:
   - Preservar seções DOCX
   - Manter quebras de página
   - Aplicar numeração unificada
   - Gerar TOC com números corretos
3. Tratar junção de seções diferentes
4. Testar merge de documentos complexos

**Entregáveis**:
- `ServicoMergeDOCX` atualizado
- Merge que preserva estrutura de seções

## Fase 7: Migração de Dados

### Tarefa 7.1: Criar Script de Migração
**Status**: Pending  
**Estimativa**: 4 horas  
**Dependências**: Tarefas 2.1-2.6, 5.1, 5.2  
**Responsável**: Kiro

**Descrição**: Criar script para migrar dados existentes para novo esquema.

**Subtarefas**:
1. Criar script `migrar_capitulos_classificacao.py`
2. Implementar migração que:
   - Classifica capítulos existentes
   - Extrai seções de documentos existentes
   - Calcula números de página históricos
   - Atualiza referências cruzadas
3. Adicionar validação de consistência
4. Adicionar opção de rollback
5. Testar em ambiente de teste

**Entregáveis**:
- Script de migração funcional
- Documentação de uso
- Script de rollback

### Tarefa 7.2: Executar Migração em Teste
**Status**: Pending  
**Estimativa**: 2 horas  
**Dependências**: Tarefa 7.1  
**Responsável**: Kiro

**Descrição**: Executar e validar migração em ambiente de teste.

**Subtarefas**:
1. Criar backup de banco de teste
2. Executar script de migração
3. Validar consistência dos dados
4. Testar funcionalidades com dados migrados
5. Corrigir problemas identificados
6. Executar rollback se necessário

**Entregáveis**:
- Relatório de migração de teste
- Lista de problemas corrigidos
- Confirmação de consistência

## Fase 8: Testes e Validação

### Tarefa 8.1: Testes Unitários e de Integração
**Status**: Pending  
**Estimativa**: 6 horas  
**Dependências**: Todas as tarefas anteriores  
**Responsável**: Kiro

**Descrição**: Criar testes abrangentes para todo o sistema.

**Subtarefas**:
1. Criar testes unitários para cada novo serviço
2. Criar testes de integração para fluxos completos
3. Testar com documentos de diferentes complexidades
4. Testar cenários de borda
5. Medir cobertura de testes
6. Corrigir bugs identificados

**Entregáveis**:
- Suíte completa de testes
- Cobertura > 80% para novo código
- Relatório de bugs corrigidos

### Tarefa 8.2: Testes de Regressão
**Status**: Pending  
**Estimativa**: 4 horas  
**Dependências**: Tarefa 8.1  
**Responsável**: Kiro

**Descrição**: Garantir que funcionalidades existentes não foram quebradas.

**Subtarefas**:
1. Executar testes existentes do projeto
2. Testar fluxos principais do sistema
3. Validar compatibilidade com dados existentes
4. Testar performance com documentos grandes
5. Corrigir regressões identificadas

**Entregáveis**:
- Relatório de regressão
- Confirmação de compatibilidade
- Otimizações de performance

### Tarefa 8.3: Documentação Final
**Status**: Pending  
**Estimativa**: 3 horas  
**Dependências**: Todas as tarefas anteriores  
**Responsável**: Kiro

**Descrição**: Criar documentação completa do sistema atualizado.

**Subtarefas**:
1. Atualizar documentação técnica
2. Criar guia de migração para desenvolvedores
3. Documentar APIs e pontos de integração
4. Criar exemplos de uso
5. Atualizar README do projeto

**Entregáveis**:
- Documentação técnica atualizada
- Guia de migração
- Exemplos de uso

## Cronograma Estimado

**Fase 1**: 6 horas (Análise e Planejamento)
**Fase 2**: 12 horas (Modelos e Serviços Base)
**Fase 3**: 5 horas (Integração Extração)
**Fase 4**: 6 horas (Integração Sincronização)
**Fase 5**: 12 horas (Numeração e Rastreamento)
**Fase 6**: 13 horas (Integração Serviços Dependentes)
**Fase 7**: 6 horas (Migração de Dados)
**Fase 8**: 13 horas (Testes e Validação)

**Total Estimado**: 73 horas

## Riscos e Mitigações

1. **Risco**: Compatibilidade com dados existentes
   **Mitigação**: Migração gradual, campos opcionais inicialmente, rollback planejado

2. **Risco**: Performance com documentos grandes
   **Mitigação**: Otimização incremental, cache, processamento assíncrono

3. **Risco**: Complexidade da integração
   **Mitigação**: Abordagem faseada, testes contínuos, validação em cada fase

4. **Risco**: Bugs em produção
   **Mitigação**: Testes abrangentes, ambiente de staging, monitoramento

## Critérios de Aceitação Final

1. Todos os serviços existentes funcionam sem prejuízo
2. Nova classificação de capítulos está operacional
3. Sistema de numeração unificada funciona corretamente
4. Rastreamento de páginas é preciso
5. Migração de dados foi bem-sucedida
6. Testes têm cobertura > 80%
7. Documentação está atualizada
8. Performance aceitável com documentos de até 500 páginas