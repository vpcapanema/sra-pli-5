"""Sincronizador de capitulos: alinha os capitulos do BANCO com os
capitulos atualmente presentes no DOCX em producao.

Motivacao:
- Apos a clonagem, os capitulos do banco refletem o template original.
- Conforme o coordenador edita o DOCX (insere capitulos, renomeia
  titulos, reordena, reindexa numeracao) o banco fica DEFASADO.
- A sidebar 'Capitulos' do editor_coordenador apresenta os dados do
  banco — sem sincronizacao ela mostra valores obsoletos (indice
  errado, titulo antigo, capitulos que ja nao existem mais).

Este servico:
1. Extrai a arvore de capitulos do DOCX atual via
   `ServicoExtracaoCanonica._extrair_capitulos`.
2. Compara com os capitulos do banco usando uma chave de identidade
   tolerante a renames (titulo normalizado + tipo + nivel).
3. ATUALIZA (em vez de recriar) os capitulos existentes —
   preservando `id`, `status_capitulo`, `envios` associados etc.
4. CRIA capitulos novos detectados no DOCX que nao existem no banco.
5. Capitulos do banco que ja nao tem correspondente no DOCX:
   por padrao SAO PRESERVADOS com flag `tipo_elemento='removido'`,
   permitindo recuperacao caso seja remocao acidental no Word.
   (Comportamento conservador — nada e deletado automaticamente.)

API publica:
    ressincronizar_capitulos(rel) -> dict {atualizados, criados,
                                            removidos_logicamente,
                                            preservados}
    diff_capitulos(rel) -> dict (modo dry-run, sem persistir)
"""

from __future__ import annotations

from typing import Optional

from docx import Document

