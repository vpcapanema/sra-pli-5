"""Servicos para telas de configuracao."""
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from app import db
from app.models.biblioteca_formatacao import BibliotecaFormatacaoCanonica
from app.models.dominio import Dominio
from app.models.modelo_relatorio import ModeloRelatorio
from app.models.relatorio_base import RelatorioBase
from app.models.relatorio_finalizado import RelatorioFinalizado
from app.services.servico_extracao_canonica import ServicoExtracaoCanonica


STORAGE_CANONICOS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'storage', 'canonicos'
)


def criar_biblioteca_formatacao(dados, arquivo):
    """Cria biblioteca canonica, salva DOCX e executa extracao."""
    nome = (dados.get('nome_biblioteca') or '').strip()
    descricao = (dados.get('descricao') or '').strip()
    if not nome:
        return False, 'O nome da biblioteca é obrigatório.'
    if not arquivo or not arquivo.filename.endswith('.docx'):
        return False, 'Envie um arquivo .docx válido.'

    bib = BibliotecaFormatacaoCanonica(
        nome_biblioteca=nome,
        descricao=descricao or None,
        ativa=True,
    )
    db.session.add(bib)
    db.session.flush()

    nome_bib_seguro = secure_filename(nome)
    dir_bib = os.path.join(STORAGE_CANONICOS, nome_bib_seguro)
    os.makedirs(dir_bib, exist_ok=True)
    nome_seguro = secure_filename(arquivo.filename)
    caminho_docx = os.path.join(dir_bib, nome_seguro)
    arquivo.save(caminho_docx)

    try:
        ServicoExtracaoCanonica.extrair(caminho_docx, dir_bib)
    except (OSError, IOError, RuntimeError) as erro:
        db.session.rollback()
        return False, f'Erro na extração: {erro}'

    bib.caminho_arquivo = dir_bib
    bib.arquivo_docx = nome_seguro
    bib.extraida = True
    db.session.commit()
    return True, f'Biblioteca "{nome}" criada e parâmetros extraídos.'


def carregar_parametros_biblioteca(bib):
    """Carrega arquivos JSON extraidos da biblioteca canonica."""
    dados = {
        'canonico_formatacao': {},
        'canonico_macro': [],
        'canonico_capitulos': [],
    }
    if not bib.caminho_arquivo:
        return dados
    arquivos = (
        (ServicoExtracaoCanonica.ARQUIVO_FORMATACAO, 'canonico_formatacao', {}),
        (ServicoExtracaoCanonica.ARQUIVO_MACRO, 'canonico_macro', []),
        (ServicoExtracaoCanonica.ARQUIVO_CAPITULOS, 'canonico_capitulos', []),
    )
    for nome, chave, default in arquivos:
        caminho = os.path.join(bib.caminho_arquivo, nome)
        if os.path.exists(caminho):
            with open(caminho, 'r', encoding='utf-8') as arquivo:
                dados[chave] = json.load(arquivo)
        else:
            dados[chave] = default
    return dados


def atualizar_biblioteca_formatacao(id_bib, dados):
    """Atualiza metadados de uma biblioteca de formatacao."""
    bib = BibliotecaFormatacaoCanonica.query.get_or_404(id_bib)
    bib.nome_biblioteca = dados.get('nome_biblioteca', bib.nome_biblioteca)
    bib.descricao = dados.get('descricao', bib.descricao)
    bib.ativa = 'ativa' in dados
    try:
        db.session.commit()
        return True, 'Biblioteca atualizada com sucesso.', bib
    except SQLAlchemyError as erro:
        db.session.rollback()
        return False, f'Erro ao atualizar biblioteca: {erro}', bib


def excluir_biblioteca_formatacao(id_bib):
    """Exclui biblioteca canonica e seus arquivos."""
    bib = BibliotecaFormatacaoCanonica.query.get_or_404(id_bib)
    nome = bib.nome_biblioteca
    try:
        if bib.caminho_arquivo and os.path.exists(bib.caminho_arquivo):
            shutil.rmtree(bib.caminho_arquivo, ignore_errors=True)
        db.session.delete(bib)
        db.session.commit()
        return True, f'Biblioteca "{nome}" excluída.'
    except (OSError, IOError) as erro:
        db.session.rollback()
        return False, f'Erro ao excluir biblioteca: {erro}'


