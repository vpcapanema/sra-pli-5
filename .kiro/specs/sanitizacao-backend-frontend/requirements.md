# Requirements Document

## Introduction

Este documento descreve as correções pontuais e cirúrgicas a serem aplicadas ao backend Python (Flask) e frontend (Jinja2 + JS vanilla + CSS) do **SRA-PLI**, com base em diagnóstico estático já realizado. O escopo é estritamente sanitização: remoção de variáveis e imports não usados, substituição de `except Exception: pass` silenciosos por log central, modernização de `var` para `let`/`const` em JS, eliminação de handlers inline (`onclick`/`onchange`/`onsubmit`) em templates Jinja, remoção de `!important` redundantes em CSS interno e tratamento de um `TODO` de UX. Nenhuma alteração arquitetural, contrato de API, schema de banco, comportamento observável ou stack tecnológica é alvo desta sanitização.

Cada item de diagnóstico é tratado como um requisito independente (R1–R26) para permitir verificação granular, com requisitos não-funcionais transversais (NF1–NF6) garantindo a integridade do sistema durante e após a aplicação.

## Glossary

- **Sistema_SRA**: aplicação web SRA-PLI (backend Flask + frontend Jinja/JS/CSS) localizada em `app/`.
- **Backend_SRA**: módulos Python sob `app/` (rotas, serviços, modelos, utilitários).
- **Frontend_SRA**: artefatos sob `app/templates/`, `app/static/css/` e `app/static/js/` (excluindo `app/static/editor-react/`).
- **Logger_Central**: utilitário de logging do projeto definido em `app/utils/logger.py`, usado para registrar eventos com nível `info`, `warning` e `error`.
- **Handler_Inline**: atributo `onclick=`, `onchange=` ou `onsubmit=` declarado diretamente em elemento HTML dentro de template Jinja.
- **JS_Companion**: arquivo `*.js` em `app/static/js/` que já é incluído pelo template HTML correspondente e contém scripts associados àquele template.
- **JS_Dedicado**: arquivo `*.js` novo em `app/static/js/`, criado especificamente para um template que ainda não possui JS_Companion, e referenciado via `{{ static_v('js/<nome>.js') }}` no template.
- **JS_Utilitario_Confirmacao**: módulo JS compartilhado em `app/static/js/` que centraliza confirmação genérica de submit de formulário via padrão `data-attribute` (`data-confirm` e `data-confirm-message`).
- **Linter_Pyflakes**: ferramenta `python -m pyflakes` executada sobre o pacote `app`.
- **CSRF_Token**: token CSRF emitido pelo backend (Flask-WTF) e propagado em forms e em headers `X-CSRFToken` de requests `fetch`/`XHR` mutantes.
- **static_v**: helper Jinja `static_v(path)` definido no projeto para cache-busting de assets estáticos.
- **Comportamento_Observavel**: rotas HTTP (paths e métodos), payloads de resposta, efeitos visuais renderizados (incluindo `getComputedStyle`), mensagens e fluxos de UX percebidos pelo usuário final.

## Requirements

### Requirement 1: Remover variável local não usada `tab` em `servico_captioning.py`

**User Story:** Como mantenedor do Backend_SRA, quero remover a variável local `tab` que está atribuída e nunca usada na função `_anexar_numero_inline_equacao` em `app/services/servico_captioning.py`, para que o código fique livre de variáveis mortas e o Linter_Pyflakes não reporte aviso nessa função.

#### Acceptance Criteria

1. THE Backend_SRA SHALL não conter atribuição da variável `tab` na função `_anexar_numero_inline_equacao` de `app/services/servico_captioning.py`.
2. WHEN o desenvolvedor executar `python -m pyflakes app/services/servico_captioning.py`, THE Linter_Pyflakes SHALL não emitir a mensagem `local variable 'tab' is assigned to but never used` para esse arquivo.
3. THE Backend_SRA SHALL preservar, para os mesmos parâmetros de entrada, a estrutura XML produzida por `_anexar_numero_inline_equacao` (mesmos filhos, atributos, texto e ordem) idêntica à anterior à alteração.
4. THE Backend_SRA SHALL remover qualquer comentário `# noqa: F841` órfão associado à atribuição removida.

### Requirement 2: Remover variável local não usada `cap_atual_norm` em `servico_envio_autor.py`

**User Story:** Como mantenedor do Backend_SRA, quero remover a variável local `cap_atual_norm` que está atribuída e nunca usada em `app/services/servico_envio_autor.py:101`, para que o código fique livre de variáveis mortas.

#### Acceptance Criteria

1. THE Backend_SRA SHALL não conter atribuição nem leitura da variável `cap_atual_norm` em `app/services/servico_envio_autor.py`.
2. WHEN o desenvolvedor executar `python -m pyflakes app/services/servico_envio_autor.py`, THE Linter_Pyflakes SHALL não emitir a mensagem `local variable 'cap_atual_norm' is assigned to but never used` para esse arquivo.
3. WHEN o desenvolvedor executar `python -c "import app.services.servico_envio_autor"`, THE Backend_SRA SHALL retornar exit code 0 sem `SyntaxError` ou `NameError`.
4. THE Backend_SRA SHALL preservar, para os mesmos parâmetros de entrada, o valor de retorno e os efeitos colaterais da função onde `cap_atual_norm` estava declarada idênticos aos anteriores à alteração.

