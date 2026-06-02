"""Operacoes centrais de relatorios e capitulos ainda compartilhadas."""

from __future__ import annotations

from datetime import date

from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models.capitulo_documento import CapituloDocumento
from app.models.dominio import Dominio
from app.models.modelo_relatorio import ModeloRelatorio
from app.models.relatorio_base import RelatorioBase
from app.models.relatorio_finalizado import RelatorioFinalizado
from app.models.relatorio_producao import RelatorioProducao


def listar_modelos(apenas_ativos=True):
    query = ModeloRelatorio.query
    if apenas_ativos:
        query = query.filter_by(ativo=True)
    return query.all()


def criar_modelo(nome_modelo, descricao=None):
    modelo = ModeloRelatorio(  # type: ignore[call-arg]
        **{
            'nome_modelo': nome_modelo,
            'descricao': descricao,
        }
    )
    db.session.add(modelo)
    db.session.commit()
    return modelo


def listar_relatorios_base():
    return RelatorioBase.query.all()


def listar_relatorios_finalizados():
    try:
        return RelatorioFinalizado.query.all()
    except SQLAlchemyError:
        return []


def esta_bloqueado(rel):
    if rel is None:
        return True
    if rel.bloqueio_edicao:
        return True
    if rel.status and rel.status.codigo == "finalizado":
        return True
    return False


def listar_relatorios_producao():
    return RelatorioProducao.query.all()


def listar_versoes_trabalho():
    return RelatorioProducao.query.all()


def obter_versao_trabalho(id_versao):
    return RelatorioProducao.query.get(id_versao)


def criar_versao_trabalho(id_relatorio_base, titulo):
    return criar_relatorio_producao(id_relatorio_base, titulo)


def obter_relatorio_producao(id_relatorio):
    return RelatorioProducao.query.get(id_relatorio)


def criar_relatorio_producao(relatorio_id, titulo):
    status = Dominio.query.filter_by(tipo="status_relatorio", valor="em_producao").first()
    if not status:
        status = Dominio.query.filter_by(tipo="status_relatorio", ativo=True).first()

    relatorio = RelatorioProducao(  # type: ignore[call-arg]
        **{
            'modelo_id': relatorio_id,
            'titulo_curto': titulo,
            'codigo_d20': "D-20",
            'numero_medicao': 1,
            'mes_referencia': date.today(),
            'periodo_inicio': date.today(),
            'periodo_fim': date.today(),
            'status_id': status.id if status else 1,
            'criado_por': current_user.id if current_user.is_authenticated else None,
        }
    )
    db.session.add(relatorio)
    db.session.commit()
    return relatorio


def listar_capitulos(id_relatorio):
    return (
        CapituloDocumento.query.filter_by(
            id_relatorio=id_relatorio,
            id_capitulo_pai=None,
        )
        .order_by(CapituloDocumento.ordem_capitulo)
        .all()
    )


_BUCKET_TIPO = {
    "pre_textual": 0,
    "textual": 1,
    "pos_textual": 2,
}


def chave_ordem_indice(cap):
    bucket = _BUCKET_TIPO.get(cap.tipo_elemento or "textual", 1)
    idx = (cap.indice_capitulo or "").strip()
    partes = []
    if idx:
        for parte in idx.split("."):
            parte = parte.strip()
            if not parte:
                continue
            try:
                partes.append(int(parte))
            except ValueError:
                partes.append(10000)
    if not partes:
        partes = [9999]
    return (bucket, tuple(partes), cap.ordem_capitulo or 0)


def listar_capitulos_ordenados(id_relatorio, incluir_inativos=False):
    query = CapituloDocumento.query.filter_by(id_relatorio=id_relatorio)
    if not incluir_inativos:
        query = query.filter(
            (CapituloDocumento.ativo.is_(True)) | (CapituloDocumento.ativo.is_(None))
        )
    return sorted(query.all(), key=chave_ordem_indice)


def criar_capitulo(
    id_relatorio,
    titulo_capitulo,
    ordem_capitulo,
    nivel_capitulo=1,
    id_capitulo_pai=None,
    nome_capitulo=None,
    indice_capitulo=None,
    tipo_elemento="textual",
):
    from app.utils.auditoria import usuario_atual_id

    capitulo = CapituloDocumento(  # type: ignore[call-arg]
        **{
            'id_relatorio': id_relatorio,
            'titulo_capitulo': titulo_capitulo,
            'ordem_capitulo': ordem_capitulo,
            'nivel_capitulo': nivel_capitulo,
            'id_capitulo_pai': id_capitulo_pai,
            'nome_capitulo': nome_capitulo or titulo_capitulo,
            'indice_capitulo': indice_capitulo,
            'tipo_elemento': tipo_elemento,
            'criado_por': usuario_atual_id(),
        }
    )
    db.session.add(capitulo)
    db.session.commit()
    return capitulo
