"""
Re-extrai a árvore de capítulos de um relatório existente usando a
lógica atualizada de `ServicoExtracaoCanonica._extrair_capitulos`
(que agora respeita o índice numérico presente no título do heading
no DOCX, ex.: "5.4.6.1 Sistema" -> indice="5.4.6.1").

Uso:
    .\\venv\\Scripts\\python reextrair_capitulos.py <id_relatorio_producao>

ATENÇÃO: deleta os capítulos atuais do relatório informado e cria a
árvore novamente. Use com cuidado em produção. Faz commit ao final.
"""
from __future__ import annotations

import sys

from docx import Document

from app import create_app, db
from app.models.capitulo_documento import CapituloDocumento
from app.models.relatorio_producao import RelatorioProducao
from app.routes.relatorio import _criar_capitulo_recursivo
from app.services.servico_extracao_canonica import ServicoExtracaoCanonica


def main():
    if len(sys.argv) < 2:
        print('Uso: reextrair_capitulos.py <id_relatorio_producao>')
        sys.exit(1)

    id_rel = int(sys.argv[1])
    app = create_app()
    with app.app_context():
        rel = RelatorioProducao.query.get(id_rel)
        if not rel:
            print(f'Relatório {id_rel} não encontrado.')
            sys.exit(1)
        if not rel.caminho_template:
            print('Relatório sem caminho_template definido.')
            sys.exit(1)

        print(f'Relatório: id={rel.id} template={rel.caminho_template}')
        doc = Document(rel.caminho_template)
        arvore = ServicoExtracaoCanonica._extrair_capitulos(doc)
        print(f'Árvore extraída: {len(arvore)} raízes.')

        # Apaga capítulos atuais
        antigos = CapituloDocumento.query.filter_by(
            id_relatorio=rel.id
        ).count()
        CapituloDocumento.query.filter_by(id_relatorio=rel.id).delete()
        db.session.flush()
        print(f'Capítulos antigos removidos: {antigos}')

        ordem_global = 1
        total = 0
        for cap_raiz in arvore:
            _criar_capitulo_recursivo(
                cap_raiz, rel.id, None, ordem_global
            )
            ordem_global += 1
            total += 1

        db.session.commit()
        print(f'Capítulos raiz criados: {total}')

        # Mostrar os 15 primeiros para conferência
        novos = (
            CapituloDocumento.query
            .filter_by(id_relatorio=rel.id)
            .order_by(CapituloDocumento.ordem_capitulo)
            .limit(20)
            .all()
        )
        print()
        print(f'{"id":>5} {"niv":>3} {"indice":<10} titulo')
        for c in novos:
            print(
                f'{c.id_capitulo_documento:>5} '
                f'{c.nivel_capitulo:>3} '
                f'{(c.indice_capitulo or ""):<10} '
                f'{c.titulo_capitulo[:60]}'
            )


if __name__ == '__main__':
    main()
