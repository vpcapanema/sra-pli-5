---
description: Como criar tabelas na interface do SRA
---

# Regra obrigatória: Tabelas

**TODAS as tabelas do sistema DEVEM usar a macro `tabela()`** definida em:

```
app/templates/components/compartilhados/tabela.html
```

## Nunca faça isso

- Nunca crie `<table>` manual em nenhum template
- Nunca use classes `.sra-table` diretamente fora da macro
- Nunca remova a coluna de seleção (checkbox) ou a coluna de ações

## Como usar

1. Importar a macro no template:
```jinja
{% from "components/compartilhados/tabela.html" import tabela %}
```

2. Montar as linhas como lista de listas (primeiro item = ID da linha):
```jinja
{% set linhas = [] %}
{% for item in itens %}
    {% set acoes %}
        <button class="sra-button sra-button--sm">Editar</button>
    {% endset %}
    {% set _ = linhas.append([
        item.id,
        item.nome,
        item.status,
        acoes
    ]) %}
{% endfor %}
```

3. Chamar a macro (última coluna de `colunas` é sempre "Ações"):
```jinja
{{ tabela(
    colunas=['ID', 'Nome', 'Status', 'Ações'],
    linhas=linhas,
    vazio='Nenhum item encontrado.'
) }}
```

4. Para ações em lote, adicionar `acoes_lote`:
```jinja
{{ tabela(
    colunas=['ID', 'Nome', 'Ações'],
    linhas=linhas,
    acoes_lote=[
        {'label': 'Excluir selecionados', 'action': 'Excluir', 'url': '/rota/lote/excluir'}
    ]
) }}
```

## O que a macro inclui automaticamente

- Coluna de checkbox (select all no header, select por linha)
- Última coluna alinhada à direita (ações)
- Barra de ações em lote (aparece ao selecionar itens)
- Scroll horizontal se o conteúdo exceder o card
- Contagem de selecionados + confirmação via SweetAlert2

## Regras visuais

- A tabela NUNCA deve ultrapassar os limites do card pai
- Respeitar os paddings do `.sra-card__content`
- Se houver muitas colunas, a tabela faz scroll horizontal dentro do container
