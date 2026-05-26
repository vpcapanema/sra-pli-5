# Plano de Implementação: Endurecimento do Conceito de Capítulos

## Objetivo
Implementar as regras conceituais definidas em `CONCEITO_CAPITULOS.md` no modelo `CapituloDocumento` e serviços relacionados.

## Etapas

### ETAPA 1: Modificar o Modelo CapituloDocumento
**Objetivo**: Adicionar campo `classificacao` e validações básicas

**Tarefas**:
1. Adicionar campo `classificacao` ao modelo
2. Adicionar validações de nível/tipo
3. Criar métodos helpers para índices completos
4. Atualizar `__init__.py` do pacote models

**Arquivos**:
- `app/models/capitulo_documento.py`
- `app/models/__init__.py`

### ETAPA 2: Criar Migration para o Campo Novo
**Objetivo**: Criar migration Alembic para adicionar campo `classificacao`

**Tarefas**:
1. Gerar migration: `flask db migrate -m "add classificacao to capitulos_documento"`
2. Revisar arquivo de migration gerado
3. Aplicar migration: `flask db upgrade`

**Arquivos**:
- `migrations/versions/*_add_classificacao_to_capitulos_documento.py`

### ETAPA 3: Atualizar Serviço de Extração Canônica
**Objetivo**: Atualizar extração para classificar capítulos automaticamente

**Tarefas**:
1. Analisar `servico_extracao_canonica.py`
2. Implementar lógica de classificação
3. Testar extração com documento de exemplo

**Arquivos**:
- `app/services/servico_extracao_canonica.py`

### ETAPA 4: Atualizar Serviços Relacionados
**Objetivo**: Atualizar serviços que usam `CapituloDocumento`

**Tarefas**:
1. Atualizar `servico_relatorio.py`
2. Atualizar `servico_acoes_relatorio.py`
3. Atualizar `servico_envio_autor.py`
4. Verificar consistência

**Arquivos**:
- `app/services/servico_relatorio.py`
- `app/services/servico_acoes_relatorio.py`
- `app/services/servico_envio_autor.py`

### ETAPA 5: Atualizar UI/Templates
**Objetivo**: Mostrar prefixos e classificação na interface

**Tarefas**:
1. Atualizar `arvore_capitulos.html`
2. Atualizar `editor_autor.html`
3. Atualizar `editor_coordenador.html`
4. Testar visualização

**Arquivos**:
- `app/templates/components/relatorio/arvore_capitulos.html`
- `app/templates/editor_autor.html`
- `app/templates/editor_coordenador.html`

### ETAPA 6: Testes e Validação
**Objetivo**: Validar implementação completa

**Tarefas**:
1. Criar testes unitários
2. Testar fluxo completo
3. Validar regras de negócio
4. Documentar mudanças

**Arquivos**:
- `tests/test_capitulo_conceito.py`
- `CONCEITO_CAPITULOS_IMPLEMENTADO.md`

## Regras de Validação a Implementar

### Para Capítulo (nível 1):
- `nivel_capitulo = 1`
- `id_capitulo_pai IS NULL`
- `tipo_elemento = 'textual'`
- `classificacao IS NULL`

### Para Subcapítulo:
- `nivel_capitulo ≥ 2`
- `id_capitulo_pai NOT NULL`
- `tipo_elemento` igual ao do pai
- `classificacao` igual à do pai

### Para Anexo/Apêndice:
- `tipo_elemento = 'pos_textual'`
- `classificacao IN ('anexo', 'apendice')`
- Pode ter hierarquia própria

## Índices Completos:
- Capítulos: 1, 2, 3...
- Subcapítulos: 1.1, 1.2, 2.1...
- Anexos: ANEXO_A, ANEXO_B...
- Apêndices: APENDICE_I, APENDICE_II...

## Critérios de Aceitação
1. Modelo atualizado com campo `classificacao`
2. Validações implementadas no modelo
3. Extração canônica classifica automaticamente
4. UI mostra prefixos corretamente
5. Regras de negócio validadas
6. Testes passando
7. Documentação atualizada
