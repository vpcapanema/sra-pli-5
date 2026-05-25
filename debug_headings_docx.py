"""Lista todos os parágrafos com estilo Heading do DOCX em produção
para entender o casamento de títulos."""
import sys

from docx import Document

from app import create_app
from app.models.relatorio_producao import RelatorioProducao


def main():
    app = create_app()
    with app.app_context():
        id_rel = int(sys.argv[1]) if len(sys.argv) > 1 else 7
        rel = RelatorioProducao.query.get(id_rel)
        doc = Document(rel.caminho_template)
        print(f'Arquivo: {rel.caminho_template}\n')
        for i, p in enumerate(doc.paragraphs):
            estilo = p.style.name if p.style else ''
            if estilo and 'eading' in estilo:
                print(f'[{i:>4}] estilo={estilo!r:20s} '
                      f'texto={p.text[:80]!r}')


if __name__ == '__main__':
    main()