### Requirement 3: Remover import não usado `ServicoExtracaoCanonica` em `servico_envio_autor.py`

**User Story:** Como mantenedor do Backend_SRA, quero remover o import não usado `ServicoExtracaoCanonica` em `app/services/servico_envio_autor.py:225`, para que o módulo não carregue dependência desnecessária.

#### Acceptance Criteria

1. THE Backend_SRA SHALL remover apenas o import de `ServicoExtracaoCanonica` localizado próximo à linha 225 de `app/services/servico_envio_autor.py`, preservando outros imports do mesmo símbolo em escopos onde ele é efetivamente utilizado dentro do arquivo.
2. WHEN o desenvolvedor executar `python -m pyflakes app/services/servico_envio_autor.py`, THE Linter_Pyflakes SHALL retornar exit code 0 sem mensagens contendo `imported but unused` para `ServicoExtracaoCanonica`.
3. WHEN o desenvolvedor executar `python -c "import app.services.servico_envio_autor"`, THE Backend_SRA SHALL retornar exit code 0 sem `ImportError`, `ModuleNotFoundError` ou `NameError`.
4. THE Backend_SRA SHALL preservar inalterado o Comportamento_Observavel das funções de `app/services/servico_envio_autor.py`.

### Requirement 4: Substituir `except Exception: pass` no bloco `current_user.nome` em `SRALogHandler.emit`

**User Story:** Como mantenedor do Backend_SRA, quero substituir o `except Exception: pass` no bloco que obtém `current_user.nome` dentro de `SRALogHandler.emit` em `app/utils/logger.py` por uma chamada ao Logger_Central com nível `warning`, para que essa falha deixe de ser silenciosa.

#### Acceptance Criteria

1. THE Backend_SRA SHALL não conter o padrão `except Exception: pass` no bloco `try`/`except` de `SRALogHandler.emit` que obtém `current_user.nome` em `app/utils/logger.py`.
2. WHEN uma exceção for capturada nesse bloco, THE Backend_SRA SHALL registrar a ocorrência com nível `warning` contendo (a) identificador textual do contexto indicando "obtenção de current_user.nome em SRALogHandler.emit", (b) o tipo da exceção e (c) `str(exc)`.
3. WHEN uma exceção for capturada nesse bloco, THE Backend_SRA SHALL atribuir `'anonymous'` ao campo `user_name` em construção e prosseguir com a emissão do log original.
4. IF o registro do log de warning falhar por qualquer motivo, THEN THE Backend_SRA SHALL suprimir a falha secundária sem propagá-la ao chamador de `SRALogHandler.emit`.
5. THE Backend_SRA SHALL utilizar para o registro de warning um logger Python distinto cuja cadeia de handlers (própria e por propagação) não inclua a instância de `SRALogHandler` em execução.

### Requirement 5: Substituir `except Exception: pass` no bloco `session.perfil_ativo` em `SRALogHandler.emit`

**User Story:** Como mantenedor do Backend_SRA, quero substituir o `except Exception: pass` no bloco que obtém `session.get('perfil_ativo')` dentro de `SRALogHandler.emit` em `app/utils/logger.py` por uma chamada ao Logger_Central com nível `warning`, para que essa falha deixe de ser silenciosa.

#### Acceptance Criteria

1. THE Backend_SRA SHALL não conter o padrão `except Exception: pass` no bloco `try`/`except` de `SRALogHandler.emit` que obtém `session.get('perfil_ativo')` em `app/utils/logger.py`.
2. WHEN uma exceção for capturada nesse bloco, THE Backend_SRA SHALL registrar a ocorrência com nível `warning` contendo (a) identificador textual do contexto indicando "obtenção de session.perfil_ativo em SRALogHandler.emit", (b) o tipo da exceção e (c) `str(exc)`.
3. WHEN uma exceção for capturada nesse bloco, THE Backend_SRA SHALL atribuir string vazia ao campo `perfil` em construção e prosseguir com a emissão do log original.
4. IF o registro do log de warning falhar por qualquer motivo, THEN THE Backend_SRA SHALL suprimir a falha secundária sem propagá-la ao chamador.
5. THE Backend_SRA SHALL utilizar para o registro de warning um logger Python distinto cuja cadeia de handlers não inclua a instância de `SRALogHandler` em execução.

### Requirement 6: Substituir `except Exception: pass` no bloco `request.path/method` em `SRALogHandler.emit`

**User Story:** Como mantenedor do Backend_SRA, quero substituir o `except Exception: pass` no bloco que obtém `request.path` e `request.method` dentro de `SRALogHandler.emit` em `app/utils/logger.py` por uma chamada ao Logger_Central com nível `warning`, para que essa falha deixe de ser silenciosa.

#### Acceptance Criteria

1. THE Backend_SRA SHALL não conter o padrão `except Exception: pass` no bloco `try`/`except` de `SRALogHandler.emit` que obtém `request.path`/`request.method` em `app/utils/logger.py`.
2. WHEN uma exceção for capturada nesse bloco, THE Backend_SRA SHALL registrar a ocorrência com nível `warning` contendo (a) identificador textual do contexto indicando "obtenção de request.path/request.method em SRALogHandler.emit", (b) o tipo da exceção e (c) `str(exc)`.
3. WHEN uma exceção for capturada nesse bloco, THE Backend_SRA SHALL atribuir strings vazias aos campos `path` e `method` em construção e prosseguir com a emissão do log original.
4. IF o registro do log de warning falhar por qualquer motivo, THEN THE Backend_SRA SHALL suprimir a falha secundária sem propagá-la ao chamador.
5. THE Backend_SRA SHALL utilizar para o registro de warning um logger Python distinto cuja cadeia de handlers não inclua a instância de `SRALogHandler` em execução.

