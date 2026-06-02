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

    function configurarSeletoresTopo() {
        var relSelect = document.getElementById('ea-rel-select');
        var capSelect = document.getElementById('ea-cap-select');
        var data = document.getElementById('ea-editor-data');
        var versaoId = data ? data.getAttribute('data-id-versao') : '';

        if (relSelect) {
            relSelect.addEventListener('change', function () {
                var selectedOption = relSelect.options[relSelect.selectedIndex];
                var url = selectedOption ? selectedOption.getAttribute('data-url') : '';
                if (typeof SRALogger !== 'undefined') {
                    SRALogger.info('[ea-editor-autor] seletor de relatório alterado');
                }
                if (url) {
                    window.location.href = url;
                }
            });
        }

        if (capSelect) {
            capSelect.addEventListener('change', function () {
                var indice = capSelect.value;
                var url = '/relatorio/editor-autor?id_versao=' + encodeURIComponent(versaoId);
                if (typeof SRALogger !== 'undefined') {
                    SRALogger.info('[ea-editor-autor] seletor de capítulo alterado');
                }
                if (indice) {
                    url += '&capitulo=' + encodeURIComponent(indice);
                }
                window.location.href = url;
            });
        }
    }

    function configurarCollapses() {
        var triggers = document.querySelectorAll('[data-collapse-target]');
        triggers.forEach(function (trigger) {
            trigger.addEventListener('click', function () {
                var targetId = trigger.getAttribute('data-collapse-target');
                var panel = document.getElementById(targetId);
                if (!panel) return;

                var expandido = trigger.getAttribute('aria-expanded') === 'true';
                trigger.setAttribute('aria-expanded', expandido ? 'false' : 'true');
                panel.hidden = expandido;
            });
        });
    }

    function configurarCapitulosLivres() {
        var select = document.getElementById('ea-cap-livre-select');
        var addBtn = document.getElementById('ea-add-cap-livre');
        var list = document.getElementById('ea-caps-selecionados');
        var hiddenBox = document.getElementById('ea-caps-hidden-inputs');
        var selecionados = {};

        if (!select || !addBtn || !list || !hiddenBox) return;

        function renderSelecionados() {
            list.innerHTML = '';
            hiddenBox.innerHTML = '';

            var ids = Object.keys(selecionados);
            if (!ids.length) {
                list.innerHTML = '<li class="ea__selected-empty">Nenhum capítulo adicionado.</li>';
                return;
            }

            ids.forEach(function (id) {
                var li = document.createElement('li');
                var removeBtn = document.createElement('button');
                var input = document.createElement('input');

                li.textContent = selecionados[id] + ' ';
                removeBtn.type = 'button';
                removeBtn.textContent = 'Remover';
                removeBtn.addEventListener('click', function () {
                    delete selecionados[id];
                    renderSelecionados();
                });
                li.appendChild(removeBtn);
                list.appendChild(li);

                input.type = 'hidden';
                input.name = 'capitulos';
                input.value = id;
                hiddenBox.appendChild(input);
            });
        }

        addBtn.addEventListener('click', function () {
            var option = select.options[select.selectedIndex];
            if (!option || !option.value) return;
            selecionados[option.value] = option.textContent.replace(/\s+/g, ' ').trim();
            select.value = '';
            renderSelecionados();
        });
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

    function csrfToken() {
        var input = document.querySelector('input[name="csrf_token"]');
        return input ? input.value : '';
    }

    var previewHandles = {};
    var previewZoom = { original: 100, sugerido: 100 };

    function previewUrl(url) {
        return url + (url.indexOf('?') >= 0 ? '&' : '?') + '_t=' + Date.now();
    }

    function montarPreviewDocx(tipo, forceReload) {
        var workbench = document.getElementById('ea-preview-workbench');
        if (!workbench || !window.SRADocxEditor || !window.SRADocxEditor.mountFullViewer) {
            return;
        }
        var mountId = tipo === 'original'
            ? 'ea-upload-original-mount'
            : 'ea-upload-sugerido-mount';
        var mount = document.getElementById(mountId);
        if (!mount) return;
        if (previewHandles[tipo] && window.SRADocxEditor.unmountFullViewer) {
            window.SRADocxEditor.unmountFullViewer(previewHandles[tipo]);
            previewHandles[tipo] = null;
        }
        mount.innerHTML = '<div class="ea__viewer-loading"><i class="ph ph-spinner ph-spin"></i> Carregando...</div>';
        var url = tipo === 'original'
            ? workbench.dataset.originalUrl
            : workbench.dataset.sugeridoUrl;
        previewHandles[tipo] = window.SRADocxEditor.mountFullViewer(mountId, {
            url: forceReload ? previewUrl(url) : url,
            saveUrl: tipo === 'sugerido' ? workbench.dataset.saveUrl : null,
            csrfToken: csrfToken(),
            mode: tipo === 'sugerido' ? 'editing' : 'viewing',
        });
        setTimeout(function () {
            aplicarZoomPreview(tipo, previewZoom[tipo]);
        }, 500);
    }

    function montarPreviewUpload() {
        var workbench = document.getElementById('ea-preview-workbench');
        if (!workbench || !window.SRADocxEditor || !window.SRADocxEditor.mountFullViewer) {
            return;
        }
        montarPreviewDocx('original', false);
        montarPreviewDocx('sugerido', false);
        configurarControlesPreview();
        carregarDiagnosticoPreview(workbench.dataset.diagnosticoUrl);
        configurarModalImportar(workbench.dataset.sugeridoUrl);
        configurarSeletorBiblioteca(workbench);
    }

    function configurarSeletorBiblioteca(workbench) {
        var sel = document.getElementById('ea-sel-biblioteca');
        if (!sel) return;
        var listaUrl = workbench.dataset.bibliotecasUrl;
        var setUrl = workbench.dataset.setBibliotecaUrl;
        var status = document.getElementById('ea-biblioteca-status');

        function setStatus(texto, estado) {
            if (!status) return;
            status.textContent = texto || '';
            status.className = 'ea__biblioteca-status'
                + (estado ? ' ea__biblioteca-status--' + estado : '');
        }

        if (listaUrl) {
            fetch(listaUrl)
                .then(function (resp) { return resp.json(); })
                .then(function (bibs) {
                    (bibs || []).forEach(function (b) {
                        var opt = document.createElement('option');
                        opt.value = b.id;
                        opt.textContent = b.nome;
                        sel.appendChild(opt);
                    });
                    marcarBibliotecaAtual(sel);
                })
                .catch(function () { /* mantem so o padrao */ });
        }

        sel.addEventListener('change', function () {
            var idBib = sel.value || '';
            sel.disabled = true;
            setStatus('Regenerando previa...', 'loading');
            fetch(setUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken(),
                },
                body: JSON.stringify({ biblioteca_id: idBib }),
            })
                .then(function (resp) { return resp.json(); })
                .then(function (dados) {
                    sel.disabled = false;
                    if (!dados.ok) {
                        setStatus(dados.erro || 'Falha ao regenerar.', 'erro');
                        return;
                    }
                    setStatus('Previa atualizada.', 'ok');
                    montarPreviewDocx('sugerido', true);
                    renderDiagnostico(dados.estrutura || {});
                })
                .catch(function () {
                    sel.disabled = false;
                    setStatus('Falha de conexao ao regenerar.', 'erro');
                });
        });
    }

    function marcarBibliotecaAtual(sel) {
        var box = document.getElementById('ea-preview-diagnostico');
        var atual = box && box.getAttribute('data-biblioteca-id');
        if (atual) sel.value = atual;
    }

    function aplicarZoomPreview(tipo, percent) {
        var mountId = tipo === 'original'
            ? 'ea-upload-original-mount'
            : 'ea-upload-sugerido-mount';
        var mount = document.getElementById(mountId);
        if (!mount) return;
        var alvo = mount.querySelector('.sra-docx-viewer')
            || mount.querySelector('.docx-editor')
            || mount.firstElementChild;
        if (!alvo) return;
        alvo.style.transform = 'scale(' + (percent / 100) + ')';
        alvo.style.transformOrigin = 'top center';
        alvo.style.width = percent === 100 ? '' : (10000 / percent) + '%';
    }

    function configurarControlesPreview() {
        document.querySelectorAll('[data-preview-controls]').forEach(function (box) {
            var tipo = box.getAttribute('data-preview-controls');
            var value = box.querySelector('[data-zoom-value]');
            function setZoom(percent) {
                previewZoom[tipo] = Math.max(50, Math.min(200, percent));
                if (value) value.textContent = previewZoom[tipo] + '%';
                aplicarZoomPreview(tipo, previewZoom[tipo]);
            }
            box.querySelectorAll('[data-zoom]').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    var acao = btn.getAttribute('data-zoom');
                    if (acao === 'out') setZoom(previewZoom[tipo] - 10);
                    if (acao === 'in') setZoom(previewZoom[tipo] + 10);
                    if (acao === 'reset') setZoom(100);
                });
            });
            var reload = box.querySelector('[data-reload]');
            if (reload) {
                reload.addEventListener('click', function () {
                    montarPreviewDocx(tipo, true);
                });
            }
        });
    }

    function carregarDiagnosticoPreview(url) {
        var box = document.getElementById('ea-preview-diagnostico');
        if (!box || !url) return;
        fetch(url)
            .then(function (resp) { return resp.json(); })
            .then(function (dados) {
                var estrutura = dados.estrutura || {};
                var caps = estrutura.capitulos || [];
                var arvore = estrutura.arvore_estrutural || [];
                var pendentes = estrutura.renomeacoes_pendentes || [];
                var automaticas = estrutura.renomeacoes_automaticas_pendentes || [];
                box.innerHTML = ''
                    + '<strong>Diagnóstico e elementos extraídos</strong>'
                    + '<div class="ea__diag-grid">'
                    + '<span>Capítulos: <b>' + caps.length + '</b></span>'
                    + '<span>Estrutura: <b>' + arvore.length + '</b></span>'
                    + '<span>Renomeações pendentes: <b>' + pendentes.length + '</b></span>'
                    + '<span>Renomeações automáticas: <b>' + automaticas.length + '</b></span>'
                    + '</div>'
                    + '<pre class="ea__diag-json"></pre>';
                var pre = box.querySelector('pre');
                pre.textContent = JSON.stringify(estrutura, null, 2);
            })
            .catch(function () {
                box.innerHTML = '<strong>Diagnóstico</strong><p>Não foi possível carregar.</p>';
            });
    }

    function configurarModalImportar(sugeridoUrl) {
        var btn = document.getElementById('ea-btnAbrirModalImportar');
        var modal = document.getElementById('ea-modal-importar');
        if (!btn || !modal) return;
        var modalHandle = null;

        function fechar() {
            modal.hidden = true;
            if (modalHandle && window.SRADocxEditor.unmountFullViewer) {
                window.SRADocxEditor.unmountFullViewer(modalHandle);
                modalHandle = null;
            }
        }

        btn.addEventListener('click', function () {
            modal.hidden = false;
            if (!modalHandle && window.SRADocxEditor.mountFullViewer) {
                modalHandle = window.SRADocxEditor.mountFullViewer('ea-modal-sugerido-mount', {
                    url: sugeridoUrl,
                    mode: 'viewing',
                });
            }
        });

        modal.querySelectorAll('[data-modal-close]').forEach(function (el) {
            el.addEventListener('click', fechar);
        });
    }

    /**
     * Inicialização
     */
    document.addEventListener('DOMContentLoaded', function () {
        bindRecarregar();
        bindZoom();
        configurarSeletoresTopo();
        configurarCollapses();
        configurarCapitulosLivres();
        setupAttributionForm();
        montarEditor(false);
        montarPreviewUpload();

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
