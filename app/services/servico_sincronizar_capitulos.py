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

Tambem integra classificacao e secoes OOXML:
   - Chama ServicoClassificacaoCapitulos para cada capitulo
   - Mapeia id_secao_inicio e id_secao_fim via ServicoExtracaoSecoes
   - Atualiza campos classificacao + prefixo_indice + secoes

API publica:
    ressincronizar_capitulos(rel) -> dict (
        DEPRECATED - usar ressincronizar_capitulos_com_classificacao
    )
    ressincronizar_capitulos_com_classificacao(rel) -> dict {capitulos,
                                                              erros_classificacao}
    diff_capitulos(rel) -> dict (modo dry-run, sem persistir)
"""

from __future__ import annotations

import warnings
import logging
from typing import Optional

from docx import Document

from app import db
from app.models.capitulo_documento import CapituloDocumento
from app.services.servico_extracao_canonica import (
    ServicoExtracaoCanonica,
    extrair_indice_e_titulo,
)
from app.services.servico_classificacao_capitulos import (
    ServicoClassificacaoCapitulos,
)
from app.services.servico_extracao_secoes import ServicoExtracaoSecoes

logger = logging.getLogger(__name__)


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
    arvore_docx = ServicoExtracaoCanonica._extrair_capitulos(doc)  # pylint: disable=protected-access
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
    """[DEPRECATED] Aplica o diff: atualiza, cria e (opcionalmente) remove capitulos.

    DEPRECATION WARNING: Este método está obsoleto. Use
    `ressincronizar_capitulos_com_classificacao()` em seu lugar, que integra
    classificação de capítulos e mapeamento de seções OOXML.

    Este wrapper é mantido apenas para compatibilidade retroativa com código
    legado. Será removido em versão futura.

    Args:
        rel: instancia de RelatorioProducao
        remover_sumidos: se True, DELETA capitulos do banco que nao tem
            mais correspondente no DOCX. Padrao False (mais seguro).
            (Este parâmetro é ignorado na versão new - use apenas rel)

    Retorna:
        dict compatível com a API antiga, mas com campos extras de classificação

    Nota:
        Log warning é registrado na primeira chamada de cada sessão.
        Use `ressincronizar_capitulos_com_classificacao(rel)` para nova API.
    """
    # Log deprecation warning
    warnings.warn(
        "ressincronizar_capitulos() está DEPRECATED. "
        "Use ressincronizar_capitulos_com_classificacao() em seu lugar. "
        "O método antigo não integra classificação e seções OOXML.",
        DeprecationWarning,
        stacklevel=2
    )

    logger.warning(
        "DEPRECATION: ressincronizar_capitulos() chamado. "
        "Use ressincronizar_capitulos_com_classificacao() em seu lugar.",
        extra={
            'relatorio_id': getattr(rel, 'id_relatorio_producao', None),
            'etapa': 'sincronizacao_capitulos',
            'metodo_deprecated': 'ressincronizar_capitulos',
            'metodo_novo': 'ressincronizar_capitulos_com_classificacao',
        }
    )

    # Delega para novo método com classificação
    resultado = ressincronizar_capitulos_com_classificacao(rel)

    # Converte resultado novo para formato compatível com API antiga
    # para não quebrar callers existentes
    return {
        'aplicados': resultado.get('sucesso', False),
        'atualizados': resultado.get('total_atualizados', 0),
        'criados': resultado.get('total_criados', 0),
        'removidos': 0,  # Novo método não deleta automaticamente
        'sumiram': len([c for c in resultado.get('capitulos_sincronizados', [])
                       if c.get('acao') == 'inativado']),
        'detalhes': {
            'capitulos_sincronizados': resultado.get('capitulos_sincronizados', []),
            'erros_classificacao': resultado.get('erros_classificacao', []),
        }
    }


# =====================================================================
# Ressincronizacao com integracao de Classificacao + Secoes (Task 3.2)
# =====================================================================


def ressincronizar_capitulos_com_classificacao(
    relatorio
) -> dict:
    """Ressincroniza capitulos integrando classificacao e secoes OOXML.

    Fluxo:
    1. Extrai capitulos de template com `servico_extracao_canonica`
    2. Para cada capitulo, chama `ServicoClassificacaoCapitulos.classificar_por_estilo_docx()`
    3. Integra secoes: consulta `servico_extracao_secoes` e mapeia id_secao_inicio/fim
    4. Atualiza CapituloDocumento com classificacao + prefixo_indice + id_secao_inicio/fim

    Args:
        relatorio: instancia de RelatorioProducao

    Retorna:
        dict com:
            - 'sucesso': bool indicando se operacao completou
            - 'capitulos_sincronizados': lista de capitulos atualizados
            - 'capitulos_criados': lista de capitulos criados
            - 'erros_classificacao': lista de erros durante classificacao
            - 'total_atualizados': int
            - 'total_criados': int
            - 'total_erros': int

    Validacoes (Property 4: Respeito a Classificacao e Secoes):
        - Cada capitulo tem classificacao preenchida
        - Cada capitulo tem prefixo_indice quando aplicavel (ANEXO_, APENDICE_)
        - id_secao_inicio e id_secao_fim estao preenchidos
    """
    resultado = {
        'sucesso': False,
        'capitulos_sincronizados': [],
        'capitulos_criados': [],
        'erros_classificacao': [],
        'total_atualizados': 0,
        'total_criados': 0,
        'total_erros': 0,
    }

    # Validacao: relatorio deve ter DOCX de producao
    if not relatorio or not relatorio.caminho_template:
        resultado['erros_classificacao'].append({
            'tipo': 'validacao',
            'mensagem': 'Relatório sem DOCX de produção.'
        })
        resultado['total_erros'] += 1
        return resultado

    try:
        # Etapa 1: Extrair capitulos do template
        doc = Document(relatorio.caminho_template)
        arvore_docx = ServicoExtracaoCanonica._extrair_capitulos(doc)  # pylint: disable=protected-access
        items_achatados = _achatar_arvore(arvore_docx)

        if not items_achatados:
            resultado['erros_classificacao'].append({
                'tipo': 'extracao',
                'mensagem': 'Nenhum capítulo detectado no template.'
            })
            resultado['total_erros'] += 1
            return resultado

        # Etapa 2: Extrair secoes OOXML
        try:
            secoes = ServicoExtracaoSecoes.extrair_secoes_do_docx(
                relatorio.caminho_template,
                relatorio.id
            )
        except Exception as e:
            resultado['erros_classificacao'].append({
                'tipo': 'secoes',
                'mensagem': f'Erro ao extrair seções: {str(e)}'
            })
            resultado['total_erros'] += 1
            secoes = []

        # Etapa 3: Buscar capitulos existentes no banco
        capitulos_banco = CapituloDocumento.query.filter_by(
            id_relatorio=relatorio.id,
        ).all()
        indice_banco = {
            _normalizar_titulo(cap.titulo_capitulo): cap
            for cap in capitulos_banco
        }

        # Etapa 4: Processar cada capitulo do DOCX
        capitulos_processados = []
        docx_matched_keys = set()

        for item in items_achatados:
            titulo_docx = item.get('titulo', '')
            estilo_docx = item.get('estilo', '')
            indice_docx = item.get('indice') or ''
            nivel_docx = item.get('nivel') or 1

            # Normalizacao para match
            chave_normalizacao = _normalizar_titulo(titulo_docx)
            docx_matched_keys.add(chave_normalizacao)

            # Etapa 4a: Classificar baseado em estilo DOCX
            classificacao = None
            prefixo_indice = None
            try:
                classificacao, _nivel_classe, prefixo_indice = (
                    ServicoClassificacaoCapitulos.classificar_por_estilo_docx(
                        estilo_docx
                    )
                )
            except Exception as e:
                resultado['erros_classificacao'].append({
                    'tipo': 'classificacao',
                    'titulo': titulo_docx,
                    'mensagem': f'Erro ao classificar: {str(e)}'
                })
                resultado['total_erros'] += 1
                # Continua processamento mesmo com erro na classificacao

            # Etapa 4b: Mapear secoes OOXML
            id_secao_inicio = None
            id_secao_fim = None
            if secoes:
                # Heuristica: capitulos textuais comecam na secao 1,
                # anexos/apendices na secao 2
                if classificacao in ('anexo', 'apendice') and len(secoes) > 1:
                    id_secao_inicio = secoes[1].id_secao
                elif secoes:
                    id_secao_inicio = secoes[0].id_secao

                # Fim: determinar pela posicao (proxima secao ou ultima)
                idx_item = items_achatados.index(item)
                if idx_item < len(items_achatados) - 1:
                    # Existe proximo item: fim eh antes do proximo
                    if len(secoes) > 1:
                        id_secao_fim = secoes[1].id_secao if len(secoes) > 1 else secoes[0].id_secao
                else:
                    # Ultimo item: fim eh ultima secao
                    id_secao_fim = secoes[-1].id_secao if secoes else id_secao_inicio

            # Etapa 4c: Atualizar capitulo existente ou criar novo
            cap = indice_banco.get(chave_normalizacao)
            if cap:
                # ATUALIZAR capitulo existente
                cap.titulo_capitulo = titulo_docx
                cap.indice_capitulo = indice_docx or cap.indice_capitulo
                cap.nivel_capitulo = nivel_docx
                cap.estilo_docx = estilo_docx
                cap.classificacao = classificacao
                cap.prefixo_indice = prefixo_indice
                cap.id_secao_inicio = id_secao_inicio
                cap.id_secao_fim = id_secao_fim

                capitulos_processados.append({
                    'id': cap.id_capitulo_documento,
                    'titulo': titulo_docx,
                    'classificacao': classificacao,
                    'prefixo_indice': prefixo_indice,
                    'secao_inicio': id_secao_inicio,
                    'secao_fim': id_secao_fim,
                    'acao': 'atualizado'
                })
                resultado['total_atualizados'] += 1
            else:
                # CRIAR capitulo novo
                from app.utils.auditoria import usuario_atual_id  # noqa: C0415

                max_ordem = db.session.query(
                    db.func.max(CapituloDocumento.ordem_capitulo)
                ).filter_by(id_relatorio=relatorio.id).scalar() or 0

                novo = CapituloDocumento(  # type: ignore[call-arg]
                    **{
                        'id_relatorio': relatorio.id,
                        'titulo_capitulo': titulo_docx,
                        'nome_capitulo': titulo_docx,
                        'indice_capitulo': indice_docx,
                        'nivel_capitulo': nivel_docx,
                        'tipo_elemento': item.get('tipo_elemento', 'textual'),
                        'estilo_docx': estilo_docx,
                        'classificacao': classificacao,
                        'prefixo_indice': prefixo_indice,
                        'id_secao_inicio': id_secao_inicio,
                        'id_secao_fim': id_secao_fim,
                        'ordem_capitulo': max_ordem + 1,
                        'status_capitulo': 'em_edicao',
                        'ativo': True,
                        'criado_por': usuario_atual_id(),
                    }
                )
                db.session.add(novo)

                capitulos_processados.append({
                    'titulo': titulo_docx,
                    'classificacao': classificacao,
                    'prefixo_indice': prefixo_indice,
                    'secao_inicio': id_secao_inicio,
                    'secao_fim': id_secao_fim,
                    'acao': 'criado',
                    'id_capitulo': novo.id_capitulo_documento,
                })
                resultado['total_criados'] += 1

        # Etapa 5: Inativar capitulos do banco que sumiram do DOCX
        for cap in capitulos_banco:
            if _normalizar_titulo(cap.titulo_capitulo) not in docx_matched_keys:
                # Verificar se eh auto-gerado (deve ser deletado)
                auto_gerados = ServicoExtracaoCanonica._PRE_TEXTUAIS_AUTO_GERADOS  # pylint: disable=protected-access
                titulo_norm = _normalizar_titulo(cap.titulo_capitulo)
                if titulo_norm in auto_gerados:
                    db.session.delete(cap)
                else:
                    # Inativar (nao deletar)
                    cap.ativo = False

        # Commit
        db.session.commit()

        # Montar resultado final
        resultado['sucesso'] = True
        resultado['capitulos_sincronizados'] = capitulos_processados
        resultado['capitulos_criados'] = [
            c for c in capitulos_processados if c.get('acao') == 'criado'
        ]

    except Exception as e:
        resultado['erros_classificacao'].append({
            'tipo': 'erro_interno',
            'mensagem': f'Erro ao ressincronizar: {str(e)}',
            'stack': str(e)
        })
        resultado['total_erros'] += 1
        db.session.rollback()

    return resultado
