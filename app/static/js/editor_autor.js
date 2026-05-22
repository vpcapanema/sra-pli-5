/* ==========================================================================
   Editor do Autor — JS
   Carrega capítulos, permite upload DOCX, preview e salvar
   ========================================================================== */
(function () {
    'use strict';

    var D = window.EDITOR_DATA || {};
    var API = D.apiBase || '/api';
    var idVersao = D.idVersao;
    var idUsuario = D.idUsuario;

    var capList = document.getElementById('capList');
    var capTitulo = document.getElementById('capTitulo');
    var editorArea = document.getElementById('editorArea');
    var btnSalvar = document.getElementById('btnSalvar');
    var btnFinalizar = document.getElementById('btnFinalizar');
    var fileUpload = document.getElementById('fileUpload');

    var capitulos = [];
    var capAtivo = null;
    var docxBuffer = null; // ArrayBuffer do DOCX carregado
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
        } else if (body instanceof ArrayBuffer) {
            xhr.setRequestHeader('Content-Type', 'application/octet-stream');
        }
        if (csrfToken) {
            xhr.setRequestHeader('X-CSRF-Token', csrfToken);
        }
        xhr.onload = function () {
            if (xhr.status >= 200 && xhr.status < 300) {
                var data = xhr.responseText ? JSON.parse(xhr.responseText) : null;
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
        api('GET', '/versoes-trabalho/' + idVersao + '/capitulos', null,
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
        var isMeu = cap.id_responsavel === idUsuario;
        var div = document.createElement('div');
        div.className = 'ew__cap-item'
            + (isSub ? ' ew__cap-item--sub' : '')
            + (capAtivo && capAtivo.id === cap.id ? ' active' : '')
            + (!isMeu ? ' ew__cap-item--readonly' : '');
        div.innerHTML =
            '<span class="ew__cap-status ew__cap-status--'
            + cap.status + '"></span>'
            + '<span>' + cap.titulo + '</span>'
            + (!isMeu && cap.responsavel_nome
                ? ' <small class="ew__cap-owner">'
                  + cap.responsavel_nome + '</small>'
                : '');
        if (isMeu) {
            div.addEventListener('click', function () {
                selecionarCap(cap);
            });
        }
        capList.appendChild(div);
    }

    // ==============================================================
    // Selecionar capítulo
    // ==============================================================

    function selecionarCap(cap) {
        capAtivo = cap;
        capTitulo.textContent = cap.titulo;
        btnSalvar.disabled = true;
        docxBuffer = null;
        renderCapList();

        // Mostrar observação do coordenador se reprovado
        if (cap.status === 'reprovado' && cap.observacao_coordenador) {
            editorArea.innerHTML =
                '<div class="ew__feedback-reprovado">'
                + '<i class="ph ph-warning-circle"></i>'
                + '<strong>Capítulo reprovado</strong>'
                + '<p>' + cap.observacao_coordenador + '</p>'
                + '</div>';
            // Não retornar — continua para carregar conteúdo abaixo
        }

        // Carregar conteúdo existente
        if (cap.tem_conteudo) {
            editorArea.innerHTML =
                '<div class="ew__placeholder">'
                + '<i class="ph ph-spinner"></i>'
                + '<p>Carregando...</p></div>';
            apiBlob('/capitulos/' + cap.id + '/conteudo',
                function (err, buf) {
                    if (err || !buf) {
                        editorArea.innerHTML =
                            '<div class="ew__placeholder">'
                            + '<p>Sem conteúdo.</p></div>';
                        return;
                    }
                    docxBuffer = buf;
                    renderPreview(buf);
                    btnSalvar.disabled = true;
                });
        } else {
            editorArea.innerHTML =
                '<div class="ew__placeholder">'
                + '<i class="ph ph-file-doc"></i>'
                + '<p>Nenhum conteúdo enviado.<br>'
                + 'Faça upload de um DOCX.</p></div>';
        }
    }

    // ==============================================================
    // Preview com docx-preview
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
    // Upload DOCX
    // ==============================================================

    fileUpload.addEventListener('change', function () {
        var file = fileUpload.files[0];
        if (!file || !capAtivo) return;

        var reader = new FileReader();
        reader.onload = function () {
            docxBuffer = reader.result;
            renderPreview(docxBuffer);
            btnSalvar.disabled = false;
        };
        reader.readAsArrayBuffer(file);
        fileUpload.value = '';
    });

    // ==============================================================
    // Salvar conteúdo
    // ==============================================================

    btnSalvar.addEventListener('click', function () {
        if (!capAtivo || !docxBuffer) return;
        btnSalvar.disabled = true;
        btnSalvar.textContent = 'Salvando...';

        api('PUT', '/capitulos/' + capAtivo.id + '/conteudo',
            docxBuffer,
            function (err) {
                btnSalvar.innerHTML =
                    '<i class="ph ph-floppy-disk"></i> Salvar';
                if (err) {
                    toast('Erro ao salvar: ' + err, 'error');
                    btnSalvar.disabled = false;
                } else {
                    capAtivo.tem_conteudo = true;
                    btnSalvar.disabled = true;
                    toast('Conteúdo salvo com sucesso!', 'success');
                }
            });
    });

    // ==============================================================
    // Finalizar capítulo
    // ==============================================================

    btnFinalizar.addEventListener('click', function () {
        if (!capAtivo) return;
        if (capAtivo.status !== 'em_edicao'
            && capAtivo.status !== 'reprovado') {
            toast('Este capítulo não pode ser finalizado.', 'error');
            return;
        }
        if (!confirm(
            'Finalizar o capítulo "'
            + capAtivo.titulo
            + '"? Ele será enviado para revisão do coordenador.'
        )) return;

        api('POST', '/capitulos/' + capAtivo.id + '/finalizar',
            {},
            function (err, data) {
                if (err) { toast('Erro: ' + err, 'error'); return; }
                capAtivo.status = data.status;
                toast('Capítulo finalizado e enviado para revisão!', 'success');
                renderCapList();
            });
    });

    // ==============================================================
    // Init
    // ==============================================================
    fetchCsrf(function () {
        carregarCapitulos();
    });

})();
