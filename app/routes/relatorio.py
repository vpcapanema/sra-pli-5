"""Rotas de relatórios do SRA."""

import os
import shutil
import locale
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
from app.models.envio_conteudo import EnvioConteudo
from app.models.previsualizacao_conteudo import PrevisualizacaoConteudo
from app.models.dominio import DomStatusRelatorio
from app.models.biblioteca_formatacao import (
    BibliotecaFormatacaoCanonica
)
from app.services.servico_relatorio import ServicoRelatorio
from app.services.servico_extracao_canonica import ServicoExtracaoCanonica
from app.services.servico_envio_autor import ServicoEnvioAutor
from app.utils.htmx import render_conteudo

relatorio_bp = Blueprint(
    'relatorio', __name__, url_prefix='/relatorio'
)


def _criar_capitulo_recursivo(cap_dict, id_relatorio, id_pai, ordem, indice_pai=''):
    """Cria capítulo recursivamente a partir da árvore extraída do DOCX."""
    # Calcular índice do capítulo atual
    indice = f"{indice_pai}{ordem}" if indice_pai else str(ordem)

    # Usar tipo_elemento do dicionário extraído, ou 'textual' como padrão
    tipo = cap_dict.get('tipo_elemento', 'textual')

    capitulo = CapituloDocumento(
        id_relatorio=id_relatorio,
        id_capitulo_pai=id_pai,
        titulo_capitulo=cap_dict['titulo'],
        ordem_capitulo=ordem,
        nivel_capitulo=cap_dict['nivel'],
        tipo_elemento=tipo,
        indice_capitulo=indice,
        status_capitulo='em_edicao'
    )
    db.session.add(capitulo)
    db.session.flush()  # Para obter o ID antes de criar filhos

    # Criar filhos recursivamente
    ordem_filho = 1
    for filho in cap_dict['filhos']:
        _criar_capitulo_recursivo(
            filho, id_relatorio, capitulo.id_capitulo_documento,
            ordem_filho, f"{indice}."
        )
        ordem_filho += 1


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
    from sqlalchemy import text

    conn = db.session.connection()
    result = conn.execute(text("""
        SELECT * FROM vw_todos_relatorios
        ORDER BY data_criacao DESC
    """))

    relatorios = []
    for row in result:
        relatorios.append({
            'id': row.id,
            'tipo_relatorio': row.tipo_relatorio,
            'codigo': row.codigo,
            'titulo': row.titulo,
            'numero_medicao': row.numero_medicao,
            'mes_referencia': row.mes_referencia,
            'ano_referencia': row.ano_referencia,
            'periodo_inicio': row.periodo_inicio,
            'periodo_fim': row.periodo_fim,
            'status_codigo': row.status_codigo,
            'status_descricao': row.status_descricao,
            'data_criacao': row.data_criacao,
            'versao': row.versao,
            'criador_nome': row.criador_nome
        })

    return render_conteudo(
        ['relatorio/panorama.html'],
        relatorios=relatorios
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
def relatorios_base():
    """Lista relatórios base disponíveis."""
    relatorios = ServicoRelatorio.listar_relatorios_finalizados()
    return render_conteudo(
        ['relatorio/relatorios_base.html'],
        relatorios_finalizados=relatorios
    )


@relatorio_bp.route('/base/novo', methods=['POST'])
def criar_relatorio_base():
    """Cria um novo relatório base."""
    arquivo = request.files.get('arquivo_docx')
    if not arquivo or not arquivo.filename.endswith('.docx'):
        flash('Envie um arquivo .docx válido.', 'erro')
        return redirect(url_for('relatorio.relatorios_base'))

    # Salvar arquivo
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    dir_relatorios = os.path.join(base_dir, 'storage', 'relatorios_base')
    os.makedirs(dir_relatorios, exist_ok=True)
    nome_seguro = secure_filename(arquivo.filename)
    caminho = os.path.join(dir_relatorios, nome_seguro)
    arquivo.save(caminho)

    # NOTE: Implementar criar_relatorio_base em ServicoRelatorio
    # Por enquanto, usar criar_relatorio_finalizado
    flash('Funcionalidade em desenvolvimento.', 'info')
    return redirect(
        url_for('relatorio.relatorios_base')
    )


@relatorio_bp.route('/producao')
def relatorios_producao():
    """Lista relatórios em produção."""
    relatorios = RelatorioProducao.query.order_by(
        RelatorioProducao.criado_em.desc()
    ).all()
    return render_conteudo(
        ['relatorio/relatorios_producao.html'],
        relatorios_producao=relatorios
    )


@relatorio_bp.route('/versao-trabalho')
def versao_trabalho():
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
def capitulos():
    """Lista de relatórios de produção - redireciona para detalhe."""
    relatorios = ServicoRelatorio.listar_relatorios_producao()
    return render_conteudo(
        ['relatorio/capitulos.html'],
        relatorios_producao=relatorios
    )


@relatorio_bp.route('/editor')
def editor():
    """Lista de relatórios para edição - redireciona para editor específico."""
    relatorios = ServicoRelatorio.listar_relatorios_producao()
    return render_conteudo(
        ['relatorio/editor.html'],
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
                id_versao=versao.id_versao_trabalho)
    )