### Requirement 7: Substituir `except Exception` externo em `SRALogHandler.emit` por log warning sem recursão

**User Story:** Como mantenedor do Backend_SRA, quero substituir o `except Exception` externo de `SRALogHandler.emit` em `app/utils/logger.py` por um caminho que registre a falha com nível `warning` sem disparar recursão de logging, mantendo o fallback `self.handleError(record)` existente.

#### Acceptance Criteria

1. THE Backend_SRA SHALL não conter o padrão literal `except Exception: pass` em nenhuma das instâncias presentes dentro do método `SRALogHandler.emit` de `app/utils/logger.py` após a alteração.
2. IF uma exceção for capturada pelo bloco `except Exception` externo de `SRALogHandler.emit`, THEN THE Backend_SRA SHALL registrar a ocorrência com nível `warning` contendo, no mínimo, o tipo da exceção e `str(exc)`, utilizando um logger Python cuja cadeia de handlers não inclua a instância de `SRALogHandler` em execução.
3. THE Backend_SRA SHALL preservar a chamada existente a `self.handleError(record)` no caminho de exceção do `emit` externo.
4. IF o registro do log de warning lançar qualquer exceção, THEN THE Backend_SRA SHALL suprimir essa exceção secundária e não propagá-la ao chamador original do handler.
5. THE Backend_SRA SHALL garantir que, durante o tratamento da exceção em `emit`, o `emit` da mesma instância de `SRALogHandler` não seja invocado novamente como consequência direta ou indireta.

### Requirement 8: Modernizar `var` para `let`/`const` em `logger.js`

**User Story:** Como mantenedor do Frontend_SRA, quero modernizar declarações `var` para `let` ou `const` em `app/static/js/logger.js`, apenas onde o escopo é trivialmente compatível, para alinhar o arquivo às convenções modernas de JavaScript.

#### Acceptance Criteria

1. IF uma declaração originalmente `var` em `app/static/js/logger.js` é referenciada apenas dentro do menor bloco `{ }` que a contém e não é referenciada antes da linha de declaração nem redeclarada no mesmo escopo, THEN THE Frontend_SRA SHALL substituir essa declaração por `const` quando não houver reatribuição posterior (operadores `=`, `+=`, `-=`, `*=`, `/=`, `%=`, `++`, `--`) ou por `let` quando houver pelo menos uma reatribuição posterior.
2. IF uma declaração originalmente `var` em `app/static/js/logger.js` é referenciada fora do bloco mais próximo, é referenciada antes da linha de declaração ou é redeclarada no mesmo escopo, THEN THE Frontend_SRA SHALL preservar a declaração `var` original (identificador, inicializador e linha).
3. THE Frontend_SRA SHALL preservar a saída funcional e visual de `app/static/js/logger.js` (mesmas mensagens emitidas, mesmas funções expostas), sem introduzir novos `console.error`/`console.warn` durante carga e interação da página.
4. THE Frontend_SRA SHALL limitar todas as alterações exclusivamente ao arquivo `app/static/js/logger.js`.

### Requirement 9: Modernizar `var` para `let`/`const` em `visualizador_parametros.js`

**User Story:** Como mantenedor do Frontend_SRA, quero modernizar declarações `var` para `let` ou `const` em `app/static/js/visualizador_parametros.js`, apenas onde o escopo é trivialmente compatível, para alinhar o arquivo às convenções modernas de JavaScript.

#### Acceptance Criteria

1. IF uma declaração originalmente `var` em `app/static/js/visualizador_parametros.js` é referenciada apenas dentro do menor bloco `{ }` que a contém e não é referenciada antes da linha de declaração nem redeclarada no mesmo escopo, THEN THE Frontend_SRA SHALL substituir essa declaração por `const` quando não houver reatribuição posterior ou por `let` quando houver pelo menos uma reatribuição posterior.
2. IF uma declaração originalmente `var` em `app/static/js/visualizador_parametros.js` apresentar uso fora do bloco, hoisting ou redeclaração no mesmo escopo, THEN THE Frontend_SRA SHALL preservar a declaração `var` original.
3. THE Frontend_SRA SHALL preservar a saída funcional e visual de `app/static/js/visualizador_parametros.js`, sem introduzir novos `console.error`/`console.warn` durante carga e interação da página.
4. IF uma substituição introduzida resultar em alteração observável de comportamento ou de saída visual da página, THEN THE Frontend_SRA SHALL reverter aquela substituição específica preservando a declaração `var` original.
5. THE Frontend_SRA SHALL limitar todas as alterações exclusivamente ao arquivo `app/static/js/visualizador_parametros.js`.

### Requirement 10: Migrar `onchange` inline de `editor_coordenador.html` para `editor_coordenador.js`

**User Story:** Como mantenedor do Frontend_SRA, quero remover o Handler_Inline `onchange` do elemento `<select id="ec-rel-select">` em `app/templates/editor_coordenador.html` e migrar a lógica equivalente para o JS_Companion `app/static/js/editor_coordenador.js` via `addEventListener`.

