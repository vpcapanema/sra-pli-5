"""
Diagnóstico da árvore de capítulos — simula no backend o que o JS de
colapso vai receber no template `arvore_capitulos.html`.

Uso:
    .\venv\Scripts\python diagnostico_arvore_capitulos.py [id_versao_trabalho]

Se id_versao_trabalho não for informado, usa a versão de trabalho mais
recente.

O script imprime, para cada capítulo:
  - id, nivel, id_capitulo_pai, indice, titulo
E ao final indica:
  - Se a hierarquia está populada via FK (id_capitulo_pai)
  - Quantos capítulos teriam toggle visível
  - A hierarquia inferida pelo fallback (por nivel) caso a FK esteja vazia
"""
from __future__ import annotations

import sys

from app import create_app
from app.models.capitulo_documento import CapituloDocumento
from app.models.relatorio_producao import RelatorioProducao


def _sort_indice(cap):
    idx = cap.indice_capitulo or ''
    try:
        return [int(p) for p in idx.split('.') if p]
    except (ValueError, AttributeError):
        return [9999]


def construir_mapa_filhos_fk(capitulos):
    """Mapeia id_pai -> [filhos] usando a FK id_capitulo_pai."""
    mapa = {}
    for c in capitulos:
        if c.id_capitulo_pai:
            mapa.setdefault(c.id_capitulo_pai, []).append(c)
    return mapa


def construir_mapa_filhos_por_nivel(capitulos):
    """Fallback usado pelo JS quando id_capitulo_pai está vazio.
    Usa pilha sobre nivel_capitulo (lista já ordenada hierarquicamente)."""
    mapa = {}
    pilha = []
    for c in capitulos:
        nivel = c.nivel_capitulo or 1
        while pilha and (pilha[-1].nivel_capitulo or 1) >= nivel:
            pilha.pop()
        if pilha:
            pai = pilha[-1]
            mapa.setdefault(pai.id_capitulo_documento, []).append(c)
        pilha.append(c)
    return mapa


def main():
    app = create_app()
    with app.app_context():
        if len(sys.argv) > 1:
            id_vt = int(sys.argv[1])
            vt = RelatorioProducao.query.get(id_vt)
        else:
            vt = (
                RelatorioProducao.query
                .order_by(RelatorioProducao.id.desc())
                .first()
            )

        if not vt:
            print('Nenhum relatório em produção encontrado.')
            return

        print(f'Relatório em produção: id={vt.id}')
        print('=' * 80)

        capitulos = (
            CapituloDocumento.query
            .filter_by(id_relatorio=vt.id, ativo=True)
            .all()
        )
        capitulos.sort(key=_sort_indice)

        if not capitulos:
            print('Sem capítulos cadastrados.')
            return

        print(f'{"id":>5} {"niv":>3} {"id_pai":>7} {"indice":<10} titulo')
        print('-' * 80)
        for c in capitulos:
            print(
                f'{c.id_capitulo_documento:>5} '
                f'{c.nivel_capitulo or 1:>3} '
                f'{(c.id_capitulo_pai or "-"):>7} '
                f'{(c.indice_capitulo or ""):<10} '
                f'{c.titulo_capitulo[:50]}'
            )
        print()

        # Análise
        total = len(capitulos)
        com_fk = sum(1 for c in capitulos if c.id_capitulo_pai)
        niveis = sorted({(c.nivel_capitulo or 1) for c in capitulos})
        print(f'Total de capítulos: {total}')
        print(f'Com id_capitulo_pai populado: {com_fk}')
        print(f'Níveis distintos: {niveis}')
        print()

        if com_fk:
            print('>>> JS usará o mapa por FK (caminho primário).')
            mapa = construir_mapa_filhos_fk(capitulos)
        else:
            print('>>> JS cairá no fallback por nivel_capitulo.')
            mapa = construir_mapa_filhos_por_nivel(capitulos)

        com_filhos = [c for c in capitulos if mapa.get(c.id_capitulo_documento)]
        print(f'Capítulos que terão toggle visível: {len(com_filhos)}')
        for c in com_filhos:
            filhos = mapa[c.id_capitulo_documento]
            indice = c.indice_capitulo or '-'
            print(f'  [{indice}] {c.titulo_capitulo[:40]} -> {len(filhos)} filho(s)')

        if not com_filhos:
            print()
            print('!!! NENHUM capítulo tem subitens. A tabela é "plana"')
            print('    e portanto não há nada a colapsar. Para testar o')
            print('    colapso é preciso ter capítulos em mais de um nível.')


if __name__ == '__main__':
    main()
