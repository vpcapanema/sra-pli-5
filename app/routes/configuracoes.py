"""Rotas de configuração do SRA."""

import os

from flask import (
    Blueprint, redirect, url_for, request, flash,
    render_template, send_file, jsonify
)
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from app.models.biblioteca_formatacao import BibliotecaFormatacaoCanonica
from app.models.modelo_relatorio import ModeloRelatorio
from app.models.relatorio_base import RelatorioBase
from app.models.relatorio_finalizado import RelatorioFinalizado
from app.services.servico_configuracoes import (
    atualizar_biblioteca_formatacao,
    atualizar_modelo,
    atualizar_relatorio_finalizado_inline,
    carregar_parametros_biblioteca,
    criar_biblioteca_formatacao as criar_biblioteca_formatacao_service,
    criar_relatorio_base_finalizado,
    excluir_biblioteca_formatacao as excluir_biblioteca_formatacao_service,
    excluir_modelo as excluir_modelo_service,
    excluir_relatorio_base as excluir_relatorio_base_service,
    excluir_relatorio_finalizado as excluir_relatorio_finalizado_service,
)
from app.services.servico_relatorio import ServicoRelatorio
from app.utils.htmx import render_conteudo

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
    ok, msg = criar_biblioteca_formatacao_service(
        request.form,
        request.files.get('arquivo_docx'),
    )
    flash(msg, 'sucesso' if ok else 'erro')
    return redirect(url_for('configuracoes.biblioteca_formatacao'))


@configuracoes_bp.route(
    '/biblioteca-formatacao/<int:id_bib>/parametros'
)
@login_required
def ver_biblioteca_formatacao(id_bib):
    """Página dedicada de visualização interativa dos parâmetros."""
    bib = BibliotecaFormatacaoCanonica.query.get_or_404(id_bib)
    parametros = carregar_parametros_biblioteca(bib)

    return render_template(
        'visualizador_parametros.html',
        bib=bib,
        **parametros,
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
        ok, msg, bib = atualizar_biblioteca_formatacao(id_bib, request.form)
        flash(msg, 'sucesso' if ok else 'erro')
        if ok:
            return redirect(url_for('configuracoes.biblioteca_formatacao'))
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
    ok, msg = excluir_biblioteca_formatacao_service(id_bib)
    flash(msg, 'sucesso' if ok else 'erro')
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
    ok, msg = criar_relatorio_base_finalizado(
        request.form,
        request.files.get('arquivo_docx'),
        current_user.id,
    )
    flash(msg, 'sucesso' if ok else 'erro')
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
    '/relatorio-finalizado/<int:id_relatorio>/editar-inline',
    methods=['PUT']
)
@login_required
def editar_relatorio_finalizado_inline(id_relatorio):
    """Edição inline de campos do relatório finalizado."""
    dados = request.get_json(silent=True) or {}
    try:
        relatorio = atualizar_relatorio_finalizado_inline(
            id_relatorio, dados
        )
        return jsonify({
            'mensagem': 'Relatório atualizado.',
            'dados': {
                'id': relatorio.id,
                'titulo': relatorio.titulo or '',
                'codigo': relatorio.codigo or '',
                'versao': relatorio.versao,
                'numero_medicao': relatorio.numero_medicao,
            }
        })
    except Exception as e:
        return jsonify(
            {'erro': f'Erro ao atualizar: {e}'}
        ), 500


@configuracoes_bp.route(
    '/relatorio-finalizado/<int:id_relatorio>/excluir',
    methods=['POST']
)
@login_required
def excluir_relatorio_finalizado(id_relatorio):
    """Exclui relatório finalizado e remove arquivo."""
    ok, msg = excluir_relatorio_finalizado_service(id_relatorio)
    flash(msg, 'sucesso' if ok else 'erro')
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
        ok, msg, modelo = atualizar_modelo(id_modelo, request.form)
        flash(msg, 'sucesso' if ok else 'erro')
        if ok:
            return redirect(url_for('configuracoes.biblioteca_formatacao'))
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
    ok, msg = excluir_modelo_service(id_modelo)
    flash(msg, 'sucesso' if ok else 'erro')
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
    ok, msg = excluir_relatorio_base_service(id_relatorio)
    flash(msg, 'sucesso' if ok else 'erro')
    return redirect(
        url_for('configuracoes.biblioteca_relatorios_base')
    )
