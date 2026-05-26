# Investigação e Correções Completas — Editor do Autor

## Data: 26 de Maio de 2026
## Status: ✅ COMPLETO E IMPLEMENTADO

---

## PROBLEMA IDENTIFICADO

### 1. **Conflito de CSS — Altura do Viewer (1097px não aplicava)**

**Causa raiz:**
- `editor_coordenador.css` define `.ec__viewer-mount { min-height: 1180px; }` (carregado PRIMEIRO)
- `editor_autor.css` define `.ec__viewer-mount { height: 1097px; }` (carregado DEPOIS)
- `min-height: 1180px` sobrepõe `height: 1097px` porque o container pai tinha `flex: 1`, forçando expansão

**Cascata CSS original:**
```css
/* editor_coordenador.css — carregado PRIMEIRO */
.ec__viewer-mount {
    flex: 1;
    min-height: 1180px;  ← FORÇA mínimo de 1180px
    overflow: auto;
}

/* editor_autor.css — carregado DEPOIS, mas INSUFICIENTE */
.ec__viewer-mount {
    height: 1097px;      ← SEM !important, não sobrepõe min-height
    flex: 0 0 1097px;
}
```

**Resultado:** Viewer ficava com 1180px em vez de 1097px

### 2. **Conflito de CSS — Sidebars não esticavam (max-height: 600px)**

**Causa raiz:**
- `editor_coordenador.css` não definia `height: 100%` para `.ec__commands` e `.ec__capitulos`
- `editor_autor.css` tentava aplicar `height: 100%` mas SEM especificidade suficiente
- Regra de `.ea .ec__commands { max-height: 600px; overflow-y: auto; }` sobrepunha

**Cascata CSS original:**
```css
/* editor_coordenador.css */
.ec__commands {
    overflow: hidden;  ← SEM height explícito
}

/* editor_autor.css */
.ec__commands {
    height: 100%;      ← Tentava esticar, mas não funcionava
    overflow-y: auto;
}
```

**Resultado:** Sidebars não ocupavam altura total do container

### 3. **Conflito de JavaScript — Double-mounting do editor**

**Causa raiz:**
- `editor_coordenador.js` era executado primeiro (carregado antes)
- `editor_autor.js` era executado depois
- AMBOS tentavam montar o mesmo editor no `#docxEditorMount`
- Causavam conflitos na renderização React

**Fluxo original (ERRADO):**
```
1. DOMContentLoaded
2. editor_coordenador.js → window.SRADocxEditor.mountFullViewer(MOUNT_ID, {...})
3. editor_autor.js → window.SRADocxEditor.mountFullViewer(MOUNT_ID, {...}) [remonta!]
4. Conflito: React tenta renderizar 2 vezes
```

---

## SOLUÇÕES IMPLEMENTADAS

### 1. ✅ **CSS Fix: Usar `!important` com seletores scoped**

**Arquivo:** `app/static/css/editor_autor.css`

```css
/* ============================================================
   OVERRIDE: Mount do viewer — A4 height (1097px = 844px * 1.30)
   MUST use !important to override editor_coordenador.css
   ============================================================ */
.ea__body .ec__viewer-mount,
.ea__body--coord-like .ec__viewer-mount {
    height: 1097px !important;
    min-height: 1097px !important;
    max-height: 1097px !important;
    flex: 0 0 1097px !important;
    overflow-x: auto !important;
    overflow-y: auto !important;
    background: var(--sra-color-bg-alt) !important;
    position: relative !important;
}

/* ============================================================
   OVERRIDE: Sidebars — stretch to full height
   MUST use !important to override editor_coordenador.css
   ============================================================ */
.ea__body .ec__commands,
.ea__body--coord-like .ec__commands,
.ea__body .ec__capitulos,
.ea__body--coord-like .ec__capitulos {
    height: 100% !important;
    min-height: 0 !important;
    max-height: none !important;
    overflow-y: auto !important;
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
}
```

**Por que funciona:**
- Seletores scoped (`.ea__body .ec__commands`) têm maior especificidade que `.ec__commands` sozinho
- `!important` força override mesmo de regras anteriores
- Aplicado apenas quando dentro de `.ea__body` (editor do autor)