#### Acceptance Criteria

1. THE Frontend_SRA SHALL não conter atributos `on*` inline no elemento `<select id="ec-rel-select">` de `app/templates/editor_coordenador.html`.
2. WHEN `DOMContentLoaded` ocorrer no documento que carrega `app/templates/editor_coordenador.html`, THE Frontend_SRA SHALL registrar, a partir de `app/static/js/editor_coordenador.js`, exatamente um listener para o evento `change` no elemento `#ec-rel-select`.
3. WHEN o evento `change` ocorrer em `#ec-rel-select` e o `value` selecionado for não vazio, THE Frontend_SRA SHALL atribuir esse `value` a `window.location.href`.
4. IF o evento `change` ocorrer em `#ec-rel-select` e o `value` for vazio, `null` ou `undefined`, THEN THE Frontend_SRA SHALL não alterar `window.location.href`.
5. IF o elemento `#ec-rel-select` não estiver presente no DOM, THEN THE Frontend_SRA SHALL não lançar exceção e não registrar listener.

### Requirement 11: Migrar `onchange` inline de `editor_autor.html` para `editor_autor.js`

**User Story:** Como mantenedor do Frontend_SRA, quero remover o Handler_Inline `onchange` do elemento `<select id="ea-rel-select">` em `app/templates/editor_autor.html` e migrar a lógica equivalente para o JS_Companion `app/static/js/editor_autor.js` via `addEventListener`.

#### Acceptance Criteria

1. THE Frontend_SRA SHALL não conter atributos `on*` inline no elemento `<select id="ea-rel-select">` de `app/templates/editor_autor.html`.
2. WHEN `DOMContentLoaded` ocorrer no documento que carrega `app/templates/editor_autor.html`, THE Frontend_SRA SHALL registrar, a partir de `app/static/js/editor_autor.js`, exatamente um listener para o evento `change` no elemento `#ea-rel-select`.
3. WHEN o evento `change` ocorrer em `#ea-rel-select` e o `value` selecionado for não vazio, THE Frontend_SRA SHALL atribuir esse `value` a `window.location.href`.
4. IF o evento `change` ocorrer em `#ea-rel-select` e o `value` for vazio, `null` ou `undefined`, THEN THE Frontend_SRA SHALL não alterar `window.location.href`.
5. IF o elemento `#ea-rel-select` não estiver presente no DOM, THEN THE Frontend_SRA SHALL não lançar exceção e não registrar listener.

### Requirement 12: Migrar `onsubmit` do envio final em `editor_autor.html` para `editor_autor.js`

**User Story:** Como mantenedor do Frontend_SRA, quero remover o Handler_Inline `onsubmit` do formulário de envio final em `app/templates/editor_autor.html` (linha ~317) e migrar a confirmação correspondente para `app/static/js/editor_autor.js` via `addEventListener`.

#### Acceptance Criteria

1. THE Frontend_SRA SHALL não conter atributo `onsubmit=` no formulário de envio final de `app/templates/editor_autor.html` (formulário com classe `acao-form` cujo `action` aponta para o endpoint de envio final).
2. WHEN `DOMContentLoaded` ocorrer no documento que carrega `app/templates/editor_autor.html`, THE Frontend_SRA SHALL registrar, a partir de `app/static/js/editor_autor.js`, exatamente um listener para o evento `submit` nesse formulário.
3. WHEN o evento `submit` ocorrer nesse formulário, THE Frontend_SRA SHALL exibir um diálogo de confirmação nativo (`window.confirm`) contendo exatamente o texto `Enviar conteúdo final ao coordenador? Depois disso sua edição ficará bloqueada.`.
4. IF o usuário cancelar a confirmação, THEN THE Frontend_SRA SHALL impedir o envio do formulário e preservar a página atual sem navegação.
5. WHEN o usuário confirmar a ação, THE Frontend_SRA SHALL submeter o formulário ao endpoint definido em seu atributo `action`, preservando o campo `csrf_token` presente nos campos do formulário sem alterar seu valor.

### Requirement 13: Criar JS_Utilitario_Confirmacao e migrar `onsubmit` de `_botao_acao.html`

**User Story:** Como mantenedor do Frontend_SRA, quero criar um JS_Utilitario_Confirmacao baseado em `data-attribute` (`data-confirm` + `data-confirm-message`) e migrar o Handler_Inline `onsubmit` do macro `_botao_acao` para esse utilitário, eliminando JS inline.

#### Acceptance Criteria

1. THE Frontend_SRA SHALL não conter atributo `onsubmit=` em nenhum elemento de `app/templates/components/_botao_acao.html`.
2. THE Frontend_SRA SHALL incluir um arquivo JS_Utilitario_Confirmacao em `app/static/js/`, carregado via `{{ static_v('js/<nome>.js') }}` em layout base usado pelas telas que renderizam o macro, que registre `addEventListener('submit', ...)` em todos os formulários que possuírem o atributo `data-confirm`.
3. WHEN o evento `submit` ocorrer em formulário com `data-confirm` cujo atributo `data-confirm-message` esteja presente e não vazio, THE Frontend_SRA SHALL exibir `window.confirm` com texto exatamente igual ao valor de `data-confirm-message`.
4. IF o evento `submit` ocorrer em formulário com `data-confirm` mas sem `data-confirm-message` (ausente ou vazio), THEN THE Frontend_SRA SHALL exibir `window.confirm` com a mensagem padrão `Confirmar ação?`.
5. WHEN o usuário cancelar a confirmação, THE Frontend_SRA SHALL impedir o envio e preservar todos os campos do formulário inalterados.
6. WHEN o usuário confirmar, THE Frontend_SRA SHALL prosseguir com o envio ao endpoint de `action` usando o método de `method`, sem remover, alterar ou reordenar nenhum campo, incluindo o CSRF_Token.
7. WHEN o evento `submit` ocorrer em formulário sem `data-confirm`, THE Frontend_SRA SHALL não exibir confirmação e não alterar o fluxo padrão.
8. THE Frontend_SRA SHALL renderizar nos formulários do macro `_botao_acao` o atributo `data-confirm-message` com o mesmo texto que o `onsubmit` original passava ao `confirm()`, preservando o texto exibido.