@relatorio_bp.route('/versao-trabalho/<int:id_versao>')
def detalhe_versao(id_versao):
    """Detalhes de uma versão de trabalho."""
    versao = ServicoRelatorio.obter_versao_trabalho(id_versao)
    if not versao:
        flash('Versão de trabalho não encontrada.', 'erro')
        return redirect(url_for('relatorio.relatorios_producao'))
    lista_capitulos = ServicoRelatorio.listar_capitulos(id_versao)
    capitulos_flat = CapituloDocumento.query.filter_by(
        id_relatorio=id_versao
    ).order_by(CapituloDocumento.ordem_capitulo).all()
    bibliotecas = BibliotecaFormatacaoCanonica.query.filter_by(
        ativa=True
    ).all()
    autores = Usuario.query.filter(
        Usuario.perfil_id.in_([1, 2, 3]),  # NOTE: usar codigo do perfil
        Usuario.ativo
    ).order_by(Usuario.nome).all()
    # Relatórios em produção para o seletor
    relatorios_producao = db.session.query(RelatorioProducao).join(
        DomStatusRelatorio,
        RelatorioProducao.status_id == DomStatusRelatorio.id
    ).filter(
        DomStatusRelatorio.codigo == 'em_producao'
    ).order_by(RelatorioProducao.criado_em.desc()).all()
    componentes = [
        'components/relatorio/arvore_capitulos.html',
    ]
    return render_conteudo(
        componentes,
        perfil_ativo=session.get('perfil_ativo', ''),
        versao_trabalho=versao,
        capitulos=lista_capitulos,
        capitulos_flat=capitulos_flat,
        bibliotecas_disponiveis=bibliotecas,
        autores_disponiveis=autores,
        relatorios_producao=relatorios_producao,
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
        url_for('relatorio.detalhe_versao', id_versao=id_versao)
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
        return redirect(url_for('relatorio.relatorios_producao'))
    id_bib = request.form.get('id_biblioteca', type=int)
    if id_bib:
        versao.id_biblioteca_formatacao_canonica = id_bib
        db.session.commit()
        flash('Biblioteca vinculada com sucesso.', 'sucesso')
    else:
        flash('Selecione uma biblioteca.', 'erro')
    return redirect(url_for('relatorio.detalhe_versao', id_versao=id_versao))


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
    return redirect(url_for('relatorio.detalhe_versao', id_versao=id_versao))


# ==============================================================
# Editor do Autor
# ==============================================================

@relatorio_bp.route('/versao-trabalho/<int:id_versao>/editor-autor')
def editor_autor(id_versao):
    """Tela de edição de conteúdo do autor."""
    versao = ServicoRelatorio.obter_versao_trabalho(id_versao)
    if not versao:
        flash('Versão não encontrada.', 'erro')
        return redirect(url_for('relatorio.relatorios_producao'))
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
        return redirect(url_for('relatorio.relatorios_producao'))
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

    # Obter status inicial (em_producao)
    status_inicial = DomStatusRelatorio.query.filter_by(
        codigo='em_producao'
    ).first()

    if not status_inicial:
        flash('Status inicial não configurado.', 'erro')
        return redirect(url_for('principal.index'))

    # Processar arquivo DOCX se fornecido
    caminho_template = None
    arquivo = request.files.get('arquivo_docx')
    if arquivo and arquivo.filename.endswith('.docx'):
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))
        )
        dir_relatorios_producao = os.path.join(
            base_dir, 'storage', 'relatorios_producao'
        )
        os.makedirs(dir_relatorios_producao, exist_ok=True)
        nome_seguro = secure_filename(arquivo.filename)
        caminho_template = os.path.join(
            dir_relatorios_producao, nome_seguro
        )
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


