"""
API REST para o fluxo de edição colaborativa.
Consumida pelo editor React (docx-editor) embedado nas telas
de autor e coordenador.
"""

import secrets
import time
from io import BytesIO

from flask import Blueprint, abort, jsonify, request, send_file, session
from flask_login import login_required, current_user

from app import db
from app.models.usuario import Usuario
from app.models.relatorio_producao import RelatorioProducao
from app.models.relatorio_finalizado import RelatorioFinalizado
from app.models.capitulo_documento import CapituloDocumento
from app.models.biblioteca_formatacao import (
    BibliotecaFormatacaoCanonica
)
from app.models.notificacao import Notificacao

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

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
    vt = RelatorioProducao.query.get_or_404(id_vt)
    caps = CapituloDocumento.query.filter_by(
        id_relatorio=id_vt,
        id_capitulo_pai=None,
        ativo=True
    ).order_by(CapituloDocumento.ordem_capitulo).all()

    return jsonify({
        'id': vt.id,
        'titulo': vt.titulo_curto,
        'status': vt.status.codigo if vt.status else None,
        'id_biblioteca': None,
        'capitulos': [_serializar_capitulo(c) for c in caps],
    })


# ==============================================================
# CAPÍTULOS — CRUD
# ==============================================================

@api_bp.route('/versoes-trabalho/<int:id_vt>/capitulos')
@login_required
def listar_capitulos(id_vt):
    """Lista capítulos (raízes) da versão de trabalho."""
    caps = CapituloDocumento.query.filter_by(
        id_relatorio=id_vt,
        id_capitulo_pai=None,
        ativo=True
    ).order_by(CapituloDocumento.ordem_capitulo).all()
    return jsonify([_serializar_capitulo(c) for c in caps])


@api_bp.route(
    '/versoes-trabalho/<int:id_vt>/capitulos',
    methods=['POST']
)
@login_required
def criar_capitulo(id_vt):
    """Cria um novo capítulo/subcapítulo."""
    RelatorioProducao.query.get_or_404(id_vt)
    data = request.get_json()
    cap = CapituloDocumento(
        id_relatorio=id_vt,
        titulo_capitulo=data['titulo'],
        ordem_capitulo=data.get('ordem', 0),
        nivel_capitulo=data.get('nivel', 1),
        id_capitulo_pai=data.get('id_pai'),
        id_usuario_responsavel=data.get('id_responsavel'),
        status_capitulo='em_edicao',
    )
    db.session.add(cap)
    db.session.commit()
    return jsonify(_serializar_capitulo(cap)), 201


@api_bp.route('/capitulos/<int:id_cap>', methods=['PATCH'])
@login_required
def atualizar_capitulo(id_cap):
    """Atualiza metadados de um capítulo (coordenador only)."""
    _exigir_perfil('coordenador')
    cap = CapituloDocumento.query.get_or_404(id_cap)
    data = request.get_json()

    if 'titulo' in data:
        cap.titulo_capitulo = data['titulo']
    if 'ordem' in data:
        cap.ordem_capitulo = data['ordem']
    if 'nivel' in data:
        cap.nivel_capitulo = data['nivel']
    if 'id_responsavel' in data:
        cap.id_usuario_responsavel = data['id_responsavel']

    db.session.commit()
    return jsonify(_serializar_capitulo(cap))


@api_bp.route('/capitulos/<int:id_cap>', methods=['DELETE'])
@login_required
def excluir_capitulo(id_cap):
    """Soft-delete de um capítulo."""
    cap = CapituloDocumento.query.get_or_404(id_cap)
    cap.ativo = False
    db.session.commit()
    return '', 204


# ==============================================================
# CONTEÚDO DOCX — upload/download por capítulo
# ==============================================================

