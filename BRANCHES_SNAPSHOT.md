# Branches Snapshot — Referência Histórica

## Status atual (26 de maio de 2026)

### ✅ Branch Ativa: `master`
- **Status**: Versão estável em produção
- **Último commit**: `dee3b4f` (docs: estratégia de branches)
- **Estado**: `origin/master` sincronizado
- **Use para**: Desenvolvimento, deploy e produção

### 📦 Branch Snapshot: `cc85b287`
- **Commit**: `254312d` (Cascade snapshot 2026-05-25T11:51:40.1900394Z)
- **Tipo**: Snapshot/checkpoint histórico
- **Status**: ⚠️ NÃO MERGEAR COM MASTER (17 conflitos detectados)
- **Propósito**: Preservação de estado anterior para referência

## Por que cc85b287 existe?

A branch `cc85b287` foi criada como um snapshot automático de um estado anterior do projeto. Desde então:

- `master` evoluiu com novas mudanças (sanitização, fixes, error handlers)
- `cc85b287` contém mudanças que **divergem** de `master`
- Um merge direto criaria **17 conflitos** em arquivos críticos

## Arquivos com potencial conflito em cc85b287

Se no futuro você quiser trazer features específicas de `cc85b287`:

### Backend crítico
- `app/routes/relatorio.py` (1455+ linhas)
- `app/services/servico_envio_autor.py`
- `app/services/servico_relatorio.py`

### Frontend crítico
- `app/static/css/editor_*.css`
- `app/templates/editor_*.html`

### Modelos
- `app/models/envio_conteudo.py`
- `app/models/usuario.py`

## Como acessar cc85b287 se precisar?

```cmd
# Visualizar mudanças específicas
git show cc85b287:app/services/servico_capa.py

# Comparar com master
git diff master cc85b287 -- app/services/servico_capa.py

# Cherry-pick um commit específico (se necessário depois)
git cherry-pick <commit-hash>

# Checkout temporário para análise
git checkout cc85b287
git checkout master  # voltar
```

## Recomendação

✅ **Mantenha `master` como única branch de trabalho**  
📌 **Use `cc85b287` apenas como referência histórica**  
🚀 **Todas as mudanças futuras devem vir de `master`**

Se precisar de features de `cc85b287` no futuro:
1. Identifique a feature específica
2. Analise manualmente o código
3. Implemente novamente em `master` (evita conflitos)

## Próximas ações

- ✅ `master` é a versão oficial de trabalho
- 📦 `cc85b287` fica preservada no repositório para referência
- 🔄 Futuras mudanças vêm de `master` ou branches feature

---

*Documentação atualizada em 26 de maio de 2026*
