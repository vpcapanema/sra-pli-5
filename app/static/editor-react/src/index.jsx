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
};
