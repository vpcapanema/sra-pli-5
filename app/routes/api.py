"""
API REST para o fluxo de edição colaborativa.
Consumida pelo editor React (docx-editor) embedado nas telas
de autor e coordenador.
"""

import os
import secrets
import time
from io import BytesIO

from flask import Blueprint, abort, jsonify, request, send_file, session
from flask_login import login_required, current_user

from app.models.relatorio_producao import RelatorioProducao
from app.models.biblioteca_formatacao import (
    BibliotecaFormatacaoCanonica
)
from app.models.envio_conteudo import EnvioConteudo
from app.services.servico_api_editor import (
    MAX_UPLOAD_BYTES,
    aprovar_capitulo_api,
    atualizar_capitulo_api,
    atualizar_renomeacao_envio as atualizar_renomeacao_envio_service,
    converter_html_para_docx,
    criar_capitulo_api,
    excluir_capitulo_api,
    extrair_conteudo_capitulo,
    finalizar_capitulo_api,
    finalizar_relatorio_api,
    gerar_segmento_docx,
    listar_autores_api,
    listar_capitulos_api,
    listar_segmentos_envio,
    obter_estrutura_envio,
    obter_versao_api,
    reprovar_capitulo_api,
    servir_docx_producao,
    usuario_pode_acessar_envio,
    vincular_biblioteca_api,
)
from app.services.servico_finalizar_relatorio import FinalizacaoError
# servico_motor_renderizacao removido pos Fase 1: o DOCX em producao
# (caminho_template) e a fonte unica; nao ha mais reconstrucao a
# partir de capitulos + conteudo_docx.
from app.utils.logger import sra_log_handler

# Rate limiting simples em memória
_rate_limit_store = {}
RATE_LIMIT_MAX = 60  # requests
RATE_LIMIT_WINDOW = 60  # segundos

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.before_request
def _rate_limit():
    """Rate limiting por IP — 60 req/min."""
    ip = request.remote_addr or '0.0.0.0'
    now = time.time()
    entry = _rate_limit_store.get(ip)
    if not entry or now - entry['start'] > RATE_LIMIT_WINDOW:
        _rate_limit_store[ip] = {'start': now, 'count': 1}
    else:
        entry['count'] += 1
        if entry['count'] > RATE_LIMIT_MAX:
            abort(429)


@api_bp.before_request
def _verificar_csrf():
    """Verifica CSRF token para requests mutantes (POST/PUT/PATCH/DELETE)."""
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        token = request.headers.get('X-CSRF-Token', '')
        if token != session.get('csrf_token', ''):
            if 'csrf_token' not in session:
                session['csrf_token'] = secrets.token_hex(32)
                return
            abort(403)


@api_bp.route('/csrf-token')
@login_required
def obter_csrf_token():
    """Retorna CSRF token para uso pelo frontend."""
    if 'csrf_token' not in session:
        session['csrf_token'] = secrets.token_hex(32)
    return jsonify({'token': session['csrf_token']})


# ==============================================================
# VERSÃO DE TRABALHO
# ==============================================================

@api_bp.route('/versoes-trabalho/<int:id_vt>')
@login_required
def obter_versao(id_vt):
    """Retorna dados da versão de trabalho com capítulos."""
    return jsonify(obter_versao_api(id_vt))


# ==============================================================
# CAPÍTULOS — CRUD
# ==============================================================

@api_bp.route('/versoes-trabalho/<int:id_vt>/capitulos')
@login_required
def listar_capitulos(id_vt):
    """Lista capítulos (raízes) da versão de trabalho."""
    return jsonify(listar_capitulos_api(id_vt))


@api_bp.route(
    '/versoes-trabalho/<int:id_vt>/capitulos',
    methods=['POST']
)
@login_required
def criar_capitulo(id_vt):
    """Cria um novo capítulo/subcapítulo."""
    capitulo = criar_capitulo_api(id_vt, request.get_json(), current_user.id)
    return jsonify(capitulo), 201