### Requirement 14: Migrar `onsubmit` de `_acoes_tabela.html` para JS_Utilitario_Confirmacao

**User Story:** Como mantenedor do Frontend_SRA, quero remover o Handler_Inline `onsubmit` do macro `btn_excluir` em `app/templates/components/_acoes_tabela.html` fazendo com que ele use o JS_Utilitario_Confirmacao do Requisito 13.

#### Acceptance Criteria

1. THE Frontend_SRA SHALL não conter atributo `onsubmit=` no formulário do macro `btn_excluir` em `app/templates/components/_acoes_tabela.html`.
2. THE Frontend_SRA SHALL aplicar ao formulário do macro `btn_excluir` o atributo `data-confirm` e o atributo `data-confirm-message` com valor igual ao parâmetro `confirmacao` recebido pelo macro (default `Excluir este item e seu arquivo associado?`).
3. WHEN o usuário cancelar a confirmação acionada pelo JS_Utilitario_Confirmacao nesse formulário, THEN THE Frontend_SRA SHALL impedir o envio e preservar o estado da página.
4. THE Frontend_SRA SHALL preservar inalterado o Comportamento_Observavel das telas que renderizam o macro `btn_excluir`, incluindo o texto da confirmação e o CSRF_Token.

### Requirement 15: Migrar `onchange` inline de `arvore_capitulos.html` para `app.js`

**User Story:** Como mantenedor do Frontend_SRA, quero remover o Handler_Inline `onchange` do elemento `<select id="seletor_relatorio">` em `app/templates/components/relatorio/arvore_capitulos.html` e migrar a lógica para `app/static/js/app.js` via `addEventListener`.

#### Acceptance Criteria

1. THE Frontend_SRA SHALL não conter atributos `on*` inline em `<select id="seletor_relatorio">` em `app/templates/components/relatorio/arvore_capitulos.html`.
2. WHEN `DOMContentLoaded` ocorrer em página que renderiza esse template, THE Frontend_SRA SHALL registrar a partir de `app/static/js/app.js` exatamente um listener para o evento `change` em `#seletor_relatorio`.
3. WHEN o evento `change` ocorrer em `#seletor_relatorio` e o `value` selecionado for não vazio, THE Frontend_SRA SHALL atribuir `'/relatorio/versao-trabalho/' + value` a `window.location.href`.
4. IF o `value` for vazio, `null` ou `undefined`, THEN THE Frontend_SRA SHALL não alterar `window.location.href`.
5. IF o elemento `#seletor_relatorio` não estiver presente no DOM, THEN THE Frontend_SRA SHALL não lançar exceção e não registrar listener.

### Requirement 16: Migrar `onclick` de `painel_criar_relatorio_producao.html` para JS dedicado

**User Story:** Como mantenedor do Frontend_SRA, quero remover o Handler_Inline `onclick` que invoca `clonarDaBiblioteca()` em `app/templates/components/paineis/painel_criar_relatorio_producao.html` e migrar a vinculação para `addEventListener` em arquivo JS dedicado novo.

#### Acceptance Criteria

1. THE Frontend_SRA SHALL não conter atributo `onclick=` no botão originalmente referenciado pela linha 66 de `app/templates/components/paineis/painel_criar_relatorio_producao.html`.
2. THE Frontend_SRA SHALL preservar a definição da função `clonarDaBiblioteca` (nome, parâmetros, corpo) em sua localização atual.
3. THE Frontend_SRA SHALL incluir um arquivo JS_Dedicado em `app/static/js/`, referenciado no template via `{{ static_v('js/<nome>.js') }}`, que registre `addEventListener('click', ...)` no botão alvo após `DOMContentLoaded`.
4. WHEN o evento `click` ocorrer no botão alvo, THE Frontend_SRA SHALL invocar `clonarDaBiblioteca` exatamente uma vez por clique, com a mesma assinatura/argumentos do Handler_Inline removido.
5. IF o botão alvo não estiver presente no DOM, THEN THE Frontend_SRA SHALL não lançar exceção e não registrar listener.
6. THE Frontend_SRA SHALL preservar inalterado o Comportamento_Observavel da ação, incluindo CSRF_Token nas requisições disparadas, método/URL alvo e atualizações de UI.

### Requirement 17: Migrar `onclick` de `dashboard_coordenador.html` para JS dedicado

**User Story:** Como mantenedor do Frontend_SRA, quero remover o Handler_Inline `onclick` em `app/templates/components/paineis/dashboard_coordenador.html` e migrar a vinculação para `addEventListener` em arquivo JS dedicado.