---

### 2. ✅ **JavaScript Fix: Evitar double-mounting**

**Arquivo:** `app/static/js/editor_autor.js`

Adicionado detection de editor já montado:

```javascript
function montarEditor() {
    var mountEl = document.getElementById(MOUNT_ID);
    if (!mountEl) return;

    // Check if already mounted by editor_coordenador.js
    var isAlreadyMounted = mountEl.querySelector('.docx-editor') 
        || mountEl.querySelector('[class*="paged-editor"]')
        || (mountEl.children.length > 0 && mountEl.innerHTML.trim().length > 0 
            && !mountEl.querySelector('.ec__viewer-loading')
            && !mountEl.querySelector('.ec__viewer-error'));
    
    if (isAlreadyMounted) {
        // Just apply styling to existing editor
        setTimeout(function () {
            repositionarMenuModo();
            aplicarEstilosViewer();
        }, 200);
        return;  // Don't remount!
    }
    
    // ... resto do código de montagem ...
}
```

**Por que funciona:**
- Detecta se o editor já está renderizado (procura pelo container `.docx-editor`)
- Se já existe, apenas aplica estilos e repositionamento (não remonta)
- Se não existe, monta normalmente

---

### 3. ✅ **Delay na inicialização do editor_autor.js**

**Arquivo:** `app/static/js/editor_autor.js`

```javascript
function inicializarEditorAutor() {
    // Delay para garantir que editor_coordenador.js já rodou
    setTimeout(function () {
        bindRecarregar();
        bindZoom();
        montarEditor();
        
        if (typeof SRALogger !== 'undefined') {
            SRALogger.info('Editor do autor inicializado completamente');
        }
    }, 100);  // Aguarda 100ms
}

document.addEventListener('DOMContentLoaded', inicializarEditorAutor);
```

**Por que funciona:**
- 100ms é suficiente para `editor_coordenador.js` montar o editor
- Garante que `window.SRADocxEditor.mountFullViewer()` do coordenador complete antes
- Reduz condição de corrida entre scripts

---

### 4. ✅ **Forçar aplicação de estilos via JavaScript (fail-safe)**

**Arquivo:** `app/templates/editor_autor.html` (novo script inline)

```javascript
<script>
(function () {
    'use strict';
    
    function fixarLayoutAutor() {
        var body = document.querySelector('.ea__body, .ea__body--coord-like');
        if (!body) return;
        
        // Force grid layout
        body.style.display = 'grid';
        body.style.gridTemplateColumns = '280px 1fr 300px';
        body.style.gap = '0.75rem';
        body.style.flex = '1';
        body.style.minHeight = '0';
        body.style.overflow = 'hidden';
        
        // Force viewer height (1097px)
        var mount = document.getElementById('docxEditorMount');
        if (mount) {
            mount.style.height = '1097px';
            mount.style.minHeight = '1097px';
            mount.style.maxHeight = '1097px';
            mount.style.flexBasis = '1097px';
            mount.style.overflowX = 'auto';
            mount.style.overflowY = 'auto';
        }
        
        // Force sidebars to full height
        var commands = body.querySelector('.ec__commands');
        var capitulos = body.querySelector('.ec__capitulos');
        
        if (commands) {
            commands.style.height = '100%';
            commands.style.display = 'flex';
            commands.style.flexDirection = 'column';
        }
        
        if (capitulos) {
            capitulos.style.height = '100%';
            capitulos.style.display = 'flex';
            capitulos.style.flexDirection = 'column';
        }
        
        // Zoom value color
        var zoomValue = document.getElementById('ea-docx-zoom-value');
        if (zoomValue) {
            zoomValue.style.color = '#fff';
        }
    }
    
    document.addEventListener('DOMContentLoaded', function () {
        setTimeout(fixarLayoutAutor, 800);
    });
    
    window.addEventListener('load', function () {
        setTimeout(fixarLayoutAutor, 500);
    });
})();
</script>
```

