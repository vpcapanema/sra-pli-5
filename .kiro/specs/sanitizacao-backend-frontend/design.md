# Design Document — sanitizacao-backend-frontend

## Overview

Execução cirúrgica de 26 correções pontuais (R1–R26) e 6 não-funcionais (R27–R32) sobre `app/`. Nenhuma refatoração arquitetural, nenhum endpoint novo, nenhum schema tocado. O design abaixo descreve apenas o **mínimo necessário** para aplicar a sanitização preservando o `Comportamento_Observavel`.

Eixos da execução:

- **Backend**: edições pontuais em arquivos existentes (`servico_captioning.py`, `servico_envio_autor.py`, `logger.py`). Único símbolo novo é um helper privado em `app/utils/logger.py` para registrar warning sem recursão.
- **Frontend**: 1 utilitário novo (`confirmacao_form.js`), 1 arquivo dedicado novo (`painel_clonar.js`), modernização localizada em JS_Companion existentes, ajustes em CSS e templates.
- **Validação**: pyflakes + greps direcionados + smoke manual de fluxos.

## Architecture

### Backend (Python / Flask)

- Edições pontuais em **arquivos existentes**:
  - `app/services/servico_captioning.py` — remoção de `tab` (R1).
  - `app/services/servico_envio_autor.py` — remoção de `cap_atual_norm` e do import `ServicoExtracaoCanonica` (R2, R3).
  - `app/utils/logger.py` — substituição dos quatro `except Exception: pass` em `SRALogHandler.emit` (R4–R7).
- **Único símbolo novo no backend**: helper privado em `app/utils/logger.py` para emitir warning sem disparar recursão no próprio handler. Sem nova classe, sem novo módulo, sem alteração na assinatura pública de `SRALogHandler`.

### Frontend (Jinja / JS / CSS)

- 1 utilitário compartilhado novo: `app/static/js/confirmacao_form.js` — orquestra `data-confirm` / `data-confirm-message` (R13, R14, R18).
- 1 arquivo dedicado novo: `app/static/js/painel_clonar.js` — substitui os `onclick="clonarDaBiblioteca(...)"` (R16, R17).
- JS_Companion existentes ganham listeners adicionais, sem reescrita:
  - `app/static/js/editor_coordenador.js` — listener para `#ec-rel-select` (R10).
  - `app/static/js/editor_autor.js` — listeners para `#ea-rel-select` e para o form de envio final (R11, R12).
  - `app/static/js/app.js` — listener para `#seletor_relatorio` (R15).
  - `app/static/js/logger.js` — modernização `var` → `let`/`const` (R8).
  - `app/static/js/visualizador_parametros.js` — modernização `var` → `let`/`const` (R9).
- CSS: edição localizada em `app/static/css/app.css` (R19–R25).
- Templates: remoção dos atributos `on*` e injeção das tags `<script>` necessárias (R10–R18, R26).

### Estratégia de não-recursão para `SRALogHandler` (R4–R7)

Risco-chave: `logger.warning(...)` chamado de dentro de `SRALogHandler.emit` percorre a cadeia de handlers e pode reentrar a mesma instância, causando recursão e potencialmente perda do log original.

**Mitigação adotada** — logger nomeado isolado, definido no escopo do módulo `app/utils/logger.py`:

```python
# Logger dedicado a falhas internas do próprio handler.
# Não propaga e usa apenas StreamHandler (stderr) para evitar reentrar em SRALogHandler.
_logger_handler_emit = logging.getLogger('sra.handler_emit')
_logger_handler_emit.propagate = False
if not _logger_handler_emit.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    _logger_handler_emit.addHandler(_h)
_logger_handler_emit.setLevel(logging.WARNING)


def _logar_warning_sem_recursao(contexto: str, exc: BaseException) -> None:
    """Registra warning interno do SRALogHandler sem reentrar no próprio handler."""
    try:
        _logger_handler_emit.warning(
            "Falha em %s: %s: %s", contexto, type(exc).__name__, str(exc)
        )
    except Exception:
        # Suprime falha secundária para não quebrar o emit original.
        pass
```

Garantias atendidas:

