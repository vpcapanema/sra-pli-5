"""Rotas principais / dashboard do SRA."""

import os
from flask import Blueprint, session, render_template
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload

from app.models.relatorio_producao import RelatorioProducao
from app.models.relatorio_finalizado import RelatorioFinalizado
from app.models.biblioteca_formatacao import BibliotecaFormatacaoCanonica
from app.models.envio_conteudo import EnvioConteudo
from app.utils.htmx import render_conteudo

principal_bp = Blueprint('principal', __name__)


@principal_bp.route('/dev/botoes-icone')
@login_required
def dev_botoes_icone():
    """Pagina de demonstracao de estilos de botoes-icone.

    Mostra varias variacoes (peso do Phosphor, forma, cor, hover) para
    o usuario escolher qual aplicar em todas as tabelas.
    """
    return render_template('dev/botoes_icone.html')


@principal_bp.route('/')
@login_required
def index():
    """Rota principal do dashboard."""
    perfil_ativo = session.get('perfil_ativo', '')
    componentes = _resolver_componentes(perfil_ativo)

    relatorios_producao = RelatorioProducao.query.all()
    relatorios_finalizados = RelatorioFinalizado.query.all()
    bibliotecas_formatacao = BibliotecaFormatacaoCanonica.query.filter_by(
        ativa=True
    ).all()

    # Listar arquivos de storage/relatorios_base
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    dir_relatorios_base = os.path.join(base_dir, 'storage', 'relatorios_base')
    arquivos_relatorios_base = []
    if os.path.exists(dir_relatorios_base):
        arquivos_relatorios_base = [
            f for f in os.listdir(dir_relatorios_base)
            if f.endswith('.docx')
        ]

    # Envios de conteudo para a tabela do dashboard.
    # Coordenador/admin: ve todos. Autor: ve so os proprios envios.
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
        envios_query = envios_query.filter_by(id_usuario=current_user.id)
    envios = envios_query.all()

    # Resolve nomes para criado_por/atualizado_por (auditoria).
    # Esses campos sao Integer puros (sem FK), entao buscamos com
    # uma query batch e anexamos como atributos dinamicos.
    if envios:
        from app.models.usuario import Usuario as _U  # noqa: C0415
        ids_aud = set()
        for ev in envios:
            if ev.criado_por:
                ids_aud.add(ev.criado_por)
            if ev.atualizado_por:
                ids_aud.add(ev.atualizado_por)
        usuarios_por_id = {}
        if ids_aud:
            for u in _U.query.filter(_U.id.in_(ids_aud)).all():
                usuarios_por_id[u.id] = u
        for ev in envios:
            ev.criado_por_user = usuarios_por_id.get(ev.criado_por)
            ev.atualizado_por_user = usuarios_por_id.get(ev.atualizado_por)
            # Autor responsavel do capitulo destino (semantico do
            # conteudo, NAO do upload). Quando o coordenador sobe um
            # arquivo em nome do autor, o "Autor responsavel" do
            # capitulo aparece aqui, e o "Enviado por" aparece como
            # o coordenador (criado_por).
            cap = ev.capitulo_destino
            ev.autor_responsavel = (
                cap.responsavel if cap else None
            )

    return render_conteudo(
        componentes,
        perfil_ativo=perfil_ativo,
        relatorios_producao=relatorios_producao,
        relatorios_finalizados=relatorios_finalizados,
        arquivos_relatorios_base=arquivos_relatorios_base,
        bibliotecas_formatacao=bibliotecas_formatacao,
        envios=envios,
    )


def _resolver_componentes(perfil):
    if perfil == 'admin':
        return [
            'components/paineis/painel_indicadores.html',
            'components/paineis/painel_relatorios.html',
        ]
    elif perfil == 'coordenador':
        return [
            'components/paineis/dashboard_coordenador.html',
        ]
    elif perfil == 'autor':
        return [
            'components/paineis/painel_relatorios.html',
        ]
    # Fallback: evita <main> vazio quando o perfil não casa com nenhum
    # dos conhecidos (ex.: sessão sem perfil definido).
    return ['components/paineis/painel_relatorios.html']