@api_bp.route('/capitulos/<int:id_cap>/conteudo', methods=['PUT'])
@login_required
def salvar_conteudo(id_cap):
    """
    Salva o conteúdo do capítulo.
    Aceita:
    - application/octet-stream: DOCX binário (upload original)
    - text/html: HTML editado (converte para DOCX)
    """
    cap = CapituloDocumento.query.get_or_404(id_cap)
    # Permissão: só o responsável pode enviar conteúdo
    if (cap.id_usuario_responsavel
            and cap.id_usuario_responsavel
            != current_user.id):
        _exigir_perfil('coordenador')

    content_type = request.content_type or ''
    dados = request.get_data()

    if len(dados) > MAX_UPLOAD_BYTES:
        return jsonify({
            'erro': 'Arquivo excede limite de 50 MB'
        }), 413

    # Se for HTML editado, converte para DOCX
    if 'text/html' in content_type:
        from docx import Document
        from bs4 import BeautifulSoup
        import io

        try:
            # Parse HTML
            soup = BeautifulSoup(dados.decode('utf-8'), 'html.parser')

            # Criar novo DOCX
            doc = Document()

            # Extrair parágrafos do HTML
            for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = p.get_text(strip=True)
                if text:
                    if p.name.startswith('h'):
                        # Títulos
                        level = int(p.name[1])
                        doc.add_heading(text, level=min(level, 3))
                    else:
                        # Parágrafos
                        doc.add_paragraph(text)

            # Salvar em bytes
            buffer = io.BytesIO()
            doc.save(buffer)
            dados = buffer.getvalue()
        except Exception as e:
            return jsonify({
                'erro': f'Erro ao converter HTML para DOCX: {str(e)}'
            }), 400

    cap.conteudo_docx = dados
    db.session.commit()
    return jsonify({'ok': True, 'size': len(cap.conteudo_docx)})