- **R4.5 / R5.5 / R6.5 / R7.2** — o logger `'sra.handler_emit'` é distinto, `propagate=False` impede subir até o root logger (que carrega `SRALogHandler` via `setup_sra_logging`), e seus handlers locais são apenas `StreamHandler`.
- **R4.4 / R5.4 / R6.4 / R7.4** — o `try/except` interno do helper engole qualquer falha secundária.
- **R7.3** — o `except Exception` externo do `emit` continua chamando `self.handleError(record)` após o `_logar_warning_sem_recursao`.
- **R7.5** — como o logger isolado não tem `SRALogHandler` na cadeia (própria nem por propagação), `emit` da mesma instância não é reinvocado.

Alternativa de fallback: `logging.lastResort` (já garantidamente um `StreamHandler` em `WARNING`) pode ser usado como rede adicional dentro do `except` do helper, mas o logger nomeado já satisfaz os critérios — não é necessário introduzir mais código.

## Components and Interfaces

### Componentes novos

| Arquivo | Responsabilidade |
|---|---|
| `app/static/js/confirmacao_form.js` | Registrar `addEventListener('submit', ...)` em todo `<form data-confirm>`, exibir `window.confirm(data-confirm-message || 'Confirmar ação?')`, prevenir envio em cancelamento. Carregado uma vez via `layouts/base.html`. |
| `app/static/js/painel_clonar.js` | Após `DOMContentLoaded`, localizar botões com `data-clonar-da-biblioteca` (atributo a ser inserido nos templates de R16 e R17), ler argumentos via `data-*` e invocar `clonarDaBiblioteca` com a mesma assinatura do handler inline removido. |

### Componentes modificados — backend

| Arquivo | Mudança |
|---|---|
| `app/services/servico_captioning.py` | Remover atribuição `tab = ...` em `_anexar_numero_inline_equacao` e qualquer `# noqa: F841` órfão. |
| `app/services/servico_envio_autor.py` | Remover variável `cap_atual_norm` (linha ~101) e import local `ServicoExtracaoCanonica` (linha ~225). |
| `app/utils/logger.py` | Trocar os quatro `except Exception: pass` por `except Exception as exc: _logar_warning_sem_recursao(...)`; manter `self.handleError(record)` no `except` externo; adicionar helper privado `_logar_warning_sem_recursao` no escopo do módulo. |

### Componentes modificados — frontend (JS)

| Arquivo | Mudança |
|---|---|
| `app/static/js/logger.js` | `var` → `let`/`const` apenas onde escopo é trivialmente compatível (sem hoisting, sem redeclaração). |
| `app/static/js/visualizador_parametros.js` | Idem. |
| `app/static/js/editor_coordenador.js` | Adicionar bloco em `DOMContentLoaded` que faz `document.getElementById('ec-rel-select')?.addEventListener('change', ...)`. |
| `app/static/js/editor_autor.js` | Adicionar listener para `#ea-rel-select` (`change`) e listener `submit` no form de envio final (busca por seletor estável — `form.acao-form[data-envio-final]` ou `action` específico — ver "Pontos de injeção"). |
| `app/static/js/app.js` | Adicionar listener `change` em `#seletor_relatorio`. |

### Componentes modificados — frontend (templates)

Lista exata + ponto de injeção:

