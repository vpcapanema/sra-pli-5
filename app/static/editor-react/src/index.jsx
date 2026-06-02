/**
 * SRA DOCX Editor - Componente React para edição inline.
 *
 * Renderiza o DOCX em contenteditable e permite que o
 * coordenador faça edições pontuais diretamente no documento.
 *
 * Usa docx-preview para renderizar e envia HTML editado
 * para o backend converter para DOCX.
 */
import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createRoot } from 'react-dom/client';
import { DocxEditor as EigenpalDocxEditor } from '@eigenpal/docx-editor-react';
import '@eigenpal/docx-editor-react/styles.css';

function DocxEditor({ apiBase, capituloId, csrfToken, readOnly }) {
    const containerRef = useRef(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [modificado, setModificado] = useState(false);
    const [salvando, setSalvando] = useState(false);
    const docxBlobRef = useRef(null);

    const carregarConteudo = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const resp = await fetch(
                `${apiBase}/capitulos/${capituloId}/conteudo`
            );
            if (resp.status === 204) {
                setError('Nenhum conteúdo enviado ainda.');
                setLoading(false);
                return;
            }
            if (!resp.ok) throw new Error('Falha ao carregar');

            const blob = await resp.blob();
            docxBlobRef.current = blob;

            // Renderizar com docx-preview
            if (window.docx && containerRef.current) {
                containerRef.current.innerHTML = '';
                await window.docx.renderAsync(
                    blob,
                    containerRef.current,
                    null,
                    {
                        className: 'docx-preview-content',
                        inWrapper: true,
                        ignoreWidth: false,
                        ignoreHeight: true,
                    }
                );

                // Tornar editável se não readOnly
                if (!readOnly) {
                    const wrapper = containerRef.current.querySelector(
                        '.docx-wrapper'
                    );
                    if (wrapper) {
                        wrapper.setAttribute('contenteditable', 'true');
                        wrapper.addEventListener('input', () => {
                            setModificado(true);
                        });
                    }
                }
            }
        } catch (e) {
            setError(e.message || 'Erro desconhecido');
        }
        setLoading(false);
    }, [apiBase, capituloId, readOnly]);

    useEffect(() => {
        if (capituloId) {
            carregarConteudo();
        }
    }, [capituloId, carregarConteudo]);

    const salvarAlteracoes = async () => {
        if (!containerRef.current || salvando) return;
        setSalvando(true);

        try {
            // Captura o HTML editado
            const wrapper = containerRef.current.querySelector('.docx-wrapper');
            if (!wrapper) throw new Error('Wrapper não encontrado');

            const htmlEditado = wrapper.innerHTML;

            // Envia HTML para o backend converter para DOCX
            const resp = await fetch(
                `${apiBase}/capitulos/${capituloId}/conteudo`,
                {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'text/html',
                        'X-CSRF-Token': csrfToken,
                    },
                    body: htmlEditado,
                }
            );
            if (!resp.ok) throw new Error('Falha ao salvar');
            setModificado(false);
        } catch (e) {
            alert('Erro ao salvar: ' + e.message);
        }
        setSalvando(false);
    };

    return (
        <div className="sra-docx-editor">
            {!readOnly && (
                <div className="sra-docx-editor__toolbar">
                    <button
                        className="btn--primary"
                        onClick={salvarAlteracoes}
                        disabled={!modificado || salvando}
                    >
                        {salvando ? 'Salvando...' : 'Salvar Alterações'}
                    </button>
                    {modificado && (
                        <span className="sra-docx-editor__badge">
                            Modificado
                        </span>
                    )}
                </div>
            )}
            {loading && (
                <div className="ew__placeholder">
                    <i className="ph ph-spinner"></i>
                    <p>Carregando documento...</p>
                </div>
            )}
            {error && (
                <div className="ew__placeholder">
                    <i className="ph ph-warning"></i>
                    <p>{error}</p>
                </div>
            )}
            <div
                ref={containerRef}
                className="sra-docx-editor__content"
            />
        </div>
    );
}

/**
 * ErrorBoundary que captura falhas do EigenpalDocxEditor (ex.: schemas
 * ProseMirror rejeitando tabelas com células vazias) e dispara o
 * fallback para docx-preview no componente pai.
 */
class EditorErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false, message: null };
    }
    static getDerivedStateFromError(err) {
        return {
            hasError: true,
            message: (err && err.message) || 'Erro de renderização',
        };
    }
    componentDidCatch(err) {
        if (typeof this.props.onError === 'function') {
            this.props.onError(err);
        }
    }
    render() {
        if (this.state.hasError) return null;
        return this.props.children;
    }
}

/**
 * Visualizador completo do DOCX usando @eigenpal/docx-editor-react.
 * Faz fetch da URL informada, transforma em ArrayBuffer e renderiza
 * o editor em modo "viewing" (leitura).
 */