@api_bp.route('/capitulos/<int:id_cap>', methods=['PATCH'])
@login_required
def atualizar_capitulo(id_cap):
    """Atualiza metadados de um capítulo (coordenador only)."""
    _exigir_perfil('coordenador')
    capitulo = atualizar_capitulo_api(
        id_cap,
        request.get_json(),
        current_user.id,
    )
    return jsonify(capitulo)


@api_bp.route('/capitulos/<int:id_cap>', methods=['DELETE'])
@login_required
def excluir_capitulo(id_cap):
    """Soft-delete de um capítulo."""
    excluir_capitulo_api(id_cap)
    return '', 204


# ==============================================================
# ENVIOS DO AUTOR — blob DOCX original e segmentado por capítulo
# ==============================================================

@api_bp.route('/envios/<int:id_envio>/docx')
@login_required
def baixar_envio_docx(id_envio):
    """Serve o DOCX original do envio para visualização no editor.

    Acessível para o próprio autor que enviou e para coordenadores.
    """
    envio = EnvioConteudo.query.get_or_404(id_envio)
    if not usuario_pode_acessar_envio(
        envio, current_user.id, session.get('perfil_ativo')
    ):
        return jsonify({'erro': 'Sem permissão'}), 403
    if not envio.caminho_arquivo or not os.path.exists(envio.caminho_arquivo):
        return ('', 204)
    return send_file(
        envio.caminho_arquivo,
        mimetype=(
            'application/vnd.openxmlformats-officedocument'
            '.wordprocessingml.document'
        ),
        as_attachment=False,
        download_name=envio.nome_arquivo or f'envio_{id_envio}.docx',
    )


@api_bp.route('/envios/<int:id_envio>/estrutura')
@login_required
def buscar_estrutura_envio(id_envio):
    """Retorna a estrutura completa do DOCX enviado (capítulos, figuras, tabelas)."""  # noqa: E501
    envio = EnvioConteudo.query.get_or_404(id_envio)
    if not usuario_pode_acessar_envio(
        envio, current_user.id, session.get('perfil_ativo')
    ):
        return jsonify({'erro': 'Sem permissão'}), 403

    try:
        return jsonify(obter_estrutura_envio(id_envio))
    except ValueError as e:
        return jsonify({'erro': f'Erro ao carregar estrutura: {e}'}), 500


@api_bp.route(
    '/envios/<int:id_envio>/renomeacoes/<int:id_capitulo>',
    methods=['PATCH']
)
@login_required
def atualizar_renomeacao_envio(id_envio, id_capitulo):
    """Marca uma renomeação pendente como aprovada ou rejeitada.

    Restrito a coordenador/admin. Recebe JSON `{"aprovado": true|false}`.
    Persiste em `envio.sugestoes_json -> renomeacoes_pendentes`.
    """
    if session.get('perfil_ativo') not in ('coordenador', 'admin'):
        return jsonify({'erro': 'Sem permissão'}), 403

    payload = request.get_json(silent=True) or {}
    aprovado = bool(payload.get('aprovado'))
    resultado = atualizar_renomeacao_envio_service(
        id_envio, id_capitulo, aprovado
    )
    if resultado is None:
        return jsonify({'erro': 'Renomeação não encontrada'}), 404
    return jsonify(resultado)


@api_bp.route('/envios/<int:id_envio>/segmentos')
@login_required
def buscar_segmentos_envio(id_envio):
    """Retorna os segmentos (prévias) de um envio por capítulo."""
    envio = EnvioConteudo.query.get_or_404(id_envio)
    if not usuario_pode_acessar_envio(
        envio, current_user.id, session.get('perfil_ativo')
    ):
        return jsonify({'erro': 'Sem permissão'}), 403
    return jsonify({'segmentos': listar_segmentos_envio(id_envio)})


