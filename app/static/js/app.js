// SRA - JavaScript principal

// Sistema de Logging
if (typeof SRALogger !== 'undefined') {
    SRALogger.info('app.js carregado');
}

// SweetAlert2 — defaults em português
if (typeof Swal !== 'undefined') {
    var _swalOrigFire = Swal.fire.bind(Swal);
    Swal.fire = function (opts) {
        if (typeof opts === 'object' && opts !== null) {
            if (!opts.confirmButtonText) opts.confirmButtonText = 'Confirmar';
            if (!opts.cancelButtonText) opts.cancelButtonText = 'Cancelar';
            if (!opts.denyButtonText) opts.denyButtonText = 'Recusar';
        }
        return _swalOrigFire.apply(Swal, arguments);
    };
}

function sraInit() {
    if (typeof SRALogger !== 'undefined') {
        SRALogger.debug('sraInit() executado');
    }

    // Sidebar toggles
    document.querySelectorAll('.sidebar-menu__toggle').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var group = btn.closest('.sidebar-menu__group');
            group.classList.toggle('open');
            if (typeof SRALogger !== 'undefined') {
                SRALogger.click(btn, 'sidebar-toggle');
            }
        });
    });

    // Password toggle — mostrar/ocultar senha
    var iconeOlho = '<svg viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
    var iconeOlhoFechado = '<svg viewBox="0 0 24 24"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

    document.querySelectorAll('input[type="password"]').forEach(function (input) {
        var wrapper = input.closest('.sra-input') || input.parentElement;
        wrapper.classList.add('sra-input--password');

        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'sra-input__toggle-senha';
        btn.innerHTML = iconeOlho;
        btn.setAttribute('aria-label', 'Mostrar senha');

        btn.addEventListener('click', function () {
            var visivel = input.type === 'text';
            input.type = visivel ? 'password' : 'text';
            btn.innerHTML = visivel ? iconeOlho : iconeOlhoFechado;
            btn.setAttribute('aria-label', visivel ? 'Mostrar senha' : 'Ocultar senha');
            if (typeof SRALogger !== 'undefined') {
                SRALogger.click(btn, 'password-toggle');
            }
        });

        wrapper.appendChild(btn);
    });

    // Table selection — checkbox logic + bulk actions
    document.querySelectorAll('.sra-table-container').forEach(function (container) {
        var selectAll = container.querySelector('.sra-table__select-all');
        var bulkBar = container.querySelector('.sra-table__bulk-actions');
        var countEl = container.querySelector('.sra-table__bulk-count');
        if (!selectAll) return;

        function getRowChecks() {
            return container.querySelectorAll('.sra-table__row-select');
        }

        function updateBulk() {
            var checks = getRowChecks();
            var total = 0;
            checks.forEach(function (c) { if (c.checked) total++; });
            if (bulkBar) {
                bulkBar.hidden = total === 0;
                if (countEl) countEl.textContent = total + ' selecionado' + (total !== 1 ? 's' : '');
            }
            selectAll.checked = checks.length > 0 && total === checks.length;
            selectAll.indeterminate = total > 0 && total < checks.length;
        }

        selectAll.addEventListener('change', function () {
            getRowChecks().forEach(function (c) { c.checked = selectAll.checked; });
            updateBulk();
            if (typeof SRALogger !== 'undefined') {
                SRALogger.info('Selecionar todos: ' + selectAll.checked);
            }
        });

        container.addEventListener('change', function (e) {
            if (e.target.classList.contains('sra-table__row-select')) updateBulk();
        });

        container.addEventListener('click', function (e) {
            var btn = e.target.closest('.sra-bulk-btn');
            if (!btn) return;
            var ids = [];
            getRowChecks().forEach(function (c) { if (c.checked) ids.push(c.value); });
            if (ids.length === 0) return;

            var action = btn.dataset.action;
            var url = btn.dataset.url;

            if (typeof SRALogger !== 'undefined') {
                SRALogger.info('Ação em massa: ' + action + ' para ' + ids.length + ' itens');
            }

            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: 'Confirmar ação',
                    text: action + ' para ' + ids.length + ' item(ns)?',
                    icon: 'question',
                    showCancelButton: true,
                    confirmButtonText: 'Confirmar',
                    cancelButtonText: 'Cancelar'
                }).then(function (result) {
                    if (result.isConfirmed && url) {
                        var form = document.createElement('form');
                        form.method = 'POST';
                        form.action = url;
                        ids.forEach(function (id) {
                            var input = document.createElement('input');
                            input.type = 'hidden';
                            input.name = 'ids[]';
                            input.value = id;
                            form.appendChild(input);
                        });
                        document.body.appendChild(form);
                        form.submit();
                    }
                });
            }
        });
    });

    // Visualizador geral — Quill + fullscreen + save
    document.querySelectorAll('.sra-preview[data-modo="edicao"]').forEach(function (preview) {
        var editorEl = preview.querySelector('#sra-preview-editor');
        var toolbarEl = preview.querySelector('#sra-preview-toolbar');
        if (!editorEl || typeof Quill === 'undefined') return;

        var quill = new Quill(editorEl, {
            theme: 'snow',
            modules: {
                toolbar: {
                    container: toolbarEl
                        ? toolbarEl
                        : [
                            [{ header: [1, 2, 3, false] }],
                            ['bold', 'italic', 'underline', 'strike'],
                            [{ list: 'ordered' }, { list: 'bullet' }],
                            [{ indent: '-1' }, { indent: '+1' }],
                            [{ align: [] }],
                            ['blockquote'],
                            ['clean']
                        ]
                }
            }
        });

        // Toolbar auto-gerada se container vazio
        if (toolbarEl && toolbarEl.children.length === 0) {
            var tb = preview.querySelector('.ql-toolbar');
            if (tb) toolbarEl.appendChild(tb);
        }

        var statusEl = preview.querySelector('.sra-preview__status');
        var wordcountEl = preview.querySelector('.sra-preview__wordcount');

        function updateWordCount() {
            if (!wordcountEl) return;
            var text = quill.getText().trim();
            var words = text ? text.split(/\s+/).length : 0;
            wordcountEl.textContent = words + ' palavra' + (words !== 1 ? 's' : '');
        }
        quill.on('text-change', function () {
            if (statusEl) statusEl.textContent = 'Modificado';
            updateWordCount();
            if (typeof SRALogger !== 'undefined') {
                SRALogger.debug('Quill: texto alterado');
            }
        });
        updateWordCount();

        // Salvar
        var btnSalvar = preview.querySelector('.sra-preview__btn-salvar');
        if (btnSalvar) {
            btnSalvar.addEventListener('click', function () {
                var url = btnSalvar.dataset.url;
                if (!url) return;
                if (statusEl) statusEl.textContent = 'Salvando...';
                var html = quill.root.innerHTML;

                if (typeof SRALogger !== 'undefined') {
                    SRALogger.httpRequest('POST', url, { preview_id: preview.dataset.previewId });
                }

                fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        preview_id: preview.dataset.previewId,
                        conteudo_html: html
                    })
                })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (statusEl) statusEl.textContent = data.ok ? 'Salvo' : 'Erro ao salvar';
                    if (data.ok && typeof Swal !== 'undefined') {
                        Swal.mixin({ toast: true, position: 'top-end', showConfirmButton: false, timer: 2000, timerProgressBar: true })
                            .fire({ icon: 'success', title: 'Conteúdo salvo' });
                    }
                })
                .catch(function () {
                    if (statusEl) statusEl.textContent = 'Erro de conexão';
                });
            });
        }
    });

    // Fullscreen toggle (leitura e edição)
    document.querySelectorAll('.sra-preview__btn-fullscreen').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var preview = btn.closest('.sra-preview');
            preview.classList.toggle('sra-preview--fullscreen');
            var isFs = preview.classList.contains('sra-preview--fullscreen');
            btn.querySelector('svg').innerHTML = isFs
                ? '<polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/>'
                : '<polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/>';
        });
    });

    // Biblioteca formatação — toggle versões
    document.querySelectorAll('.sra-bib-toggle').forEach(function (btn) {
        btn.addEventListener('click', function () {
            var bibId = btn.dataset.bibId;
            document.querySelectorAll('.sra-bib-versoes').forEach(function (card) {
                if (card.dataset.bibId === bibId) {
                    card.hidden = !card.hidden;
                } else {
                    card.hidden = true;
                }
            });
        });
    });

}

// SweetAlert2 toast notifications (flash messages)
function processarFlashMessages() {
    var flashEl = document.getElementById('sra-flash-data');
    if (flashEl && typeof Swal !== 'undefined') {
        var mapa = { erro: 'error', sucesso: 'success', info: 'info', warning: 'warning' };
        var msgs = JSON.parse(flashEl.textContent);
        var toast = Swal.mixin({
            toast: true,
            position: 'top-end',
            showConfirmButton: false,
            timer: 5000,
            timerProgressBar: true,
            didOpen: function (t) {
                t.onmouseenter = Swal.stopTimer;
                t.onmouseleave = Swal.resumeTimer;
            }
        });
        msgs.forEach(function (m) {
            toast.fire({ icon: mapa[m[0]] || 'info', title: m[1] });
        });
        // Remove o nó para evitar reprocessamento em htmx:afterSwap
        flashEl.remove();
    }
}

// Init on page load
document.addEventListener('DOMContentLoaded', function() {
    sraInit();
    processarFlashMessages();
});

// Re-init after HTMX swaps new content
document.addEventListener('htmx:afterSwap', function() {
    sraInit();
    processarFlashMessages();
});
