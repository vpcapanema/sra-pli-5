/* ============================================================
   Editor do Autor — JS INDEPENDENTE

   Funcao unica:
   - Monta o @eigenpal/docx-editor-react no container PROPRIO
     (#ea-docxEditorMount) em modo editing
   - Totalmente independente do editor_coordenador.js
   - Sem conflitos, sem double-mounting
   ============================================================ */
(function () {
    'use strict';

    if (typeof SRALogger !== 'undefined') {
        SRALogger.info('[ea-editor-autor.js] carregado');
    }

    var dataEl = document.getElementById('ea-editor-data');
    if (!dataEl) {
        console.warn('[ea-editor-autor] elemento de dados ausente');
        return;
    }

    var DOCX_URL = dataEl.dataset.docxUrl;
    var MODE = dataEl.dataset.mode || 'editing';
    var MOUNT_ID = 'ea-docxEditorMount';

    if (typeof SRALogger !== 'undefined') {
        SRALogger.info('[ea-editor-autor] Configuração: modo=' + MODE + ', url=' + DOCX_URL);
    }

    var editorHandle = null;

    /**
     * Monta o editor React no container próprio
     * @param {boolean} isManualReload - True se foi acionado explicitamente pelo botão
     */
    function montarEditor(isManualReload) {
        var mountEl = document.getElementById(MOUNT_ID);
        if (!mountEl) {
            console.warn('[ea-editor-autor] container de mount não encontrado');
            return;
        }

        if (typeof SRALogger !== 'undefined') {
            SRALogger.info('[ea-editor-autor] montando editor... (manual: ' + isManualReload + ')');
        }

        // Desmontar handle anterior (se houver)
        if (editorHandle && window.SRADocxEditor
            && window.SRADocxEditor.unmountFullViewer) {
            try {
                window.SRADocxEditor.unmountFullViewer(editorHandle);
                if (typeof SRALogger !== 'undefined') {
                    SRALogger.debug('[ea-editor-autor] editor anterior desmontado');
                }
            } catch (e) { /* ignore */ }
            editorHandle = null;
        }

        // Mostrar loading
        mountEl.innerHTML = ''
            + '<div class="ea__viewer-loading">'
            + '<i class="ph ph-spinner ph-spin"></i> '
            + 'Carregando editor...'
            + '</div>';

        // Verificar se bundle carregou
        if (!window.SRADocxEditor || !window.SRADocxEditor.mountFullViewer) {
            mountEl.innerHTML = ''
                + '<div class="ea__viewer-error">'
                + '<i class="ph ph-warning"></i> '
                + 'Bundle docx-editor não carregou. '
                + 'Verifique a conexão e recarregue a página.'
                + '</div>';
            if (typeof SRALogger !== 'undefined') {
                SRALogger.error('[ea-editor-autor] Bundle docx-editor não disponível');
            }
            return;
        }

        // Cache-bust
        var url = DOCX_URL
            + (DOCX_URL.indexOf('?') >= 0 ? '&' : '?')
            + '_t=' + Date.now();

        if (typeof SRALogger !== 'undefined') {
            SRALogger.httpRequest('GET', url);
        }

        // MONTAR EDITOR
        editorHandle = window.SRADocxEditor.mountFullViewer(MOUNT_ID, {
            url: url,
            mode: MODE,
        });

        if (typeof SRALogger !== 'undefined') {
            SRALogger.info('[ea-editor-autor] editor montado com sucesso');
        }

        // Aplicar estilos após render
        setTimeout(aplicarEstilosViewer, 500);
    }

    /**
     * Aplica estilos finais (zoom branco, etc)
     */
    function aplicarEstilosViewer() {
        // Zoom value em branco
        var zoomValue = document.getElementById('ea-docx-zoom-value');
        if (zoomValue) {
            zoomValue.style.color = '#fff';
            zoomValue.style.fontWeight = '600';
        }
    }

    /**
     * Bind do botão Recarregar (ÚNICO evento que recarrega o editor)
     */
    function bindRecarregar() {
        var btn = document.getElementById('ea-btnRecarregarViewer');
        if (!btn) return;
        btn.addEventListener('click', function (evt) {
            evt.preventDefault();
            evt.stopPropagation();
            if (typeof SRALogger !== 'undefined') {
                SRALogger.click(btn, 'ea-recarregar-editor');
            }
            montarEditor(true);
        });
    }

    /**
     * Bind dos botões de zoom
     */
    function bindZoom() {
        var zoomOut = document.getElementById('ea-docx-zoom-out');
        var zoomIn = document.getElementById('ea-docx-zoom-in');
        var zoomReset = document.getElementById('ea-docx-zoom-reset');
        var zoomValue = document.getElementById('ea-docx-zoom-value');

        if (!zoomValue) return;

        var currentZoom = 100;

        if (zoomOut) {
            zoomOut.addEventListener('click', function () {
                currentZoom = Math.max(50, currentZoom - 10);
                zoomValue.textContent = currentZoom + '%';
                aplicarZoom(currentZoom);
                if (typeof SRALogger !== 'undefined') {
                    SRALogger.click(zoomOut, 'ea-zoom-out-' + currentZoom);
                }
            });
        }

        if (zoomIn) {
            zoomIn.addEventListener('click', function () {
                currentZoom = Math.min(200, currentZoom + 10);
                zoomValue.textContent = currentZoom + '%';
                aplicarZoom(currentZoom);
                if (typeof SRALogger !== 'undefined') {
                    SRALogger.click(zoomIn, 'ea-zoom-in-' + currentZoom);
                }
            });
        }

        if (zoomReset) {
            zoomReset.addEventListener('click', function () {
                currentZoom = 100;
                zoomValue.textContent = currentZoom + '%';
                aplicarZoom(currentZoom);
                if (typeof SRALogger !== 'undefined') {
                    SRALogger.click(zoomReset, 'ea-zoom-reset');
                }
            });
        }
    }

    /**
     * Aplica zoom ao conteúdo
     */
    function aplicarZoom(percent) {
        var mountEl = document.getElementById(MOUNT_ID);
        if (mountEl) {
            var scale = percent / 100;
            mountEl.style.transform = 'scale(' + scale + ')';
            mountEl.style.transformOrigin = 'top center';
            mountEl.scrollTop = 0;
            mountEl.scrollLeft = 0;
        }
    }

    /**
     * Bloqueia recarregamentos automáticos na montagem inicial
     * e em mudanças de seletor — o editor SÓ recarrega ao clicar
     * no botão "Recarregar" explicitamente.
     */
    function prevenirRecarregamentosAutomaticos() {
        var relSelect = document.getElementById('ea-rel-select');
        var capSelect = document.getElementById('ea-cap-select');

        if (relSelect) {
            relSelect.addEventListener('change', function () {
                if (typeof SRALogger !== 'undefined') {
                    SRALogger.info('[ea-editor-autor] seletor de relatório alterado → redirecionando');
                }
                // Deixa o navegador fazer o redirecionamento para nova página
                // Não recarrega editor aqui
            });
        }

        if (capSelect) {
            capSelect.addEventListener('change', function () {
                if (typeof SRALogger !== 'undefined') {
                    SRALogger.info('[ea-editor-autor] seletor de capítulo alterado');
                }
                // Apenas loga, não recarrega editor
                // O usuário clica em "Recarregar" se quiser atualizar
            });
        }
    }

    /**
     * Handler para atualização do formulário de atribuição
     * Quando o capítulo muda, atualiza:
     * - Form action para a rota correta
     * - Pre-seleciona o autor responsável
     * - Atualiza os formulários de upload também
     */
    function setupAttributionForm() {
        var capSelect = document.getElementById('ea-atribuir-cap');
        var autorSelect = document.getElementById('ea-atribuir-autor');
        var form = document.getElementById('ea-atribuir-form');
        var submitBtn = form ? form.querySelector('button[type="submit"]') : null;
        var uploadForm = document.querySelector('.ea__upload-form');
        
        if (!capSelect || !autorSelect || !form) {
            if (typeof SRALogger !== 'undefined') {
                SRALogger.warn('[ea-editor-autor] Elementos de atribuição não encontrados');
            }
            return;
        }
        
        var versaoId = form.getAttribute('data-versao-id');
        if (!versaoId) {
            if (typeof SRALogger !== 'undefined') {
                SRALogger.error('[ea-editor-autor] data-versao-id não encontrado no form');
            }
            return;
        }
        
        /**
         * Atualiza o form action e autor quando capítulo é selecionado
         */
        function atualizarForm() {
            var capId = capSelect.value;
            
            if (capId) {
                // Atualizar form action para a rota de atribuição
                var novaAction = '/relatorio/versao-trabalho/' + versaoId 
                    + '/capitulo/' + capId + '/atribuir';
                form.action = novaAction;
                
                // Atualizar upload form action também
                if (uploadForm) {
                    var novaUploadAction = '/relatorio/versao-trabalho/' + versaoId
                        + '/capitulo/' + capId + '/upload';
                    uploadForm.action = novaUploadAction;
                    if (typeof SRALogger !== 'undefined') {
                        SRALogger.info('[ea-editor-autor] Upload form action atualizado para: ' + novaUploadAction);
                    }
                }
                
                if (typeof SRALogger !== 'undefined') {
                    SRALogger.info('[ea-editor-autor] Form action atualizado para: ' + novaAction);
                }
                
                // Pre-selecionar autor responsável do capítulo
                var selectedOption = capSelect.options[capSelect.selectedIndex];
                var respId = selectedOption.getAttribute('data-resp');
                
                if (respId) {
                    autorSelect.value = respId;
                    if (typeof SRALogger !== 'undefined') {
                        SRALogger.debug('[ea-editor-autor] Autor pré-selecionado: ' + respId);
                    }
                } else {
                    autorSelect.value = '';
                }
                
                // Habilitar botão de submit
                if (submitBtn) {
                    submitBtn.disabled = false;
                }
            } else {
                form.action = '';
                if (uploadForm) {
                    uploadForm.action = '';
                }
                autorSelect.value = '';
                
                // Desabilitar botão de submit se nenhum capítulo estiver selecionado
                if (submitBtn) {
                    submitBtn.disabled = true;
                }
                
                if (typeof SRALogger !== 'undefined') {
                    SRALogger.debug('[ea-editor-autor] Form limpo');
                }
            }
        }
        
        /**
         * Prevenir submit sem capítulo selecionado
         */
        if (form) {
            form.addEventListener('submit', function (evt) {
                if (!capSelect.value) {
                    evt.preventDefault();
                    evt.stopPropagation();
                    if (typeof SRALogger !== 'undefined') {
                        SRALogger.warn('[ea-editor-autor] Tentativa de submit sem capítulo selecionado');
                    }
                    alert('Por favor, selecione um capítulo antes de confirmar.');
                    return false;
                }
            });
        }
        
        /**
         * Event listener para mudança de capítulo
         */
        capSelect.addEventListener('change', atualizarForm);
        
        /**
         * Executar ao carregar se houver capítulo pré-selecionado
         */
        if (capSelect.value) {
            setTimeout(atualizarForm, 100);
        } else if (submitBtn) {
            // Desabilitar submit button se nenhum capítulo pré-selecionado
            submitBtn.disabled = true;
        }
        
        if (typeof SRALogger !== 'undefined') {
            SRALogger.info('[ea-editor-autor] Attribution form listeners configurados');
        }
    }

    /**
     * Inicialização
     */
    document.addEventListener('DOMContentLoaded', function () {
        bindRecarregar();
        bindZoom();
        prevenirRecarregamentosAutomaticos();
        setupAttributionForm();
        montarEditor(false);
        
        if (typeof SRALogger !== 'undefined') {
            SRALogger.info('[ea-editor-autor] inicializado completamente');
        }
    });

    /**
     * Limpeza ao descarregar
     */
    window.addEventListener('beforeunload', function () {
        if (editorHandle && window.SRADocxEditor
            && window.SRADocxEditor.unmountFullViewer) {
            try {
                window.SRADocxEditor.unmountFullViewer(editorHandle);
            } catch (e) { /* ignore */ }
        }
    });
})();