@api_bp.route('/envios/<int:id_envio>/capitulos/<int:id_capitulo>/docx')
@login_required
def baixar_envio_segmento_docx(id_envio, id_capitulo):
    """Serve o DOCX segmentado por capítulo para um envio.

    Gerado em memória a partir do DOCX original do envio + classificação:
    parte do DOCX que foi atribuída ao capítulo informado.
    """
    envio = EnvioConteudo.query.get_or_404(id_envio)
    if not usuario_pode_acessar_envio(
        envio, current_user.id, session.get('perfil_ativo')
    ):
        return jsonify({'erro': 'Sem permissão'}), 403
    try:
        blob = gerar_segmento_docx(id_envio, id_capitulo)
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400
    except (OSError, RuntimeError) as e:
        return jsonify({'erro': f'Falha ao gerar segmento: {e}'}), 500
    if not blob:
        return ('', 204)
    return send_file(
        BytesIO(blob),
        mimetype=(
            'application/vnd.openxmlformats-officedocument'
            '.wordprocessingml.document'
        ),
        as_attachment=False,
        download_name=f'envio_{id_envio}_cap_{id_capitulo}.docx',
    )


@api_bp.route(
    '/envios/<int:id_envio>/capitulos/<int:id_capitulo>/docx',
    methods=['PUT']
)
@login_required
def salvar_envio_segmento_docx(id_envio, id_capitulo):
    """Salva o DOCX editado (pelo editor no browser) como o segmento
    confirmado daquele capítulo no envio.

    Aceita:
    - application/octet-stream: bytes DOCX
    - text/html: HTML do contenteditable; convertido para DOCX
    """
    envio = EnvioConteudo.query.get_or_404(id_envio)
    if envio.id_usuario != current_user.id:
        return jsonify({'erro': 'Sem permissão'}), 403
    try:
        gerar_segmento_docx(id_envio, id_capitulo)
    except ValueError as e:
        return jsonify({'erro': str(e)}), 400
    except (OSError, RuntimeError) as e:
        return jsonify({'erro': f'Falha ao validar segmento: {e}'}), 500

    content_type = request.content_type or ''
    dados = request.get_data()
    if len(dados) > MAX_UPLOAD_BYTES:
        return jsonify({'erro': 'Arquivo excede 50 MB'}), 413

    if 'text/html' in content_type:
        try:
            dados = converter_html_para_docx(dados)
        except (ValueError, TypeError, AttributeError) as e:
            return jsonify(
                {'erro': f'Erro ao converter HTML para DOCX: {e}'}
            ), 400

    # DEPRECATED: pos-Fase 1, edicoes inline foram substituidas por
    # upload + merge in-place (servico_merge_docx). Este endpoint nao
    # persiste mais nada. Mantido por compatibilidade do frontend ate
    # que `editor_autor.js` e `editor_coordenador.js` migrem para o
    # fluxo de upload completo.
    return jsonify({
        'erro': (
            'Endpoint depreciado. Use o fluxo de upload de DOCX por '
            'capitulo (rota /relatorio/.../capitulo/<id>/upload).'
        ),
    }), 410


# ==============================================================
# CONTEÚDO DOCX — upload/download por capítulo
# ==============================================================

@api_bp.route('/capitulos/<int:id_cap>/conteudo', methods=['PUT'])
@login_required
def salvar_conteudo(id_cap):
    """DEPRECATED (pos-Fase 1).

    Salvar conteudo de capitulo via API foi substituido pelo fluxo de
    upload de DOCX completo + merge in-place. O frontend deve enviar
    um arquivo `.docx` para
    `POST /relatorio/versao-trabalho/<id>/capitulo/<id_cap>/upload`
    e confirmar na tela de previa.

    Mantemos a rota retornando 410 Gone para que o frontend antigo
    receba mensagem clara em vez de salvar em coluna que ja foi
    removida do banco.
    """
    _ = id_cap
    return jsonify({
        'erro': (
            'Endpoint depreciado. Use o fluxo de upload completo de '
            'DOCX (rota /relatorio/.../capitulo/<id>/upload).'
        ),
    }), 410


