"""Servicos do editor do autor/coordenador."""
from __future__ import annotations

import os

from app import db
from app.models.capitulo_documento import CapituloDocumento
from app.models.envio_conteudo import EnvioConteudo
from app.models.relatorio_producao import RelatorioProducao
from app.models.usuario import Usuario
from app.models.dominio import Dominio
from app.services.servico_acoes_relatorio import listar_por_grupo
from app.services import servico_relatorio_core as relatorio_core


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def atribuir_responsavel_capitulo(
    id_versao, id_capitulo, id_responsavel, id_usuario
):
    """Atribui responsavel a um capitulo."""
    cap = CapituloDocumento.query.get_or_404(id_capitulo)
    if cap.id_relatorio != id_versao:
        return False, "Capítulo não pertence à versão informada.", cap
    rel = RelatorioProducao.query.get(cap.id_relatorio)
    if relatorio_core.esta_bloqueado(rel):
        return (
            False,
            "Relatório finalizado ou bloqueado — não é possível alterar "
            "responsáveis. Crie uma nova versão para continuar.",
            cap,
        )
    cap.id_usuario_responsavel = id_responsavel if id_responsavel else None
    cap.criado_por = id_usuario
    db.session.commit()
    return True, "Responsável atribuído ao capítulo.", cap


def obter_contexto_editor_autor(
    versao, _id_versao, id_usuario, perfil_ativo, id_capitulo_selecionado
):
    """Monta contexto da tela do editor do autor."""
    todos_relatorios = RelatorioProducao.query.order_by(
        RelatorioProducao.criado_em.desc()
    ).all()
    caps_autor = relatorio_core.listar_capitulos_ordenados(versao.id)
    capitulos_do_autor_ids = {
        cap.id_capitulo_documento
        for cap in caps_autor
        if cap.id_usuario_responsavel == id_usuario
    }
    capitulos_livres = [
        cap for cap in caps_autor if cap.id_usuario_responsavel is None
    ]
    rel_bloqueado = relatorio_core.esta_bloqueado(versao)
    capitulo_selecionado = _resolver_capitulo_selecionado(
        caps_autor, id_capitulo_selecionado
    )
    redirect_indice = _indice_redirect_legado(
        capitulo_selecionado, caps_autor, id_capitulo_selecionado
    )
    if redirect_indice:
        return {"redirect_indice": redirect_indice}

    envio_pendente = None
    if (
        capitulo_selecionado is not None
        and _pode_abrir_capitulo(capitulo_selecionado, id_usuario, perfil_ativo)
    ):
        envio_pendente = (
            EnvioConteudo.query.filter_by(
                id_capitulo_destino=capitulo_selecionado.id_capitulo_documento,
                status_envio="em_previa",
            )
            .order_by(EnvioConteudo.criado_em.desc())
            .first()
        )

    caminhos_relativos = {}
    if envio_pendente and envio_pendente.caminho_arquivo:
        try:
            caminhos_relativos["upload"] = os.path.relpath(
                envio_pendente.caminho_arquivo, BASE_DIR
            )
        except ValueError:
            caminhos_relativos["upload"] = envio_pendente.caminho_arquivo

        from app.services.servico_envio_autor import ServicoEnvioAutor

        try:
            # pylint: disable=protected-access
            caminho_sugerido = (
                ServicoEnvioAutor._caminho_novo_docx_sugerido(  # type: ignore[attr-defined]
                    envio_pendente
                )
            )
            if caminho_sugerido:
                caminhos_relativos["sugerido"] = os.path.relpath(
                    caminho_sugerido, BASE_DIR
                )
        except Exception:
            caminhos_relativos["sugerido"] = None

    return {
        "versao": versao,
        "todos_relatorios": todos_relatorios,
        "capitulos": caps_autor,
        "capitulos_livres": capitulos_livres,
        "capitulos_do_autor_ids": capitulos_do_autor_ids,
        "rel_bloqueado": rel_bloqueado,
        "grupos_acoes": listar_por_grupo(
            perfil_ativo="coordenador", rel_bloqueado=rel_bloqueado
        ),
        "capitulo_selecionado": capitulo_selecionado,
        "envio_pendente": envio_pendente,
        "caminhos_relativos": caminhos_relativos,
        "perfil_ativo": perfil_ativo,
        "autores_disponiveis": _listar_autores(perfil_ativo),
        "id_capitulo_selecionado": id_capitulo_selecionado,
    }


def assumir_capitulos(id_versao, ids, id_usuario):
    """Associa capitulos livres ao autor."""
    caps = CapituloDocumento.query.filter(
        CapituloDocumento.id_relatorio == id_versao,
        CapituloDocumento.id_capitulo_documento.in_(ids),
        CapituloDocumento.id_usuario_responsavel.is_(None),
    ).all()
    for capitulo in caps:
        capitulo.id_usuario_responsavel = id_usuario
        capitulo.criado_por = id_usuario
    db.session.commit()
    return len(caps)


def enviar_final_autor(id_versao, id_usuario):
    """Marca capitulos do autor como enviados para revisao."""
    caps = CapituloDocumento.query.filter_by(
        id_relatorio=id_versao,
        id_usuario_responsavel=id_usuario,
    ).all()
    if not caps:
        return 0
    for capitulo in caps:
        capitulo.status_capitulo = "enviado_revisao"
    db.session.commit()
    return len(caps)


def _resolver_capitulo_selecionado(capitulos, identificador):
    if not identificador:
        return None
    return next(
        (cap for cap in capitulos if cap.indice_capitulo == identificador),
        None,
    )


def _indice_redirect_legado(capitulo_selecionado, capitulos, identificador):
    if capitulo_selecionado is not None or not identificador:
        return None
    if not identificador.isdigit():
        return None
    capitulo_legado = next(
        (
            cap for cap in capitulos
            if cap.id_capitulo_documento == int(identificador)
        ),
        None,
    )
    if capitulo_legado and capitulo_legado.indice_capitulo:
        return capitulo_legado.indice_capitulo
    return None


def _pode_abrir_capitulo(capitulo, id_usuario, perfil_ativo):
    if capitulo is None:
        return False
    return (
        capitulo.id_usuario_responsavel == id_usuario
        or perfil_ativo in ("coordenador", "admin")
    )


def _listar_autores(perfil_ativo):
    if perfil_ativo not in ("coordenador", "admin"):
        return []
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