def criar_relatorio_base_finalizado(dados, arquivo, id_usuario):
    """Cria entrada de relatorio finalizado usada como relatorio base."""
    if not arquivo or not arquivo.filename.endswith('.docx'):
        return False, 'Envie um arquivo .docx válido.'
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    dir_relatorios = os.path.join(base_dir, 'storage', 'relatorios_base')
    os.makedirs(dir_relatorios, exist_ok=True)
    nome_seguro = secure_filename(arquivo.filename)
    caminho = os.path.join(dir_relatorios, nome_seguro)
    arquivo.save(caminho)
    status = Dominio.query.filter_by(
        tipo='status_relatorio',
        valor='finalizado',
    ).first()
    relatorio = RelatorioFinalizado(
        relatorio_id=None,
        modelo_id=None,
        biblioteca_id=None,
        status_id=status.id if status else None,
        snapshot_conteudo={},
        artefato_docx=None,
        nome_arquivo=nome_seguro,
        caminho_arquivo=caminho,
        finalizado_por=id_usuario,
        codigo=dados.get('codigo_pli'),
        titulo=dados.get('titulo_curto'),
        numero_medicao=dados.get('numero_medicao', type=int),
        mes_referencia=_parse_mes_referencia(dados.get('mes_referencia')),
        ano_referencia=dados.get('ano_referencia', type=int),
        periodo_inicio=_parse_data(dados.get('periodo_inicio')),
        periodo_fim=_parse_data(dados.get('periodo_fim')),
        versao='R00',
    )
    try:
        db.session.add(relatorio)
        db.session.commit()
        return True, 'Relatório base cadastrado com sucesso.'
    except SQLAlchemyError as erro:
        db.session.rollback()
        return False, f'Erro ao cadastrar relatório: {erro}'


def atualizar_relatorio_finalizado_inline(id_relatorio, dados):
    """Atualiza campos inline de relatorio finalizado."""
    relatorio = RelatorioFinalizado.query.get_or_404(id_relatorio)
    for campo in ('titulo', 'codigo', 'versao'):
        if campo in dados:
            setattr(relatorio, campo, dados[campo])
    if dados.get('numero_medicao'):
        relatorio.numero_medicao = int(dados['numero_medicao'])
    if dados.get('periodo_inicio'):
        relatorio.periodo_inicio = _parse_data(dados['periodo_inicio'])
    if dados.get('periodo_fim'):
        relatorio.periodo_fim = _parse_data(dados['periodo_fim'])
    db.session.commit()
    return relatorio


def excluir_relatorio_finalizado(id_relatorio):
    """Exclui relatorio finalizado e arquivo associado."""
    relatorio = RelatorioFinalizado.query.get_or_404(id_relatorio)
    titulo = relatorio.titulo or relatorio.codigo or 'Relatório'
    try:
        if relatorio.caminho_arquivo and os.path.exists(relatorio.caminho_arquivo):
            os.remove(relatorio.caminho_arquivo)
        db.session.delete(relatorio)
        db.session.commit()
        return True, f'Relatório "{titulo}" excluído.'
    except (OSError, IOError) as erro:
        db.session.rollback()
        return False, f'Erro ao excluir relatório: {erro}'


def atualizar_modelo(id_modelo, dados):
    """Atualiza um modelo de relatorio."""
    modelo = ModeloRelatorio.query.get_or_404(id_modelo)
    modelo.nome_modelo = dados.get('nome_modelo', modelo.nome_modelo)
    modelo.descricao = dados.get('descricao', modelo.descricao)
    modelo.ativo = 'ativo' in dados
    try:
        db.session.commit()
        return True, 'Modelo atualizado com sucesso.', modelo
    except SQLAlchemyError as erro:
        db.session.rollback()
        return False, f'Erro ao atualizar modelo: {erro}', modelo


def excluir_modelo(id_modelo):
    """Exclui modelo e relatorios base vinculados."""
    modelo = ModeloRelatorio.query.get_or_404(id_modelo)
    nome = modelo.nome_modelo
    try:
        for relatorio_base in modelo.relatorios_base:
            if relatorio_base.caminho_arquivo and os.path.exists(
                relatorio_base.caminho_arquivo
            ):
                os.remove(relatorio_base.caminho_arquivo)
            db.session.delete(relatorio_base)
        db.session.delete(modelo)
        db.session.commit()
        return True, f'Modelo "{nome}" excluído.'
    except (OSError, IOError) as erro:
        db.session.rollback()
        return False, f'Erro ao excluir modelo: {erro}'


def excluir_relatorio_base(id_relatorio):
    """Exclui relatorio base e arquivo associado."""
    relatorio = RelatorioBase.query.get_or_404(id_relatorio)
    titulo = relatorio.titulo
    try:
        if relatorio.caminho_arquivo and os.path.exists(relatorio.caminho_arquivo):
            os.remove(relatorio.caminho_arquivo)
        db.session.delete(relatorio)
        db.session.commit()
        return True, f'Relatório base "{titulo}" excluído.'
    except (OSError, IOError) as erro:
        db.session.rollback()
        return False, f'Erro ao excluir relatório: {erro}'


def _parse_data(valor):
    return datetime.strptime(valor, '%Y-%m-%d').date() if valor else None


def _parse_mes_referencia(valor):
    if not valor:
        return None
    meses_pt_en = {
        'janeiro': 'January', 'fevereiro': 'February',
        'março': 'March', 'abril': 'April',
        'maio': 'May', 'junho': 'June',
        'julho': 'July', 'agosto': 'August',
        'setembro': 'September', 'outubro': 'October',
        'novembro': 'November', 'dezembro': 'December',
    }
    for pt, en in meses_pt_en.items():
        valor = valor.replace(pt, en)
    return datetime.strptime(valor, '%B de %Y')