@api_bp.route('/capitulos/<int:id_cap>/conteudo')
@login_required
def obter_conteudo(id_cap):
    """Retorna o DOCX binario do capitulo isolado.

    Pos-Fase 1: extraido em tempo real do DOCX em producao
    (caminho_template do relatorio) via
    `servico_merge_docx.extrair_capitulo_como_docx`. Nao usa mais
    `cap.conteudo_docx` (coluna em vias de ser removida).
    """
    try:
        conteudo, erro, status = extrair_conteudo_capitulo(id_cap)
    except (ValueError, OSError, RuntimeError) as e:
        return (f'Erro ao extrair capitulo: {e}', 500)
    if erro:
        return (erro, status)
    if not conteudo:
        return ('Capitulo nao localizado no DOCX em producao', 404)

    return send_file(
        BytesIO(conteudo),
        mimetype=(
            'application/vnd.openxmlformats-officedocument'
            '.wordprocessingml.document'
        ),
        as_attachment=False,
        download_name=f'capitulo_{id_cap}.docx',
    )


# ==============================================================
# WORKFLOW — finalizar, aprovar, reprovar
# ==============================================================

@api_bp.route(
    '/relatorios-producao/<int:id_rp>/finalizar',
    methods=['POST']
)
@login_required
def finalizar_relatorio(id_rp):
    """Coordenador finaliza o relatório de produção.

    Pos-Fase 1: delega para `servico_finalizar_relatorio.finalizar`,
    que cria snapshot do `caminho_template` (fonte unica) em
    `storage/relatorios_finalizados/`, calcula checksum, persiste
    `RelatorioFinalizado` e avanca status para 'finalizado'.

    Nao monta mais o DOCX a partir de `conteudo_docx` por capitulo.
    """
    _exigir_perfil('coordenador')
    try:
        resultado = finalizar_relatorio_api(id_rp, current_user.id)
    except FinalizacaoError as e:
        return jsonify({'erro': str(e)}), 400
    except (OSError, RuntimeError) as e:
        return jsonify({'erro': f'Erro inesperado: {e}'}), 500
    return jsonify(resultado), 201


@api_bp.route(
    '/capitulos/<int:id_cap>/finalizar', methods=['POST']
)
@login_required
def finalizar_capitulo(id_cap):
    """Autor marca capítulo como finalizado (pronto para revisão)."""
    _exigir_perfil('autor')
    capitulo, erro, status = finalizar_capitulo_api(id_cap, current_user.id)
    if erro:
        return jsonify({'erro': erro}), status
    return jsonify(capitulo)


@api_bp.route(
    '/capitulos/<int:id_cap>/aprovar', methods=['POST']
)
@login_required
def aprovar_capitulo(id_cap):
    """Coordenador aprova o capítulo."""
    _exigir_perfil('coordenador')
    capitulo, erro, status = aprovar_capitulo_api(id_cap)
    if erro:
        return jsonify({'erro': erro}), status
    return jsonify(capitulo)


@api_bp.route(
    '/capitulos/<int:id_cap>/reprovar', methods=['POST']
)
@login_required
def reprovar_capitulo(id_cap):
    """Coordenador reprova o capítulo com justificativa."""
    _exigir_perfil('coordenador')
    data = request.get_json() or {}
    capitulo, erro, status = reprovar_capitulo_api(
        id_cap, data.get('observacao', '')
    )
    if erro:
        return jsonify({'erro': erro}), status
    return jsonify(capitulo)


# ==============================================================
# RENDERIZAÇÃO — serve o DOCX em producao direto
# ==============================================================
# Pos-Fase 1: o DOCX em `RelatorioProducao.caminho_template` JA E o
# documento final montado (autores fizeram merge in-place via
# `servico_merge_docx`). Nao ha mais reconstrucao do zero. As rotas
# legadas abaixo apenas servem esse arquivo (com sanitizacao para o
# eigenpal). `_gerar_docx_versao` e `MotorRenderizacao` foram
# removidos.