| Template | Edição | `<script>` extra |
|---|---|---|
| `app/templates/layouts/base.html` | Inserir `<script src="{{ static_v('js/confirmacao_form.js') }}" defer></script>` no bloco de scripts globais (perto do final do `<body>`, antes de blocos `{% block scripts %}` específicos). | Sim — único ponto de carga global do utilitário. |
| `app/templates/editor_coordenador.html` | Remover `onchange=` de `<select id="ec-rel-select">`. | Não (JS_Companion já incluído). |
| `app/templates/editor_autor.html` | Remover `onchange=` de `<select id="ea-rel-select">` e `onsubmit=` do form de envio final (linha ~317); adicionar marcador estável no form (ex.: `data-envio-final` ou manter `action` como seletor). | Não. |
| `app/templates/components/_botao_acao.html` | Remover `onsubmit=` do macro; emitir `data-confirm` e `data-confirm-message="<mensagem original>"`. | Não — coberto pelo utilitário em `base.html`. |
| `app/templates/components/_acoes_tabela.html` | No macro `btn_excluir`: remover `onsubmit=`; emitir `data-confirm` e `data-confirm-message="{{ confirmacao }}"`. | Não. |
| `app/templates/components/relatorio/arvore_capitulos.html` | Remover `onchange=` de `<select id="seletor_relatorio">`. | Não (`app.js` já carregado). |
| `app/templates/components/paineis/painel_criar_relatorio_producao.html` | Remover `onclick=` da linha ~66; adicionar `data-clonar-da-biblioteca` e `data-*` com argumentos. Incluir `<script src="{{ static_v('js/painel_clonar.js') }}" defer></script>`. | Sim. |
| `app/templates/components/paineis/dashboard_coordenador.html` | Remover `onclick=` da linha ~101; mesma marcação `data-clonar-da-biblioteca`. Incluir `<script src="{{ static_v('js/painel_clonar.js') }}" defer></script>`. | Sim. |
| `app/templates/components/configuracoes/biblioteca_formatacao.html` | Remover `onsubmit=` do form da linha ~19; adicionar `data-confirm` e `data-confirm-message='Excluir biblioteca "{{ b.nome_biblioteca }}"? Esta ação não pode ser desfeita.'` (preservando aspas e pontuação). | Não. |
| `app/templates/components/relatorio/card_cadastro_relatorio_versao_trabalho.html` | R26: remover bloco do card OU substituir texto por rótulo "em desenvolvimento" (depende de decisão do usuário). Remover marcador `TODO`. | Não. |

### Carregamento do JS_Utilitario_Confirmacao

**Carregamento**: `confirmacao_form.js` é injetado **uma única vez** em `app/templates/layouts/base.html`, próximo ao final do `<body>`, antes de qualquer `{% block scripts %}` filho:

```html
<script src="{{ static_v('js/confirmacao_form.js') }}" defer></script>
```

**Cobertura**: `base.html` é estendido (direta ou indiretamente) por todas as telas que renderizam `_botao_acao` e `_acoes_tabela`, incluindo `biblioteca_formatacao.html`. A injeção em `base.html` cobre R13, R14 e R18 sem necessidade de incluir o script em cada template filho.

**Forma do utilitário** (esboço):

```js
(function () {
  'use strict';
  function instalar() {
    document.querySelectorAll('form[data-confirm]').forEach(function (form) {
      if (form.dataset.confirmInstalado === '1') return;
      form.dataset.confirmInstalado = '1';
      form.addEventListener('submit', function (ev) {
        var msg = form.getAttribute('data-confirm-message');
        if (!msg) msg = 'Confirmar ação?';
        if (!window.confirm(msg)) {
          ev.preventDefault();
          ev.stopPropagation();
        }
      });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', instalar);
  } else {
    instalar();
  }
})();
```

Observações:

- Marcação `data-confirm-instalado` evita registro duplo em re-execuções acidentais.
- O utilitário **não** modifica payload nem CSRF_Token — apenas decide se o submit prossegue (R28, R13.6, R14.4, R18.4).

### Componente `painel_clonar.js`

Estratégia: substituir `onclick="clonarDaBiblioteca(arg1, arg2, ...)"` por marcação declarativa nos templates e binding único no JS dedicado.

Marcação no template (exemplo):

```html
<button type="button"
        class="..."
        data-clonar-da-biblioteca
        data-arg-id="{{ b.id }}"
        data-arg-tipo="{{ tipo }}">
  Clonar
</button>
```

JS dedicado (esboço):

```js
(function () {
  'use strict';
  function instalar() {
    document.querySelectorAll('[data-clonar-da-biblioteca]').forEach(function (btn) {
      if (btn.dataset.clonarInstalado === '1') return;
      btn.dataset.clonarInstalado = '1';
      btn.addEventListener('click', function () {
        if (typeof window.clonarDaBiblioteca !== 'function') return;
        var id = btn.getAttribute('data-arg-id');
        var tipo = btn.getAttribute('data-arg-tipo');
        window.clonarDaBiblioteca(id, tipo);
      });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', instalar);
  } else {
    instalar();
  }
})();
```

A função `clonarDaBiblioteca` original (presumivelmente em escopo global definido em outro JS ou inline em outro lugar) **não é movida** — preserva-se a definição (R16.2, R17.2). O conjunto exato de argumentos será confirmado durante a leitura das duas linhas de origem (`painel_criar_relatorio_producao.html:66` e `dashboard_coordenador.html:101`) na fase de implementação.

### Estratégia para CSS (R19–R25)

