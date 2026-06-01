"""Operacoes de negocio das rotas de relatorio."""
from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone

from werkzeug.utils import secure_filename

from app import db
from app.models.capitulo_documento import CapituloDocumento
from app.models.dominio import Dominio
from app.models.envio_conteudo import EnvioConteudo
from app.models.relatorio_producao import RelatorioProducao


def criar_relatorio_producao(dados, arquivo, id_usuario):
    """Cria relatorio de producao com upload DOCX opcional."""
    status_inicial = Dominio.query.filter_by(
        tipo="status_relatorio", valor="em_producao"
    ).first()
    if not status_inicial:
        return None, "Status inicial não configurado."

    caminho_template = _salvar_docx_producao(arquivo)
    relatorio = RelatorioProducao(
        codigo_d20=dados.get("codigo_pli"),
        numero_medicao=dados.get("numero_medicao", type=int),
        mes_referencia=_parse_data_hora(dados.get("mes_referencia"), "%B de %Y"),
        periodo_inicio=_parse_data_hora(dados.get("periodo_inicio"), "%Y-%m-%d"),
        periodo_fim=_parse_data_hora(dados.get("periodo_fim"), "%Y-%m-%d"),
        titulo_curto=dados.get("titulo_curto"),
        status_id=status_inicial.id,
        criado_por=id_usuario,
        ano_referencia=dados.get("ano_referencia", type=int),
        versao_atual="R00",
        bloqueio_edicao=False,
        caminho_template=caminho_template,
    )
    db.session.add(relatorio)
    db.session.commit()
    return relatorio, "Relatório de produção criado com sucesso."


def editar_envio_inline(id_envio, dados):
    """Atualiza campos inline de envio de conteudo."""
    envio = EnvioConteudo.query.get_or_404(id_envio)
    for campo in ("nome_arquivo", "status_envio"):
        if campo in dados:
            setattr(envio, campo, dados[campo])
    db.session.commit()
    return {
        "id": envio.id_envio_conteudo,
        "nome_arquivo": envio.nome_arquivo,
        "status_envio": envio.status_envio,
    }


def editar_relatorio_producao_inline(id_relatorio, dados):
    """Atualiza campos inline do relatorio de producao."""
    relatorio = RelatorioProducao.query.get_or_404(id_relatorio)
    for campo in ("titulo_curto", "codigo_d20", "versao_atual"):
        if campo in dados:
            setattr(relatorio, campo, dados[campo])
    if dados.get("numero_medicao"):
        relatorio.numero_medicao = int(dados["numero_medicao"])
    if dados.get("periodo_inicio"):
        relatorio.periodo_inicio = _parse_data(dados["periodo_inicio"])
    if dados.get("periodo_fim"):
        relatorio.periodo_fim = _parse_data(dados["periodo_fim"])
    relatorio.atualizado_em = datetime.now(timezone.utc)
    db.session.commit()
    return {
        "id": relatorio.id,
        "titulo_curto": relatorio.titulo_curto or "",
        "codigo_d20": relatorio.codigo_d20,
        "versao_atual": relatorio.versao_atual,
        "numero_medicao": relatorio.numero_medicao,
    }


def excluir_relatorio_producao(id_relatorio):
    """Exclui relatorio de producao e arquivo associado."""
    relatorio = RelatorioProducao.query.get_or_404(id_relatorio)
    titulo = relatorio.titulo_curto or relatorio.codigo_d20 or "Relatório"
    CapituloDocumento.query.filter_by(id_relatorio=id_relatorio).delete()
    if relatorio.caminho_template and os.path.exists(relatorio.caminho_template):
        os.remove(relatorio.caminho_template)
    db.session.delete(relatorio)
    db.session.commit()
    return f'Relatório "{titulo}" excluído com sucesso.'


def clonar_arquivo_base(arquivo_base, titulo_curto):
    """Copia arquivo base para storage de producao e retorna novo caminho."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    dir_base = os.path.join(base_dir, "storage", "relatorios_base")
    dir_producao = os.path.join(base_dir, "storage", "relatorios_producao")
    os.makedirs(dir_producao, exist_ok=True)
    caminho_base = os.path.join(dir_base, arquivo_base)
    if not os.path.exists(caminho_base):
        return None
    nome_arquivo = titulo_curto or arquivo_base.replace(".docx", "")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    nome_seguro = secure_filename(f"{nome_arquivo}_{timestamp}.docx")
    caminho_producao = os.path.join(dir_producao, nome_seguro)
    shutil.copy2(caminho_base, caminho_producao)
    return caminho_producao


def _salvar_docx_producao(arquivo):
    nome = arquivo.filename if arquivo else None
    if not nome or not nome.endswith(".docx"):
        return None
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    dir_relatorios = os.path.join(base_dir, "storage", "relatorios_producao")
    os.makedirs(dir_relatorios, exist_ok=True)
    caminho = os.path.join(dir_relatorios, secure_filename(nome))
    arquivo.save(caminho)
    return caminho


def _parse_data(valor):
    return datetime.strptime(valor, "%Y-%m-%d").date()


def _parse_data_hora(valor, formato):
    return datetime.strptime(valor, formato) if valor else None