def _servir_docx_producao(vt, *, as_attachment: bool, nome: str):
    """Helper comum para servir o DOCX em producao com sanitizacao."""
    conteudo, erro = servir_docx_producao(vt)
    if erro:
        return jsonify({'erro': erro}), 404
    mimetype = (
        'application/vnd.openxmlformats-officedocument'
        '.wordprocessingml.document'
    )
    if isinstance(conteudo, str):
        return send_file(
            conteudo,
            as_attachment=as_attachment,
            download_name=nome,
            mimetype=mimetype,
        )
    if conteudo is None:
        return jsonify({'erro': 'DOCX não disponível'}), 404
    return send_file(
        BytesIO(conteudo),
        as_attachment=as_attachment,
        download_name=nome,
        mimetype=mimetype,
    )


@api_bp.route(
    '/versoes-trabalho/<int:id_vt>/renderizar', methods=['POST']
)
@login_required
def renderizar_versao(id_vt):
    """Serve o DOCX em producao (fonte unica) como download.

    Rota mantida por compatibilidade do frontend; pos-Fase 1 nao
    monta mais nada — simplesmente devolve `caminho_template`. Para
    finalizar (snapshot + bloqueio), use
    `POST /api/relatorios-producao/<id>/finalizar` ou a rota web
    `/relatorio/producao/<id>/gerar-final`.
    """
    vt = RelatorioProducao.query.get_or_404(id_vt)
    return _servir_docx_producao(
        vt,
        as_attachment=True,
        nome=f'relatorio_{vt.id}_{vt.versao_atual}.docx',
    )


@api_bp.route(
    '/versoes-trabalho/<int:id_vt>/preview-docx'
)
@login_required
def preview_versao(id_vt):
    """Preview inline do DOCX em producao (sem download)."""
    vt = RelatorioProducao.query.get_or_404(id_vt)
    return _servir_docx_producao(
        vt,
        as_attachment=False,
        nome=f'preview_{vt.id}.docx',
    )


# ==============================================================
# GESTÃO DA VERSÃO — vincular biblioteca, listar autores
# ==============================================================

@api_bp.route(
    '/versoes-trabalho/<int:id_vt>/vincular-biblioteca',
    methods=['POST']
)
@login_required
def vincular_biblioteca(id_vt):
    """Coordenador vincula uma biblioteca canônica à versão."""
    _exigir_perfil('coordenador')
    data = request.get_json()
    id_bib = data.get('id_biblioteca')
    ok, erro = vincular_biblioteca_api(id_vt, id_bib)
    if not ok:
        return jsonify({'erro': erro}), 400
    return jsonify({'ok': True, 'id_biblioteca': id_bib})


@api_bp.route('/usuarios-autores')
@login_required
def listar_autores():
    """Lista usuários com perfil 'autor' ativos.

    Retorna lista de autores cadastrados, utilizando a tabela de domínios
    para buscar o perfil 'autor' dinamicamente.
    """
    return jsonify(listar_autores_api())


@api_bp.route('/bibliotecas-formatacao')
@login_required
def listar_bibliotecas():
    """Lista bibliotecas de formatação ativas."""
    bibs = BibliotecaFormatacaoCanonica.query.filter_by(
        ativa=True, extraida=True
    ).order_by(
        BibliotecaFormatacaoCanonica.nome_biblioteca
    ).all()
    return jsonify([
        {
            'id': b.id_biblioteca_formatacao_canonica,
            'nome': b.nome_biblioteca,
        }
        for b in bibs
    ])


# ==============================================================
# Helpers
# ==============================================================

def _exigir_perfil(*perfis):
    """Aborta se o usuário não tem um dos perfis exigidos."""
    perfil_ativo = session.get('perfil_ativo', '')
    if perfil_ativo not in perfis:
        abort(403)


@api_bp.route('/logs')
@login_required
def get_logs():
    """Retorna logs do sistema para exibição no navegador."""
    level = request.args.get('level')
    limit = request.args.get('limit', 100, type=int)
    logs = sra_log_handler.get_logs(level=level, limit=limit)
    return jsonify({'logs': logs})
