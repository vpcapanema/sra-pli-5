/**
 * confirmacao_form.js
 *
 * Utilitário compartilhado de confirmação de submit de formulário.
 *
 * Padrão de uso nos templates:
 *   <form action="..." method="post"
 *         data-confirm
 *         data-confirm-message='Excluir item "X"? Esta ação não pode ser desfeita.'>
 *     ...
 *   </form>
 *
 * - Em todo `form[data-confirm]` é registrado UM listener `submit` que
 *   exibe `window.confirm(data-confirm-message)`. Se `data-confirm-message`
 *   estiver ausente ou vazio, é usado o texto padrão `Confirmar ação?`.
 * - Em cancelamento, o envio é abortado via `preventDefault` + `stopPropagation`.
 * - O utilitário NÃO altera, remove ou reordena campos do formulário
 *   (incluindo o token CSRF) — apenas decide se o submit prossegue.
 * - Idempotência: o atributo `data-confirm-instalado="1"` impede registro
 *   duplicado caso `instalar()` seja chamado mais de uma vez.
 */
(function () {
  'use strict';

  function instalar() {
    // Localiza todos os formulários marcados com `data-confirm`.
    document.querySelectorAll('form[data-confirm]').forEach(function (form) {
      // Sentinela de idempotência: evita registro duplicado.
      if (form.dataset.confirmInstalado === '1') {
        return;
      }
      form.dataset.confirmInstalado = '1';

      form.addEventListener('submit', function (ev) {
        // Mensagem do diálogo: usa `data-confirm-message` ou fallback.
        var msg = form.getAttribute('data-confirm-message');
        if (!msg) {
          msg = 'Confirmar ação?';
        }
        // Em cancelamento: aborta o envio e impede propagação.
        if (!window.confirm(msg)) {
          ev.preventDefault();
          ev.stopPropagation();
        }
      });
    });
  }

  // Inicialização: aguarda DOMContentLoaded se o documento ainda está carregando;
  // caso contrário, instala imediatamente.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', instalar);
  } else {
    instalar();
  }
})();
