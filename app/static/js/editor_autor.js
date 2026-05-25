/* ==========================================================================
   Editor do Autor — JS

   Responsabilidades:
     1. Carregar o DOCX inteiro via fetch e renderizar com docx-preview.
     2. Controlar zoom da visualizacao (botoes + / -).
     3. Reagir ao seletor de capitulo: rola ate o capitulo escolhido
        (busca pelo titulo no DOM gerado pelo docx-preview).
     4. Destacar visualmente os capitulos pelos quais o autor logado
        e responsavel (caps_meus passado pelo backend).

   A edicao em si continua sendo via fluxo de upload-de-DOCX por
   capitulo (botao "upload" ao lado de cada capitulo MEU na
   sidebar) — sem mudancas.
   ========================================================================== */
(function () {
    'use strict';

    var dataEl = document.getElementById('ea-data');
    if (!dataEl) return;

    var docxUrl = dataEl.dataset.docxUrl;
    var capsMeus = [];
    try {
        capsMeus = JSON.parse(dataEl.dataset.capsMeus || '[]');
    } catch (e) {
        console.warn('caps_meus invalido', e);
    }

    var mount = document.getElementById('docx-preview-mount');
    var btnZoomIn = document.getElementById('zoom-in');
    var btnZoomOut = document.getElementById('zoom-out');
    var btnZoomReset = document.getElementById('zoom-reset');
    var zoomValue = document.getElementById('zoom-value');
    var capSelect = document.getElementById('ea-cap-select');

    var currentZoom = 1.0;

    // ======================================================
    // 1. Carrega e renderiza o DOCX
    // ======================================================
    function carregarDocx() {
        if (!window.docx || !window.docx.renderAsync) {
            mount.innerHTML = '<div class="ea__viewer-loading">' +
                '<i class="ph ph-warning"></i> ' +
                'Falha ao carregar a biblioteca docx-preview.</div>';
            return;
        }

        fetch(docxUrl, { credentials: 'same-origin' })
            .then(function (r) {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.blob();
            })
            .then(function (blob) {
                mount.innerHTML = '';
                return window.docx.renderAsync(blob, mount, null, {
                    inWrapper: true,
                    ignoreWidth: false,
                    ignoreHeight: false,
                    breakPages: true,
                    experimental: true
                });
            })
            .then(function () {
                marcarCapitulosEditaveis();
            })
            .catch(function (err) {
                console.error('Erro ao carregar DOCX:', err);
                mount.innerHTML = '<div class="ea__viewer-loading">' +
                    '<i class="ph ph-x-circle"></i> ' +
                    'Erro ao carregar o documento: ' + err.message +
                    '</div>';
            });
    }

    // ======================================================
    // 2. Destaca os capitulos do autor no DOM renderizado.
    //    Estrategia: percorre as <option> do seletor que tem
    //    data-editavel="1" e procura o texto do titulo no doc.
    // ======================================================
    function marcarCapitulosEditaveis() {
        if (!capSelect) return;
        var opts = capSelect.querySelectorAll('option[data-editavel="1"]');
        if (!opts.length) return;

        var headings = mount.querySelectorAll(
            'h1, h2, h3, h4, p[class*="Heading"], p[class*="Titulo"]'
        );

        opts.forEach(function (opt) {
            var label = (opt.textContent || '').replace(/★ MEU/i, '').trim();
            if (!label) return;
            for (var i = 0; i < headings.length; i++) {
                var txt = (headings[i].textContent || '').trim();
                if (txt && label.indexOf(txt) !== -1) {
                    headings[i].classList.add('ea-hl-meu');
                    headings[i].setAttribute(
                        'data-cap-id', opt.value || ''
                    );
                    break;
                }
            }
        });
    }

    // ======================================================
    // 3. Zoom
    // ======================================================
    function aplicarZoom() {
        var docWrap = mount.querySelector('.docx-wrapper') || mount;
        docWrap.style.transform = 'scale(' + currentZoom + ')';
        if (zoomValue) {
            zoomValue.textContent = Math.round(currentZoom * 100) + '%';
        }
    }

    if (btnZoomIn) {
        btnZoomIn.addEventListener('click', function () {
            currentZoom = Math.min(currentZoom + 0.1, 2.5);
            aplicarZoom();
        });
    }
    if (btnZoomOut) {
        btnZoomOut.addEventListener('click', function () {
            currentZoom = Math.max(currentZoom - 0.1, 0.5);
            aplicarZoom();
        });
    }
    if (btnZoomReset) {
        btnZoomReset.addEventListener('click', function () {
            currentZoom = 1.0;
            aplicarZoom();
        });
    }

    // ======================================================
    // 4. Scroll ate o capitulo selecionado
    // ======================================================
    if (capSelect) {
        capSelect.addEventListener('change', function () {
            var capId = this.value;
            if (!capId) {
                mount.scrollTop = 0;
                return;
            }
            var alvo = mount.querySelector(
                '[data-cap-id="' + capId + '"]'
            );
            if (alvo) {
                alvo.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    }

    // Boot
    carregarDocx();
})();