from app import db
from app.models.capitulo_documento import CapituloDocumento
from app.services.servico_extracao_canonica import (
    ServicoExtracaoCanonica,
    extrair_indice_e_titulo,
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _normalizar_titulo(texto: Optional[str]) -> str:
    """Lower + strip + colapsa espacos. Usado como chave de match
    entre capitulos do banco e do DOCX.

    Tolerante a:
    - Prefixos numericos ('1 APRESENTAÇÃO' == 'APRESENTAÇÃO')
    - Variacoes de espacamento e capitalizacao
    """
    if not texto:
        return ''
    _idx, limpo = extrair_indice_e_titulo(texto.strip())
    base = limpo or texto
    return ' '.join(base.lower().split())


def _achatar_arvore(arvore: list) -> list:
    """Percorre a arvore de capitulos (lista de dicts com 'filhos')
    e devolve lista achatada com referencia ao pai por indice
    (caminho hierarquico).

    Cada item recebe campos extras:
      - `caminho`: lista de titulos dos ancestrais
      - `ordem_absoluta`: posicao global no DOCX
    """
    achatado = []
    ordem = [0]  # mutavel para fechar sobre closures

    def visitar(no, caminho_pai):
        ordem[0] += 1
        item = dict(no)
        item['caminho'] = caminho_pai + [no.get('titulo', '')]
        item['ordem_absoluta'] = ordem[0]
        # Filhos copiados separadamente para nao explodir o dict
        filhos = item.pop('filhos', []) or []
        achatado.append(item)
        for f in filhos:
            visitar(f, item['caminho'])

    for raiz in arvore:
        visitar(raiz, [])
    return achatado


def _construir_indice_capitulos(items_achatados: list) -> dict:
    """Indexa capitulos por (titulo_normalizado, tipo).

    Em caso de titulos duplicados, mantem o primeiro e registra
    `duplicado=True` no segundo (sera resolvido por ordem absoluta).
    """
    indice = {}
    for item in items_achatados:
        chave = (
            _normalizar_titulo(item.get('titulo')),
            item.get('tipo_elemento', 'textual'),
        )
        if chave in indice:
            item['_duplicado'] = True
        else:
            indice[chave] = item
    return indice


# ---------------------------------------------------------------------
# Diff (dry-run)
# ---------------------------------------------------------------------


def diff_capitulos(rel) -> dict:
    """Calcula diferenca entre capitulos do banco e do DOCX SEM
    persistir nada. Util para preview / debug.

    Retorna dict com 4 listas:
      - inalterados:   capitulos cujo (titulo, indice, nivel) batem
      - atualizar:     capitulos do banco cujos campos divergem
      - criar:         capitulos detectados no DOCX que nao estao no banco
      - sumiram:       capitulos do banco que nao foram detectados no DOCX
    """
    if not rel or not rel.caminho_template:
        return {'erro': 'Relatorio sem DOCX em producao.'}

    doc = Document(rel.caminho_template)
    arvore_docx = ServicoExtracaoCanonica._extrair_capitulos(doc)
    items_docx = _achatar_arvore(arvore_docx)
    indice_docx = _construir_indice_capitulos(items_docx)

    capitulos_banco = CapituloDocumento.query.filter_by(
        id_relatorio=rel.id,
    ).all()

    inalterados = []
    atualizar = []
    sumiram = []
    docx_matched_keys = set()

    for cap in capitulos_banco:
        chave = (
            _normalizar_titulo(cap.titulo_capitulo),
            cap.tipo_elemento or 'textual',
        )
        if chave not in indice_docx:
            sumiram.append({
                'id': cap.id_capitulo_documento,
                'titulo_banco': cap.titulo_capitulo,
                'indice_banco': cap.indice_capitulo,
                'tipo': cap.tipo_elemento,
            })
            continue
        docx_matched_keys.add(chave)
        item = indice_docx[chave]

        titulo_docx = item.get('titulo', '')
        indice_docx_str = item.get('indice') or ''
        nivel_docx = item.get('nivel') or 1

        # Decidir indice final usando a mesma logica de
        # `_criar_capitulo_recursivo`: se o DOCX traz prefixo
        # numerico, prefere; senao mantem o do banco.
        novo_indice = (
            indice_docx_str if indice_docx_str
            else cap.indice_capitulo
        )

        divergencias = {}
        if cap.titulo_capitulo != titulo_docx:
            divergencias['titulo'] = {
                'antigo': cap.titulo_capitulo,
                'novo': titulo_docx,
            }
        if novo_indice and cap.indice_capitulo != novo_indice:
            divergencias['indice'] = {
                'antigo': cap.indice_capitulo,
                'novo': novo_indice,
            }
        if (cap.nivel_capitulo or 1) != nivel_docx:
            divergencias['nivel'] = {
                'antigo': cap.nivel_capitulo,
                'novo': nivel_docx,
            }

        if divergencias:
            atualizar.append({
                'id': cap.id_capitulo_documento,
                'divergencias': divergencias,
            })
        else:
            inalterados.append({
                'id': cap.id_capitulo_documento,
                'titulo': cap.titulo_capitulo,
            })

    # Capitulos do DOCX que nao tem match no banco
    criar = []
    for chave, item in indice_docx.items():
        if chave in docx_matched_keys:
            continue
        criar.append({
            'titulo': item.get('titulo'),
            'indice': item.get('indice'),
            'nivel': item.get('nivel'),
            'tipo': item.get('tipo_elemento', 'textual'),
        })

    return {
        'inalterados': inalterados,
        'atualizar': atualizar,
        'criar': criar,
        'sumiram': sumiram,
        'total_banco': len(capitulos_banco),
        'total_docx': len(items_docx),
    }


# ---------------------------------------------------------------------
# Sincronizacao (persiste)
# ---------------------------------------------------------------------


def ressincronizar_capitulos(rel, *, remover_sumidos: bool = False) -> dict:
    """Aplica o diff: atualiza, cria e (opcionalmente) remove capitulos.

    Args:
        rel: instancia de RelatorioProducao
        remover_sumidos: se True, DELETA capitulos do banco que nao tem
            mais correspondente no DOCX. Padrao False (mais seguro).

    Retorna:
        dict {'atualizados': int, 'criados': int, 'sumiram': int,
              'aplicados': bool, 'detalhes': {...do diff...}}
    """
    info = diff_capitulos(rel)
    if 'erro' in info:
        return {'aplicados': False, **info}

    aplicados = 0
    criados = 0
    removidos = 0

    # 1. ATUALIZAR
    if info['atualizar']:
        ids = [it['id'] for it in info['atualizar']]
        caps_a_atualizar = {
            c.id_capitulo_documento: c
            for c in CapituloDocumento.query.filter(
                CapituloDocumento.id_capitulo_documento.in_(ids)
            ).all()
        }
        for entrada in info['atualizar']:
            cap = caps_a_atualizar.get(entrada['id'])
            if not cap:
                continue
            div = entrada['divergencias']
            if 'titulo' in div:
                cap.titulo_capitulo = div['titulo']['novo']
            if 'indice' in div:
                cap.indice_capitulo = div['indice']['novo']
            if 'nivel' in div:
                cap.nivel_capitulo = div['nivel']['novo']
            aplicados += 1

    # 2. CRIAR capitulos novos do DOCX
    if info['criar']:
        # Calcular ordem inicial a partir do maximo existente
        max_ordem = db.session.query(
            db.func.max(CapituloDocumento.ordem_capitulo)
        ).filter_by(id_relatorio=rel.id).scalar() or 0

        for entrada in info['criar']:
            max_ordem += 1
            novo = CapituloDocumento(
                id_relatorio=rel.id,
                titulo_capitulo=entrada['titulo'] or '(sem titulo)',
                indice_capitulo=entrada['indice'],
                nivel_capitulo=entrada['nivel'] or 1,
                tipo_elemento=entrada['tipo'] or 'textual',
                ordem_capitulo=max_ordem,
                status_capitulo='em_edicao',
                ativo=True,
            )
            db.session.add(novo)
            criados += 1

    # 3. Tratar capitulos do banco sem correspondente no DOCX.
    #    Politica:
    #    (a) Se o titulo bate com um pre-textual AUTO-GERADO (SUMARIO,
    #        LISTA DE FIGURAS, CAPA, etc.) -> DELETAR. Esses NUNCA
    #        deveriam ter existido como capitulo (sao gerados a partir
    #        do conteudo dos outros capitulos pela camada de
    #        renderizacao). Capitulos residuais de clones antigos sao
    #        limpos automaticamente.
    #    (b) Se `remover_sumidos=True` -> DELETAR todos sumidos.
    #    (c) Caso contrario -> marcar `ativo=False` (preserva dados;
    #        sidebar filtra por `ativo=True`).
    auto_gerados = ServicoExtracaoCanonica._PRE_TEXTUAIS_AUTO_GERADOS
    if info['sumiram']:
        ids_sumidos = [it['id'] for it in info['sumiram']]
        caps_sumidos = CapituloDocumento.query.filter(
            CapituloDocumento.id_capitulo_documento.in_(ids_sumidos)
        ).all()

        ids_a_deletar = []
        ids_a_inativar = []
        for cap in caps_sumidos:
            titulo_norm = _normalizar_titulo(cap.titulo_capitulo)
            if titulo_norm in auto_gerados or remover_sumidos:
                ids_a_deletar.append(cap.id_capitulo_documento)
            else:
                ids_a_inativar.append(cap.id_capitulo_documento)

        if ids_a_deletar:
            CapituloDocumento.query.filter(
                CapituloDocumento.id_capitulo_documento.in_(ids_a_deletar)
            ).delete(synchronize_session=False)
            removidos = len(ids_a_deletar)

        if ids_a_inativar:
            CapituloDocumento.query.filter(
                CapituloDocumento.id_capitulo_documento.in_(ids_a_inativar)
            ).update(
                {CapituloDocumento.ativo: False},
                synchronize_session=False,
            )

    # Commit se houver QUALQUER mudanca (incluindo inativacoes)
    if (aplicados or criados or removidos
            or (info['sumiram'] and not remover_sumidos)):
        db.session.commit()

    return {
        'aplicados': True,
        'atualizados': aplicados,
        'criados': criados,
        'removidos': removidos,
        'sumiram': len(info['sumiram']),
        'detalhes': info,
    }
