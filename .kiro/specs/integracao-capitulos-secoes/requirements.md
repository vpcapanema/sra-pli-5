# Requirements Document - Integração do Conceito de Capítulos com Seções DOCX

## Introdução

Este documento descreve os requisitos para a análise e integração do novo conceito de capítulos (distinção seção DOCX vs capítulo conceitual) com os serviços existentes do SRA-PLI. O objetivo é implementar um sistema unificado de numeração e rastreamento que capture as quebras de seção e página do DOCX, permitindo a atualização automática de índices para capítulos, tabelas, figuras e equações.

## Contexto

O sistema SRA-PLI atualmente possui:
1. **Serviço de Extração Canônica** (`servico_extracao_canonica.py`) - extrai estrutura do DOCX
2. **Serviço de Sincronização de Capítulos** (`servico_sincronizar_capitulos.py`) - alinha capítulos do banco com DOCX
3. **Serviço de TOC** (`servico_toc.py`) - geração de sumário
4. **Serviço de Cross-References** (`servico_cross_refs.py`) - referências cruzadas
5. **Serviço de Captioning** (`servico_captioning.py`) - legendas de figuras/tabelas
6. **Serviço de Merge DOCX** (`servico_merge_docx.py`) - montagem de documentos
7. **Outros serviços** relacionados ao fluxo de relatórios

O novo conceito introduz:
- **Capítulo**: nível 1, textual, sem classificação
- **Subcapítulo**: nível ≥ 2, textual, com pai
- **Anexo**: `pos_textual`, classificação `'anexo'`, prefixo `ANEXO_`
- **Apêndice**: `pos_textual`, classificação `'apendice'`, prefixo `APENDICE_`
- **Seção DOCX**: representação técnica de seções DOCX (`w:sectPr`)
- **Quebra de Página**: rastreamento de quebras dentro de seções

## Glossário

- **Sistema_SRA**: aplicação web SRA-PLI (backend Flask + frontend Jinja/JS/CSS)
- **Backend_SRA**: módulos Python sob `app/` (rotas, serviços, modelos, utilitários)
- **DOCX_Modelo**: documento DOCX base que define a estrutura canônica
- **DOCX_Producao**: documento DOCX em edição ativa
- **Seção_DOCX**: elemento técnico `w:sectPr` no OOXML, define propriedades de página
- **Capítulo_Conceitual**: unidade lógica de conteúdo (nível 1 = capítulo, nível ≥ 2 = subcapítulo)
- **Elemento_Indexável**: qualquer elemento que recebe numeração automática (capítulo, tabela, figura, equação)
- **Sistema_Numeração_Unificada**: sistema que atribui números sequenciais a todos os elementos indexáveis
- **Rastreamento_Páginas**: sistema que mapeia elementos para números de página
- **Serviço_Extracao_Seções**: novo serviço para extrair seções DOCX e quebras de página
- **Serviço_Classificacao_Capitulos**: novo serviço para classificar capítulos por estilo DOCX

## Requisitos

### Requisito 1: Análise Minuciosa dos Serviços Existentes

**User Story:** Como arquiteto do Sistema_SRA, quero analisar todos os serviços existentes para entender seus fluxos, dependências e pontos de integração, garantindo que a nova arquitetura de capítulos não cause prejuízo funcional.

#### Critérios de Aceitação

1. THE Backend_SRA SHALL ter todos os 18 serviços existentes analisados e documentados
2. WHEN a análise for concluída, THE Sistema_SRA SHALL ter um mapeamento completo de:
   - Dependências entre serviços
   - Fluxos de dados principais
   - Pontos de integração com o novo conceito de capítulos
   - Impactos potenciais de cada mudança
3. THE Análise SHALL identificar serviços críticos que NÃO podem ser modificados
4. THE Análise SHALL propor um plano de migração gradual com compatibilidade retroativa
5. THE Análise SHALL ser documentada em um relatório técnico com recomendações específicas

### Requisito 2: Integração com Serviço de Extração Canônica

**User Story:** Como mantenedor do Backend_SRA, quero integrar o novo conceito de capítulos com o `ServicoExtracaoCanonica` para que a extração capture tanto seções DOCX quanto a classificação conceitual.

#### Critérios de Aceitação

1. WHEN `ServicoExtracaoCanonica.extrair()` for executado, THE Sistema_SRA SHALL extrair:
   - Seções DOCX (`w:sectPr`) com propriedades de página
   - Quebras de página dentro de seções
   - Classificação conceitual de capítulos (capítulo, subcapítulo, anexo, apêndice)
   - Mapeamento entre estilos DOCX e tipos conceituais
2. THE Sistema_SRA SHALL preservar a saída JSON existente (`canonico_formatacao.json`, `canonico_estrutura_macro.json`, `canonico_capitulos.json`)
3. THE Sistema_SRA SHALL adicionar um novo arquivo `canonico_secoes.json` com:
   - Lista de seções DOCX com propriedades
   - Lista de quebras de página com posição
   - Mapeamento seção → capítulos
