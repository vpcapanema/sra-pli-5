# Estratégia de Branches — SRA · PLI-SP

## Visão geral

O projeto utiliza uma estratégia **single-branch** com `master` como única branch de produção. Todas as mudanças devem convergir para `master`.

## Configuração atual

- **Branch principal**: `master` (default)
- **Remote HEAD**: `origin/master`
- **Proteção**: `master` deve ser o ponto de convergência única

## Workflow

### Para desenvolvimento local

1. **Criar branch local a partir de `master`**:
   ```cmd
   git checkout master
   git pull origin master
   git checkout -b feature/sua-feature
   ```

2. **Fazer commits na branch local**:
   ```cmd
   git add .
   git commit -m "feat: descrição da mudança"
   ```

3. **Enviar e criar PR** (se necessário review):
   ```cmd
   git push -u origin feature/sua-feature
   ```
   Criar Pull Request no GitHub para revisão.

4. **Merge para `master`** (após aprovação):
   ```cmd
   git checkout master
   git pull origin master
   git merge feature/sua-feature
   git push origin master
   ```

   Ou via GitHub PR e delete a branch remota.

5. **Limpar local**:
   ```cmd
   git branch -d feature/sua-feature
   ```

### Branches antigas (deprecadas)

As seguintes branches existem no remoto mas **não devem ser usadas**:
- `chore/limpeza-pendencias` — merged em `master`
- `chore/sanitizacao-backend-frontend` — merged em `master`
- `fix/database-url-psycopg3` — merged em `master`
- `fix/tasks-json-venv-path` — merged em `master`

Podem ser deletadas remotamente se desejado:
```cmd
git push origin --delete chore/limpeza-pendencias
git push origin --delete chore/sanitizacao-backend-frontend
git push origin --delete fix/database-url-psycopg3
git push origin --delete fix/tasks-json-venv-path
```

## Normas de commit

- Mensagens em **português do Brasil**
- Prefixo: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, etc.
- Exemplo: `feat(app): adicionar handlers de erro customizados`

## Resumo

✅ **Use apenas `master`** para desenvolvimento e produção.  
✅ **Crie branches locais** para features/fixes e delete após merge.  
✅ **Mantenha `master` limpo e atualizado**.  
✅ **Todos os commits** vão para `master` como fonte única de verdade.
