"""Rotas de configuração do SRA."""

import os
import json
import shutil
from datetime import datetime

from flask import (
    Blueprint, redirect, url_for, request, flash,
    render_template, send_file
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models.biblioteca_formatacao import BibliotecaFormatacaoCanonica
from app.models.modelo_relatorio import ModeloRelatorio
from app.models.relatorio_base import RelatorioBase
from app.models.relatorio_finalizado import RelatorioFinalizado
from app.models.dominio import DomStatusRelatorio
from app.services.servico_extracao_canonica import ServicoExtracaoCanonica
from app.services.servico_relatorio import ServicoRelatorio
from app.utils.htmx import render_conteudo

STORAGE_CANONICOS = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'storage', 'canonicos'
)

configuracoes_bp = Blueprint(
    'configuracoes', __name__, url_prefix='/configuracoes'
)


@configuracoes_bp.route('/biblioteca-formatacao')
@login_required
def biblioteca_formatacao():
    """Lista bibliotecas de formatação canônica."""
    bibliotecas = BibliotecaFormatacaoCanonica.query.order_by(
        BibliotecaFormatacaoCanonica.id_biblioteca_formatacao_canonica
    ).all()
    return render_conteudo(
        ['configuracoes/biblioteca_formatacao.html'],
        bibliotecas=bibliotecas
    )


@configuracoes_bp.route('/biblioteca-formatacao', methods=['POST'])
@login_required
def criar_biblioteca_formatacao():
    """Cria biblioteca + upload DOCX + extração canônica."""
    nome = request.form.get('nome_biblioteca', '').strip()
    descricao = request.form.get('descricao', '').strip()
    arquivo = request.files.get('arquivo_docx')

    if not nome:
        flash('O nome da biblioteca é obrigatório.', 'erro')
        return redirect(
            url_for('configuracoes.biblioteca_formatacao')
        )

    if not arquivo or not arquivo.filename.endswith('.docx'):
        flash('Envie um arquivo .docx válido.', 'erro')
        return redirect(
            url_for('configuracoes.biblioteca_formatacao')
        )

    # Criar registro
    bib = BibliotecaFormatacaoCanonica(
        nome_biblioteca=nome,
        descricao=descricao or None,
        ativa=True
    )
    db.session.add(bib)
    db.session.flush()

    # Diretório: storage/canonicos/{nome_biblioteca}/
    nome_bib_seguro = secure_filename(nome)
    dir_bib = os.path.join(STORAGE_CANONICOS, nome_bib_seguro)
    os.makedirs(dir_bib, exist_ok=True)

    # Salvar DOCX original
    nome_seguro = secure_filename(arquivo.filename)
    caminho_docx = os.path.join(dir_bib, nome_seguro)
    arquivo.save(caminho_docx)

    # Executar extração canônica
    try:
        ServicoExtracaoCanonica.extrair(caminho_docx, dir_bib)
    except (OSError, IOError, RuntimeError) as e:
        flash(f'Erro na extração: {e}', 'erro')
        db.session.rollback()
        return redirect(
            url_for('configuracoes.biblioteca_formatacao')
        )

    # Atualizar registro
    bib.caminho_arquivo = dir_bib
    bib.arquivo_docx = nome_seguro
    bib.extraida = True
    db.session.commit()

    flash(
        f'Biblioteca "{nome}" criada e parâmetros extraídos.',
        'sucesso'
    )
    return redirect(url_for('configuracoes.biblioteca_formatacao'))