Para cada uma das 7 regras, **a remoção de `!important` é o passo único e suficiente** se nenhuma regra concorrente de maior especificidade existir no próprio `app.css`. Procedimento:

1. **Inspeção pré-edição** — `grep_search` por cada seletor afetado em `app/static/css/app.css` para identificar regras concorrentes.
2. **Caso A — sem concorrência**: remover apenas o `!important` da declaração indicada. Termina aqui.
3. **Caso B — concorrência detectada**:
   - Para regras `[hidden]` / `--hidden` (R20–R22, R24): manter o seletor (atributo + classe já é específico). Em conflito posterior, dobrar a classe (`.sra-tree__item--hidden.sra-tree__item--hidden`) ou o atributo (`.sra-tree__toggle[hidden][hidden]`) para subir a especificidade sem reintroduzir `!important`.
   - Para `.sigma-pli-conteiner__icon--lg svg` (R19): se houver concorrência, dobrar a classe pai (`.sigma-pli-conteiner__icon--lg.sigma-pli-conteiner__icon--lg svg`).
   - Para `text-align` (R23, R25): dobrar a classe alvo.
4. **Validação visual**: inspeção manual com DevTools (`getComputedStyle`) nas telas afetadas confirma os valores esperados. Critério vinculado a R19.2, R20.2, R21.2, R22.2, R23.2, R24.2, R25.2.

Regras alvo (texto exato a alterar):

| # | Regra | Declaração | Estratégia padrão |
|---|---|---|---|
| R19 | `.sigma-pli-conteiner__icon--lg svg` / `... svg *` | `stroke`, `fill`, `stroke-width` | Remover `!important`. |
| R20 | `.sra-tree__item--hidden` | `display: none` | Remover `!important`. |
| R21 | `.sra-tree__toggle[hidden]` | `display: none` | Remover `!important`. |
| R22 | `.sra-table--cap-collapsible .sra-cap-row--hidden` | `display: none` | Remover `!important`. |
| R23 | `.sra-table__header--left` | `text-align: left` | Remover `!important`. |
| R24 | `.sra-cap-toggle[hidden]` | `display: none` | Remover `!important`. |
| R25 | `.sra-cap-cell--title` | `text-align: left` | Remover `!important`. |

## Data Models

Esta sanitização **não introduz nem altera entidades persistidas**. Nenhum modelo SQLAlchemy é tocado, nenhuma migration é necessária, nenhuma coluna é adicionada ou removida. O contrato de dados visível para clientes (payloads de rota, schema do banco) permanece idêntico (R27.1, R27.2).

Estruturas de dados in-memory novas:

- `_logger_handler_emit` (escopo de módulo em `app/utils/logger.py`) — instância de `logging.Logger` nomeada `'sra.handler_emit'`, isolada via `propagate=False`. Não persistida.
- Atributos `data-*` em DOM:
  - `data-confirm` (presença booleana)
  - `data-confirm-message` (string com a mensagem do `confirm()`)
  - `data-confirm-instalado` (sentinela `"1"` para idempotência)
  - `data-clonar-da-biblioteca` (presença booleana)
  - `data-arg-*` (argumentos posicionais para `clonarDaBiblioteca`)
  - `data-clonar-instalado` (sentinela `"1"` para idempotência)

Nenhum desses atributos transita pela rede; servem apenas como contrato local entre template e JS utilitário.

## Error Handling

### Backend

- **`SRALogHandler.emit`** — quatro pontos de captura, todos canalizados para `_logar_warning_sem_recursao(contexto, exc)`:
  - `current_user.nome` → `user_name = 'anonymous'` e prossegue (R4.3).
  - `session.get('perfil_ativo')` → `perfil = ''` e prossegue (R5.3).
  - `request.path` / `request.method` → `path = ''`, `method = ''` e prossegue (R6.3).
  - `except Exception` externo → mantém `self.handleError(record)` e registra warning (R7.3).
- **Falha secundária no helper** — `try/except Exception: pass` interno suprime e nunca propaga ao chamador (R4.4, R5.4, R6.4, R7.4).
- **Imports/variáveis removidos (R1–R3)** — sem mudança de fluxo de erro; comportamento de exceção das funções afetadas permanece idêntico (R1.3, R2.4, R3.4).

### Frontend