@api_bp.route('/capitulos/<int:id_cap>/conteudo')
@login_required
def obter_conteudo(id_cap):
    """Retorna o DOCX binário do capítulo."""
    cap = CapituloDocumento.query.get_or_404(id_cap)
    if not cap.conteudo_docx:
        return ('', 204)
    return send_file(
        BytesIO(cap.conteudo_docx),
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
    """Coordenador finaliza o relatório de produção."""
    _exigir_perfil('coordenador')
    relatorio = RelatorioProducao.query.get_or_404(id_rp)

    if relatorio.bloqueio_edicao:
        return jsonify({'erro': 'Relatório já finalizado'}), 400

    # Gerar snapshot completo de todos os dados
    snapshot = {
        'relatorio': {
            'id': relatorio.id,
            'codigo_d20': relatorio.codigo_d20,
            'numero_medicao': relatorio.numero_medicao,
            'mes_referencia': (
                relatorio.mes_referencia.isoformat()
                if relatorio.mes_referencia else None
            ),
            'periodo_inicio': (
                relatorio.periodo_inicio.isoformat()
                if relatorio.periodo_inicio else None
            ),
            'periodo_fim': (
                relatorio.periodo_fim.isoformat()
                if relatorio.periodo_fim else None
            ),
            'titulo_curto': relatorio.titulo_curto,
            'versao_atual': relatorio.versao_atual,
            'ano_referencia': relatorio.ano_referencia,
        },
        'capitulos': [],
        'revisoes': [],
        'envios': [],
    }

    # Capturar capítulos
    capitulos = CapituloDocumento.query.filter_by(
        id_relatorio=id_rp
    ).all()
    for cap in capitulos:
        snapshot['capitulos'].append({
            'id': cap.id_capitulo_documento,
            'titulo': cap.titulo_capitulo,
            'indice': cap.indice_capitulo,
            'ordem': cap.ordem_capitulo,
            'nivel': cap.nivel_capitulo,
            'status': cap.status_capitulo,
            'id_responsavel': cap.id_usuario_responsavel,
            'conteudo_docx': (
                cap.conteudo_docx.hex() if cap.conteudo_docx else None
            ),
            'observacao_coordenador': cap.observacao_coordenador,
        })

    # Capturar revisões
    for rev in relatorio.revisoes:
        snapshot['revisoes'].append({
            'id': rev.id_revisao,
            'id_usuario_coordenador': rev.id_usuario_coordenador,
            'status': rev.status_revisao,
            'observacao': rev.observacao,
        })

    # Capturar envios
    for env in relatorio.envios:
        snapshot['envios'].append({
            'id': env.id_envio_conteudo,
            'id_usuario': env.id_usuario,
            'nome_arquivo': env.nome_arquivo,
            'status': env.status_envio,
        })

    # Gerar DOCX final (TODO: implementar renderização)
    from app.services.servico_motor_renderizacao import MotorRenderizacao
    motor = MotorRenderizacao()
    try:
        docx_bytes = motor.renderizar_versao(id_rp)
    except Exception as e:
        return jsonify({'erro': f'Erro ao gerar DOCX: {str(e)}'}), 500

    # Criar registro em relatorios_finalizados
    relatorio_finalizado = RelatorioFinalizado(
        relatorio_id=relatorio.id,
        modelo_id=relatorio.modelo_id,
        biblioteca_id=relatorio.biblioteca_id,
        status_id=relatorio.status_id,
        snapshot_conteudo=snapshot,
        artefato_docx=docx_bytes,
        nome_arquivo=(
            f"relatorio_{relatorio.id}_R{relatorio.versao_atual}.docx"
        ),
        finalizado_por=current_user.id,
        data_finalizacao=db.func.now(),
        codigo=relatorio.codigo_d20,
        titulo=relatorio.titulo_curto,
        mes_referencia=relatorio.mes_referencia,
        ano_referencia=relatorio.ano_referencia,
        periodo_inicio=relatorio.periodo_inicio,
        periodo_fim=relatorio.periodo_fim,
        numero_medicao=relatorio.numero_medicao,
        versao=relatorio.versao_atual,
    )

    db.session.add(relatorio_finalizado)

    # Bloquear edição no relatório de produção
    relatorio.bloqueio_edicao = True

    db.session.commit()

    return jsonify({
        'mensagem': 'Relatório finalizado com sucesso',
        'id_finalizado': relatorio_finalizado.id,
        'versao': relatorio_finalizado.versao,
    }), 201


@api_bp.route(
    '/capitulos/<int:id_cap>/finalizar', methods=['POST']
)
@login_required
def finalizar_capitulo(id_cap):
    """Autor marca capítulo como finalizado (pronto para revisão)."""
    _exigir_perfil('autor')
    cap = CapituloDocumento.query.get_or_404(id_cap)
    if cap.status_capitulo not in ('em_edicao', 'reprovado'):
        return jsonify({'erro': 'Status inválido para finalizar'}), 400
    # Só o responsável pode finalizar
    if (cap.id_usuario_responsavel
            and cap.id_usuario_responsavel
            != current_user.id):
        return jsonify({'erro': 'Sem permissão'}), 403
    cap.status_capitulo = 'finalizado'
    # Notificar coordenador(es)
    # TODO: Implementar query de coordenadores usando dom_perfis_usuario
    # coordenadores = Usuario.query.filter(
    #     Usuario.perfil_id == 2,  # coordenador
    #     Usuario.ativo
    # ).all()
    # for coord in coordenadores:
    #     _notificar(
    #         coord.id,
    #         f'Capítulo "{cap.titulo_capitulo}" finalizado '
    #         f'pelo autor e aguarda revisão.'
    #     )
    db.session.commit()
    return jsonify(_serializar_capitulo(cap))


@api_bp.route(
    '/capitulos/<int:id_cap>/aprovar', methods=['POST']
)
@login_required
def aprovar_capitulo(id_cap):
    """Coordenador aprova o capítulo."""
    _exigir_perfil('coordenador')
    cap = CapituloDocumento.query.get_or_404(id_cap)
    if cap.status_capitulo != 'finalizado':
        return jsonify({'erro': 'Capítulo não está finalizado'}), 400
    cap.status_capitulo = 'aprovado'
    cap.observacao_coordenador = None
    # Notificar autor
    if cap.id_usuario_responsavel:
        _notificar(
            cap.id_usuario_responsavel,
            f'Capítulo "{cap.titulo_capitulo}" aprovado '
            f'pelo coordenador.'
        )
    db.session.commit()
    return jsonify(_serializar_capitulo(cap))


@api_bp.route(
    '/capitulos/<int:id_cap>/reprovar', methods=['POST']
)
@login_required
def reprovar_capitulo(id_cap):
    """Coordenador reprova o capítulo com justificativa."""
    _exigir_perfil('coordenador')
    cap = CapituloDocumento.query.get_or_404(id_cap)
    if cap.status_capitulo != 'finalizado':
        return jsonify({'erro': 'Capítulo não está finalizado'}), 400
    data = request.get_json() or {}
    cap.status_capitulo = 'reprovado'
    cap.observacao_coordenador = data.get('observacao', '')
    # Notificar autor
    if cap.id_usuario_responsavel:
        _notificar(
            cap.id_usuario_responsavel,
            f'Capítulo "{cap.titulo_capitulo}" reprovado. '
            f'Observação: {cap.observacao_coordenador}'
        )
    db.session.commit()
    return jsonify(_serializar_capitulo(cap))


# ==============================================================
# RENDERIZAÇÃO — gera DOCX completo com formatação canônica
# ==============================================================

@api_bp.route(
    '/versoes-trabalho/<int:id_vt>/renderizar', methods=['POST']
)
@login_required
def renderizar_versao(id_vt):
    """
    Monta o DOCX final aplicando a biblioteca canônica.
    Retorna o DOCX binário.
    """
    RelatorioProducao.query.get_or_404(id_vt)
    return jsonify({
        'erro': 'Funcionalidade de biblioteca canônica não implementada'
    }), 501


@api_bp.route(
    '/versoes-trabalho/<int:id_vt>/preview-docx'
)
@login_required
def preview_versao(id_vt):
    """
    Gera o DOCX renderizado para preview via docx-preview.
    Igual ao renderizar mas sem forçar download.
    """
    RelatorioProducao.query.get_or_404(id_vt)
    return ('Funcionalidade de biblioteca canônica não implementada', 501)


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
    RelatorioProducao.query.get_or_404(id_vt)
    data = request.get_json()
    id_bib = data.get('id_biblioteca')
    if not id_bib:
        return jsonify({'erro': 'id_biblioteca obrigatório'}), 400
    BibliotecaFormatacaoCanonica.query.get_or_404(id_bib)
    # TODO: Implementar vinculo de biblioteca no novo schema
    db.session.commit()
    return jsonify({'ok': True, 'id_biblioteca': id_bib})


@api_bp.route('/usuarios-autores')
@login_required
def listar_autores():
    """Lista usuários com perfil 'autor' ativos."""
    autores = Usuario.query.filter(
        Usuario.perfil_id == 1,  # TODO: usar codigo do perfil
        Usuario.ativo
    ).order_by(Usuario.nome).all()
    return jsonify([
        {'id': u.id, 'nome': u.nome}
        for u in autores
    ])


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


def _notificar(id_usuario, mensagem, tipo='workflow'):
    """Cria notificação para o usuário."""
    n = Notificacao(
        id_usuario_destino=id_usuario,
        tipo_notificacao=tipo,
        mensagem=mensagem
    )
    db.session.add(n)


def _serializar_capitulo(cap):
    """Serializa CapituloDocumento para JSON."""
    filhos = CapituloDocumento.query.filter_by(
        id_capitulo_pai=cap.id_capitulo_documento,
        ativo=True
    ).order_by(CapituloDocumento.ordem_capitulo).all()

    return {
        'id': cap.id_capitulo_documento,
        'titulo': cap.titulo_capitulo,
        'ordem': cap.ordem_capitulo,
        'nivel': cap.nivel_capitulo,
        'status': cap.status_capitulo,
        'id_responsavel': cap.id_usuario_responsavel,
        'responsavel_nome': (
            cap.responsavel.nome
            if cap.responsavel else None
        ),
        'tem_conteudo': cap.conteudo_docx is not None,
        'observacao_coordenador': cap.observacao_coordenador,
        'filhos': [_serializar_capitulo(f) for f in filhos],
    }
