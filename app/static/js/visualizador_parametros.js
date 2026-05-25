/* ==========================================================================
   Inspetor de Parâmetros Canônicos — JS  (3 abas)
   ========================================================================== */
(function () {
    'use strict';

    if (typeof SRALogger !== 'undefined') {
        SRALogger.info('visualizador_parametros.js carregado');
    }

    const vpDataScript = document.getElementById('vpData');
    if (!vpDataScript) {
        if (typeof SRALogger !== 'undefined') {
            SRALogger.warn('Elemento vpData não encontrado');
        }
        return;
    }

    const D = JSON.parse(vpDataScript.textContent) || {};
    const macro = D.macro || [];
    const capitulos = D.capitulos || [];
    const fmt = D.formatacao || {};
    const docxContainer = document.getElementById('docxContainer');
    const pagesContainer = document.getElementById('vpPages');

    if (typeof SRALogger !== 'undefined') {
        SRALogger.debug('Dados carregados: ' + macro.length + ' macros, ' + capitulos.length + ' capítulos');
    }

    // Estado inicial: documento visível, páginas ocultas
    if (docxContainer) docxContainer.style.display = 'flex';
    if (pagesContainer) pagesContainer.style.display = 'none';

    const TIPO_LABEL = {
        capa: 'Capa', pre_textual: 'Pré-textuais',
        textual: 'Textuais', pos_textual: 'Pós-textuais'
    };
    let activeTab = 'documento';

    function mm(v) { return v + 'mm'; }

    // ---- helpers ----
    function el(tag, cls, html) {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (html !== undefined) e.innerHTML = html;
        return e;
    }
    function fmtTag(label, value) {
        return '<span class="vp__fmt-tag"><b>' + label + '</b> '
            + (value != null ? value : '—') + '</span>';
    }
    function findEstiloRaw(id) {
        const arr = fmt.estilos_paragrafo || [];
        for (let i = 0; i < arr.length; i++) {
            if (arr[i].style_id === id || arr[i].nome === id)
                return arr[i];
        }
        return null;
    }
    function getEstilo(id) {
        const est = findEstiloRaw(id);
        if (!est) return null;
        // Resolve inheritance chain
        const merged = {};
        const chain = [];
        let cur = est;
        const seen = {};
        while (cur && !seen[cur.style_id]) {
            chain.unshift(cur);
            seen[cur.style_id] = true;
            cur = cur.base_style
                ? findEstiloRaw(cur.base_style) : null;
        }
        const props = [
            'fonte_nome', 'fonte_tamanho_pt', 'negrito',
            'italico', 'sublinhado', 'cor_rgb', 'alinhamento',
            'espacamento_antes_pt', 'espacamento_depois_pt',
            'entre_linhas', 'recuo_esquerda_cm',
            'recuo_direita_cm', 'recuo_primeira_linha_cm'
        ];
        for (let i = 0; i < chain.length; i++) {
            for (let j = 0; j < props.length; j++) {
                const p = props[j];
                if (chain[i][p] != null) merged[p] = chain[i][p];
            }
        }
        merged.nome = est.nome;
        merged.style_id = est.style_id;
        return merged;
    }
    function alignMap(a) {
        if (!a) return '';
        const m = {
            'LEFT (0)': 'left', 'CENTER (1)': 'center',
            'RIGHT (2)': 'right', 'JUSTIFY (3)': 'justify'
        };
        return m[a] || '';
    }
    function applyCss(node, est) {
        if (!est) return;
        if (est.fonte_nome)
            node.style.fontFamily = '"' + est.fonte_nome + '", serif';
        if (est.fonte_tamanho_pt)
            node.style.fontSize = est.fonte_tamanho_pt + 'pt';
        if (est.negrito) node.style.fontWeight = 'bold';
        if (est.italico) node.style.fontStyle = 'italic';
        if (est.cor_rgb) node.style.color = '#' + est.cor_rgb;
        const al = alignMap(est.alinhamento);
        if (al) node.style.textAlign = al;
        if (est.espacamento_antes_pt)
            node.style.marginTop = est.espacamento_antes_pt + 'pt';
        if (est.espacamento_depois_pt)
            node.style.marginBottom = est.espacamento_depois_pt + 'pt';
        if (est.entre_linhas && typeof est.entre_linhas === 'number')
            node.style.lineHeight = String(est.entre_linhas);
        if (est.recuo_esquerda_cm)
            node.style.marginLeft = est.recuo_esquerda_cm + 'cm';
        if (est.recuo_primeira_linha_cm)
            node.style.textIndent = est.recuo_primeira_linha_cm + 'cm';
    }

    // ---- section helpers ----
    function getSecao(idx) {
        const secoes = fmt.secoes || [];
        return secoes[idx] || secoes[0] || {
            largura_pagina_mm: 210, altura_pagina_mm: 297,
            margem_top_mm: 25, margem_right_mm: 30,
            margem_bottom_mm: 20, margem_left_mm: 30
        };
    }
    function getSectionForBloco(bloco) {
        if (!bloco) return getSecao(0);
        const indices = bloco.secoes_indices || [];
        return indices.length ? getSecao(indices[0]) : getSecao(0);
    }

    // ---- highlight in preview ----
    function clearHighlights() {
        pagesContainer.querySelectorAll('.vp-highlight').forEach(
            function (e) { e.classList.remove('vp-highlight'); }
        );
        document.querySelectorAll(
            '.vp__macro-block.active, .vp__tree-node.active, '
            + '.vp__fmt-card.active'
        ).forEach(function (e) { e.classList.remove('active'); });
    }
    function highlightBlock(key) {
        clearHighlights();
        const targets = pagesContainer.querySelectorAll(
            '[data-block="' + key + '"]'
        );
        targets.forEach(function (t) {
            t.classList.add('vp-highlight');
        });
        if (targets.length) {
            targets[0].scrollIntoView({
                behavior: 'smooth', block: 'center'
            });
        }
    }

    // ==============================================================
    // PAGE CREATION — Word-like pages
    // ==============================================================
    let pageCounter = 0;

    function createPage(secao, secIdx, showBadge) {
        pageCounter++;
        const w = secao.largura_pagina_mm || 210;
        const h = secao.altura_pagina_mm || 297;
        const mt = secao.margem_top_mm || 25;
        const mr = secao.margem_right_mm || 30;
        const mb = secao.margem_bottom_mm || 20;
        const ml = secao.margem_left_mm || 30;

        const pg = el('div', 'vp__page');
        pg.style.width = mm(w);
        pg.style.height = mm(h);
        pg.style.paddingTop = mm(mt);
        pg.style.paddingRight = mm(mr);
        pg.style.paddingBottom = mm(mb);
        pg.style.paddingLeft = mm(ml);

        // Margin guide (dashed inner border)
        const guide = el('div', 'vp__page-margin-guide');
        guide.style.position = 'absolute';
        guide.style.top = mm(mt);
        guide.style.right = mm(mr);
        guide.style.bottom = mm(mb);
        guide.style.left = mm(ml);
        guide.style.border = '1px dashed rgba(100,149,237,.25)';
        guide.style.pointerEvents = 'none';
        guide.style.zIndex = '0';
        pg.appendChild(guide);

        if (showBadge !== false) {
            const badge = el('div', 'vp__page-section-badge',
                'Seção ' + (secIdx + 1) + ' · '
                + Math.round(w) + '×' + Math.round(h) + 'mm'
                + ' · M: ' + mt.toFixed(1) + '/'
                + mr.toFixed(1) + '/' + mb.toFixed(1) + '/'
                + ml.toFixed(1)
                + (secao.orientacao === 'landscape' ? ' ↔' : ''));
            pg.appendChild(badge);
        }

        const num = el('div', 'vp__page-number',
            String(pageCounter));
        pg.appendChild(num);

        pagesContainer.appendChild(pg);
        return pg;
    }

    // ==============================================================
    // DOCX-PREVIEW — shared fetch + render
    // ==============================================================
    let docxBlob = null; // cached blob

    function fetchDocx(cb) {
        if (docxBlob) { cb(docxBlob); return; }
        const url = D.docxUrl;
        if (!url) {
            cb(null);
            return;
        }
        const xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);
        xhr.responseType = 'arraybuffer';
        xhr.onload = function () {
            if (xhr.status === 200) {
                docxBlob = xhr.response;
                cb(docxBlob);
            } else {
                cb(null);
            }
        };
        xhr.onerror = function () { cb(null); };
        xhr.send();
    }

    function renderDocxPreview(container, opts) {
        fetchDocx(function (blob) {
            if (!blob) {
                container.innerHTML =
                    '<p style="padding:20px;color:#999">'
                    + 'DOCX não disponível.</p>';
                return;
            }
            // eslint-disable-next-line no-undef
            docx.renderAsync(blob, container, null, opts || {
                className: 'vp-docx',
                inWrapper: true,
                ignoreWidth: false,
                ignoreHeight: false,
                ignoreFonts: false,
                breakPages: true,
                renderHeaders: true,
                renderFooters: true,
                renderFootnotes: true,
                debug: false,
            });
        });
    }

    // ==============================================================
    // TAB: DOCUMENTO — real DOCX via docx-preview (read-only)
    // ==============================================================
    function renderTabDocumento() {
        docxContainer.innerHTML =
            '<div class="vp__docx-loading">'
            + '<i class="ph ph-spinner"></i> Carregando documento…'
            + '</div>';
        renderDocxPreview(docxContainer, {
            useBase64URL: false,
            renderChanges: false,
            experimental: false
        });
    }

    // ==============================================================
    // TAB: ESTRUTURA MACRO — pages with real block titles
    // ==============================================================
    function renderTabMacro() {
        pagesContainer.innerHTML = '';
        pageCounter = 0;

        if (!macro.length) {
            const pg0 = createPage(getSecao(0), 0);
            pg0.appendChild(el('p', '',
                '<em>Nenhum dado macro extraído.</em>'));
            return;
        }

        macro.forEach(function (bloco) {
            const sec = getSectionForBloco(bloco);
            const secIdx = (bloco.secoes_indices || [0])[0] || 0;
            const pg = createPage(sec, secIdx);
            pg.setAttribute('data-block', 'macro.' + bloco.tipo);

            const lbl = el('div',
                'vp-label vp-label--' + bloco.tipo,
                (TIPO_LABEL[bloco.tipo] || bloco.tipo)
                    .toUpperCase());
            pg.appendChild(lbl);

            const title = el('div', 'vp__macro-page-title');
            title.innerHTML = '<strong>'
                + (TIPO_LABEL[bloco.tipo] || bloco.tipo)
                + '</strong>';
            if (bloco.titulos && bloco.titulos.length) {
                const ul = el('ul', '');
                ul.style.textAlign = 'left';
                ul.style.marginTop = '16px';
                ul.style.fontSize = '10pt';
                ul.style.lineHeight = '2';
                ul.style.color = '#333';
                bloco.titulos.forEach(function (t) {
                    ul.appendChild(el('li', '', t));
                });
                title.appendChild(ul);
            }
            const nPar = bloco.fim_paragrafo
                - bloco.inicio_paragrafo + 1;
            const meta = el('div', '');
            meta.style.marginTop = '12px';
            meta.style.fontSize = '8pt';
            meta.style.color = '#999';
            meta.textContent = nPar + ' parágrafos (§'
                + bloco.inicio_paragrafo + '–'
                + bloco.fim_paragrafo + ')';
            title.appendChild(meta);
            pg.appendChild(title);
        });
    }

    // ==============================================================
    // TAB: CAPÍTULOS — tree diagram on one page
    // ==============================================================
    function renderTabCapitulos() {
        pagesContainer.innerHTML = '';
        pageCounter = 0;

        const sec0 = getSecao(0);
        const pg = createPage(sec0, 0, false);
        pg.classList.add('vp__cap-tree-page');

        const lbl = el('div', 'vp-label vp-label--textual',
            'ÁRVORE DE CAPÍTULOS');
        pg.appendChild(lbl);
        pg.appendChild(el('div', '', '&nbsp;'));

        buildTreeOnPage(pg, capitulos, '', 1);

        if (!capitulos.length) {
            pg.appendChild(el('p', '',
                '<em>Nenhum capítulo extraído.</em>'));
        }
    }

    function buildTreeOnPage(pg, caps, numPrefix, level) {
        for (let i = 0; i < caps.length; i++) {
            const cap = caps[i];
            const num = numPrefix + (i + 1);
            const lvlCls = 'cap-item cap-level-' + level;
            const item = el('div', lvlCls);
            item.setAttribute('data-block',
                'cap.' + numPrefix.replace(/\./g, '') + i);
            item.innerHTML =
                '<span class="cap-num">' + num + '</span>'
                + '<span class="cap-title">'
                + cap.titulo + '</span>';
            pg.appendChild(item);

            if (cap.filhos && cap.filhos.length) {
                buildTreeOnPage(
                    pg, cap.filhos, num + '.', level + 1);
            }
        }
    }

    // ==============================================================
    // Tab switcher
    // ==============================================================
    function switchTab(tab) {
        activeTab = tab;
        document.querySelectorAll('.vp__tab').forEach(
            function (btn) {
                btn.classList.toggle('active',
                    btn.getAttribute('data-tab') === tab);
            });
        // Toggle containers
        if (tab === 'documento') {
            if (docxContainer) docxContainer.style.display = 'flex';
            if (pagesContainer) pagesContainer.style.display = 'none';
        } else {
            if (docxContainer) docxContainer.style.display = 'none';
            if (pagesContainer) {
                pagesContainer.style.display = 'flex';
                pagesContainer.style.zoom = '0.55';
            }
        }
        if (tab === 'documento') renderTabDocumento();
        else if (tab === 'macro') renderTabMacro();
        else if (tab === 'capitulos') renderTabCapitulos();
    }
    document.querySelectorAll('.vp__tab').forEach(
        function (btn) {
            btn.addEventListener('click', function () {
                switchTab(btn.getAttribute('data-tab'));
            });
        });

    // Helpers to find macro blocks
    function findBloco(tipo) {
        for (let i = 0; i < macro.length; i++) {
            if (macro[i].tipo === tipo) return macro[i];
        }
        return null;
    }
    function findBlocoSecIdx(tipo) {
        const b = findBloco(tipo);
        return b && b.secoes_indices && b.secoes_indices.length
            ? b.secoes_indices[0] : 0;
    }

    // ==============================================================
    // 1. MACRO — inspector timeline
    // ==============================================================
    function buildMacroTimeline() {
        const tl = document.getElementById('macroTimeline');
        if (!tl) return;
        tl.innerHTML = '';
        macro.forEach(function (bloco) {
            const nPar = bloco.fim_paragrafo
                - bloco.inicio_paragrafo + 1;
            let secInfo = '';
            if (bloco.secoes_indices && bloco.secoes_indices.length) {
                secInfo = ' · Seções: '
                    + bloco.secoes_indices.map(function (si) {
                        return si + 1;
                    }).join(', ');
            }
            const card = el('div', 'vp__macro-block');
            card.innerHTML =
                '<div class="vp__macro-bar vp__macro-bar--'
                    + bloco.tipo + '"></div>'
                + '<div class="vp__macro-info">'
                +   '<div class="vp__macro-tipo">'
                +       (TIPO_LABEL[bloco.tipo] || bloco.tipo)
                +   '</div>'
                +   '<div class="vp__macro-meta">'
                +       nPar + ' parágrafos (§'
                +       bloco.inicio_paragrafo + '–'
                +       bloco.fim_paragrafo + ')' + secInfo
                +   '</div>'
                +   (bloco.titulos && bloco.titulos.length
                        ? '<div class="vp__macro-titulos">'
                          + bloco.titulos.slice(0, 5).join(' · ')
                          + '</div>'
                        : '')
                + '</div>';
            card.addEventListener('click', function () {
                card.classList.toggle('active');
                highlightBlock('macro.' + bloco.tipo);
            });
            tl.appendChild(card);
        });
    }

    // ==============================================================
    // 2. CAPÍTULOS — inspector tree
    // ==============================================================
    function buildCapTree() {
        const tree = document.getElementById('capTree');
        if (!tree) return;
        tree.innerHTML = '';
        renderTree(tree, capitulos, '', '');
    }
    function renderTree(container, caps, prefix, numPrefix) {
        for (let i = 0; i < caps.length; i++) {
            const cap = caps[i];
            const key = 'cap.' + prefix + i;
            const num = numPrefix + (i + 1);
            const node = el('div', 'vp__tree-node');
            node.innerHTML =
                '<span class="vp__tree-level">H'
                + cap.nivel + '</span>'
                + '<span class="vp__tree-title">'
                + num + '  ' + cap.titulo + '</span>';
            node.setAttribute('data-cap-key', key);
            node.addEventListener('click', (function (k, n) {
                return function () {
                    n.classList.toggle('active');
                    highlightBlock(k);
                };
            })(key, node));
            container.appendChild(node);
            if (cap.filhos && cap.filhos.length) {
                const children = el('div', 'vp__tree-children');
                renderTree(children, cap.filhos,
                    prefix + i + '.', num + '.');
                container.appendChild(children);
            }
        }
    }

    // ==============================================================
    // 3. FORMATAÇÃO — inspector cards
    // ==============================================================
    function buildFormatacao() {
        buildSecoes();
        buildEstilosParagrafo();
        buildEstilosCaractere();
        buildNumeracao();
        buildProps();
    }

    function buildSecoes() {
        const body = document.getElementById('subSecoesBody');
        if (!body) return;
        body.innerHTML = '';
        const secoes = fmt.secoes || [];
        if (!secoes.length) {
            body.innerHTML = '<p style="font-size:.75rem;color:#999">'
                + 'Nenhuma seção extraída.</p>';
            return;
        }
        secoes.forEach(function (s, i) {
            const card = el('div', 'vp__fmt-card');
            let parRange = '';
            if (s.inicio_paragrafo !== undefined) {
                parRange = fmtTag('Parágrafos',
                    '§' + s.inicio_paragrafo
                    + '–' + s.fim_paragrafo);
            }
            card.innerHTML =
                '<div class="vp__fmt-card-title">Seção '
                + (i + 1) + '</div>'
                + '<div class="vp__fmt-row">'
                +   fmtTag('Tamanho',
                        Math.round(s.largura_pagina_mm || 0)
                        + '×' + Math.round(s.altura_pagina_mm || 0)
                        + ' mm')
                +   fmtTag('Orientação', s.orientacao || '?')
                +   fmtTag('Colunas', s.colunas || 1)
                +   parRange
                + '</div>'
                + '<div class="vp__fmt-row" style="margin-top:3px">'
                +   fmtTag('Margem T',
                        (s.margem_top_mm || 0).toFixed(1) + ' mm')
                +   fmtTag('R',
                        (s.margem_right_mm || 0).toFixed(1) + ' mm')
                +   fmtTag('B',
                        (s.margem_bottom_mm || 0).toFixed(1) + ' mm')
                +   fmtTag('L',
                        (s.margem_left_mm || 0).toFixed(1) + ' mm')
                + '</div>';
            card.addEventListener('click', function () {
                card.classList.toggle('active');
                highlightBlock('secao.' + i);
            });
            body.appendChild(card);
        });
    }

    function buildEstilosParagrafo() {
        const body = document.getElementById('subEstilosBody');
        if (!body) return;
        body.innerHTML = '';
        const estilos = (fmt.estilos_paragrafo || []).filter(
            function (e) {
                return e.fonte_nome || e.fonte_tamanho_pt;
            }
        );
        if (!estilos.length) {
            body.innerHTML = '<p style="font-size:.75rem;color:#999">'
                + 'Nenhum estilo com fonte definida.</p>';
            return;
        }
        estilos.forEach(function (est) {
            const card = el('div', 'vp__fmt-card');
            card.innerHTML =
                '<div class="vp__fmt-card-title">' + est.nome
                + ' <small style="color:#999">('
                + est.style_id + ')</small></div>'
                + '<div class="vp__fmt-row">'
                +   fmtTag('Fonte', est.fonte_nome)
                +   fmtTag('Tam.', est.fonte_tamanho_pt
                        ? est.fonte_tamanho_pt + 'pt' : '—')
                +   fmtTag('Alinhamento',
                        alignMap(est.alinhamento) || '—')
                +   (est.negrito ? fmtTag('', '<b>N</b>') : '')
                +   (est.italico ? fmtTag('', '<i>I</i>') : '')
                +   (est.cor_rgb
                        ? fmtTag('Cor',
                            '<span style="display:inline-block;'
                            + 'width:10px;height:10px;background:#'
                            + est.cor_rgb + ';border-radius:2px;'
                            + 'vertical-align:middle"></span> #'
                            + est.cor_rgb)
                        : '')
                + '</div>'
                + '<div class="vp__fmt-preview" id="prev-'
                + est.style_id + '">Texto de exemplo com este '
                + 'estilo aplicado.</div>';
            setTimeout(function () {
                const prev = document.getElementById(
                    'prev-' + est.style_id);
                if (prev) applyCss(prev, est);
            }, 0);
            card.addEventListener('click', function () {
                card.classList.toggle('active');
                highlightBlock('estilo.' + est.style_id);
            });
            body.appendChild(card);
        });
    }

    function buildEstilosCaractere() {
        const body = document.getElementById('subCaractereBody');
        if (!body) return;
        body.innerHTML = '';
        const estilos = (fmt.estilos_caractere || []).filter(
            function (e) {
                return e.fonte_nome || e.negrito || e.italico;
            }
        );
        if (!estilos.length) {
            body.innerHTML = '<p style="font-size:.75rem;color:#999">'
                + 'Nenhum estilo de caractere com propriedades.</p>';
            return;
        }
        estilos.forEach(function (est) {
            const card = el('div', 'vp__fmt-card');
            card.innerHTML =
                '<div class="vp__fmt-card-title">'
                + est.nome + '</div>'
                + '<div class="vp__fmt-row">'
                +   fmtTag('Fonte', est.fonte_nome || '—')
                +   fmtTag('Tam.', est.fonte_tamanho_pt
                        ? est.fonte_tamanho_pt + 'pt' : '—')
                +   (est.negrito ? fmtTag('', '<b>N</b>') : '')
                +   (est.italico ? fmtTag('', '<i>I</i>') : '')
                + '</div>';
            body.appendChild(card);
        });
    }

    function buildNumeracao() {
        const body = document.getElementById('subNumeracaoBody');
        if (!body) return;
        body.innerHTML = '';
        const nums = fmt.numeracao || [];
        if (!nums.length) {
            body.innerHTML = '<p style="font-size:.75rem;color:#999">'
                + 'Nenhuma numeração extraída.</p>';
            return;
        }
        nums.forEach(function (num) {
            const card = el('div', 'vp__fmt-card');
            const niveis = (num.niveis || []).map(function (n) {
                return fmtTag('Nv' + n.nivel,
                    (n.formato || '?') + ' "'
                    + (n.texto_nivel || '') + '"');
            }).join('');
            card.innerHTML =
                '<div class="vp__fmt-card-title">Numeração #'
                + num.abstract_num_id + '</div>'
                + '<div class="vp__fmt-row">' + niveis + '</div>';
            body.appendChild(card);
        });
    }

    function buildProps() {
        const body = document.getElementById('subPropsBody');
        if (!body) return;
        body.innerHTML = '';
        const props = fmt.propriedades_documento || {};
        const card = el('div', 'vp__fmt-card');
        card.innerHTML =
            '<div class="vp__fmt-row">'
            +   fmtTag('Título', props.titulo || '—')
            +   fmtTag('Autor', props.autor || '—')
            +   fmtTag('Assunto', props.assunto || '—')
            + '</div>'
            + '<div class="vp__fmt-row" style="margin-top:3px">'
            +   fmtTag('Parágrafos', props.total_paragrafos || 0)
            +   fmtTag('Tabelas', props.total_tabelas || 0)
            +   fmtTag('Seções', props.total_secoes || 0)
            + '</div>';
        body.appendChild(card);
    }

    // ==============================================================
    // Accordion toggles
    // ==============================================================
    document.querySelectorAll('.vp__section-toggle').forEach(
        function (btn) {
            btn.addEventListener('click', function () {
                btn.closest('.vp__section').classList.toggle(
                    'collapsed');
            });
        }
    );
    document.querySelectorAll('.vp__sub-toggle').forEach(
        function (btn) {
            btn.addEventListener('click', function () {
                btn.closest('.vp__sub').classList.toggle('collapsed');
            });
        }
    );

    // ==============================================================
    // Init
    // ==============================================================
    buildMacroTimeline();
    buildCapTree();
    buildFormatacao();
    switchTab('documento');

})();