4. THE Sistema_SRA SHALL atualizar `canonico_capitulos.json` para incluir:
   - Campo `classificacao` (capítulo, subcapítulo, anexo, apêndice)
   - Campo `prefixo_indice` (ANEXO_, APENDICE_, vazio)
   - Campo `estilo_docx` (nome do estilo DOCX)
   - Campos `id_secao_inicio` e `id_secao_fim`

### Requisito 3: Integração com Serviço de Sincronização de Capítulos

**User Story:** Como mantenedor do Backend_SRA, quero atualizar o `ServicoSincronizarCapitulos` para usar a nova classificação conceitual e preservar o mapeamento com seções DOCX.

#### Critérios de Aceitação

1. WHEN `ressincronizar_capitulos()` for executado, THE Sistema_SRA SHALL:
   - Usar a nova classificação conceitual (capítulo, subcapítulo, anexo, apêndice)
   - Preservar o mapeamento com seções DOCX
   - Atualizar campos `classificacao`, `prefixo_indice`, `estilo_docx`
2. THE Sistema_SRA SHALL criar registros em `SecaoDOCX` para cada seção detectada
3. THE Sistema_SRA SHALL criar registros em `QuebraPagina` para quebras detectadas
4. THE Sistema_SRA SHALL manter a compatibilidade com capítulos existentes (migração automática)
5. THE Sistema_SRA SHALL atualizar a função `diff_capitulos()` para incluir a nova classificação

### Requisito 4: Sistema de Numeração Unificada

**User Story:** Como usuário do Sistema_SRA, quero que todos os elementos indexáveis (capítulos, tabelas, figuras, equações) recebam numeração automática e consistente.

#### Critérios de Aceitação

1. THE Sistema_SRA SHALL implementar um sistema de numeração unificada que:
   - Atribui números sequenciais a capítulos (1, 2, 3...)
   - Atribui números hierárquicos a subcapítulos (1.1, 1.2, 2.1...)
   - Atribui números a tabelas (Tabela 1, Tabela 2...)
   - Atribui números a figuras (Figura 1, Figura 2...)
   - Atribui números a equações (Equação 1, Equação 2...)
2. WHEN um elemento for adicionado ou removido, THE Sistema_SRA SHALL atualizar automaticamente todos os números subsequentes
3. THE Sistema_SRA SHALL preservar a numeração existente quando possível
4. THE Sistema_SRA SHALL permitir numeração específica para anexos (ANEXO A, ANEXO B) e apêndices (APÊNDICE A, APÊNDICE B)
5. THE Sistema_SRA SHALL expor uma API para consulta da numeração atual

### Requisito 5: Rastreamento de Números de Página

**User Story:** Como usuário do Sistema_SRA, quero que o sistema rastreie os números de página de todos os elementos para geração correta de sumário e listas.

#### Critérios de Aceitação

1. THE Sistema_SRA SHALL implementar um sistema de rastreamento de páginas que:
   - Mapeia cada capítulo para seu número de página inicial
   - Mapeia cada tabela/figura/equação para seu número de página
   - Considera quebras de seção e página do DOCX
2. WHEN o DOCX for modificado, THE Sistema_SRA SHALL recalcular os números de página
3. THE Sistema_SRA SHALL usar as seções DOCX (`w:sectPr`) para determinar propriedades de página
4. THE Sistema_SRA SHALL considerar diferentes formatos de numeração (romana, decimal) por seção
5. THE Sistema_SRA SHALL expor os números de página via API para geração de TOC

### Requisito 6: Integração com Serviço de TOC

**User Story:** Como mantenedor do Backend_SRA, quero atualizar o `ServicoTOC` para usar o novo sistema de numeração e rastreamento de páginas.

#### Critérios de Aceitação

1. WHEN `ServicoTOC.gerar_toc()` for executado, THE Sistema_SRA SHALL:
   - Usar a nova classificação conceitual
   - Usar os números de página rastreados
   - Incluir anexos e apêndices com prefixos apropriados
   - Gerar sumário hierárquico correto
2. THE Sistema_SRA SHALL atualizar a geração de listas de figuras e tabelas
3. THE Sistema_SRA SHALL preservar a formatação existente do TOC
4. THE Sistema_SRA SHALL tratar corretamente seções com numeração romana vs decimal

### Requisito 7: Integração com Serviço de Cross-References

**User Story:** Como mantenedor do Backend_SRA, quero atualizar o `ServicoCrossRefs` para usar o novo sistema de numeração unificada.

#### Critérios de Aceitação

1. WHEN `ServicoCrossRefs.resolver_referencias()` for executado, THE Sistema_SRA SHALL:
   - Usar os números unificados para referências
   - Atualizar referências automaticamente quando números mudarem
   - Tratar referências a anexos e apêndices
2. THE Sistema_SRA SHALL preservar a funcionalidade existente de referências cruzadas
3. THE Sistema_SRA SHALL adicionar suporte a referências a subcapítulos
4. THE Sistema_SRA SHALL validar referências contra a nova classificação