#### Acceptance Criteria

1. THE Frontend_SRA SHALL não conter atributo `onclick=` no botão originalmente referenciado pela linha 101 de `app/templates/components/paineis/dashboard_coordenador.html`.
2. THE Frontend_SRA SHALL preservar a definição da função invocada pelo Handler_Inline (`clonarDaBiblioteca`) em sua localização atual.
3. THE Frontend_SRA SHALL incluir um arquivo JS_Dedicado (ou reusar o do Requisito 16) em `app/static/js/`, referenciado via `{{ static_v(...) }}`, que registre `addEventListener('click', ...)` no botão alvo após `DOMContentLoaded`.
4. WHEN o evento `click` ocorrer no botão alvo, THE Frontend_SRA SHALL invocar a função-alvo exatamente uma vez por clique, com a mesma assinatura/argumentos do Handler_Inline removido.
5. IF o botão alvo não estiver presente no DOM, THEN THE Frontend_SRA SHALL não lançar exceção e não registrar listener.
6. THE Frontend_SRA SHALL preservar inalterado o Comportamento_Observavel da ação, incluindo CSRF_Token nas requisições disparadas.

### Requirement 18: Migrar `onsubmit` de `biblioteca_formatacao.html` para JS_Utilitario_Confirmacao

**User Story:** Como mantenedor do Frontend_SRA, quero remover o Handler_Inline `onsubmit` do formulário de exclusão em `app/templates/components/configuracoes/biblioteca_formatacao.html` fazendo com que ele use o JS_Utilitario_Confirmacao do Requisito 13.

#### Acceptance Criteria

1. THE Frontend_SRA SHALL não conter atributo `onsubmit=` (nem qualquer atributo iniciado por `on`) no formulário originalmente referenciado pela linha 19 de `app/templates/components/configuracoes/biblioteca_formatacao.html`.
2. THE Frontend_SRA SHALL aplicar ao formulário alvo o atributo `data-confirm` e o atributo `data-confirm-message` cujo valor seja exatamente igual à mensagem original `Excluir biblioteca "<nome>"? Esta ação não pode ser desfeita.`, com `<nome>` interpolado a partir de `b.nome_biblioteca` sem alterações de capitalização, espaços ou pontuação.
3. WHEN o usuário cancelar a confirmação, THE Frontend_SRA SHALL impedir o envio e preservar a tela atual sem navegação.
4. WHEN o usuário confirmar, THE Frontend_SRA SHALL submeter o formulário ao mesmo `action` e `method` originais, preservando o CSRF_Token.

### Requirement 19: Remover `!important` em `.sigma-pli-conteiner__icon--lg svg` (`stroke`/`fill`)

**User Story:** Como mantenedor do Frontend_SRA, quero remover o `!important` das declarações `stroke` e `fill` da regra `.sigma-pli-conteiner__icon--lg svg` / `.sigma-pli-conteiner__icon--lg svg *` em `app/static/css/app.css`, garantindo previamente que a especificidade do seletor é suficiente.

#### Acceptance Criteria

1. THE Frontend_SRA SHALL não conter `!important` nas declarações `stroke` e `fill` da regra que mira `.sigma-pli-conteiner__icon--lg svg` e `.sigma-pli-conteiner__icon--lg svg *` em `app/static/css/app.css`.
2. WHEN um ícone com classe `.sigma-pli-conteiner__icon--lg` for renderizado, THE Frontend_SRA SHALL aplicar aos elementos `svg` e seus descendentes os mesmos valores computados de `stroke`, `fill` e `stroke-width` observados antes da remoção do `!important` (verificação via `getComputedStyle`).
3. IF, após a remoção, alguma regra CSS de origem do autor sobrescrever esses valores, THEN THE Frontend_SRA SHALL ajustar a especificidade do seletor (sem reintroduzir `!important`) para que os valores originais voltem a prevalecer.
4. THE Frontend_SRA SHALL preservar inalterado o restante de `app/static/css/app.css` fora do bloco modificado.

### Requirement 20: Remover `!important` em `.sra-tree__item--hidden { display: none }`

**User Story:** Como mantenedor do Frontend_SRA, quero remover o `!important` da regra `.sra-tree__item--hidden { display: none; }` em `app/static/css/app.css`, garantindo previamente que a especificidade do seletor é suficiente.

#### Acceptance Criteria

1. THE Frontend_SRA SHALL não conter `!important` na declaração `display: none` da regra que mira `.sra-tree__item--hidden` em `app/static/css/app.css`.
2. WHEN um elemento com classe `.sra-tree__item--hidden` for renderizado, THE Frontend_SRA SHALL apresentar `display` computado igual a `none`.
3. IF, após a remoção, alguma regra CSS sobrescrever `display`, THEN THE Frontend_SRA SHALL ajustar a especificidade do seletor (sem reintroduzir `!important`) para preservar o comportamento de ocultação.
4. THE Frontend_SRA SHALL preservar demais `!important` do arquivo fora desta regra.

### Requirement 21: Remover `!important` em `.sra-tree__toggle[hidden] { display: none }`

**User Story:** Como mantenedor do Frontend_SRA, quero remover o `!important` da regra `.sra-tree__toggle[hidden] { display: none; }` em `app/static/css/app.css`, garantindo previamente que a especificidade do seletor é suficiente.

#### Acceptance Criteria