@configuracoes_bp.route(
    '/biblioteca-formatacao/<int:id_bib>/parametros'
)
@login_required
def ver_biblioteca_formatacao(id_bib):
    """Página dedicada de visualização interativa dos parâmetros."""
    bib = BibliotecaFormatacaoCanonica.query.get_or_404(id_bib)

    formatacao = {}
    macro = []
    capitulos = []
    if bib.caminho_arquivo:
        for nome, default in [
            (ServicoExtracaoCanonica.ARQUIVO_FORMATACAO, {}),
            (ServicoExtracaoCanonica.ARQUIVO_MACRO, []),
            (ServicoExtracaoCanonica.ARQUIVO_CAPITULOS, []),
        ]:
            caminho = os.path.join(bib.caminho_arquivo, nome)
            if os.path.exists(caminho):
                with open(caminho, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
            else:
                dados = default
            if nome == ServicoExtracaoCanonica.ARQUIVO_FORMATACAO:
                formatacao = dados
            elif nome == ServicoExtracaoCanonica.ARQUIVO_MACRO:
                macro = dados
            else:
                capitulos = dados

    return render_template(
        'visualizador_parametros.html',
        bib=bib,
        canonico_formatacao=formatacao,
        canonico_macro=macro,
        canonico_capitulos=capitulos,
    )


@configuracoes_bp.route(
    '/biblioteca-formatacao/<int:id_bib>/editar',
    methods=['GET', 'POST']
)
@login_required
def editar_biblioteca_formatacao(id_bib):
    """Edita uma biblioteca de formatação."""
    bib = BibliotecaFormatacaoCanonica.query.get_or_404(id_bib)
    if request.method == 'POST':
        bib.nome_biblioteca = request.form.get(
            'nome_biblioteca', bib.nome_biblioteca
        )
        bib.descricao = request.form.get('descricao', bib.descricao)
        bib.ativa = 'ativa' in request.form
        try:
            db.session.commit()
            flash('Biblioteca atualizada com sucesso.', 'sucesso')
            return redirect(url_for('configuracoes.biblioteca_formatacao'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Erro ao atualizar biblioteca: {e}', 'erro')
    return render_template(
        'components/configuracoes/editar_biblioteca_formatacao.html',
        bib=bib,
    )


@configuracoes_bp.route(
    '/biblioteca-formatacao/<int:id_bib>/docx'
)
@login_required
def baixar_docx_biblioteca(id_bib):
    """Serve o DOCX modelo para renderização via docx-preview."""
    bib = BibliotecaFormatacaoCanonica.query.get_or_404(id_bib)
    if not bib.caminho_arquivo or not bib.arquivo_docx:
        return ('DOCX não disponível', 404)
    caminho = os.path.join(
        bib.caminho_arquivo, bib.arquivo_docx
    )
    if not os.path.exists(caminho):
        return ('Arquivo não encontrado', 404)
    return send_file(
        caminho,
        mimetype=(
            'application/vnd.openxmlformats-officedocument'
            '.wordprocessingml.document'
        ),
        as_attachment=False,
    )


@configuracoes_bp.route(
    '/biblioteca-formatacao/<int:id_bib>/excluir',
    methods=['POST']
)
@login_required
def excluir_biblioteca_formatacao(id_bib):
    """Exclui biblioteca de formatação canônica e arquivos."""
    bib = BibliotecaFormatacaoCanonica.query.get_or_404(id_bib)
    nome = bib.nome_biblioteca
    try:
        if bib.caminho_arquivo and os.path.exists(bib.caminho_arquivo):
            shutil.rmtree(bib.caminho_arquivo, ignore_errors=True)
        db.session.delete(bib)
        db.session.commit()
        flash(
            f'Biblioteca "{nome}" excluída.',
            'sucesso'
        )
    except (OSError, IOError) as e:
        db.session.rollback()
        flash(f'Erro ao excluir biblioteca: {e}', 'erro')
    return redirect(
        url_for('configuracoes.biblioteca_formatacao')
    )


@configuracoes_bp.route('/biblioteca-relatorios-base')
@login_required
def biblioteca_relatorios_base():
    """Biblioteca de relatórios base — visualização de relatórios."""
    try:
        relatorios_finalizados = \
            ServicoRelatorio.listar_relatorios_finalizados()
    except SQLAlchemyError as e:
        flash(f'Erro ao carregar relatórios base: {str(e)}', 'erro')
        relatorios_finalizados = []
    return render_conteudo(
        ['configuracoes/biblioteca_relatorios_base.html'],
        relatorios_finalizados=relatorios_finalizados
    )


@configuracoes_bp.route('/biblioteca-relatorios-base',
                        methods=['POST'])
@login_required
def criar_relatorio_base():
    """Cria relatório finalizado com upload DOCX para storage."""

    try:
        arquivo = request.files.get('arquivo_docx')
        if not arquivo or not arquivo.filename.endswith('.docx'):
            flash('Envie um arquivo .docx válido.', 'erro')
            return redirect(
                url_for('configuracoes.biblioteca_relatorios_base')
            )

        # Salvar arquivo em storage/relatorios_base
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        dir_relatorios = os.path.join(base_dir, 'storage', 'relatorios_base')
        os.makedirs(dir_relatorios, exist_ok=True)
        nome_seguro = secure_filename(arquivo.filename)
        caminho = os.path.join(dir_relatorios, nome_seguro)
        arquivo.save(caminho)

        # Obter status inicial
        status = DomStatusRelatorio.query.filter_by(
            codigo='finalizado'
        ).first()

        # Mapeamento de meses em português para inglês
        meses_pt_en = {
            'janeiro': 'January', 'fevereiro': 'February',
            'março': 'March', 'abril': 'April',
            'maio': 'May', 'junho': 'June',
            'julho': 'July', 'agosto': 'August',
            'setembro': 'September', 'outubro': 'October',
            'novembro': 'November', 'dezembro': 'December'
        }

        mes_ref_str = request.form.get('mes_referencia')
        mes_ref = None
        if mes_ref_str:
            for pt, en in meses_pt_en.items():
                mes_ref_str = mes_ref_str.replace(pt, en)
            mes_ref = datetime.strptime(mes_ref_str, '%B de %Y')

        # Criar RelatorioFinalizado (apenas, sem RelatorioProducao)
        # pois o arquivo está em storage/relatorios_base
        relatorio = RelatorioFinalizado(
            relatorio_id=None,
            modelo_id=None,
            biblioteca_id=None,
            status_id=status.id if status else None,
            snapshot_conteudo={},
            artefato_docx=None,
            nome_arquivo=nome_seguro,
            caminho_arquivo=caminho,
            finalizado_por=current_user.id,
            codigo=request.form.get('codigo_pli'),
            titulo=request.form.get('titulo_curto'),
            numero_medicao=request.form.get('numero_medicao', type=int),
            mes_referencia=mes_ref,
            ano_referencia=request.form.get('ano_referencia', type=int),
            periodo_inicio=datetime.strptime(
                request.form.get('periodo_inicio'), '%Y-%m-%d'
            ) if request.form.get('periodo_inicio') else None,
            periodo_fim=datetime.strptime(
                request.form.get('periodo_fim'), '%Y-%m-%d'
            ) if request.form.get('periodo_fim') else None,
            versao='R00'
        )

        db.session.add(relatorio)
        db.session.commit()

        flash('Relatório base cadastrado com sucesso.', 'sucesso')
        return redirect(url_for('configuracoes.biblioteca_relatorios_base'))
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Erro ao cadastrar relatório: {str(e)}', 'erro')
        return redirect(url_for('configuracoes.biblioteca_relatorios_base'))


@configuracoes_bp.route(
    '/relatorio-finalizado/<int:id_relatorio>/visualizar'
)
@login_required
def visualizar_relatorio_finalizado(id_relatorio):
    """Renderiza página de visualização do relatório finalizado."""

    relatorio = RelatorioFinalizado.query.get_or_404(id_relatorio)
    return render_template(
        'visualizador_relatorio_finalizado.html',
        relatorio=relatorio
    )


@configuracoes_bp.route(
    '/relatorio-finalizado/<int:id_relatorio>/arquivo'
)
@login_required
def arquivo_relatorio_finalizado(id_relatorio):
    """Serve o DOCX do relatório finalizado."""

    relatorio = RelatorioFinalizado.query.get_or_404(id_relatorio)
    if not relatorio.caminho_arquivo:
        return ('Arquivo não disponível', 404)
    if not os.path.exists(relatorio.caminho_arquivo):
        return ('Arquivo não encontrado', 404)
    return send_file(
        relatorio.caminho_arquivo,
        mimetype=(
            'application/vnd.openxmlformats-officedocument'
            '.wordprocessingml.document'
        ),
        as_attachment=False,
    )


@configuracoes_bp.route(
    '/relatorio-finalizado/<int:id_relatorio>/excluir',
    methods=['POST']
)
@login_required
def excluir_relatorio_finalizado(id_relatorio):
    """Exclui relatório finalizado e remove arquivo."""

    relatorio = RelatorioFinalizado.query.get_or_404(id_relatorio)
    titulo = relatorio.titulo or relatorio.codigo or 'Relatório'
    try:
        if relatorio.caminho_arquivo and os.path.exists(
            relatorio.caminho_arquivo
        ):
            os.remove(relatorio.caminho_arquivo)
        db.session.delete(relatorio)
        db.session.commit()
        flash(f'Relatório "{titulo}" excluído.', 'sucesso')
    except (OSError, IOError) as e:
        db.session.rollback()
        flash(f'Erro ao excluir relatório: {e}', 'erro')
    return redirect(url_for('configuracoes.biblioteca_relatorios_base'))


# --- Modelo Relatório ---


@configuracoes_bp.route('/modelo/<int:id_modelo>')
@login_required
def detalhe_modelo(id_modelo):
    """Detalhes de um modelo de relatório."""
    modelo = ModeloRelatorio.query.get_or_404(id_modelo)
    return render_conteudo(
        ['components/configuracoes/detalhe_modelo.html'],
        modelo=modelo,
    )


@configuracoes_bp.route('/modelo/<int:id_modelo>/visualizar')
@login_required
def visualizar_modelo(id_modelo):
    """Visualização read-only de um modelo de relatório."""
    modelo = ModeloRelatorio.query.get_or_404(id_modelo)
    return render_conteudo(
        ['components/configuracoes/visualizar_modelo.html'],
        modelo=modelo,
    )


@configuracoes_bp.route(
    '/modelo/<int:id_modelo>/editar',
    methods=['GET', 'POST']
)
@login_required
def editar_modelo(id_modelo):
    """Edita um modelo de relatório."""
    modelo = ModeloRelatorio.query.get_or_404(id_modelo)
    if request.method == 'POST':
        modelo.nome_modelo = request.form.get(
            'nome_modelo', modelo.nome_modelo
        )
        modelo.descricao = request.form.get('descricao', modelo.descricao)
        modelo.ativo = 'ativo' in request.form
        try:
            db.session.commit()
            flash('Modelo atualizado com sucesso.', 'sucesso')
            return redirect(url_for('configuracoes.biblioteca_formatacao'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Erro ao atualizar modelo: {e}', 'erro')
    return render_conteudo(
        ['components/configuracoes/editar_modelo.html'],
        modelo=modelo,
    )


@configuracoes_bp.route(
    '/modelo/<int:id_modelo>/excluir',
    methods=['POST']
)
@login_required
def excluir_modelo(id_modelo):
    """Exclui modelo e todos os relatórios base vinculados."""
    modelo = ModeloRelatorio.query.get_or_404(id_modelo)
    nome = modelo.nome_modelo
    try:
        # Remove relatórios base vinculados
        for rb in modelo.relatorios_base:
            if rb.caminho_arquivo and os.path.exists(rb.caminho_arquivo):
                os.remove(rb.caminho_arquivo)
            db.session.delete(rb)
        db.session.delete(modelo)
        db.session.commit()
        flash(f'Modelo "{nome}" excluído.', 'sucesso')
    except (OSError, IOError) as e:
        db.session.rollback()
        flash(f'Erro ao excluir modelo: {e}', 'erro')
    return redirect(
        url_for('configuracoes.biblioteca_relatorios_base')
    )


# --- Relatório Base ---


@configuracoes_bp.route('/relatorio-base/<int:id_relatorio>')
@login_required
def detalhe_relatorio_base(id_relatorio):
    """Detalhes de um relatório base."""
    relatorio = RelatorioBase.query.get_or_404(id_relatorio)
    return render_conteudo(
        ['components/configuracoes/detalhe_relatorio_base.html'],
        relatorio=relatorio,
    )


@configuracoes_bp.route(
    '/relatorio-base/<int:id_relatorio>/excluir',
    methods=['POST']
)
@login_required
def excluir_relatorio_base(id_relatorio):
    """Exclui relatório base e remove arquivo."""
    relatorio = RelatorioBase.query.get_or_404(id_relatorio)
    titulo = relatorio.titulo
    try:
        if (relatorio.caminho_arquivo and
                os.path.exists(relatorio.caminho_arquivo)):
            os.remove(relatorio.caminho_arquivo)
        db.session.delete(relatorio)
        db.session.commit()
        flash(
            f'Relatório base "{titulo}" excluído.',
            'sucesso'
        )
    except (OSError, IOError) as e:
        db.session.rollback()
        flash(f'Erro ao excluir relatório: {e}', 'erro')
    return redirect(
        url_for('configuracoes.biblioteca_relatorios_base')
    )
