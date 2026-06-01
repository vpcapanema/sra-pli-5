"""Servicos de composicao do dashboard principal."""
from __future__ import annotations

import os

from sqlalchemy.orm import joinedload

from app.models.biblioteca_formatacao import BibliotecaFormatacaoCanonica
from app.models.envio_conteudo import EnvioConteudo
from app.models.relatorio_finalizado import RelatorioFinalizado
from app.models.relatorio_producao import RelatorioProducao
from app.models.usuario import Usuario


def obter_contexto_dashboard(perfil_ativo, id_usuario):
    """Monta os dados exibidos no dashboard principal."""
    envios = _listar_envios_dashboard(perfil_ativo, id_usuario)
    _anexar_auditoria_envios(envios)
    return {
        'relatorios_producao': RelatorioProducao.query.all(),
        'relatorios_finalizados': RelatorioFinalizado.query.all(),
        'bibliotecas_formatacao': BibliotecaFormatacaoCanonica.query.filter_by(
            ativa=True
        ).all(),
        'arquivos_relatorios_base': _listar_arquivos_relatorios_base(),
        'envios': envios,
    }


def _listar_arquivos_relatorios_base():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    dir_relatorios_base = os.path.join(base_dir, 'storage', 'relatorios_base')
    if not os.path.exists(dir_relatorios_base):
        return []
    return [
        arquivo for arquivo in os.listdir(dir_relatorios_base)
        if arquivo.endswith('.docx')
    ]


def _listar_envios_dashboard(perfil_ativo, id_usuario):
    envios_query = (
        EnvioConteudo.query
        .options(
            joinedload(EnvioConteudo.relatorio),
            joinedload(EnvioConteudo.capitulo_destino),
            joinedload(EnvioConteudo.criador),
        )
        .order_by(EnvioConteudo.criado_em.desc())
    )
    if perfil_ativo == 'autor':
        envios_query = envios_query.filter_by(id_usuario=id_usuario)
    return envios_query.all()


def _anexar_auditoria_envios(envios):
    if not envios:
        return
    ids_aud = set()
    for envio in envios:
        if envio.criado_por:
            ids_aud.add(envio.criado_por)
        if envio.atualizado_por:
            ids_aud.add(envio.atualizado_por)

    usuarios_por_id = {}
    if ids_aud:
        for usuario in Usuario.query.filter(Usuario.id.in_(ids_aud)).all():
            usuarios_por_id[usuario.id] = usuario

    for envio in envios:
        envio.criado_por_user = usuarios_por_id.get(envio.criado_por)
        envio.atualizado_por_user = usuarios_por_id.get(envio.atualizado_por)
        capitulo = envio.capitulo_destino
        envio.autor_responsavel = capitulo.responsavel if capitulo else None