def _parse_mes_referencia_br(valor):
    """Parse string de mês em PT-BR (ex: 'maio de 2026') para date."""
    if not valor:
        return None
    meses_pt = {
        'janeiro': 1, 'fevereiro': 2, 'março': 3, 'marco': 3,
        'abril': 4, 'maio': 5, 'junho': 6, 'julho': 7,
        'agosto': 8, 'setembro': 9, 'outubro': 10,
        'novembro': 11, 'dezembro': 12,
    }
    v = valor.strip().lower()
    # Aceita "maio de 2026", "maio 2026", "2026-05-01"
    try:
        return datetime.strptime(valor, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        pass
    for nome, n in meses_pt.items():
        if v.startswith(nome):
            resto = v[len(nome):].strip().lstrip('de ').strip()
            try:
                ano = int(resto[:4])
                return datetime(ano, n, 1).date()
            except (ValueError, TypeError):
                return None
    return None


def _parse_data_iso(valor):
    """Parse 'YYYY-MM-DD' tolerante."""
    if not valor:
        return None
    try:
        return datetime.strptime(valor, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


@relatorio_bp.route('/producao/clonar-biblioteca', methods=['POST'])
def clonar_da_biblioteca():
    """Clona um relatório finalizado da biblioteca para produção.

    Idempotente: se já existir um RelatorioProducao com mesmo
    titulo_curto, devolve-o em vez de criar duplicado.
    """
    perfil = session.get('perfil_ativo')
    if perfil not in ('coordenador', 'admin'):
        return jsonify({'erro': 'Acesso restrito'}), 403

    payload = request.get_json(silent=True) or {}
    arquivo_base = payload.get('arquivo_base')
    biblioteca_id = payload.get('biblioteca_id')
    titulo_curto = (payload.get('titulo_curto') or '').strip()
    codigo_pli = (payload.get('codigo_pli') or '').strip()

    if not arquivo_base:
        return jsonify({'erro': 'Arquivo não fornecido'}), 400
    if not biblioteca_id:
        return jsonify(
            {'erro': 'Biblioteca de formatação não fornecida'}
        ), 400

    status_inicial = DomStatusRelatorio.query.filter_by(
        codigo='em_producao'
    ).first()
    if not status_inicial:
        return jsonify({'erro': 'Status inicial não configurado'}), 500

    # Anti-duplicação: mesmo título e código → reaproveita
    if titulo_curto or codigo_pli:
        query = RelatorioProducao.query
        if titulo_curto:
            query = query.filter(
                RelatorioProducao.titulo_curto == titulo_curto
            )
        if codigo_pli:
            query = query.filter(
                RelatorioProducao.codigo_d20 == codigo_pli
            )
        existente = query.first()
        if existente:
            return jsonify({
                'mensagem': 'Já existe relatório com esses dados',
                'id_producao': existente.id,
                'duplicado': True,
                'logs': [{
                    'mensagem': (
                        'Relatório já existente — reutilizando registro'
                    ),
                    'status': 'success'
                }],
            }), 200

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    dir_base = os.path.join(base_dir, 'storage', 'relatorios_base')
    dir_producao = os.path.join(
        base_dir, 'storage', 'relatorios_producao'
    )
    os.makedirs(dir_producao, exist_ok=True)

    caminho_base = os.path.join(dir_base, arquivo_base)
    if not os.path.exists(caminho_base):
        return jsonify({'erro': 'Arquivo base não encontrado'}), 404

    nome_arquivo = titulo_curto or arquivo_base.replace('.docx', '')
    # Suffix com timestamp para evitar sobrescrita ao reclonar
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    nome_arquivo_seguro = secure_filename(
        f"{nome_arquivo}_{timestamp}.docx"
    )
    caminho_producao = os.path.join(dir_producao, nome_arquivo_seguro)
    shutil.copy2(caminho_base, caminho_producao)

    relatorio_producao = RelatorioProducao(
        codigo_d20=codigo_pli or 'D-20',
        numero_medicao=(
            int(payload['numero_medicao'])
            if payload.get('numero_medicao') else None
        ),
        mes_referencia=_parse_mes_referencia_br(
            payload.get('mes_referencia')
        ),
        periodo_inicio=_parse_data_iso(payload.get('periodo_inicio')),
        periodo_fim=_parse_data_iso(payload.get('periodo_fim')),
        titulo_curto=titulo_curto or None,
        status_id=status_inicial.id,
        criado_por=current_user.id,
        ano_referencia=(
            int(payload['ano_referencia'])
            if payload.get('ano_referencia') else None
        ),
        versao_atual='R00',
        bloqueio_edicao=False,
        caminho_template=caminho_producao,
        biblioteca_id=biblioteca_id,
    )
    db.session.add(relatorio_producao)
    db.session.commit()

    logs = [
        {'mensagem': 'Validando dados...', 'status': 'success'},
        {'mensagem': 'Copiando arquivo...', 'status': 'success'},
        {
            'mensagem': 'Criando relatório de produção...',
            'status': 'success'
        },
        {
            'mensagem': 'Configurando status inicial...',
            'status': 'success'
        },
        {
            'mensagem': 'Extraindo estrutura de capítulos...',
            'status': 'pending'
        },
    ]

    try:
        from docx import Document
        doc = Document(caminho_producao)
        capitulos_arvore = ServicoExtracaoCanonica._extrair_capitulos(doc)

        # Antes de inserir: garantir que não há capítulos existentes
        # para este relatório (defesa contra duplicação por re-clone).
        CapituloDocumento.query.filter_by(
            id_relatorio=relatorio_producao.id
        ).delete()

        ordem_global = 1
        total = 0
        for cap_raiz in capitulos_arvore:
            _criar_capitulo_recursivo(
                cap_raiz, relatorio_producao.id, None, ordem_global
            )
            ordem_global += 1
            total += 1

        db.session.commit()
        logs[-1] = {
            'mensagem': (
                f'Extraindo estrutura de capítulos... '
                f'({total} raízes; árvore deduplicada)'
            ),
            'status': 'success'
        }
    except Exception as e:
        db.session.rollback()
        logs[-1] = {
            'mensagem': f'Erro ao extrair capítulos: {e}',
            'status': 'error'
        }
        return jsonify({
            'erro': f'Erro ao extrair capítulos: {e}',
            'logs': logs,
        }), 500

    return jsonify({
        'mensagem': 'Clonagem realizada com sucesso',
        'id_producao': relatorio_producao.id,
        'logs': logs,
    })


@relatorio_bp.route(
    '/producao/<int:id_relatorio>/excluir',
    methods=['POST']
)
@login_required
def excluir_relatorio_producao(id_relatorio):
    """Exclui relatório de produção e remove arquivo do storage."""

    perfil = session.get('perfil_ativo')
    if perfil != 'coordenador' and perfil != 'admin':
        return jsonify({'erro': 'Acesso restrito a coordenadores.'}), 403

    relatorio = RelatorioProducao.query.get_or_404(id_relatorio)
    titulo = relatorio.titulo_curto or relatorio.codigo_d20 or 'Relatório'

    try:
        # Deletar capítulos associados primeiro
        from app.models.capitulo_documento import CapituloDocumento
        CapituloDocumento.query.filter_by(
            id_relatorio=id_relatorio
        ).delete()

        # Remover arquivo do storage/relatorios_producao
        if relatorio.caminho_template and os.path.exists(
            relatorio.caminho_template
        ):
            os.remove(relatorio.caminho_template)

        db.session.delete(relatorio)
        db.session.commit()
        return jsonify({'mensagem': f'Relatório "{titulo}" excluído com sucesso.'})
    except (OSError, IOError) as e:
        db.session.rollback()
        return jsonify({'erro': f'Erro ao excluir relatório: {e}'}), 500


@relatorio_bp.route('/producao/<int:id_relatorio>/gerar-final')
@login_required
def gerar_final(id_relatorio):
    """Gera e envia o DOCX final montado a partir dos capítulos."""
    vt = RelatorioProducao.query.get_or_404(id_relatorio)
    try:
        # Importação tardia para evitar ciclo de blueprints
        from app.routes.api import _gerar_docx_versao
        docx_bytes = _gerar_docx_versao(vt)
    except (ValueError, RuntimeError, OSError) as e:
        flash(f'Erro ao gerar relatório final: {e}', 'erro')
        return redirect(
            url_for('relatorio.detalhe_versao', id_versao=id_relatorio)
        )

    from io import BytesIO
    from flask import send_file
    return send_file(
        BytesIO(docx_bytes),
        as_attachment=True,
        download_name=f'relatorio_{vt.id}_{vt.versao_atual}.docx',
        mimetype=(
            'application/vnd.openxmlformats-officedocument'
            '.wordprocessingml.document'
        ),
    )


@relatorio_bp.route('/producao/<int:id_relatorio>/docx')
@login_required
def baixar_docx_producao(id_relatorio):
    """Serve o DOCX do relatório de produção para visualização."""
    relatorio = RelatorioProducao.query.get_or_404(id_relatorio)

    if not relatorio.caminho_template:
        return ('DOCX não disponível', 404)

    if not os.path.exists(relatorio.caminho_template):
        return ('Arquivo não encontrado', 404)

    from flask import send_file
    return send_file(
        relatorio.caminho_template,
        as_attachment=False,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


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

    # NOTE: Implementar extração de elementos DOCX
    # Usar ServicoExtracaoCanonica para extrair estrutura

    return jsonify({
        'mensagem': 'Upload realizado',
        'caminho': caminho
    })


# ==============================================================
# Envios de Conteúdo
# ==============================================================

# ==============================================================
# Upload, prévia e confirmação do autor
# ==============================================================

@relatorio_bp.route(
    '/versao-trabalho/<int:id_versao>/capitulo/<int:id_capitulo>/upload',
    methods=['GET', 'POST']
)
def upload_conteudo(id_versao, id_capitulo):
    """Tela de upload de conteúdo do autor para um capítulo."""
    versao = ServicoRelatorio.obter_versao_trabalho(id_versao)
    capitulo = CapituloDocumento.query.get_or_404(id_capitulo)
    if not versao or capitulo.id_relatorio != versao.id:
        flash('Capítulo não pertence à versão informada.', 'erro')
        return redirect(url_for('relatorio.relatorios_producao'))

    if request.method == 'POST':
        arquivo = request.files.get('arquivo_docx')
        if not arquivo or not (arquivo.filename or '').endswith('.docx'):
            flash('Envie um arquivo .docx válido.', 'erro')
            return redirect(url_for(
                'relatorio.upload_conteudo',
                id_versao=id_versao, id_capitulo=id_capitulo,
            ))
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(__file__))
        )
        try:
            envio = ServicoEnvioAutor.processar_upload(
                id_relatorio=id_versao,
                id_usuario=current_user.id,
                arquivo_storage=arquivo,
                base_dir=base_dir,
                id_capitulo_destino=id_capitulo,
            )
        except (OSError, ValueError) as e:
            flash(f'Falha no upload: {e}', 'erro')
            return redirect(url_for(
                'relatorio.upload_conteudo',
                id_versao=id_versao, id_capitulo=id_capitulo,
            ))
        flash(
            'Upload realizado. Revise a prévia e confirme a importação.',
            'sucesso'
        )
        return redirect(url_for(
            'relatorio.previa_envio',
            id_envio=envio.id_envio_conteudo,
        ))

    # GET: render tela
    envio = EnvioConteudo.query.filter_by(
        id_relatorio=id_versao,
        id_usuario=current_user.id,
        status_envio='em_previa',
    ).order_by(EnvioConteudo.criado_em.desc()).first()
    capitulos_nav = ServicoRelatorio.listar_capitulos(id_versao)
    return render_conteudo(
        ['components/capitulo/upload_docx.html'],
        versao_trabalho=versao,
        capitulo=capitulo,
        envio=envio,
        capitulos_nav=capitulos_nav,
        preview_html=None,
    )


@relatorio_bp.route('/envios-conteudo/<int:id_envio>/previa')
def previa_envio(id_envio):
    """Mostra prévias geradas a partir do envio para o autor confirmar."""
    envio = EnvioConteudo.query.get_or_404(id_envio)
    if (envio.id_usuario != current_user.id
            and session.get('perfil_ativo') not in ('coordenador', 'admin')):
        flash('Sem permissão.', 'erro')
        return redirect(url_for('principal.index'))

    previas = envio.previsualizacoes
    versao = ServicoRelatorio.obter_versao_trabalho(envio.id_relatorio)
    return render_conteudo(
        ['components/capitulo/previa_envio.html'],
        envio=envio,
        previas=previas,
        versao_trabalho=versao,
    )


@relatorio_bp.route(
    '/envios-conteudo/<int:id_envio>/confirmar/<acao>',
    methods=['POST']
)
def confirmar_envio(id_envio, acao):
    """Aplica decisão do autor: importar ou rejeitar."""
    envio = EnvioConteudo.query.get_or_404(id_envio)
    if (envio.id_usuario != current_user.id
            and session.get('perfil_ativo') not in ('coordenador', 'admin')):
        flash('Sem permissão.', 'erro')
        return redirect(url_for('principal.index'))

    if acao not in ('importar', 'rejeitar'):
        flash('Ação inválida.', 'erro')
        return redirect(
            url_for('relatorio.previa_envio', id_envio=id_envio)
        )

    resultado = ServicoEnvioAutor.confirmar(envio=envio, acao=acao)
    if not resultado.get('ok'):
        flash(resultado.get('erro') or 'Falha ao processar.', 'erro')
        return redirect(
            url_for('relatorio.previa_envio', id_envio=id_envio)
        )

    if acao == 'importar':
        flash(
            f"Importado para {resultado.get('capitulos_atualizados', 0)} "
            f"capítulo(s).",
            'sucesso'
        )
    else:
        flash('Envio rejeitado.', 'info')

    return redirect(
        url_for('relatorio.detalhe_versao', id_versao=envio.id_relatorio)
    )


@relatorio_bp.route(
    '/envios-conteudo/<int:id_envio>/conteudo',
    methods=['POST']
)
def salvar_conteudo_autor(id_envio):
    """Alias de compatibilidade com o template de prévia.

    Aceita texto HTML editado pelo autor antes da confirmação.
    Atualmente, apenas marca o envio como atualizado.
    """
    envio = EnvioConteudo.query.get_or_404(id_envio)
    if envio.id_usuario != current_user.id:
        return jsonify({'erro': 'Sem permissão'}), 403
    # Persistência do HTML editado: associa como prévia 'editada'.
    dados = request.get_data(as_text=True) or ''
    if dados:
        prev = PrevisualizacaoConteudo(
            id_envio_conteudo=envio.id_envio_conteudo,
            tipo_previsualizacao='editada',
            resultado_html=dados,
        )
        db.session.add(prev)
        db.session.commit()
    return jsonify({'ok': True})


@relatorio_bp.route('/envios-conteudo')
def listar_envios_conteudo():
    """Lista envios de conteúdo filtrando por relatório."""
    id_relatorio = request.args.get('id_relatorio', type=int)

    if id_relatorio:
        envios = EnvioConteudo.query.filter_by(
            id_relatorio=id_relatorio
        ).order_by(EnvioConteudo.criado_em.desc()).all()
    else:
        envios = []

    return render_conteudo(
        ['components/relatorio/tabela_envios_conteudo.html'],
        envios=envios
    )


@relatorio_bp.route('/todos-relatorios')
def listar_todos_relatorios():
    """Lista todos os relatórios da VIEW vw_todos_relatorios."""
    from sqlalchemy import text

    conn = db.session.connection()
    result = conn.execute(text("""
        SELECT * FROM vw_todos_relatorios
        ORDER BY data_criacao DESC
    """))

    relatorios = []
    for row in result:
        relatorios.append({
            'id': row.id,
            'tipo_relatorio': row.tipo_relatorio,
            'codigo': row.codigo,
            'titulo': row.titulo,
            'numero_medicao': row.numero_medicao,
            'mes_referencia': row.mes_referencia,
            'ano_referencia': row.ano_referencia,
            'periodo_inicio': row.periodo_inicio,
            'periodo_fim': row.periodo_fim,
            'status_codigo': row.status_codigo,
            'status_descricao': row.status_descricao,
            'data_criacao': row.data_criacao,
            'versao': row.versao,
            'criador_nome': row.criador_nome
        })

    # Se for chamado via HTMX para o seletor, retorna o seletor
    if request.args.get('seletor') == 'true':
        return render_conteudo(
            ['components/relatorio/seletor_relatorio.html'],
            relatorios=relatorios,
            id_relatorio_selecionado=None
        )

    return render_conteudo(
        ['components/relatorio/tabela_todos_relatorios.html'],
        relatorios=relatorios
    )