function FullDocxViewer({ url, mode = 'viewing', saveUrl = null, csrfToken = '' }) {
    const [buffer, setBuffer] = useState(null);
    const [error, setError] = useState(null);
    const [editorFailed, setEditorFailed] = useState(false);
    const [failureMsg, setFailureMsg] = useState('');
    const [dirty, setDirty] = useState(false);
    const [saving, setSaving] = useState(false);
    const editorRef = useRef(null);

    // Modos válidos do @eigenpal/docx-editor-react.
    // Aceitar 'review' como alias legado para 'viewing'.
    const VALID_MODES = ['editing', 'suggesting', 'viewing'];
    const editorMode = VALID_MODES.includes(mode)
        ? mode
        : (mode === 'review' ? 'viewing' : 'viewing');

    useEffect(() => {
        let cancelled = false;
        setBuffer(null);
        setError(null);
        setEditorFailed(false);
        setFailureMsg('');
        fetch(url)
            .then((r) => {
                if (r.status === 204) {
                    throw new Error(
                        'Documento ainda não disponível para este item.'
                    );
                }
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.arrayBuffer();
            })
            .then((buf) => {
                if (cancelled) return;
                if (!buf || buf.byteLength === 0) {
                    setError('Documento vazio ou indisponível.');
                    return;
                }
                setBuffer(buf);
            })
            .catch((err) => {
                if (!cancelled) setError(err.message || 'Erro');
            });
        return () => { cancelled = true; };
    }, [url]);

    if (error) {
        return (
            <div className="ew__placeholder">
                <i className="ph ph-warning"></i>
                <p>Erro ao carregar documento: {error}</p>
            </div>
        );
    }
    if (!buffer) {
        return (
            <div className="sra-docx-viewer__loading">
                <i className="ph ph-spinner ph-spin"></i>
                <span>Carregando documento...</span>
            </div>
        );
    }
    const salvarDocx = async () => {
        if (!saveUrl || !editorRef.current || saving) return;
        setSaving(true);
        try {
            const salvo = await editorRef.current.save({ selective: false });
            if (!salvo) throw new Error('Editor não retornou DOCX.');
            const resp = await fetch(saveUrl, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'X-CSRF-Token': csrfToken,
                },
                body: salvo,
            });
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            setDirty(false);
        } catch (err) {
            alert('Erro ao salvar DOCX: ' + ((err && err.message) || 'erro'));
        }
        setSaving(false);
    };

    if (editorFailed) {
        return (
            <div className="ew__placeholder">
                <i className="ph ph-warning"></i>
                <p>Erro ao renderizar DOCX no editor: {failureMsg}</p>
            </div>
        );
    }

    return (
        <EditorErrorBoundary
            onError={(err) => {
                setFailureMsg((err && err.message) || 'erro de renderização');
                setEditorFailed(true);
            }}
        >
            <div className="sra-docx-viewer">
                {saveUrl && (
                    <div className="sra-docx-editor__toolbar">
                        <button
                            className="btn--primary"
                            onClick={salvarDocx}
                            disabled={!dirty || saving}
                        >
                            {saving ? 'Salvando...' : 'Salvar alterações'}
                        </button>
                        {dirty && (
                            <span className="sra-docx-editor__badge">
                                Alterações não salvas
                            </span>
                        )}
                    </div>
                )}
                <EigenpalDocxEditor
                    ref={editorRef}
                    documentBuffer={buffer}
                    mode={editorMode}
                    readOnly={editorMode === 'viewing'}
                    onChange={() => setDirty(true)}
                    onSave={(salvo) => {
                        if (!saveUrl || !salvo) return;
                        fetch(saveUrl, {
                            method: 'PUT',
                            headers: {
                                'Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                'X-CSRF-Token': csrfToken,
                            },
                            body: salvo,
                        }).then(() => setDirty(false));
                    }}
                    onError={(err) => {
                        setFailureMsg(
                            (err && err.message) || 'erro de renderização'
                        );
                        setEditorFailed(true);
                    }}
                />
            </div>
        </EditorErrorBoundary>
    );
}

// Mount point global — chamado pelo JS do coordenador
window.SRADocxEditor = {
    mount(containerId, props) {
        const el = document.getElementById(containerId);
        if (!el) return;
        const root = createRoot(el);
        root.render(<DocxEditor {...props} />);
        return root;
    },
    unmount(root) {
        if (root) root.unmount();
    },
    mountFullViewer(containerId, props) {
        const el = document.getElementById(containerId);
        if (!el) return null;
        const root = createRoot(el);
        root.render(<FullDocxViewer {...props} />);
        return root;
    },
    unmountFullViewer(root) {
        if (root && typeof root.unmount === 'function') root.unmount();
    },
};
