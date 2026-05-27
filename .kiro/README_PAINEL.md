# 📊 Painel de Progresso - SRA PLI-5

Sistema automático de visualização de progresso das tasks do projeto.

## 🎯 Componentes

### 1. **Painel Interativo** (`painel_progresso.html`)
- Visualização em tempo real do progresso
- 4 gráficos interativos (Chart.js)
- Matriz de dependências
- Estatísticas atualizadas
- **Gerado automaticamente** pelo script de atualização

### 2. **Script de Atualização** (`atualizar_painel.py`)
Analisa os arquivos `tasks.md` e regenera o HTML com dados frescos.

**Uso manual:**
```bash
python .kiro/atualizar_painel.py
```

**Saída:**
```
📊 Atualizando Painel de Progresso...
📖 Analisando Spec 1: tasks.md
   ✓ 50 tasks (✅ 5 | ⏳ 45)
📖 Analisando Spec 2: tasks.md
   ✓ 19 tasks (✅ 0 | ⏳ 19)
🎨 Gerando HTML...
✅ Painel atualizado: .kiro/painel_progresso.html
📊 Total: 69 tasks | ✅ 5 concluídas
```

### 3. **Hook de Auto-Atualização** (Automático)
Detecta mudanças em `tasks.md` e regenera o painel automaticamente.

**Nome do Hook:** `auto-update-painel`
**Evento:** Quando qualquer arquivo `tasks.md` é editado
**Ação:** Executa `python .kiro/atualizar_painel.py`

## 📖 Como Usar

### Abrir o Painel
1. **Direto no navegador:**
   ```
   file:///d:/REPOSITORIOS/sra-pli-5/.kiro/painel_progresso.html
   ```

2. **Com Live Server (VS Code):**
   - Instalar extensão "Live Server"
   - Click direito em `painel_progresso.html` → "Open with Live Server"

3. **Atualizar dados:**
   ```bash
   python .kiro/atualizar_painel.py
   ```

### Visualizações Disponíveis

#### 📊 Estatísticas Principais
- **Total de Tasks**: Contagem total de tasks em ambas specs
- **Concluídas**: Tasks completadas com checkbox `[x]`
- **Pendentes**: Tasks não iniciadas com checkbox `[ ]`
- **Taxa de Conclusão**: Percentual visual com progress bar

#### 📈 Gráficos
1. **Distribuição por Spec** (Doughnut)
   - Proporção Spec 1 vs Spec 2

2. **Status de Execução** (Bar)
   - Concluídas vs Pendentes

3. **Sprints - Spec 1** (Stacked Bar)
   - Progresso de cada sprint
   - Completas e Pendentes lado a lado

4. **Fases - Spec 2** (Horizontal Bar)
   - Tasks por fase

#### 📋 Tabela de Dependências
- Status de cada Sprint/Fase
- Bloqueadores
- Tarefas concluídas/total

## 🔄 Fluxo de Atualização

```
┌─────────────────┐
│  tasks.md       │
│  modificado     │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ Hook "auto-update-painel"
│ (fileEdited event)
└────────┬────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ python .kiro/atualizar_painel.py
│ ├─ Lê tasks.md (Spec 1 + 2)
│ ├─ Extrai status [x] vs [ ]
│ ├─ Calcula estatísticas
│ └─ Gera novo HTML
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ painel_progresso.html
│ (HTML regenerado com dados
│  frescos)
└──────────────────────────────┘
```

## 📝 Estrutura do tasks.md

O script analisa checkboxes no formato padrão:

```markdown
- [x] 1.1 Task concluída
  - Está marcada com [x]
  
- [ ] 1.2 Task pendente
  - Está marcada com [ ] (vazio)

- [x]* 1.3 Task concluída com asterisco
  - Variação também suportada
```

**Padrão esperado:**
```
- [CHECKBOX] NUMERO.NUMERO TITULO
```

Exemplos:
- `- [x] 1.1 Criar ServicoNiveladorErros` ✅
- `- [ ] 2.3 Implementar match fuzzy` ⏳
- `- [x]* 3.5 Testes property-based` ✅

## 🎨 Customizações

### Cores
Editável no HTML em `<style>`:
```css
.spec-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
```

### Responsividade
O painel já é mobile-friendly com breakpoints em `@media (max-width: 768px)`

### Gráficos
Usando Chart.js v3. Configuração em `<script>`:
```javascript
new Chart(ctx, {
    type: 'bar',  // ou 'doughnut', 'line', etc
    data: { ... },
    options: { ... }
})
```

## 🐛 Troubleshooting

### Script não atualiza?
1. Verifique se Python está instalado: `python --version`
2. Verifique a sintaxe dos tasks.md (checkboxes)
3. Execute manualmente: `python .kiro/atualizar_painel.py`

### HTML não aparece?
1. Verifique o caminho: `.kiro/painel_progresso.html`
2. Limpe cache do navegador (Ctrl+F5)
3. Verifique console do navegador (F12) para erros

### Hook não funciona?
1. Verifique se o hook foi criado: `kiro hooks list`
2. Salve o arquivo tasks.md com Ctrl+S
3. Aguarde ~3 segundos (timeout padrão)
4. Recarregue o HTML

## 📊 Exemplo de Saída

```
Total de Tasks:     69
├─ Spec 1 (Automação):        50 tasks
│  ├─ Concluídas: 5 ✅
│  └─ Pendentes: 45 ⏳
│
└─ Spec 2 (Integração):       19 tasks
   ├─ Concluídas: 0 ✅
   └─ Pendentes: 19 ⏳

Taxa de Conclusão: 7.2%
```

## 🔗 Links Úteis

- Arquivo: `.kiro/painel_progresso.html`
- Script: `.kiro/atualizar_painel.py`
- Tasks Spec 1: `.kiro/specs/automacao-montagem-relatorios/tasks.md`
- Tasks Spec 2: `.kiro/specs/integracao-capitulos-secoes/tasks.md`
- Painel Markdown: `.kiro/PAINEL_PROGRESSO_TASKS.md`

## 📅 Histórico de Atualizações

| Data | Atualização |
|------|-------------|
| 2026-05-26 | ✅ Painel criado e script de atualização implementado |
| 2026-05-26 | ✅ Hook de auto-atualização configurado |
| 2026-05-26 | ✅ 4 gráficos interativos implementados |

---

**Manutenção**: Para manter o painel atualizado, basta editar os `tasks.md` e o painel regenerará automaticamente! 🚀
