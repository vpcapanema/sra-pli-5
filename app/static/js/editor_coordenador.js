/* ==========================================================================
   Editor do Coordenador — JS
   Review, edição inline, aprovar/reprovar, preview completo, exportar
   ========================================================================== */
(function () {
    'use strict';

    var D = window.EDITOR_DATA || {};
    var API = D.apiBase || '/api';
    var idVersao = D.idVersao;

    var capList = document.getElementById('capList');
    var capTitulo = document.getElementById('capTitulo');
    var editorArea = document.getElementById('editorArea');
    var reviewBar = document.getElementById('reviewBar');
    var obsInput = document.getElementById('obsInput');
    var btnAprovar = document.getElementById('btnAprovar');
    var btnReprovar = document.getElementById('btnReprovar');
    var btnPreviewFull = document.getElementById('btnPreviewFull');
    var btnExportar = document.getElementById('btnExportar');

    var capitulos = [];
    var capAtivo = null;
    var csrfToken = '';

    // ==============================================================
    // API helpers
    // ==============================================================

    function toast(msg, tipo) {
        tipo = tipo || 'info';
        var el = document.createElement('div');
        el.className = 'ew__toast ew__toast--' + tipo;
        el.textContent = msg;
        document.body.appendChild(el);
        setTimeout(function () { el.remove(); }, 4000);
    }

    function fetchCsrf(cb) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', API + '/csrf-token', true);
        xhr.onload = function () {
            if (xhr.status === 200) {
                var data = JSON.parse(xhr.responseText);
                csrfToken = data.token;
            }
            if (cb) cb();
        };
        xhr.send();
    }

    function api(method, path, body, cb) {
        var xhr = new XMLHttpRequest();
        xhr.open(method, API + path, true);
        if (body && !(body instanceof ArrayBuffer)) {
            xhr.setRequestHeader('Content-Type', 'application/json');
            body = JSON.stringify(body);
        }
        if (csrfToken) {
            xhr.setRequestHeader('X-CSRF-Token', csrfToken);
        }
        xhr.onload = function () {
            if (xhr.status >= 200 && xhr.status < 300) {
                var data = xhr.responseText
                    ? JSON.parse(xhr.responseText) : null;
                if (cb) cb(null, data);
            } else {
                if (cb) cb(xhr.statusText || 'Erro');
            }
        };
        xhr.onerror = function () { if (cb) cb('Erro de rede'); };
        xhr.send(body || null);
    }

    function apiBlob(path, cb) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', API + path, true);
        xhr.responseType = 'arraybuffer';
        xhr.onload = function () {
            if (xhr.status === 200) cb(null, xhr.response);
            else if (xhr.status === 204) cb(null, null);
            else cb('Erro');
        };
        xhr.onerror = function () { cb('Erro'); };
        xhr.send();
    }

    // ==============================================================
    // Carregar capítulos
    // ==============================================================

    function carregarCapitulos() {
        api('GET', '/versoes-trabalho/' + idVersao + '/capitulos',
            null,
            function (err, data) {
                if (err) return;
                capitulos = data || [];
                renderCapList();
            });
    }

    function renderCapList() {
        capList.innerHTML = '';
        capitulos.forEach(function (cap) {
            renderCapItem(cap, false);
            if (cap.filhos) {
                cap.filhos.forEach(function (f) {
                    renderCapItem(f, true);
                });
            }
        });
    }

    function renderCapItem(cap, isSub) {
        var div = document.createElement('div');
        div.className = 'ew__cap-item'
            + (isSub ? ' ew__cap-item--sub' : '')
            + (capAtivo && capAtivo.id === cap.id ? ' active' : '');
        var label = cap.titulo;
        if (cap.responsavel_nome) {
            label += ' <small style="color:#888">('
                + cap.responsavel_nome + ')</small>';
        }
        div.innerHTML =
            '<span class="ew__cap-status ew__cap-status--'
            + cap.status + '"></span>'
            + '<span>' + label + '</span>';
        div.addEventListener('click', function () {
            selecionarCap(cap);
        });
        capList.appendChild(div);
    }

    // ==============================================================
    // Selecionar capítulo para revisão
    // ==============================================================

    var reactEditorRoot = null;

    function selecionarCap(cap) {
        capAtivo = cap;
        capTitulo.textContent = cap.titulo;
        renderCapList();
        obsInput.value = '';

        // Mostrar review bar se capítulo está finalizado
        if (cap.status === 'finalizado') {
            reviewBar.classList.remove('ew__hidden');
        } else {
            reviewBar.classList.add('ew__hidden');
        }

        // Desmontar editor React anterior
        if (reactEditorRoot && window.SRADocxEditor) {
            window.SRADocxEditor.unmount(reactEditorRoot);
            reactEditorRoot = null;
        }

        // Carregar preview ou editor inline
        if (cap.tem_conteudo) {
            editorArea.innerHTML =
                '<div class="ew__placeholder">'
                + '<i class="ph ph-spinner ph-spin"></i>'
                + '<p>Carregando...</p></div>';

            // Se temos o editor React e cap está finalizado, usar edição inline
            if (window.SRADocxEditor && cap.status === 'finalizado') {
                editorArea.innerHTML = '';
                reactEditorRoot = window.SRADocxEditor.mount(
                    'reactEditorMount',
                    {
                        apiBase: API,
                        capituloId: cap.id,
                        csrfToken: csrfToken,
                        readOnly: false
                    }
                );
            } else {
                apiBlob('/capitulos/' + cap.id + '/conteudo',
                    function (err, buf) {
                        if (err || !buf) {
                            editorArea.innerHTML =
                                '<div class="ew__placeholder">'
                                + '<p>Sem conteúdo.</p></div>';
                            return;
                        }
                        renderPreview(buf);
                    });
            }
        } else {
            editorArea.innerHTML =
                '<div class="ew__placeholder">'
                + '<i class="ph ph-file-doc"></i>'
                + '<p>Autor ainda não enviou conteúdo.</p></div>';
        }
    }

    // ==============================================================
    // Preview
    // ==============================================================

    function renderPreview(buffer) {
        editorArea.innerHTML = '';
        // eslint-disable-next-line no-undef
        docx.renderAsync(buffer, editorArea, null, {
            className: 'ew-docx',
            inWrapper: true,
            ignoreWidth: false,
            ignoreHeight: false,
            ignoreFonts: false,
            breakPages: true,
            renderHeaders: true,
            renderFooters: true,
        });
    }

    // ==============================================================
    // Preview completo (documento renderizado inteiro)
    // ==============================================================

    btnPreviewFull.addEventListener('click', function () {
        capAtivo = null;
        capTitulo.textContent = 'Documento Completo (Preview)';
        reviewBar.classList.add('ew__hidden');
        renderCapList();

        editorArea.innerHTML =
            '<div class="ew__placeholder">'
            + '<i class="ph ph-spinner ph-spin"></i>'
            + '<p>Renderizando documento completo...</p></div>';

        apiBlob('/versoes-trabalho/' + idVersao + '/preview-docx',
            function (err, buf) {
                if (err || !buf) {
                    editorArea.innerHTML =
                        '<div class="ew__placeholder">'
                        + '<p>Erro ao gerar preview.</p></div>';
                    return;
                }
                renderPreview(buf);
            });
    });

    // ==============================================================
    // Aprovar / Reprovar
    // ==============================================================

    btnAprovar.addEventListener('click', function () {
        if (!capAtivo) return;
        if (!confirm(
            'Aprovar o capítulo "' + capAtivo.titulo + '"?'
        )) return;

        api('POST', '/capitulos/' + capAtivo.id + '/aprovar', {},
            function (err, data) {
                if (err) { toast('Erro: ' + err, 'error'); return; }
                capAtivo.status = data.status;
                reviewBar.classList.add('ew__hidden');
                toast('Capítulo aprovado!', 'success');
                carregarCapitulos();
            });
    });

    btnReprovar.addEventListener('click', function () {
        if (!capAtivo) return;
        var obs = obsInput.value.trim();
        if (!obs) {
            toast('Informe uma observação para a reprovação.', 'error');
            obsInput.focus();
            return;
        }
        if (!confirm(
            'Reprovar o capítulo "' + capAtivo.titulo + '"?'
        )) return;

        api('POST', '/capitulos/' + capAtivo.id + '/reprovar',
            { observacao: obs },
            function (err, data) {
                if (err) { toast('Erro: ' + err, 'error'); return; }
                capAtivo.status = data.status;
                reviewBar.classList.add('ew__hidden');
                toast('Capítulo reprovado. O autor será notificado.', 'info');
                carregarCapitulos();
            });
    });

    // ==============================================================
    // Exportar DOCX final
    // ==============================================================

    btnExportar.addEventListener('click', function () {
        btnExportar.disabled = true;
        btnExportar.textContent = 'Gerando...';

        var xhr = new XMLHttpRequest();
        xhr.open('POST', API + '/versoes-trabalho/'
            + idVersao + '/renderizar', true);
        xhr.responseType = 'blob';
        xhr.setRequestHeader('Content-Type', 'application/json');
        if (csrfToken) xhr.setRequestHeader('X-CSRF-Token', csrfToken);
        xhr.onload = function () {
            btnExportar.disabled = false;
            btnExportar.innerHTML =
                '<i class="ph ph-download"></i> Exportar DOCX Final';
            if (xhr.status === 200) {
                var blob = xhr.response;
                var url = URL.createObjectURL(blob);
                var a = document.createElement('a');
                a.href = url;
                a.download = 'relatorio_final.docx';
                a.click();
                URL.revokeObjectURL(url);
                toast('Documento exportado com sucesso!', 'success');
            } else {
                toast('Erro ao exportar documento.', 'error');
            }
        };
        xhr.onerror = function () {
            btnExportar.disabled = false;
            btnExportar.innerHTML =
                '<i class="ph ph-download"></i> Exportar DOCX Final';
            toast('Erro de rede ao exportar.', 'error');
        };
        xhr.send('{}');
    });

    // ==============================================================
    // Init
    // ==============================================================
    fetchCsrf(function () {
        carregarCapitulos();
    });

})();