1. THE Frontend_SRA SHALL não conter `!important` na declaração `display: none` da regra que mira `.sra-tree__toggle[hidden]` em `app/static/css/app.css`.
2. WHEN um elemento `.sra-tree__toggle` com atributo `hidden` for renderizado, THE Frontend_SRA SHALL apresentar `display` computado igual a `none`.
3. IF outra regra autoral sobrescrever `display` para esse seletor, THEN THE Frontend_SRA SHALL ajustar a especificidade (sem reintroduzir `!important`) para preservar a ocultação.
4. THE Frontend_SRA SHALL preservar demais `!important` do arquivo fora desta regra.

### Requirement 22: Remover `!important` em `.sra-table--cap-collapsible .sra-cap-row--hidden { display: none }`

**User Story:** Como mantenedor do Frontend_SRA, quero remover o `!important` da regra `.sra-table--cap-collapsible .sra-cap-row--hidden { display: none; }` em `app/static/css/app.css`, garantindo previamente que a especificidade do seletor é suficiente.

#### Acceptance Criteria

1. THE Frontend_SRA SHALL não conter `!important` na declaração `display: none` da regra que mira `.sra-table--cap-collapsible .sra-cap-row--hidden`.
2. WHEN um elemento `.sra-cap-row--hidden` dentro de `.sra-table--cap-collapsible` for renderizado, THE Frontend_SRA SHALL apresentar `display` computado igual a `none`.
3. IF outra regra autoral sobrescrever `display` para esse seletor, THEN THE Frontend_SRA SHALL ajustar a especificidade (sem reintroduzir `!important`) para preservar a ocultação.
4. THE Frontend_SRA SHALL preservar demais `!important` do arquivo fora desta regra.
5. WHEN a classe `.sra-cap-row--hidden` for adicionada ou removida dinamicamente em uma linha de tabela já renderizada, THE Frontend_SRA SHALL alternar coerentemente a presença visual da linha sem requerer recarregamento da página.

### Requirement 23: Remover `!important` em `.sra-table__header--left { text-align: left }`

**User Story:** Como mantenedor do Frontend_SRA, quero remover o `!important` da regra `.sra-table__header--left { text-align: left; }` em `app/static/css/app.css`, garantindo previamente que a especificidade do seletor é suficiente.

#### Acceptance Criteria

1. THE Frontend_SRA SHALL não conter `!important` na declaração `text-align: left` da regra que mira `.sra-table__header--left`.
2. WHEN um elemento `.sra-table__header--left` for renderizado, THE Frontend_SRA SHALL apresentar `text-align` computado igual a `left`.
3. IF outra regra autoral sobrescrever `text-align` para esse seletor, THEN THE Frontend_SRA SHALL ajustar a especificidade (sem reintroduzir `!important`) para preservar o alinhamento.
4. THE Frontend_SRA SHALL preservar demais declarações da regra original (seletor e demais propriedades) inalteradas.

### Requirement 24: Remover `!important` em `.sra-cap-toggle[hidden] { display: none }`

**User Story:** Como mantenedor do Frontend_SRA, quero remover o `!important` da regra `.sra-cap-toggle[hidden] { display: none; }` em `app/static/css/app.css`, garantindo previamente que a especificidade do seletor é suficiente.

#### Acceptance Criteria

1. THE Frontend_SRA SHALL não conter `!important` na declaração `display: none` da regra que mira `.sra-cap-toggle[hidden]`.
2. WHEN um elemento `.sra-cap-toggle` com atributo `hidden` for renderizado, THE Frontend_SRA SHALL apresentar `display` computado igual a `none`.
3. IF outra regra autoral sobrescrever `display` para esse seletor, THEN THE Frontend_SRA SHALL ajustar a especificidade (sem reintroduzir `!important`) para preservar a ocultação.

### Requirement 25: Remover `!important` em `.sra-cap-cell--title { text-align: left }`

**User Story:** Como mantenedor do Frontend_SRA, quero remover o `!important` da regra `.sra-cap-cell--title { text-align: left; }` em `app/static/css/app.css`, garantindo previamente que a especificidade do seletor é suficiente.

#### Acceptance Criteria

1. THE Frontend_SRA SHALL não conter `!important` na declaração `text-align: left` da regra que mira `.sra-cap-cell--title`.
2. WHEN um elemento `.sra-cap-cell--title` for renderizado, THE Frontend_SRA SHALL apresentar `text-align` computado igual a `left`.
3. IF outra regra autoral sobrescrever `text-align` para esse seletor, THEN THE Frontend_SRA SHALL ajustar a especificidade (sem reintroduzir `!important`) para preservar o alinhamento.
4. THE Frontend_SRA SHALL preservar demais declarações da regra original (seletor e demais propriedades) inalteradas.

### Requirement 26: Resolver `TODO` em `card_cadastro_relatorio_versao_trabalho.html`

**User Story:** Como mantenedor do Frontend_SRA, quero resolver o `TODO` presente na linha 38 de `app/templates/components/relatorio/card_cadastro_relatorio_versao_trabalho.html`, confirmando antes com o usuário se a funcionalidade já existe em outro fluxo.

#### Acceptance Criteria

