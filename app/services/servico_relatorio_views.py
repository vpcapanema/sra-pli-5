"""Servicos de consulta para telas de relatorio."""
from __future__ import annotations

from sqlalchemy import text

from app import db
from app.models.biblioteca_formatacao import BibliotecaFormatacaoCanonica
from app.models.capitulo_documento import CapituloDocumento
from app.models.dominio import Dominio
from app.models.relatorio_producao import RelatorioProducao
from app.models.usuario import Usuario
from app.services import servico_relatorio_core as relatorio_core
from app.services.servico_acoes_relatorio import listar_por_grupo
from app.services.servico_sincronizar_capitulos import (
    ressincronizar_capitulos_com_classificacao,
)


def listar_panorama_relatorios():
    """Lista relatorios consolidados da view de panorama."""
    conn = db.session.connection()
    result = conn.execute(text("""
        SELECT * FROM vw_todos_relatorios
        ORDER BY data_criacao DESC
    """))
    return [
        {
            "id": row.id,
            "tipo_relatorio": row.tipo_relatorio,
            "codigo": row.codigo,
            "titulo": row.titulo,
            "numero_medicao": row.numero_medicao,
            "mes_referencia": row.mes_referencia,
            "ano_referencia": row.ano_referencia,
            "periodo_inicio": row.periodo_inicio,
            "periodo_fim": row.periodo_fim,
            "status_codigo": row.status_codigo,
            "status_descricao": row.status_descricao,
            "data_criacao": row.data_criacao,
            "versao": row.versao,
            "criador_nome": row.criador_nome,
        }
        for row in result
    ]


def obter_contexto_detalhe_versao(id_versao):
    """Monta o contexto da tela de detalhe da versao de trabalho."""
    versao = relatorio_core.obter_versao_trabalho(id_versao)
    if not versao:
        return None

    capitulos_flat = CapituloDocumento.query.filter_by(
        id_relatorio=id_versao
    ).all()
    capitulos_flat.sort(key=_sort_indice_capitulo)

    return {
        "versao_trabalho": versao,
        "capitulos": relatorio_core.listar_capitulos(id_versao),
        "capitulos_flat": capitulos_flat,
        "bibliotecas_disponiveis": (
            BibliotecaFormatacaoCanonica.query.filter_by(ativa=True).all()
        ),
        "autores_disponiveis": _listar_autores_ativos(),
        "relatorios_producao": _listar_relatorios_em_producao(),
    }


def obter_contexto_editor_coordenador(id_versao, perfil_ativo, logger):
    """Monta contexto da tela do editor do coordenador."""
    todos_relatorios = RelatorioProducao.query.order_by(
        RelatorioProducao.criado_em.desc()
    ).all()
    if id_versao is None:
        if not todos_relatorios:
            return None, todos_relatorios
        id_versao = todos_relatorios[0].id

    versao = relatorio_core.obter_versao_trabalho(id_versao)
    if not versao:
        return None, todos_relatorios

    bibliotecas = (
        BibliotecaFormatacaoCanonica.query.filter_by(ativa=True)
        .order_by(BibliotecaFormatacaoCanonica.nome_biblioteca)
        .all()
    )
    biblioteca_atual = None
    if versao.biblioteca_id:
        biblioteca_atual = BibliotecaFormatacaoCanonica.query.get(
            versao.biblioteca_id
        )

    if versao.caminho_template:
        try:
            ressincronizar_capitulos_com_classificacao(versao)
        except RuntimeError as exc:  # pragma: no cover - defesa
            logger.warning(
                "Sincronizacao de capitulos falhou (id_rel=%s): %s",
                versao.id,
                exc,
            )

    rel_bloqueado = relatorio_core.esta_bloqueado(versao)
    return {
        "versao": versao,
        "todos_relatorios": todos_relatorios,
        "bibliotecas": bibliotecas,
        "biblioteca_atual": biblioteca_atual,
        "capitulos": relatorio_core.listar_capitulos_ordenados(versao.id),
        "rel_bloqueado": rel_bloqueado,
        "grupos_acoes": listar_por_grupo(
            perfil_ativo=perfil_ativo or "",
            rel_bloqueado=rel_bloqueado,
        ),
    }, todos_relatorios


def _sort_indice_capitulo(cap):
    idx = cap.indice_capitulo or ""
    try:
        return [int(parte) for parte in idx.split(".") if parte]
    except (ValueError, AttributeError):
        return [9999]


def _listar_autores_ativos():
    perfil_autor = Dominio.query.filter_by(
        tipo="perfil_usuario", valor="autor"
    ).first()
    if not perfil_autor:
        return []
    return (
        Usuario.query
        .filter_by(perfil_id=perfil_autor.id_dominio, ativo=True)
        .order_by(Usuario.nome)
        .all()
    )


def _listar_relatorios_em_producao():
    return (
        db.session.query(RelatorioProducao)
        .join(Dominio, RelatorioProducao.status_id == Dominio.id_dominio)
        .filter(
            Dominio.tipo == "status_relatorio",
            Dominio.valor == "em_producao",
        )
        .order_by(RelatorioProducao.criado_em.desc())
        .all()
    )
