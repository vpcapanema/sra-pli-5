# SRA DOCX Editor (React)

Componente React para edição inline de documentos DOCX no editor do coordenador.

## Setup

```bash
cd app/static/editor-react
npm install
npm run build
```

O bundle será gerado em `app/static/js/docx-editor-bundle.js`.

## Desenvolvimento

```bash
npm run dev
```

## Dependências

- **react** / **react-dom** — Framework UI
- **docx-preview** — Renderização de DOCX (carregada via CDN no template)
- **esbuild** — Bundler (rápido, zero config)

## Nota

O bundle só é necessário se quiser habilitar edição inline pelo coordenador.
Sem o bundle, o sistema funciona em modo read-only com preview via docx-preview.
