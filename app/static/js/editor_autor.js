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

    if (typeof SRALogger !== 'undefined') {
        SRALogger.info('editor_autor.js carregado');
    }

    var dataEl = document.getElementById('ea-data');
    if (!dataEl) {
        if (typeof SRALogger !== 'undefined') {
            SRALogger.warn('Elemento ea-data não encontrado');
        }
        return;
    }

    var docxUrl = dataEl.dataset.docxUrl;
    var capsMeus = [];
    try {
        capsMeus = JSON.parse(dataEl.dataset.capsMeus || '[]');
        if (typeof SRALogger !== 'undefined') {
            SRALogger.debug('Capítulos do autor carregados: ' + capsMeus.length);
        }
    } catch (e) {
        console.warn('caps_meus invalido', e);
        if (typeof SRALogger !== 'undefined') {
            SRALogger.error('Erro ao parsear caps_meus', e);
        }
    }

    var mount = document.getElementById('docxEditorMount');
    var capSelect = document.getElementById('ea-cap-select');
    var capLivreSelect = document.getElementById('ea-cap-livre-select');
    var btnAddCapLivre = document.getElementById('ea-add-cap-livre');
    var capsSelecionados = document.getElementById('ea-caps-selecionados');
    var capsHiddenInputs = document.getElementById('ea-caps-hidden-inputs');
    var btnDocxZoomIn = document.getElementById('ea-docx-zoom-in');
    var btnDocxZoomOut = document.getElementById('ea-docx-zoom-out');
    var btnDocxZoomReset = document.getElementById('ea-docx-zoom-reset');
    var docxZoomValue = document.getElementById('ea-docx-zoom-value');

    var currentZoom = 1.0;
    var capitulosEscolhidos = [];

    function inicializarColapsaveis() {
        var triggers = document.querySelectorAll('.ea__collapse-trigger');
        triggers.forEach(function (trigger) {
            trigger.addEventListener('click', function () {
                var wrapper = trigger.closest('.ea__collapse');
                if (!wrapper) return;

                var panel = wrapper.querySelector('.ea__collapse-panel');
                if (!panel) return;

                var vaiAbrir = panel.hasAttribute('hidden');
                panel.toggleAttribute('hidden', !vaiAbrir);
                trigger.setAttribute('aria-expanded', vaiAbrir ? 'true' : 'false');
                wrapper.classList.toggle('is-open', vaiAbrir);
            });
        });
    }

    function atualizarListaCapitulosEscolhidos() {
        if (!capsSelecionados || !capsHiddenInputs) return;
        capsSelecionados.innerHTML = '';
        capsHiddenInputs.innerHTML = '';

        if (!capitulosEscolhidos.length) {
            capsSelecionados.innerHTML = '<li class="ea__selected-empty">' +
                'Nenhum capítulo adicionado.</li>';
            return;
        }

        capitulosEscolhidos.forEach(function (item) {
            var li = document.createElement('li');
            li.className = 'ea__selected-item';
            li.innerHTML = '<span>' + item.label + '</span>' +
                '<button type="button" data-cap-id="' + item.id + '">' +
                '<i class="ph ph-x"></i></button>';
            capsSelecionados.appendChild(li);

            var input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'capitulos';
            input.value = item.id;
            capsHiddenInputs.appendChild(input);
        });
    }

    function inicializarSeletorCapitulosLivres() {
        if (!capLivreSelect || !btnAddCapLivre) return;

        btnAddCapLivre.addEventListener('click', function () {
            var opt = capLivreSelect.options[capLivreSelect.selectedIndex];
            if (!opt || !opt.value) return;
            var jaExiste = capitulosEscolhidos.some(function (item) {
                return item.id === opt.value;
            });
            if (jaExiste) return;

            capitulosEscolhidos.push({
                id: opt.value,
                label: (opt.textContent || '').trim()
            });
            opt.disabled = true;
            capLivreSelect.value = '';
            atualizarListaCapitulosEscolhidos();
        });

        if (capsSelecionados) {
            capsSelecionados.addEventListener('click', function (ev) {
                var btn = ev.target.closest('button[data-cap-id]');
                if (!btn) return;
                var id = btn.dataset.capId;
                capitulosEscolhidos = capitulosEscolhidos.filter(
                    function (item) { return item.id !== id; }
                );
                var opt = capLivreSelect.querySelector(
                    'option[value="' + id + '"]'
                );
                if (opt) opt.disabled = false;
                atualizarListaCapitulosEscolhidos();
            });
        }
    }

    // ======================================================
    // 1. Destaca os capitulos do autor no DOM renderizado.
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
    // 4. Scroll ate o capitulo selecionado
    // ======================================================
    if (capSelect) {
        capSelect.addEventListener('change', function () {
            var capId = this.value;
            if (typeof SRALogger !== 'undefined') {
                SRALogger.info('Capítulo selecionado: ' + capId);
            }
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

    function aplicarZoomDocx() {
        var mountEditor = document.getElementById('docxEditorMount');
        if (!mountEditor) return;
        var alvo = mountEditor.querySelector(
            '.sra-docx-viewer, .sra-docx-editor, .docx-wrapper, [class*="docx"]'
        ) || mountEditor.firstElementChild;
        if (!alvo) return;
        alvo.style.transform = 'scale(' + currentZoom + ')';
        alvo.style.transformOrigin = 'top center';
        alvo.style.width = (100 / currentZoom) + '%';
        if (docxZoomValue) {
            docxZoomValue.textContent = Math.round(currentZoom * 100) + '%';
        }
    }

    function inicializarZoomDocx() {
        function alterar(delta) {
            currentZoom = Math.max(.5, Math.min(1.75, currentZoom + delta));
            aplicarZoomDocx();
        }
        if (btnDocxZoomIn) {
            btnDocxZoomIn.addEventListener('click', function () {
                alterar(.1);
            });
        }
        if (btnDocxZoomOut) {
            btnDocxZoomOut.addEventListener('click', function () {
                alterar(-.1);
            });
        }
        if (btnDocxZoomReset) {
            btnDocxZoomReset.addEventListener('click', function () {
                currentZoom = 1;
                aplicarZoomDocx();
            });
        }
        setTimeout(aplicarZoomDocx, 800);
        setTimeout(aplicarZoomDocx, 1600);
    }

    inicializarColapsaveis();
    inicializarSeletorCapitulosLivres();
    inicializarZoomDocx();
    setTimeout(marcarCapitulosEditaveis, 1500);
    inicializarEnvioContainers();

    if (typeof SRALogger !== 'undefined') {
        SRALogger.info('Editor do autor inicializado');
    }

    // ======================================================
    // Carregar conteúdo dos containers de envio
    // ======================================================
    function inicializarEnvioContainers() {
        var envioData = document.getElementById('ea-envio-data');
        if (!envioData) return;

        var idEnvio = envioData.dataset.idEnvio;
        if (!idEnvio) return;

        // Carregar DOCX original quando o container for aberto
        var docxOriginalTrigger = document.querySelector(
            '[data-collapse-target="ea-preview-docx-original"]'
        );
        if (docxOriginalTrigger) {
            docxOriginalTrigger.addEventListener('click', function () {
                var mount = document.getElementById('ea-docx-original-mount');
                if (!mount || mount.children.length > 0) return; // Já carregado

                carregarDocxOriginal(idEnvio, mount);
            });
        }

        // Carregar segmentos quando o container for aberto
        var segmentosTrigger = document.querySelector('[data-collapse-target="ea-preview-segmentos"]');
        if (segmentosTrigger) {
            segmentosTrigger.addEventListener('click', function () {
                var treeMount = document.getElementById('ea-estrutura-tree');
                if (!treeMount || treeMount.children.length > 0) return;
                carregarSegmentos(idEnvio, treeMount);
            });
        }
    }

    function carregarDocxOriginal(idEnvio, mount) {
        var url = '/api/envios/' + idEnvio + '/docx';
        fetch(url)
            .then(function (res) {
                if (!res.ok) throw new Error('Erro ao carregar DOCX');
                return res.arrayBuffer();
            })
            .then(function (buffer) {
                if (window.docx && window.docx.renderAsync) {
                    return window.docx.renderAsync(buffer, mount);
                }
                throw new Error('docx-preview não disponível');
            })
            .catch(function (err) {
                console.error('Erro ao carregar DOCX original:', err);
                mount.innerHTML = '<p class="ea__panel-text">Erro ao carregar DOCX original.</p>';
            });
    }

    function carregarSegmentos(idEnvio, mount) {
        var url = '/api/envios/' + idEnvio + '/estrutura';
        fetch(url)
            .then(function (res) {
                if (!res.ok) throw new Error('Erro ao carregar estrutura');
                return res.json();
            })
            .then(function (data) {
                if (!data) return;

                var treeMount = document.getElementById('ea-estrutura-tree');
                var contentMount = document.getElementById('ea-estrutura-content');

                if (!treeMount || !contentMount) return;

                // Renderizar árvore de capítulos
                renderizarArvoreCapitulos(data.capitulos || [], treeMount);

                // Renderizar conteúdo preenchido
                renderizarConteudoPreenchido(data, contentMount);
            })
            .catch(function (err) {
                console.error('Erro ao carregar estrutura:', err);
                mount.innerHTML = '<p class="ea__panel-text">Erro ao carregar estrutura.</p>';
            });
    }

    function renderizarArvoreCapitulos(capitulos, mount) {
        mount.innerHTML = '';

        if (!capitulos || capitulos.length === 0) {
            mount.innerHTML = '<p class="ea__panel-text">Nenhum capítulo encontrado.</p>';
            return;
        }

        capitulos.forEach(function (cap) {
            var node = criarNoCapitulo(cap, 1);
            mount.appendChild(node);
        });
    }

    function criarNoCapitulo(cap, nivel) {
        var div = document.createElement('div');
        div.className = 'ea__capitulo-node ea__capitulo-node--level-' + nivel;

        var header = document.createElement('div');
        header.className = 'ea__capitulo-header';
        header.innerHTML = '<span class="ea__capitulo-indice">' +
            (cap.indice || '') + '</span>' +
            '<span class="ea__capitulo-titulo">' + (cap.titulo || '') + '</span>';

        div.appendChild(header);

        // Renderizar filhos (subcapítulos)
        if (cap.filhos && cap.filhos.length > 0) {
            var childrenDiv = document.createElement('div');
            childrenDiv.className = 'ea__capitulo-children';
            cap.filhos.forEach(function (filho) {
                childrenDiv.appendChild(criarNoCapitulo(filho, nivel + 1));
            });
            div.appendChild(childrenDiv);
        }

        return div;
    }

    function renderizarConteudoPreenchido(data, mount) {
        mount.innerHTML = '';

        if (!data.capitulos || data.capitulos.length === 0) {
            mount.innerHTML = '<p class="ea__panel-text">Nenhum conteúdo para exibir.</p>';
            return;
        }

        // Renderizar figuras e tabelas
        if (data.legendas) {
            if (data.legendas.figuras && data.legendas.figuras.total_ocorrencias > 0) {
                var figDiv = document.createElement('div');
                figDiv.style.marginBottom = '1rem';
                figDiv.style.padding = '0.75rem';
                figDiv.style.background = 'white';
                figDiv.style.borderRadius = '6px';
                figDiv.innerHTML = '<h4 style="margin: 0 0 0.5rem 0; font-size: 0.9rem; color: #004b36;">Figuras encontradas</h4>';

                var figInfo = document.createElement('div');
                figInfo.style.fontSize = '0.8rem';
                figInfo.style.color = '#52635e';
                figInfo.innerHTML = '<p>Total: ' + data.legendas.figuras.total_ocorrencias + '</p>';
                if (data.legendas.figuras.estilo_predominante) {
                    figInfo.innerHTML += '<p>Estilo: ' + data.legendas.figuras.estilo_predominante + '</p>';
                }
                if (data.legendas.figuras.exemplos && data.legendas.figuras.exemplos.length > 0) {
                    figInfo.innerHTML += '<p>Exemplos: ' + data.legendas.figuras.exemplos.join(', ') + '</p>';
                }
                figDiv.appendChild(figInfo);
                mount.appendChild(figDiv);
            }

            if (data.legendas.tabelas && data.legendas.tabelas.total_ocorrencias > 0) {
                var tabDiv = document.createElement('div');
                tabDiv.style.marginBottom = '1rem';
                tabDiv.style.padding = '0.75rem';
                tabDiv.style.background = 'white';
                tabDiv.style.borderRadius = '6px';
                tabDiv.innerHTML = '<h4 style="margin: 0 0 0.5rem 0; font-size: 0.9rem; color: #004b36;">Tabelas encontradas</h4>';

                var tabInfo = document.createElement('div');
                tabInfo.style.fontSize = '0.8rem';
                tabInfo.style.color = '#52635e';
                tabInfo.innerHTML = '<p>Total: ' + data.legendas.tabelas.total_ocorrencias + '</p>';
                if (data.legendas.tabelas.estilo_predominante) {
                    tabInfo.innerHTML += '<p>Estilo: ' + data.legendas.tabelas.estilo_predominante + '</p>';
                }
                if (data.legendas.tabelas.exemplos && data.legendas.tabelas.exemplos.length > 0) {
                    tabInfo.innerHTML += '<p>Exemplos: ' + data.legendas.tabelas.exemplos.join(', ') + '</p>';
                }
                tabDiv.appendChild(tabInfo);
                mount.appendChild(tabDiv);
            }
        }

        // Renderizar sequência linear de capítulos
        data.capitulos.forEach(function (cap) {
            var capDiv = document.createElement('div');
            capDiv.style.marginBottom = '1rem';
            capDiv.style.padding = '0.75rem';
            capDiv.style.background = 'white';
            capDiv.style.borderRadius = '6px';

            capDiv.innerHTML = '<h4 style="margin: 0 0 0.5rem 0; font-size: 0.9rem; color: #004b36;">' +
                (cap.indice || '') + ' ' + (cap.titulo || '') + '</h4>';

            if (cap.nivel) {
                var nivelDiv = document.createElement('div');
                nivelDiv.style.fontSize = '0.8rem';
                nivelDiv.style.color = '#52635e';
                nivelDiv.innerHTML = 'Nível: ' + cap.nivel;
                capDiv.appendChild(nivelDiv);
            }

            mount.appendChild(capDiv);
        });
    }
})();
