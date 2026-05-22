"""Rotas de relatórios do SRA."""

import os
import shutil
from datetime import datetime

from flask import (
    Blueprint, redirect, render_template,
    url_for, flash, request, session, jsonify
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from app.models.usuario import Usuario
from app.models.capitulo_documento import CapituloDocumento
from app.models.relatorio_producao import RelatorioProducao
from app.models.dominio import DomStatusRelatorio
from app.models.biblioteca_formatacao import (
    BibliotecaFormatacaoCanonica
)
from app.services.servico_relatorio import ServicoRelatorio
from app.utils.htmx import render_conteudo

relatorio_bp = Blueprint(
    'relatorio', __name__, url_prefix='/relatorio'
)


@relatorio_bp.before_request
@login_required
def verificar_acesso():
    """Verifica se o usuário tem perfil autorizado."""
    perfil = session.get('perfil_ativo')
    if perfil not in ('coordenador', 'admin', 'autor'):
        flash('Acesso restrito.', 'erro')
        return redirect(url_for('principal.index'))


@relatorio_bp.route('/panorama')
def panorama():
    """Exibe panorama de relatórios."""
    linhas = ServicoRelatorio.panorama()
    return render_conteudo(
        ['components/relatorio/panorama_relatorios.html'],
        perfil_ativo=session.get('perfil_ativo', ''),
        panorama=linhas
    )


@relatorio_bp.route('/modelos')
def listar_modelos():
    """Lista modelos de relatório."""
    modelos = ServicoRelatorio.listar_modelos(
        apenas_ativos=False
    )
    return render_conteudo(
        ['components/relatorio/lista_modelos.html'],
        perfil_ativo=session.get('perfil_ativo', ''),
        modelos=modelos
    )


@relatorio_bp.route('/modelos/novo', methods=['POST'])
def criar_modelo():
    """Cria um novo modelo de relatório."""
    ServicoRelatorio.criar_modelo(
        nome_modelo=request.form.get('nome_modelo'),
        descricao=request.form.get('descricao')
    )
    flash('Modelo criado com sucesso.', 'sucesso')
    return redirect(url_for('relatorio.listar_modelos'))


@relatorio_bp.route('/base')
def listar_relatorios_base():
    """Lista relatórios base disponíveis."""
    relatorios = ServicoRelatorio.listar_relatorios_base()
    modelos = ServicoRelatorio.listar_modelos()
    return render_conteudo(
        ['components/relatorio/lista_relatorios_base.html'],
        perfil_ativo=session.get('perfil_ativo', ''),
        relatorios_base=relatorios,
        modelos=modelos
    )


@relatorio_bp.route('/base/novo', methods=['POST'])
def criar_relatorio_base():
    """Cria um novo relatório base."""
    arquivo = request.files.get('arquivo_docx')
    if not arquivo or not arquivo.filename.endswith('.docx'):
        flash('Envie um arquivo .docx válido.', 'erro')
        return redirect(url_for('relatorio.listar_relatorios_base'))

    # Salvar arquivo
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    dir_relatorios = os.path.join(base_dir, 'storage', 'relatorios_base')
    os.makedirs(dir_relatorios, exist_ok=True)
    nome_seguro = secure_filename(arquivo.filename)
    caminho = os.path.join(dir_relatorios, nome_seguro)
    arquivo.save(caminho)

    # TODO: Implementar criar_relatorio_base em ServicoRelatorio
    # Por enquanto, usar criar_relatorio_finalizado
    flash('Funcionalidade em desenvolvimento.', 'info')
    return redirect(
        url_for('relatorio.listar_relatorios_base')
    )


@relatorio_bp.route('/versao-trabalho')
def listar_versoes():
    """Lista versões de trabalho."""
    versoes = ServicoRelatorio.listar_versoes_trabalho()
    relatorios = ServicoRelatorio.listar_relatorios_base()
    return render_conteudo(
        ['components/relatorio/card_cadastro_relatorio_versao_trabalho.html'],
        perfil_ativo=session.get('perfil_ativo', ''),
        versoes_trabalho=versoes,
        relatorios_base=relatorios
    )


@relatorio_bp.route('/capitulos')
def painel_capitulos():
    """Lista de relatórios de produção - redireciona para detalhe."""
    relatorios = ServicoRelatorio.listar_relatorios_producao()
    return render_conteudo(
        ['components/relatorio/lista_relatorios_producao.html'],
        perfil_ativo=session.get('perfil_ativo'),
        relatorios_producao=relatorios
    )


@relatorio_bp.route('/editor')
def painel_editor():
    """Lista de relatórios para edição - redireciona para editor específico."""
    relatorios = ServicoRelatorio.listar_relatorios_producao()
    perfil = session.get('perfil_ativo')
    return render_conteudo(
        ['components/relatorio/lista_relatorios_producao.html'],
        perfil_ativo=perfil,
        relatorios_producao=relatorios
    )


@relatorio_bp.route('/versao-trabalho/nova', methods=['POST'])
def criar_versao():
    """Cria uma nova versão de trabalho."""
    versao = ServicoRelatorio.criar_versao_trabalho(
        id_relatorio_base=request.form.get(
            'id_relatorio_base', type=int
        ),
        titulo=request.form.get('titulo')
    )
    flash('Versão de trabalho criada com sucesso.', 'sucesso')
    return redirect(
        url_for('relatorio.detalhe_versao',
                id=versao.id_versao_trabalho)
    )


@relatorio_bp.route('/versao-trabalho/<int:id_versao>')
def detalhe_versao(id_versao):
    """Detalhes de uma versão de trabalho."""
    versao = ServicoRelatorio.obter_versao_trabalho(id)
    if not versao:
        flash('Versão de trabalho não encontrada.', 'erro')
        return redirect(url_for('relatorio.listar_versoes'))
    capitulos = ServicoRelatorio.listar_capitulos(id_versao)
    capitulos_flat = CapituloDocumento.query.filter_by(
        id_relatorio=id_versao
    ).order_by(CapituloDocumento.ordem_capitulo).all()
    bibliotecas = BibliotecaFormatacaoCanonica.query.filter_by(
        ativa=True
    ).all()
    autores = Usuario.query.filter(
        Usuario.perfil_id.in_([1, 2, 3]),  # TODO: usar codigo do perfil
        Usuario.ativo
    ).order_by(Usuario.nome).all()
    componentes = [
        'components/relatorio/arvore_capitulos.html',
        'components/paineis/painel_capitulos_coordenador.html',
    ]
    return render_conteudo(
        componentes,
        perfil_ativo=session.get('perfil_ativo', ''),
        versao_trabalho=versao,
        capitulos=capitulos,
        capitulos_flat=capitulos_flat,
        bibliotecas_disponiveis=bibliotecas,
        autores_disponiveis=autores,
    )


@relatorio_bp.route(
    '/versao-trabalho/<int:id_versao>/capitulo/novo',
    methods=['POST']
)
def criar_capitulo(id_versao):
    """Cria um novo capítulo na versão de trabalho."""
    ServicoRelatorio.criar_capitulo(
        id_relatorio=id_versao,
        titulo_capitulo=request.form.get('titulo_capitulo'),
        ordem_capitulo=request.form.get(
            'ordem_capitulo', type=int
        ),
        nivel_capitulo=request.form.get(
            'nivel_capitulo', type=int, default=1
        ),
        id_capitulo_pai=request.form.get(
            'id_capitulo_pai', type=int
        ),
        nome_capitulo=request.form.get('nome_capitulo'),
        indice_capitulo=request.form.get('indice_capitulo')
    )
    flash('Capítulo adicionado.', 'sucesso')
    return redirect(
        url_for('relatorio.detalhe_versao', id=id_versao)
    )


# ==============================================================
# Vincular Biblioteca Canônica
# ==============================================================

@relatorio_bp.route(
    '/versao-trabalho/<int:id_versao>/vincular-biblioteca',
    methods=['POST']
)
def vincular_biblioteca(id_versao):
    """Vincula uma biblioteca de formatação canônica à versão."""
    versao = ServicoRelatorio.obter_versao_trabalho(id_versao)
    if not versao:
        flash('Versão não encontrada.', 'erro')
        return redirect(url_for('relatorio.listar_versoes'))
    id_bib = request.form.get('id_biblioteca', type=int)
    if id_bib:
        versao.id_biblioteca_formatacao_canonica = id_bib
        db.session.commit()
        flash('Biblioteca vinculada com sucesso.', 'sucesso')
    else:
        flash('Selecione uma biblioteca.', 'erro')
    return redirect(url_for('relatorio.detalhe_versao', id=id))


# ==============================================================
# Atribuir Responsável a Capítulo
# ==============================================================

@relatorio_bp.route(
    '/versao-trabalho/<int:id_versao>/capitulo/<int:id_capitulo>/atribuir',
    methods=['POST']
)
def atribuir_responsavel(id_versao, id_capitulo):
    """Coordenador atribui um responsável a um capítulo."""
    cap = CapituloDocumento.query.get_or_404(id_capitulo)
    id_resp = request.form.get('id_usuario_responsavel', type=int)
    cap.id_usuario_responsavel = id_resp if id_resp else None
    db.session.commit()
    flash('Responsável atualizado.', 'sucesso')
    return redirect(url_for('relatorio.detalhe_versao', id=id_versao))


# ==============================================================
# Editor do Autor
# ==============================================================

@relatorio_bp.route('/versao-trabalho/<int:id_versao>/editor-autor')
def editor_autor(id_versao):
    """Tela de edição de conteúdo do autor."""
    versao = ServicoRelatorio.obter_versao_trabalho(id_versao)
    if not versao:
        flash('Versão não encontrada.', 'erro')
        return redirect(url_for('relatorio.listar_versoes'))
    return render_template(
        'editor_autor.html',
        versao=versao,
    )


# ==============================================================
# Editor do Coordenador (Revisão)
# ==============================================================

@relatorio_bp.route('/versao-trabalho/<int:id_versao>/editor-coordenador')
def editor_coordenador(id_versao):
    """Tela de revisão e edição do coordenador."""
    versao = ServicoRelatorio.obter_versao_trabalho(id_versao)
    if not versao:
        flash('Versão não encontrada.', 'erro')
        return redirect(url_for('relatorio.listar_versoes'))
    return render_template(
        'editor_coordenador.html',
        versao=versao,
    )


# ==============================================================
# Criar Relatório de Produção
# ==============================================================

@relatorio_bp.route(
    '/producao/novo', methods=['POST']
)
def criar_relatorio_producao():
    """Cria relatório de produção com base em informações cadastrais."""
    perfil = session.get('perfil_ativo')
    if perfil != 'coordenador' and perfil != 'admin':
        flash('Acesso restrito a coordenadores.', 'erro')
        return redirect(url_for('principal.index'))

    # Obter status inicial (em_edicao)
    status_inicial = DomStatusRelatorio.query.filter_by(
        codigo='em_edicao'
    ).first()

    if not status_inicial:
        flash('Status inicial não configurado.', 'erro')
        return redirect(url_for('principal.index'))

    # Processar arquivo DOCX se fornecido
    caminho_template = None
    arquivo = request.files.get('arquivo_docx')
    if arquivo and arquivo.filename.endswith('.docx'):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        dir_templates = os.path.join(base_dir, 'storage', 'templates_producao')
        os.makedirs(dir_templates, exist_ok=True)
        nome_seguro = secure_filename(arquivo.filename)
        caminho_template = os.path.join(dir_templates, nome_seguro)
        arquivo.save(caminho_template)

    # Criar relatório de produção
    relatorio = RelatorioProducao(
        codigo_d20=request.form.get('codigo_pli'),
        numero_medicao=request.form.get('numero_medicao', type=int),
        mes_referencia=datetime.strptime(
            request.form.get('mes_referencia'), '%B de %Y'
        ) if request.form.get('mes_referencia') else None,
        periodo_inicio=datetime.strptime(
            request.form.get('periodo_inicio'), '%Y-%m-%d'
        ) if request.form.get('periodo_inicio') else None,
        periodo_fim=datetime.strptime(
            request.form.get('periodo_fim'), '%Y-%m-%d'
        ) if request.form.get('periodo_fim') else None,
        titulo_curto=request.form.get('titulo_curto'),
        status_id=status_inicial.id,
        criado_por=current_user.id,
        ano_referencia=request.form.get('ano_referencia', type=int),
        versao_atual='R00',
        bloqueio_edicao=False,
        caminho_template=caminho_template
    )

    db.session.add(relatorio)
    db.session.commit()

    flash('Relatório de produção criado com sucesso.', 'sucesso')
    return redirect(
        url_for('relatorio.detalhe_versao', id_versao=relatorio.id)
    )


@relatorio_bp.route('/producao/clonar-biblioteca', methods=['POST'])
def clonar_da_biblioteca():
    """Clona um relatório finalizado da biblioteca para produção."""

    perfil = session.get('perfil_ativo')
    if perfil != 'coordenador' and perfil != 'admin':
        return jsonify({'erro': 'Acesso restrito'}), 403

    arquivo_base = request.json.get('arquivo_base')
    if not arquivo_base:
        return jsonify({'erro': 'Arquivo não fornecido'}), 400

    # Obter status inicial (em_edicao)
    status_inicial = DomStatusRelatorio.query.filter_by(
        codigo='em_edicao'
    ).first()

    if not status_inicial:
        return jsonify({'erro': 'Status inicial não configurado'}), 500

    # Copiar arquivo de storage/relatorios_base para
    # storage/relatorios_producao
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    dir_base = os.path.join(base_dir, 'storage', 'relatorios_base')
    dir_producao = os.path.join(base_dir, 'storage', 'relatorios_producao')
    os.makedirs(dir_producao, exist_ok=True)

    caminho_base = os.path.join(dir_base, arquivo_base)
    if not os.path.exists(caminho_base):
        return jsonify({'erro': 'Arquivo base não encontrado'}), 404

    # Nome do arquivo de produção: usar titulo_curto ou codigo
    nome_arquivo = (request.json.get('titulo_curto') or
                    arquivo_base.replace('.docx', ''))
    nome_arquivo_seguro = secure_filename(f"{nome_arquivo}.docx")
    caminho_producao = os.path.join(dir_producao, nome_arquivo_seguro)

    # Copiar arquivo
    shutil.copy2(caminho_base, caminho_producao)

    # Criar RelatorioProducao
    relatorio_producao = RelatorioProducao(
        codigo_d20=request.json.get('codigo_pli'),
        numero_medicao=request.json.get('numero_medicao', type=int),
        mes_referencia=datetime.strptime(
            request.json.get('mes_referencia'), '%B de %Y'
        ) if request.json.get('mes_referencia') else None,
        periodo_inicio=datetime.strptime(
            request.json.get('periodo_inicio'), '%Y-%m-%d'
        ) if request.json.get('periodo_inicio') else None,
        periodo_fim=datetime.strptime(
            request.json.get('periodo_fim'), '%Y-%m-%d'
        ) if request.json.get('periodo_fim') else None,
        titulo_curto=request.json.get('titulo_curto'),
        status_id=status_inicial.id,
        criado_por=current_user.id,
        ano_referencia=request.json.get('ano_referencia', type=int),
        versao_atual='R00',
        bloqueio_edicao=False,
        caminho_template=caminho_producao
    )

    db.session.add(relatorio_producao)
    db.session.commit()

    return jsonify({
        'mensagem': 'Clonagem realizada com sucesso',
        'id_producao': relatorio_producao.id
    })


@relatorio_bp.route('/producao/upload-docx', methods=['POST'])
def upload_docx_clonagem():
    """Faz upload de DOCX para clonagem."""
    perfil = session.get('perfil_ativo')
    if perfil != 'coordenador' and perfil != 'admin':
        return jsonify({'erro': 'Acesso restrito'}), 403

    arquivo = request.files.get('arquivo_docx')
    if not arquivo or not arquivo.filename.endswith('.docx'):
        return jsonify({'erro': 'Arquivo inválido'}), 400

    # Salvar arquivo temporariamente
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    dir_temp = os.path.join(base_dir, 'storage', 'temp')
    os.makedirs(dir_temp, exist_ok=True)
    nome_seguro = secure_filename(arquivo.filename)
    caminho = os.path.join(dir_temp, nome_seguro)
    arquivo.save(caminho)

    # TODO: Implementar extração de elementos DOCX
    # Usar ServicoExtracaoCanonica para extrair estrutura

    return jsonify({
        'mensagem': 'Upload realizado',
        'caminho': caminho
    })