### Requisito 8: Integração com Serviço de Captioning

**User Story:** Como mantenedor do Backend_SRA, quero atualizar o `ServicoCaptioning` para usar o novo sistema de numeração unificada.

#### Critérios de Aceitação

1. WHEN `ServicoCaptioning.anexar_legenda()` for executado, THE Sistema_SRA SHALL:
   - Usar os números unificados para legendas
   - Atualizar números automaticamente quando elementos forem adicionados/removidos
   - Tratar legendas em anexos e apêndices
2. THE Sistema_SRA SHALL preservar a funcionalidade existente de legendas
3. THE Sistema_SRA SHALL adicionar suporte a legendas numeradas hierarquicamente
4. THE Sistema_SRA SHALL considerar a posição na página para legendas

### Requisito 9: Integração com Serviço de Merge DOCX

**User Story:** Como mantenedor do Backend_SRA, quero atualizar o `ServicoMergeDOCX` para considerar as seções DOCX e quebras de página.

#### Critérios de Aceitação

1. WHEN `ServicoMergeDOCX.mesclar()` for executado, THE Sistema_SRA SHALL:
   - Preservar as seções DOCX dos documentos originais
   - Manter as quebras de página corretas
   - Aplicar a numeração unificada ao documento final
   - Gerar TOC e listas com números de página corretos
2. THE Sistema_SRA SHALL tratar corretamente a junção de seções com propriedades diferentes
3. THE Sistema_SRA SHALL preservar a formatação de página (margens, orientação, tamanho)
4. THE Sistema_SRA SHALL atualizar referências cruzadas no documento mesclado

### Requisito 10: Migração de Dados Existente

**User Story:** Como administrador do Sistema_SRA, quero migrar os dados existentes para o novo esquema sem perda de informação.

#### Critérios de Aceitação

1. THE Sistema_SRA SHALL fornecer um script de migração que:
   - Classifica capítulos existentes (capítulo vs subcapítulo vs anexo vs apêndice)
   - Extrai seções DOCX de documentos existentes
   - Calcula números de página históricos
   - Atualiza referências cruzadas existentes
2. WHEN a migração for executada, THE Sistema_SRA SHALL preservar:
   - Todos os dados de capítulos existentes
   - Todas as relações entre capítulos e envios
   - Todo o histórico de auditoria
   - Todas as referências cruzadas existentes
3. THE Sistema_SRA SHALL permitir rollback em caso de falha na migração
4. THE Sistema_SRA SHALL validar a consistência dos dados após migração

### Requisito 11: Testes de Integração

**User Story:** Como desenvolvedor do Sistema_SRA, quero testes abrangentes que garantam a integração correta do novo conceito.

#### Critérios de Aceitação

1. THE Sistema_SRA SHALL ter testes unitários para:
   - `ServicoClassificacaoCapitulos`
   - `ServicoExtracaoSecoes`
   - Sistema de numeração unificada
   - Sistema de rastreamento de páginas
2. THE Sistema_SRA SHALL ter testes de integração para:
   - Fluxo completo de extração → classificação → sincronização
   - Geração de TOC com novo sistema
   - Atualização automática de números
   - Migração de dados
3. THE Sistema_SRA SHALL ter testes de regressão para garantir que funcionalidades existentes não foram quebradas
4. THE Sistema_SRA SHALL testar com documentos DOCX reais de diferentes complexidades

### Requisito 12: Documentação e APIs

**User Story:** Como desenvolvedor do Sistema_SRA, quero documentação clara e APIs consistentes para o novo sistema.

#### Critérios de Aceitação

1. THE Sistema_SRA SHALL ter documentação técnica que descreve:
   - O novo conceito de capítulos vs seções DOCX
   - O sistema de numeração unificada
   - O sistema de rastreamento de páginas
   - APIs e pontos de integração
2. THE Sistema_SRA SHALL ter documentação de migração para desenvolvedores
3. THE Sistema_SRA SHALL ter exemplos de uso para cada novo serviço
4. THE Sistema_SRA SHALL manter a documentação existente atualizada

## Requisitos Não-Funcionais

### NF1: Compatibilidade Retroativa
THE Sistema_SRA SHALL manter compatibilidade com todos os dados e funcionalidades existentes. Nenhum prejuízo funcional é permitido.

### NF2: Performance
THE Sistema_SRA SHALL processar documentos DOCX de até 500 páginas em menos de 30 segundos para operações de extração e sincronização.

### NF3: Consistência de Dados
THE Sistema_SRA SHALL garantir a consistência dos dados durante a migração e operações concorrentes.

### NF4: Manutenibilidade
THE Sistema_SRA SHALL ter código modular com baixo acoplamento entre serviços novos e existentes.

### NF5: Testabilidade
THE Sistema_SRA SHALL ter cobertura de testes de pelo menos 80% para o novo código.

### NF6: Documentação
THE Sistema_SRA SHALL ter documentação atualizada para todas as mudanças arquiteturais.