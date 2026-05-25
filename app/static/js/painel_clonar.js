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
        // Suporte simples a 1-2 argumentos posicionais; templates podem
        // passar apenas data-arg-id se o segundo argumento for irrelevante.
        if (tipo !== null && tipo !== '') {
          window.clonarDaBiblioteca(id, tipo);
        } else {
          window.clonarDaBiblioteca(id);
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