- **`confirmacao_form.js`** — em cancelamento, `event.preventDefault()` + `event.stopPropagation()`; em ausência de `data-confirm-message`, fallback para `'Confirmar ação?'` (R13.4).
- **`painel_clonar.js`** — em ausência da função global `clonarDaBiblioteca` (`typeof !== 'function'`), o handler retorna sem lançar; em ausência do botão alvo, o seletor `querySelectorAll` retorna lista vazia e nada é registrado (R16.5, R17.5).
- **JS_Companion** — todos os listeners verificam existência do elemento antes de registrar (`if (el) el.addEventListener(...)`) para satisfazer R10.5, R11.5, R12.x, R15.5.

### CSS

- Não há "tratamento de erro" para CSS; o procedimento de **inspeção pré-edição** + **dobra de especificidade** funciona como mecanismo de contenção para regras concorrentes (R19.3, R20.3, R21.3, R22.3, R23.3, R24.3, R25.3).

## Testing Strategy

### Plano de validação (sequência)

1. **Backend estático** — `python -m pyflakes app` e validar que mensagens reportadas em R1–R3 sumiram.
2. **Imports OK** — `python -c "import app.services.servico_envio_autor"`, `python -c "import app.services.servico_captioning"`, `python -c "import app.utils.logger"` (todos exit 0).
3. **Não-recursão do handler** — caso simples ad-hoc: instanciar `SRALogHandler`, mockar `current_user.is_authenticated` para levantar, emitir um record. Validar que `emit` foi chamado **uma vez** e que `_logger_handler_emit` registrou warning. Pode ser feito ad-hoc via `python -c` com counter ou em `tests/`.
4. **Frontend — ausência de handlers inline** — `grep_search` no escopo dos templates listados:
   - `onclick=` em `painel_criar_relatorio_producao.html`, `dashboard_coordenador.html` → 0 resultados.
   - `onchange=` em `editor_coordenador.html`, `editor_autor.html`, `arvore_capitulos.html` → 0.
   - `onsubmit=` em `editor_autor.html`, `_botao_acao.html`, `_acoes_tabela.html`, `biblioteca_formatacao.html` → 0.
5. **CSS — ausência de `!important` nas regras alvo** — `grep_search` por `!important` em cada bloco de regra listado em R19–R25 → 0 resultados nessas regras.
6. **TODO** — `grep_search` por `TODO` em `card_cadastro_relatorio_versao_trabalho.html` → 0 resultados após decisão do usuário.
7. **Smoke manual de fluxos (R10–R18)** — checklist mínimo:
   - **R10**: trocar relatório no select de `editor_coordenador` → navega.
   - **R11**: trocar relatório no select de `editor_autor` → navega.
   - **R12**: clicar "Enviar conteúdo final" no `editor_autor` → diálogo com texto exato; cancelar mantém na página; confirmar envia.
   - **R13**: qualquer botão `_botao_acao` com `data-confirm` → diálogo aparece; cancelar não envia; confirmar envia preservando CSRF.
   - **R14**: botão excluir em `_acoes_tabela` → diálogo com texto do parâmetro `confirmacao`; cancelar não envia.
   - **R15**: select `#seletor_relatorio` em `arvore_capitulos` → navega para `/relatorio/versao-trabalho/<id>`.
   - **R16**: clicar "Clonar" em `painel_criar_relatorio_producao` → mesma ação observável de antes.
   - **R17**: clicar "Clonar" em `dashboard_coordenador` → idem.
   - **R18**: excluir biblioteca em `biblioteca_formatacao` → diálogo com texto exato `Excluir biblioteca "<nome>"? Esta ação não pode ser desfeita.`.
8. **CSS smoke** — abrir DevTools nas telas afetadas e verificar `getComputedStyle` para cada regra de R19–R25.

### Estratégia de execução em fases