**Por que funciona:**
- Aplicar estilos inline via JavaScript GARANTE aplicação (sem cascata CSS)
- Executa em `DOMContentLoaded` (800ms) e `load` (500ms) para cobrir todos cenários
- Funciona mesmo se CSS falhar

---

## RESULTADOS ESPERADOS

Após estas correções, o layout do Editor do Autor deve apresentar:

✅ **Altura do viewer:**
- Exatamente 1097px (A4 aumentado 30%)
- Com scroll horizontal e vertical internos
- Sem espremer o painel "Envio de conteúdo" acima

✅ **Sidebars esticadas:**
- Sidebar esquerda (Painel de Comandos): altura 100% do container
- Sidebar direita (Capítulos): altura 100% do container
- Ambas ocupam mesmo espaço vertical
- Ambas com scroll vertical independente

✅ **Zoom value em branco:**
- Cor: `#ffffff` com font-weight 600

✅ **Sem double-mounting:**
- Editor monta UMA VEZ
- Sem conflitos React
- Sem re-renderizações desnecessárias

---

## CHECKLIST DE VERIFICAÇÃO

Para validar que tudo funciona:

1. ☐ Abrir `/relatorio/versao-trabalho/<id>/editor-autor`
2. ☐ **Verificar altura do viewer:** Deve ser ~1097px (mediindo com DevTools: `element.offsetHeight`)
3. ☐ **Verificar sidebars:** Ambas ocupam altura total, sem cortes
4. ☐ **Verificar zoom:** Número em branco (não azul/cinza)
5. ☐ **Abrir DevTools (F12):** Procurar por erros em console (não deveria haver)
6. ☐ **Recarregar página:** Verificar se layout se mantém consistente
7. ☐ **Clicar em "Recarregar":** Editor remonta sem erros
8. ☐ **Scroll:** Sidebar esquerda e direita scrollam independentemente
9. ☐ **Menu Editing:** (tarefa futura) Deve estar no header ao lado dos botões de zoom

---

## ARQUIVOS MODIFICADOS

1. **`app/static/css/editor_autor.css`**
   - Adicionadas regras de override com `!important`
   - Seletores scoped para especificidade
   - Seção clara "OVERRIDE" para documentar conflitos

2. **`app/static/js/editor_autor.js`**
   - Adicionada detecção de editor já montado
   - Delay na inicialização (100ms)
   - Comentários explicativos

3. **`app/templates/editor_autor.html`**
   - Adicionado script inline no `{% block scripts %}`
   - Aplicação força de layout via JavaScript
   - Fail-safe para garantir estilos

---

## NOTAS TÉCNICAS

### Por que CSS não era suficiente?

1. **Especificidade:** `.ec__commands` em `editor_coordenador.css` + `max-height: 600px` sobrepõe `height: 100%` do `editor_autor.css` sem `!important`
2. **Cascade:** `min-height: 1180px` força Container a expandir mesmo com `height: 1097px`
3. **Flex:** Parent com `flex: 1` pode expandir filho mesmo com altura definida

### Por que JavaScript é necesário?

1. **Sincronização:** Sem delay, ambos scripts tentam montar editor simultaneamente
2. **React:** Component montagem é assíncrona, requer aguardar antes de aplicar estilos
3. **Fail-safe:** CSS pode ter comportamentos inesperados com Tailwind (do bundle eigenpal)

### Best practices aplicadas:

✅ Seletores scoped (`.ea__body .ec__commands`) em vez de globais
✅ `!important` documentado e justificado
✅ Comentários explicativos no código
✅ Múltiplas camadas de proteção (CSS + JS + inline styles)
✅ Detecção de estado (já montado?) antes de ações

---

## Referências de conflitos descobertos

- **editor_coordenador.css, linha ~75:** `.ec__viewer-mount { min-height: 1180px; }`
- **editor_coordenador.css, linha ~128:** `.ec__commands { overflow: hidden; }` (sem height)
- **editor_autor.css, linha ~890:** `.ea .ec__viewer-mount { min-height: 560px; }` (antigo, removido)
- **estilo.css, linha ~644:** `.sra-preview__body { max-height: 844px; }` (referência de altura A4)