1. WHEN a alteração no arquivo for concluída, THE Frontend_SRA SHALL não conter nenhuma ocorrência da string `TODO` em comentários ou conteúdo de `app/templates/components/relatorio/card_cadastro_relatorio_versao_trabalho.html`.
2. IF o mantenedor não obtiver confirmação explícita do usuário sobre a existência da funcionalidade em outro fluxo antes da alteração, THEN THE Frontend_SRA SHALL preservar o arquivo inalterado.
3. WHERE o usuário confirmar que a funcionalidade já existe em outro fluxo do Sistema_SRA, THE Frontend_SRA SHALL remover do template o bloco do card associado ao `TODO`, de forma que o card não seja mais renderizado.
4. WHERE o usuário confirmar que a funcionalidade ainda não existe em outro fluxo do Sistema_SRA, THE Frontend_SRA SHALL manter o card no template e exibir, em substituição ao texto original, um rótulo visível ao usuário contendo a expressão "em desenvolvimento", em PT-BR, sem o marcador `TODO` no comentário ou no conteúdo renderizado.
5. WHEN o template for renderizado em qualquer tela após a alteração, THE Frontend_SRA SHALL preservar inalterado o Comportamento_Observavel das demais áreas (demais cards, botões, links, formulários e mensagens já existentes).
6. IF a alteração gerar erro de sintaxe Jinja2 ou impedir a renderização do template, THEN THE Frontend_SRA SHALL ser revertido ao estado anterior à alteração.

## Requisitos Não-Funcionais (27-32)

### Requirement 27: Preservação de comportamento

**User Story:** Como usuário final do Sistema_SRA, quero que a sanitização não altere nenhum comportamento percebido da aplicação, para que minhas operações continuem funcionando exatamente como antes.

#### Acceptance Criteria

1. THE Sistema_SRA SHALL preservar inalterado o conjunto de rotas HTTP existente antes da sanitização (mesmos métodos, mesmos paths).
2. THE Sistema_SRA SHALL preservar inalterado o formato e o conteúdo dos payloads de resposta retornados pelas rotas existentes para entradas equivalentes.
3. THE Sistema_SRA SHALL preservar inalterada a aparência visual renderizada para o usuário final em todas as telas afetadas pela sanitização.

### Requirement 28: Preservação de proteção CSRF

**User Story:** Como responsável por segurança do Sistema_SRA, quero que toda submissão mutante (forms e requests `fetch`/`XHR`) continue protegida por CSRF_Token após a sanitização, para não introduzir regressão de segurança.

#### Acceptance Criteria

1. WHEN um formulário existente antes da sanitização exigia CSRF_Token, THE Sistema_SRA SHALL continuar incluindo CSRF_Token no formulário equivalente após a sanitização.
2. WHEN uma requisição `fetch` ou `XHR` mutante existente antes da sanitização incluía header `X-CSRFToken`, THE Sistema_SRA SHALL continuar incluindo o header `X-CSRFToken` na requisição equivalente após a sanitização.

### Requirement 29: Idioma PT-BR

**User Story:** Como mantenedor do Sistema_SRA, quero que comentários, mensagens e nomes introduzidos durante a sanitização sigam o padrão PT-BR do projeto.

#### Acceptance Criteria

1. THE Sistema_SRA SHALL apresentar em português do Brasil os comentários, mensagens de log, mensagens ao usuário e identificadores introduzidos pela sanitização, exceto termos técnicos consagrados em inglês (ex.: `addEventListener`, `submit`).

### Requirement 30: Cache-busting de assets

**User Story:** Como mantenedor do Frontend_SRA, quero que qualquer novo asset estático referenciado em template Jinja durante a sanitização passe pelo helper `static_v`, para preservar a estratégia de cache-busting.

#### Acceptance Criteria

1. WHEN a sanitização introduzir referência a um novo asset estático em template Jinja, THE Frontend_SRA SHALL referenciá-lo por meio de `{{ static_v('<caminho>') }}`.

### Requirement 31: Áreas intocadas

**User Story:** Como mantenedor do Sistema_SRA, quero que a sanitização não toque em áreas explicitamente fora de escopo, para evitar efeitos colaterais.

#### Acceptance Criteria

1. THE Sistema_SRA SHALL preservar sem alteração os arquivos sob `app/static/editor-react/`.
2. THE Sistema_SRA SHALL preservar sem alteração os arquivos `.env`, os arquivos sob `migrations/`, os arquivos sob `storage/`, o arquivo `requirements.txt` e o arquivo `package-lock.json`.
3. THE Sistema_SRA SHALL preservar sem alteração os blocos de tratamento de exceção listados como "manter intocados": `app/services/servico_relatorio.py:101`, `app/services/servico_sanitizar_docx.py:534`, as duas ocorrências em `app/services/servico_capa.py`, `app/routes/relatorio.py:774` e `app/services/servico_finalizar_relatorio.py:109`.

### Requirement 32: Validação final

**User Story:** Como mantenedor do Sistema_SRA, quero validar objetivamente que os itens corrigidos não voltam a aparecer nas verificações estáticas, para garantir o fechamento da sanitização.

#### Acceptance Criteria

1. WHEN o desenvolvedor executar `python -m pyflakes app`, THE Linter_Pyflakes SHALL não reportar nenhum dos itens corrigidos pelos Requisitos 1, 2 e 3.
2. THE Frontend_SRA SHALL não conter atributos `onclick=`, `onchange=` ou `onsubmit=` nos pontos listados nos Requisitos 10 a 18.
3. THE Frontend_SRA SHALL não conter `!important` em `app/static/css/app.css` nas regras listadas nos Requisitos 19 a 25.