| Fase | Escopo | Requisitos | Dependências |
|---|---|---|---|
| **A** — Backend | Edição em `servico_captioning.py`, `servico_envio_autor.py`, `logger.py` | R1–R7 | Nenhuma. Itens independentes entre si, paralelizáveis. |
| **B** — CSS | Edição em `app.css` | R19–R25 | Nenhuma. Independentes entre si. |
| **C** — JS utilitário | Criar `confirmacao_form.js` e `painel_clonar.js`; modernizar `logger.js` e `visualizador_parametros.js` | R8, R9, R13 (parcial), R16 (parcial), R17 (parcial) | Nenhuma. |
| **D** — Templates frontend | Remover `on*` e injetar tags `<script>`/`data-*`; ajustar JS_Companion | R10, R11, R12, R13, R14, R15, R16, R17, R18 | C precede D para R13/R14/R16/R17/R18. |
| **E** — UX (TODO) | R26 em `card_cadastro_relatorio_versao_trabalho.html` | R26 | Confirmação explícita do usuário sobre existência ou não da funcionalidade em outro fluxo. |
| **F** — Validação final | Rodar pyflakes, greps e smoke | R32 (e cobertura cruzada de NF6) | Todas as anteriores concluídas. |

### Riscos conhecidos

| Risco | Mitigação |
|---|---|
| Recursão de logging em `SRALogHandler.emit` ao chamar `logger.warning(...)`. | Logger nomeado `'sra.handler_emit'` com `propagate=False` e `StreamHandler` próprio. Helper `_logar_warning_sem_recursao` engloba o registro em `try/except` para suprimir falha secundária. |
| Remoção de `!important` quebrar visualmente em algum browser/contexto onde havia regra concorrente fora de `app.css`. | Inspeção pré-edição com `grep_search` em `app/static/css/`; smoke manual com DevTools (`getComputedStyle`) em cada tela afetada após a remoção. Em conflito, dobrar especificidade do seletor sem reintroduzir `!important`. |
| `clonarDaBiblioteca` ter assinatura/argumentos diferentes nos dois templates (R16, R17). | Leitura literal das duas linhas de origem antes de definir os `data-arg-*`. Se assinaturas divergirem, parametrizar via `data-*` distintos por template ou dois entry points no mesmo `painel_clonar.js`. |
| Modernização `var` → `let`/`const` introduzir TDZ ou redeclaração em escopo. | Aplicar apenas onde escopo é trivialmente compatível (whitelist do agente `sra-code-sanitizer`). Em dúvida, preservar `var`. R8.4, R9.4 cobrem reversão localizada. |
| R26 exigir decisão de produto fora do escopo de código. | Escalonar para o usuário antes de tocar no template. R26.2 garante que, sem confirmação, o arquivo permanece inalterado. |
| `data-confirm-message` perder o texto exato do `confirm()` original (R13.8, R18.2). | Copiar verbatim a string do `onsubmit` original para `data-confirm-message`, preservando aspas, pontuação e interpolação Jinja. |
| Listener registrado duas vezes em re-renderizações dinâmicas. | Marcador `data-confirm-instalado="1"` / `data-clonar-instalado="1"` no elemento garante idempotência. |

## Correctness Properties

*Esta sanitização é majoritariamente verificação estática (grep + pyflakes) e smoke manual. A única lógica nova com potencial de regressão é a estratégia de não-recursão em `SRALogHandler.emit`, que admite uma propriedade testável.*

### Property 1: Não-recursão em SRALogHandler.emit

For any `logging.LogRecord` emitted in a context where the blocks `current_user.nome`, `session.perfil_ativo`, `request.path/method` or the outer `try` raise an exception, the `emit` method of the same `SRALogHandler` instance is invoked at most once as a direct or indirect consequence of that log.

**Validates: Requirements 4.5, 5.5, 6.5, 7.2, 7.5**

### Property 2: Estabilidade de saída XML em `_anexar_numero_inline_equacao`

For any input accepted by `_anexar_numero_inline_equacao`, the produced XML structure (same children, attributes, text and order) is identical to the version prior to the removal of the `tab` variable.

**Validates: Requirements 1.3**

### Property 3: Idempotência de instalação dos listeners

For any execution of `confirmacao_form.js` or `painel_clonar.js` over a document, each target element (`form[data-confirm]`, `[data-clonar-da-biblioteca]`) has at most one `submit` / `click` listener registered by the utility, even if the installer function is invoked multiple times.

**Validates: Requirements 13.2, 16.3, 17.3**

*Nota: estas propriedades são especificadas formalmente para fins de rastreabilidade; a verificação é feita via teste example-based (Property 1: 1 teste com mock; Property 2: 1-2 fixtures DOCX; Property 3: 1 teste em DOM simulado ou smoke manual). Não justificam PBT (100+ iterações) porque o espaço de entrada relevante é pequeno e o custo/benefício não compensa.*

