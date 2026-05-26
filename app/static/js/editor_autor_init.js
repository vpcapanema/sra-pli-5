/* ============================================================
   Editor do Autor — Inicialização
   
   Script de inicialização do editor do autor com handlers
   para seletores e formulários.
   ============================================================ */
(function () {
    'use strict';

    if (typeof SRALogger !== 'undefined') {
        SRALogger.info('[editor_autor_init.js] carregado');
    }

    document.addEventListener('DOMContentLoaded', function() {
        if (typeof SRALogger !== 'undefined') {
            SRALogger.info('[editor_autor_init] Inicializando handlers do editor');
        }

        // Handler para seletor de relatório — redireciona para novo URL
        var relSelect = document.getElementById('ea-rel-select');
        if (relSelect) {
            relSelect.addEventListener('change', function() {
                var selectedOption = relSelect.options[relSelect.selectedIndex];
                var url = selectedOption.getAttribute('data-url');
                if (url) {
                    if (typeof SRALogger !== 'undefined') {
                        SRALogger.info('[editor_autor_init] Redirecionando para: ' + url);
                    }
                    window.location.href = url;
                }
            });
            if (typeof SRALogger !== 'undefined') {
                SRALogger.debug('[editor_autor_init] Seletor de relatório inicializado');
            }
        }

        // Handler para atualizar form action quando capítulo é selecionado
        var capSelect = document.getElementById('ea-atribuir-cap');
        var form = document.getElementById('ea-atribuir-form');
        if (capSelect && form) {
            function atualizarAction() {
                if (capSelect.value) {
                    var baseUrl = form.getAttribute('data-base-url');
                    var newAction = baseUrl + capSelect.value + '/atribuir';
                    form.action = newAction;
                    if (typeof SRALogger !== 'undefined') {
                        SRALogger.debug('[editor_autor_init] Form action: ' + newAction);
                    }
                } else {
                    form.action = '';
                }
            }

            capSelect.addEventListener('change', atualizarAction);
            
            // Prevenir submissão sem capítulo e action preenchido
            form.addEventListener('submit', function(evt) {
                if (!capSelect.value || !form.action) {
                    evt.preventDefault();
                    evt.stopPropagation();
                    if (typeof SRALogger !== 'undefined') {
                        SRALogger.warn('[editor_autor_init] Tentativa de submit sem capítulo selecionado');
                    }
                    alert('Por favor, selecione um capítulo antes de confirmar.');
                    return false;
                }
            });

            // Executar na carga se houver capítulo pré-selecionado
            if (capSelect.value) {
                atualizarAction();
            }

            if (typeof SRALogger !== 'undefined') {
                SRALogger.info('[editor_autor_init] Formulário de atribuição inicializado');
            }
        }

        if (typeof SRALogger !== 'undefined') {
            SRALogger.info('[editor_autor_init] Todos os handlers inicializados com sucesso');
        }
    });
})();
