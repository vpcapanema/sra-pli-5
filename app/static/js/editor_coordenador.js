/* ============================================================
   Editor do Coordenador — JS

   Funcao unica e enxuta:
   - Monta o @eigenpal/docx-editor-react em modo `editing` ou `viewing`
     no container `#docxEditorMount`, carregando o DOCX a partir da URL
     fornecida pelo template (data-docx-url).
   - Botao "Recarregar" remonta o editor (apos qualquer acao do painel
     de comandos, basta navegar de volta e clicar — ou e disparado
     automaticamente apos o redirect pos-acao).

   Acoes do painel (Inserir Sumario, Reindexar, etc.) sao forms POST
   classicos que dao redirect com flash message. Nada de AJAX para
   essas operacoes: a re-renderizacao do DOCX no editor acontece
   naturalmente quando o navegador volta da pagina.
   ============================================================ */
(function () {
    'use strict';

    var dataEl = document.getElementById('editor-coord-data');
    if (!dataEl) {
        console.warn('[editor_coordenador] dados ausentes');
        return;
    }

    var DOCX_URL = dataEl.dataset.docxUrl;
    var MODE = dataEl.dataset.mode || 'editing';
    var MOUNT_ID = 'docxEditorMount';

    var editorHandle = null;

    function montarEditor() {
        var mountEl = document.getElementById(MOUNT_ID);
        if (!mountEl) return;

        // Desmontar handle anterior (se houver)
        if (editorHandle && window.SRADocxEditor
            && window.SRADocxEditor.unmountFullViewer) {
            try {
                window.SRADocxEditor.unmountFullViewer(editorHandle);
            } catch (e) { /* ignore */ }
            editorHandle = null;
        }

        mountEl.innerHTML = ''
            + '<div class="ec__viewer-loading">'
            + '<i class="ph ph-spinner ph-spin"></i> '
            + 'Carregando editor...'
            + '</div>';

        if (!window.SRADocxEditor
            || !window.SRADocxEditor.mountFullViewer) {
            mountEl.innerHTML = ''
                + '<div class="ec__viewer-error">'
                + '<i class="ph ph-warning"></i> '
                + 'Bundle docx-editor não carregou. '
                + 'Verifique a conexão e recarregue a página.'
                + '</div>';
            return;
        }

        // Cache-bust para sempre pegar o DOCX mais recente do servidor
        // (apos uma acao de painel, o disco mudou e o navegador pode
        // ter o anterior em cache).
        var url = DOCX_URL
            + (DOCX_URL.indexOf('?') >= 0 ? '&' : '?')
            + '_t=' + Date.now();

        editorHandle = window.SRADocxEditor.mountFullViewer(MOUNT_ID, {
            url: url,
            mode: MODE,
        });
    }

    function bindRecarregar() {
        var btn = document.getElementById('btnRecarregarViewer');
        if (!btn) return;
        btn.addEventListener('click', function () {
            montarEditor();
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        bindRecarregar();
        montarEditor();
    });

    window.addEventListener('beforeunload', function () {
        if (editorHandle && window.SRADocxEditor
            && window.SRADocxEditor.unmountFullViewer) {
            try {
                window.SRADocxEditor.unmountFullViewer(editorHandle);
            } catch (e) { /* ignore */ }
        }
    });
})();
