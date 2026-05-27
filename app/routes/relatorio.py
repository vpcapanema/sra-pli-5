"""Rotas de relatórios do SRA."""

# noqa: C0302 (too-many-lines)

from io import BytesIO
import json
import os
import shutil
from datetime import datetime, timezone

from flask import (
    Blueprint,
    redirect,
    render_template,
    url_for,
    flash,
    request,
    session,
    jsonify,
    current_app,
    send_file,
)
from docx import Document
from flask_login import login_required, current_user
from sqlalchemy import text
from werkzeug.utils import secure_filename

from app import db
from app.models.usuario import Usuario
from app.models.capitulo_documento import CapituloDocumento
from app.models.relatorio_producao import RelatorioProducao
from app.models.envio_conteudo import EnvioConteudo
from app.models.previsualizacao_conteudo import PrevisualizacaoConteudo
from app.models.dominio import Dominio
from app.models.biblioteca_formatacao import BibliotecaFormatacaoCanonica
from app.services.servico_relatorio import ServicoRelatorio
from app.services.servico_extracao_canonica import ServicoExtracaoCanonica
from app.services.servico_envio_autor import ServicoEnvioAutor
from app.services.servico_acoes_relatorio import listar_por_grupo
from app.services.servico_sincronizar_capitulos import ressincronizar_capitulos_com_classificacao
from app.services.servico_capa import aplicar_dados_completos
from app.services.servico_finalizar_relatorio import (
    finalizar,
    gerar_preview,
    FinalizacaoError,
)
from app.services.servico_perfil_formatacao import PerfilFormatacao
from app.services.servico_toc import (
    inserir_sumario,
    inserir_lista_figuras,
    inserir_lista_tabelas,
)
from app.services.servico_captioning import reindexar_captions
from app.services.servico_cross_refs import substituir_referencias
from app.services.servico_sanitizar_docx import sanitizar_docx
from app.utils.htmx import render_conteudo

relatorio_bp = Blueprint("relatorio", __name__, url_prefix="/relatorio")


def _criar_capitulo_recursivo(
    cap_dict, id_relatorio, id_pai, ordem, indice_pai="", ordem_absoluta=None
):
    """Cria capítulo recursivamente a partir da árvore extraída do DOCX.

    Prioriza o `indice` extraído do próprio título do heading no DOCX
    (ex.: "5.4.6.1 Sistema SIGMA-PLI" -> indice="5.4.6.1"). Cai no
    índice calculado por ordem hierárquica apenas quando o DOCX não
    traz prefixo numérico (caso de pré/pós-textuais ou Headings sem
    numeração no texto).

    `ordem` é o número que será usado no fallback do índice (já vem
    pré-contado por tipo de elemento na raiz, e por irmão nas demais
    profundidades). `ordem_absoluta` é a posição global no relatório
    (preserva ordem física do DOCX) e vai para `ordem_capitulo` no DB.
    """
    indice_do_docx = cap_dict.get("indice")
    if indice_do_docx:
        indice = indice_do_docx
    else:
        indice = f"{indice_pai}{ordem}" if indice_pai else str(ordem)

    # Usar tipo_elemento do dicionário extraído, ou 'textual' como padrão
    tipo = cap_dict.get("tipo_elemento", "textual")
    ordem_db = ordem_absoluta if ordem_absoluta is not None else ordem

    # Auditoria: registra quem disparou a clonagem como criador dos
    # capitulos. Em fluxos sem usuario logado (jobs), `criado_por` cai
    # para None — coluna eh nullable.
    criador_id = (
        current_user.id
        if current_user and current_user.is_authenticated
        else None
    )

    capitulo = CapituloDocumento(
        id_relatorio=id_relatorio,
        id_capitulo_pai=id_pai,
        titulo_capitulo=cap_dict["titulo"],
        ordem_capitulo=ordem_db,
        nivel_capitulo=cap_dict["nivel"],
        tipo_elemento=tipo,
        indice_capitulo=indice,
        # `nome_capitulo` espelha o titulo na criacao automatica.
        nome_capitulo=cap_dict.get("nome") or cap_dict["titulo"],
        status_capitulo="em_edicao",
        criado_por=criador_id,
    )
    db.session.add(capitulo)
    db.session.flush()  # Para obter o ID antes de criar filhos

    # Criar filhos recursivamente
    ordem_filho = 1
    for filho in cap_dict["filhos"]:
        _criar_capitulo_recursivo(
            filho,
            id_relatorio,
            capitulo.id_capitulo_documento,
            ordem_filho,
            f"{indice}.",
        )
        ordem_filho += 1


@relatorio_bp.before_request
@login_required
def verificar_acesso():
    """Verifica se o usuário tem perfil autorizado."""
    perfil = session.get("perfil_ativo")
    if perfil not in ("coordenador", "admin", "autor"):
        flash("Acesso restrito.", "erro")
        return redirect(url_for("principal.index"))


@relatorio_bp.route("/panorama")
def panorama():
    """Exibe panorama de relatorios."""
    conn = db.session.connection()
    result = conn.execute(text("""
        SELECT * FROM vw_todos_relatorios
        ORDER BY data_criacao DESC
    """))

    relatorios = []
    for row in result:
        relatorios.append(
            {
                "id": row.id,
                "tipo_relatorio": row.tipo_relatorio,
                "codigo": row.codigo,
                "titulo": row.titulo,
                "numero_medicao": row.numero_medicao,
                "mes_referencia": row.mes_referencia,
                "ano_referencia": row.ano_referencia,
                "periodo_inicio": row.periodo_inicio,
                "periodo_fim": row.periodo_fim,
                "status_codigo": row.status_codigo,
                "status_descricao": row.status_descricao,
                "data_criacao": row.data_criacao,
                "versao": row.versao,
                "criador_nome": row.criador_nome,
            }
        )

    return render_conteudo(
        ["components/relatorio/panorama_relatorios.html"],
        relatorios=relatorios,
        id_relatorio_selecionado=None,
    )


@relatorio_bp.route("/modelos")
def listar_modelos():
    """Lista modelos de relatório."""
    modelos = ServicoRelatorio.listar_modelos(apenas_ativos=False)
    return render_conteudo(
        ["components/relatorio/lista_modelos.html"],
        perfil_ativo=session.get("perfil_ativo", ""),
        modelos=modelos,
    )


@relatorio_bp.route("/modelos/novo", methods=["POST"])
def criar_modelo():
    """Cria um novo modelo de relatório."""
    ServicoRelatorio.criar_modelo(
        nome_modelo=request.form.get("nome_modelo"),
        descricao=request.form.get("descricao"),
    )
    flash("Modelo criado com sucesso.", "sucesso")
    return redirect(url_for("relatorio.listar_modelos"))


@relatorio_bp.route("/base")
def relatorios_base():
    """Lista relatórios base disponíveis."""
    relatorios = ServicoRelatorio.listar_relatorios_finalizados()
    return render_conteudo(
        ["relatorio/relatorios_base.html"], relatorios_finalizados=relatorios
    )


@relatorio_bp.route("/base/novo", methods=["POST"])
def criar_relatorio_base():
    """Cria um novo relatório base."""
    arquivo = request.files.get("arquivo_docx")
    if not arquivo or not arquivo.filename.endswith(".docx"):
        flash("Envie um arquivo .docx válido.", "erro")
        return redirect(url_for("relatorio.relatorios_base"))

    # Salvar arquivo
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    dir_relatorios = os.path.join(base_dir, "storage", "relatorios_base")
    os.makedirs(dir_relatorios, exist_ok=True)
    nome_seguro = secure_filename(arquivo.filename)
    caminho = os.path.join(dir_relatorios, nome_seguro)
    arquivo.save(caminho)

    # NOTE: Implementar criar_relatorio_base em ServicoRelatorio
    # Por enquanto, usar criar_relatorio_finalizado
    flash("Funcionalidade em desenvolvimento.", "info")
    return redirect(url_for("relatorio.relatorios_base"))


@relatorio_bp.route("/producao")
def relatorios_producao():
    """Lista relatórios em produção."""
    relatorios = RelatorioProducao.query.order_by(
        RelatorioProducao.criado_em.desc()
    ).all()
    return render_conteudo(
        ["relatorio/relatorios_producao.html"], relatorios_producao=relatorios
    )


@relatorio_bp.route("/versao-trabalho")
def versao_trabalho():
    """Lista versões de trabalho."""
    versoes = ServicoRelatorio.listar_versoes_trabalho()
    relatorios = ServicoRelatorio.listar_relatorios_base()
    return render_conteudo(
        ["components/relatorio/card_cadastro_relatorio_versao_trabalho.html"],
        perfil_ativo=session.get("perfil_ativo", ""),
        versoes_trabalho=versoes,
        relatorios_base=relatorios,
    )


@relatorio_bp.route("/capitulos")
def listar_capitulos():
    """Lista de relatórios de produção - redireciona para detalhe."""
    relatorios = ServicoRelatorio.listar_relatorios_producao()
    return render_conteudo(["relatorio/capitulos.html"], relatorios_producao=relatorios)


@relatorio_bp.route("/editor")
def editor():
    """Lista de relatórios para edição - redireciona para editor específico."""
    relatorios = ServicoRelatorio.listar_relatorios_producao()
    return render_conteudo(["relatorio/editor.html"], relatorios_producao=relatorios)


@relatorio_bp.route("/versao-trabalho/nova", methods=["POST"])
def criar_versao():
    """Cria uma nova versão de trabalho."""
    versao = ServicoRelatorio.criar_versao_trabalho(
        id_relatorio_base=request.form.get("id_relatorio_base", type=int),
        titulo=request.form.get("titulo"),
    )
    flash("Versão de trabalho criada com sucesso.", "sucesso")
    return redirect(
        url_for("relatorio.detalhe_versao", id_versao=versao.id_versao_trabalho)
    )


@relatorio_bp.route("/versao-trabalho/<int:id_versao>")
def detalhe_versao(id_versao):
    """Detalhes de uma versão de trabalho."""
    versao = ServicoRelatorio.obter_versao_trabalho(id_versao)
    if not versao:
        flash("Versão de trabalho não encontrada.", "erro")
        return redirect(url_for("relatorio.relatorios_producao"))
    lista_capitulos = ServicoRelatorio.listar_capitulos(id_versao)
    capitulos_flat = CapituloDocumento.query.filter_by(id_relatorio=id_versao).all()

    def _sort_indice(cap):
        """Ordena por índice numérico hierárquico.

        Ex.: 1 < 2 < 5.1 < 5.2 < 5.10.
        """
        idx = cap.indice_capitulo or ""
        try:
            return [int(p) for p in idx.split(".") if p]
        except (ValueError, AttributeError):
            return [9999]

    capitulos_flat.sort(key=_sort_indice)
    bibliotecas = BibliotecaFormatacaoCanonica.query.filter_by(ativa=True).all()

    # Lista de autores ativos (perfil 'autor' em `dominios`).
    # Usado no select "Responsável" da tabela "Painel de Edição —
    # Coordenador" e no painel de atribuicao do editor.
    perfil_autor = Dominio.query.filter_by(
        tipo="perfil_usuario", valor="autor"
    ).first()
    if perfil_autor:
        autores = (
            Usuario.query
            .filter_by(perfil_id=perfil_autor.id_dominio, ativo=True)
            .order_by(Usuario.nome)
            .all()
        )
    else:
        autores = []
    # Relatórios em produção para o seletor
    relatorios_prod = (
        db.session.query(RelatorioProducao)
        .join(Dominio, RelatorioProducao.status_id == Dominio.id_dominio)
        .filter(
            Dominio.tipo == "status_relatorio",
            Dominio.valor == "em_producao",
        )
        .order_by(RelatorioProducao.criado_em.desc())
        .all()
    )
    componentes = [
        "components/relatorio/arvore_capitulos.html",
    ]
    return render_conteudo(
        componentes,
        perfil_ativo=session.get("perfil_ativo", ""),
        versao_trabalho=versao,
        capitulos=lista_capitulos,
        capitulos_flat=capitulos_flat,
        bibliotecas_disponiveis=bibliotecas,
        autores_disponiveis=autores,
        relatorios_producao=relatorios_prod,
    )


@relatorio_bp.route("/versao-trabalho/<int:id_versao>/capitulo/novo", methods=["POST"])
def criar_capitulo(id_versao):
    """Cria um novo capítulo na versão de trabalho."""
    ServicoRelatorio.criar_capitulo(
        id_relatorio=id_versao,
        titulo_capitulo=request.form.get("titulo_capitulo"),
        ordem_capitulo=request.form.get("ordem_capitulo", type=int),
        nivel_capitulo=request.form.get("nivel_capitulo", type=int, default=1),
        id_capitulo_pai=request.form.get("id_capitulo_pai", type=int),
        nome_capitulo=request.form.get("nome_capitulo"),
        indice_capitulo=request.form.get("indice_capitulo"),
        tipo_elemento=request.form.get("tipo_elemento", "textual"),
    )
    flash("Capítulo adicionado.", "sucesso")
    return redirect(url_for("relatorio.detalhe_versao", id_versao=id_versao))


# ==============================================================
# Vincular Biblioteca Canônica
# ==============================================================


@relatorio_bp.route(
    "/versao-trabalho/<int:id_versao>/vincular-biblioteca", methods=["POST"]
)
def vincular_biblioteca(id_versao):
    """Vincula uma biblioteca de formatação canônica à versão."""
    versao = ServicoRelatorio.obter_versao_trabalho(id_versao)
    if not versao:
        flash("Versão não encontrada.", "erro")
        return redirect(url_for("relatorio.relatorios_producao"))
    id_bib = request.form.get("id_biblioteca", type=int)
    if id_bib:
        versao.biblioteca_id = id_bib
        db.session.commit()
        flash("Biblioteca vinculada com sucesso.", "sucesso")
    else:
        flash("Selecione uma biblioteca.", "erro")
    return redirect(url_for("relatorio.detalhe_versao", id_versao=id_versao))


# ==============================================================
# Atribuir Responsável a Capítulo
# ==============================================================


@relatorio_bp.route(
    "/versao-trabalho/<int:id_versao>/capitulo/<int:id_capitulo>/atribuir",
    methods=["POST"],
)
def atribuir_responsavel(id_versao, id_capitulo):
    """Coordenador atribui um responsável a um capítulo.

    Rejeita quando o relatório está bloqueado/finalizado para evitar
    mudanças após o snapshot ter sido gerado.
    """
    cap = CapituloDocumento.query.get_or_404(id_capitulo)
    rel = RelatorioProducao.query.get(cap.id_relatorio)
    if ServicoRelatorio.esta_bloqueado(rel):
        flash(
            "Relatório finalizado ou bloqueado — não é possível alterar "
            "responsáveis. Crie uma nova versão para continuar.",
            "erro",
        )
        return redirect(url_for("relatorio.detalhe_versao", id_versao=id_versao))
    id_resp = request.form.get("id_usuario_responsavel", type=int)
    cap.id_usuario_responsavel = id_resp if id_resp else None
    db.session.commit()
    flash("Responsável atualizado.", "sucesso")

    # Memoriza a ultima atribuicao por relatorio na sessao do
    # coordenador. O editor do autor usa isso para congelar os
    # selects da seção 1 ate que ele mude de relatorio (estado dura
    # ate logout ou troca explicita pelo botao "Editar selecao").
    ultima = session.get("ultima_atribuicao", {})
    if not isinstance(ultima, dict):
        ultima = {}
    ultima[str(id_versao)] = {
        "id_capitulo": id_capitulo,
        "id_usuario_responsavel": id_resp,
    }
    session["ultima_atribuicao"] = ultima

    # Se o coordenador atribuiu pelo editor do autor, voltamos pra ele
    # preservando o id_versao no contexto. Senao, vai para o detalhe.
    referer = request.referrer or ""
    if "/editor-autor" in referer:
        return redirect(
            url_for("relatorio.editor_autor", id_versao=id_versao)
        )
    return redirect(url_for("relatorio.detalhe_versao", id_versao=id_versao))


@relatorio_bp.route(
    "/versao-trabalho/<int:id_versao>/limpar-ultima-atribuicao",
    methods=["POST"],
)
def limpar_ultima_atribuicao(id_versao):
    """Coordenador clica em 'Editar seleção' — descongela os selects
    da seção 1 do editor do autor removendo o registro da ultima
    atribuicao para este relatorio na sessao."""
    ultima = session.get("ultima_atribuicao", {})
    if isinstance(ultima, dict) and str(id_versao) in ultima:
        ultima.pop(str(id_versao), None)
        session["ultima_atribuicao"] = ultima
    return redirect(
        url_for("relatorio.editor_autor", id_versao=id_versao)
    )


# ==============================================================
# Editor do Autor
# ==============================================================


@relatorio_bp.route("/editor-autor")
@login_required
def editor_autor():
    """Tela de edicao de conteudo do autor.

    Quando `id_versao` nao e fornecido (entrada pela sidebar), abre
    automaticamente o relatorio de producao mais recente. Caso nao
    exista nenhum relatorio em producao, redireciona com aviso.

    A pagina contem 2 seletores no topo:
     - Relatorio (todos os de producao)
     - Capitulo (todos do relatorio selecionado; com badge para
       indicar de quais o usuario logado e responsavel)

    A area de visualizacao renderiza o DOCX inteiro em modo
    preview; a edicao real continua acontecendo por capitulo
    (fluxo de upload + previa + confirmar) restrito aos capitulos
    onde `id_usuario_responsavel == current_user.id`.
    """
    # Lista de relatorios em producao para o seletor de topo
    todos_relatorios = RelatorioProducao.query.order_by(
        RelatorioProducao.criado_em.desc()
    ).all()

    # Pega id_versao da query string ou usa o mais recente
    id_versao = request.args.get("id_versao", type=int)
    if id_versao is None:
        if not todos_relatorios:
            flash(
                "Nao ha relatorios em producao. Aguarde um coordenador "
                "criar um relatorio antes de acessar o editor.",
                "aviso",
            )
            return redirect(url_for("principal.index"))
        id_versao = todos_relatorios[0].id

    versao = ServicoRelatorio.obter_versao_trabalho(id_versao)
    if not versao:
        flash("Versão não encontrada.", "erro")
        return redirect(url_for("relatorio.relatorios_producao"))

    # Todos os capitulos do relatorio, em ordem hierarquica global
    # (1 -> 1.1 -> 1.2 -> 2 -> 2.1 ...), via indice_capitulo.
    caps_autor = ServicoRelatorio.listar_capitulos_ordenados(versao.id)

    # Capitulos cuja responsabilidade e do usuario logado
    capitulos_do_autor_ids = {
        c.id_capitulo_documento
        for c in caps_autor
        if c.id_usuario_responsavel == current_user.id
    }
    capitulos_livres = [c for c in caps_autor if c.id_usuario_responsavel is None]
    rel_bloqueado = ServicoRelatorio.esta_bloqueado(versao)

    # Capitulo selecionado para upload (via query string).
    # - Autor: so carrega o painel de upload se ele for responsavel.
    # - Coordenador/admin: pode carregar qualquer capitulo do relatorio
    #   (ele upa em nome do autor).
    # O identificador do capitulo e o indice (ex: "4.4.7"), nao o ID do banco.
    id_capitulo_selecionado = request.args.get("capitulo", type=str)
    capitulo_selecionado = None
    envio_pendente = None
    perfil_ativo_inicial = session.get("perfil_ativo")
    
    # Busca o capitulo pelo indice_capitulo
    if id_capitulo_selecionado:
        capitulo_selecionado = next(
            (
                c
                for c in caps_autor
                if c.indice_capitulo == id_capitulo_selecionado
            ),
            None,
        )
    
    pode_abrir_capitulo = (
        capitulo_selecionado is not None
        and (
            capitulo_selecionado.id_usuario_responsavel == current_user.id
            or perfil_ativo_inicial in ("coordenador", "admin")
        )
    )
    
    if pode_abrir_capitulo and capitulo_selecionado:
        envio_pendente = (
            EnvioConteudo.query.filter_by(
                id_capitulo_destino=capitulo_selecionado.id_capitulo_documento,
                status_envio="em_previa",
            )
            .order_by(EnvioConteudo.criado_em.desc())
            .first()
        )

    grupos_acoes = listar_por_grupo(
        perfil_ativo="coordenador",
        rel_bloqueado=rel_bloqueado,
    )

    # Coordenador pode atribuir qualquer capítulo a qualquer autor
    # ativo. Listamos apenas usuários com perfil 'autor' para popular
    # o seletor "Autor responsável" no painel.
    perfil_ativo = session.get("perfil_ativo")
    autores_disponiveis = []
    if perfil_ativo in ("coordenador", "admin"):
        from app.models.dominio import Dominio  # noqa: C0415

        perfil_autor = Dominio.query.filter_by(
            tipo="perfil_usuario", valor="autor"
        ).first()
        if perfil_autor:
            autores_disponiveis = (
                Usuario.query
                .filter_by(perfil_id=perfil_autor.id, ativo=True)
                .order_by(Usuario.nome)
                .all()
            )

    # Estado de "ultima atribuicao" do coordenador para este relatorio.
    # Usado para congelar os selects da seção 1 ate que ele clique em
    # "Editar selecao" (que dispara /limpar-ultima-atribuicao).
    ultima_atribuicao = None
    if perfil_ativo in ("coordenador", "admin"):
        registro = (session.get("ultima_atribuicao") or {}).get(
            str(versao.id)
        )
        if isinstance(registro, dict):
            ultima_atribuicao = registro

    return render_template(
        "editor_autor.html",
        versao=versao,
        todos_relatorios=todos_relatorios,
        capitulos=caps_autor,
        capitulos_livres=capitulos_livres,
        capitulos_do_autor_ids=capitulos_do_autor_ids,
        rel_bloqueado=rel_bloqueado,
        grupos_acoes=grupos_acoes,
        capitulo_selecionado=capitulo_selecionado,
        envio_pendente=envio_pendente,
        perfil_ativo=perfil_ativo,
        autores_disponiveis=autores_disponiveis,
        id_capitulo_selecionado=id_capitulo_selecionado,
        ultima_atribuicao=ultima_atribuicao,
    )


@relatorio_bp.route(
    "/versao-trabalho/<int:id_versao>/editor-autor/assumir-capitulos", methods=["POST"]
)
@login_required
def editor_autor_assumir_capitulos(id_versao):
    """Autor assume responsabilidade por capítulos selecionados."""
    versao = ServicoRelatorio.obter_versao_trabalho(id_versao)
    if not versao:
        flash("Versão não encontrada.", "erro")
        return redirect(url_for("relatorio.relatorios_producao"))
    if ServicoRelatorio.esta_bloqueado(versao):
        flash("Relatório finalizado ou bloqueado.", "erro")
        return redirect(url_for("relatorio.editor_autor", id_versao=id_versao))

    ids = request.form.getlist("capitulos")
    if not ids:
        flash("Selecione ao menos um capítulo.", "aviso")
        return redirect(url_for("relatorio.editor_autor", id_versao=id_versao))

    caps_assumir = CapituloDocumento.query.filter(
        CapituloDocumento.id_relatorio == id_versao,
        CapituloDocumento.id_capitulo_documento.in_(ids),
        CapituloDocumento.id_usuario_responsavel.is_(None),
    ).all()
    for capitulo in caps_assumir:
        capitulo.id_usuario_responsavel = current_user.id
    db.session.commit()

    flash(f"{len(caps_assumir)} capítulo(s) associado(s) ao seu usuário.", "sucesso")
    return redirect(url_for("relatorio.editor_autor") + "?id_versao=" + str(id_versao))


@relatorio_bp.route(
    "/versao-trabalho/<int:id_versao>/editor-autor/enviar-final", methods=["POST"]
)
@login_required
def editor_autor_enviar_final(id_versao):
    """Envia conteúdo final do autor para revisão do coordenador."""
    versao = ServicoRelatorio.obter_versao_trabalho(id_versao)
    if not versao:
        flash("Versão não encontrada.", "erro")
        return redirect(url_for("relatorio.relatorios_producao"))

    if ServicoRelatorio.esta_bloqueado(versao):
        flash("Relatório já finalizado/bloqueado.", "erro")
        return redirect(
            url_for("relatorio.editor_autor") + "?id_versao=" + str(id_versao)
        )

    caps_final = CapituloDocumento.query.filter_by(
        id_relatorio=id_versao,
        id_usuario_responsavel=current_user.id,
    ).all()
    if not caps_final:
        flash("Você não possui capítulos para enviar.", "aviso")
        return redirect(
            url_for("relatorio.editor_autor") + "?id_versao=" + str(id_versao)
        )

    for capitulo in caps_final:
        capitulo.status_capitulo = "enviado_revisao"
    db.session.commit()

    flash(
        "Conteúdo final enviado ao coordenador para revisão. "
        "A edição pelo autor foi encerrada para seus capítulos.",
        "sucesso",
    )
    return redirect(url_for("relatorio.editor_autor") + "?id_versao=" + str(id_versao))


# ==============================================================
# Dispatch universal: abrir editor por perfil
# ==============================================================


@relatorio_bp.route("/producao/<int:id_relatorio>/abrir")
@login_required
def abrir_editor(id_relatorio):
    """Roteia o usuário para o editor adequado ao seu perfil ativo.

    Aceita `?capitulo=<id>` na query string e propaga para o editor
    de destino — assim, o link "Abrir" dentro de uma linha da tabela
    "Painel de Edição — Coordenador" pre-seleciona o capitulo no
    `#ea-cap-select` e em `#ea-atribuir-cap`/`#ea-atribuir-autor` do
    editor do autor (e idem para o coordenador).

    O identificador do capitulo e o indice (ex: "4.4.7"), nao o ID do banco.
    Se receber um ID numerico, converte para indice antes de propagar.
    """
    rel = ServicoRelatorio.obter_versao_trabalho(id_relatorio)
    if not rel:
        flash("Relatório não encontrado.", "erro")
        return redirect(url_for("relatorio.relatorios_producao"))

    id_capitulo = request.args.get("capitulo")
    perfil_ativo = session.get("perfil_ativo")
    
    # Se o capitulo for um ID numerico (int), converte para indice
    indice_capitulo = None
    if id_capitulo:
        try:
            id_capitulo_int = int(id_capitulo)
            # Busca o capitulo pelo ID para obter o indice
            cap = CapituloDocumento.query.get(id_capitulo_int)
            if cap:
                indice_capitulo = cap.indice_capitulo
        except (ValueError, TypeError):
            # Ja e um indice, mantem como esta
            indice_capitulo = id_capitulo
    
    if perfil_ativo in ("coordenador", "admin"):
        url = url_for(
            "relatorio.editor_coordenador", id_versao=id_relatorio
        )
        if indice_capitulo:
            url = f"{url}?capitulo={indice_capitulo}"
        return redirect(url)
    if perfil_ativo == "autor":
        url = (
            url_for("relatorio.editor_autor")
            + "?id_versao=" + str(id_relatorio)
        )
        if indice_capitulo:
            url = f"{url}&capitulo={indice_capitulo}"
        return redirect(url)
    flash("Sem permissão para abrir o editor deste relatório.", "erro")
    return redirect(url_for("relatorio.relatorios_producao"))


# ==============================================================
# Editor do Coordenador (Revisão)
# ==============================================================


@relatorio_bp.route("/editor-coordenador", defaults={"id_versao": None})
@relatorio_bp.route("/versao-trabalho/<int:id_versao>/editor-coordenador")
@login_required
def editor_coordenador(id_versao):
    """Tela principal de revisão e editoração do coordenador.

    Quando `id_versao` nao e fornecido (entrada pela sidebar), abre
    automaticamente o relatorio de producao mais recente. A pagina
    inclui um seletor no topo para trocar de relatorio sem voltar.

    Reúne:
    - Seletor de relatorio (topo)
    - Visualizador do DOCX em producao (eigenpal docx-editor em modo editing)
    - Painel de comandos (catalogo de acoes)
    - Seletor de biblioteca canonica de formatacao
    - Lista de capitulos com status
    - Botao para finalizar relatorio
    """
    # Lista de relatorios em producao para o seletor de topo
    todos_relatorios = RelatorioProducao.query.order_by(
        RelatorioProducao.criado_em.desc()
    ).all()

    if id_versao is None:
        if not todos_relatorios:
            flash(
                "Nao ha relatorios em producao. Crie um para iniciar a " "editoracao.",
                "aviso",
            )
            return redirect(url_for("relatorio.relatorios_producao"))
        id_versao = todos_relatorios[0].id

    versao = ServicoRelatorio.obter_versao_trabalho(id_versao)
    if not versao:
        flash("Versão não encontrada.", "erro")
        return redirect(url_for("relatorio.relatorios_producao"))

    # Bibliotecas canônicas disponíveis para o seletor
    bibliotecas = (
        BibliotecaFormatacaoCanonica.query.filter_by(ativa=True)
        .order_by(BibliotecaFormatacaoCanonica.nome_biblioteca)
        .all()
    )
    biblioteca_atual = None
    if versao.biblioteca_id:
        biblioteca_atual = BibliotecaFormatacaoCanonica.query.get(versao.biblioteca_id)

    # Sincronizar capitulos do banco com o estado atual do DOCX em
    # producao ANTES de listar — garante que a sidebar mostre exata-
    # mente os indices/titulos que estao no documento renderizado.
    # Agora integra classificacao e mapeamento de secoes OOXML.
    # Defensivo: erros aqui nao bloqueiam o editor (apenas logamos).
    if versao.caminho_template and os.path.exists(versao.caminho_template):
        try:
            ressincronizar_capitulos_com_classificacao(versao)
        except Exception as exc:  # pragma: no cover - defesa  # pylint: disable=broad-exception-caught  # noqa: W0718  # pylint: disable=broad-exception-caught
            current_app.logger.warning(
                "Sincronizacao de capitulos falhou (id_rel=%s): %s",
                versao.id,
                exc,
            )

    # Capítulos em ordem hierarquica global (1 -> 1.1 -> 1.2 -> 2 ...).
    caps_coord = ServicoRelatorio.listar_capitulos_ordenados(versao.id)

    rel_bloqueado = ServicoRelatorio.esta_bloqueado(versao)

    # Catalogo de acoes disponiveis para este usuario+relatorio
    grupos_acoes = listar_por_grupo(
        perfil_ativo=session.get("perfil_ativo") or "",
        rel_bloqueado=rel_bloqueado,
    )

    return render_template(
        "editor_coordenador.html",
        versao=versao,
        todos_relatorios=todos_relatorios,
        bibliotecas=bibliotecas,
        biblioteca_atual=biblioteca_atual,
        capitulos=caps_coord,
        rel_bloqueado=rel_bloqueado,
        grupos_acoes=grupos_acoes,
    )


# ==============================================================
# Criar Relatório de Produção
# ==============================================================


@relatorio_bp.route("/producao/novo", methods=["POST"])
def criar_relatorio_producao():
    """Cria relatório de produção com base em informações cadastrais."""
    perfil = session.get("perfil_ativo")
    if perfil != "coordenador" and perfil != "admin":
        flash("Acesso restrito a coordenadores.", "erro")
        return redirect(url_for("principal.index"))

    # Obter status inicial (em_producao)
    status_inicial = Dominio.query.filter_by(
        tipo="status_relatorio", valor="em_producao"
    ).first()

    if not status_inicial:
        flash("Status inicial não configurado.", "erro")
        return redirect(url_for("principal.index"))

    # Processar arquivo DOCX se fornecido
    caminho_template = None
    arquivo = request.files.get("arquivo_docx")
    if arquivo and arquivo.filename.endswith(".docx"):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        dir_relatorios_producao = os.path.join(
            base_dir, "storage", "relatorios_producao"
        )
        os.makedirs(dir_relatorios_producao, exist_ok=True)
        nome_seguro = secure_filename(arquivo.filename)
        caminho_template = os.path.join(dir_relatorios_producao, nome_seguro)
        arquivo.save(caminho_template)

    # Criar relatório de produção
    relatorio = RelatorioProducao(
        codigo_d20=request.form.get("codigo_pli"),
        numero_medicao=request.form.get("numero_medicao", type=int),
        mes_referencia=(
            datetime.strptime(request.form.get("mes_referencia"), "%B de %Y")
            if request.form.get("mes_referencia")
            else None
        ),
        periodo_inicio=(
            datetime.strptime(request.form.get("periodo_inicio"), "%Y-%m-%d")
            if request.form.get("periodo_inicio")
            else None
        ),
        periodo_fim=(
            datetime.strptime(request.form.get("periodo_fim"), "%Y-%m-%d")
            if request.form.get("periodo_fim")
            else None
        ),
        titulo_curto=request.form.get("titulo_curto"),
        status_id=status_inicial.id,
        criado_por=current_user.id,
        ano_referencia=request.form.get("ano_referencia", type=int),
        versao_atual="R00",
        bloqueio_edicao=False,
        caminho_template=caminho_template,
    )

    db.session.add(relatorio)
    db.session.commit()

    flash("Relatório de produção criado com sucesso.", "sucesso")
    return redirect(url_for("relatorio.detalhe_versao", id_versao=relatorio.id))


def _parse_mes_referencia_br(valor):
    """Parse string de mês em PT-BR (ex: 'maio de 2026') para date."""
    if not valor:
        return None
    meses_pt = {
        "janeiro": 1,
        "fevereiro": 2,
        "março": 3,
        "marco": 3,
        "abril": 4,
        "maio": 5,
        "junho": 6,
        "julho": 7,
        "agosto": 8,
        "setembro": 9,
        "outubro": 10,
        "novembro": 11,
        "dezembro": 12,
    }
    v = valor.strip().lower()
    # Aceita "maio de 2026", "maio 2026", "2026-05-01"
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        pass
    for nome, n in meses_pt.items():
        if v.startswith(nome):
            resto = v[len(nome) :].strip().lstrip("de ").strip()
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
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@relatorio_bp.route("/producao/clonar-biblioteca", methods=["POST"])
def clonar_da_biblioteca():
    """Clona um relatório finalizado da biblioteca para produção.

    Idempotente: se já existir um RelatorioProducao com mesmo
    titulo_curto, devolve-o em vez de criar duplicado.
    """
    perfil = session.get("perfil_ativo")
    if perfil not in ("coordenador", "admin"):
        return jsonify({"erro": "Acesso restrito"}), 403

    payload = request.get_json(silent=True) or {}
    arquivo_base = payload.get("arquivo_base")
    biblioteca_id = payload.get("biblioteca_id")
    titulo_curto = (payload.get("titulo_curto") or "").strip()
    codigo_pli = (payload.get("codigo_pli") or "").strip()

    if not arquivo_base:
        return jsonify({"erro": "Arquivo não fornecido"}), 400
    if not biblioteca_id:
        return jsonify({"erro": "Biblioteca de formatação não fornecida"}), 400

    status_inicial = Dominio.query.filter_by(
        tipo="status_relatorio", valor="em_producao"
    ).first()
    if not status_inicial:
        return jsonify({"erro": "Status inicial não configurado"}), 500

    # Anti-duplicação: mesmo título e código → reaproveita
    if titulo_curto or codigo_pli:
        query = RelatorioProducao.query
        if titulo_curto:
            query = query.filter(RelatorioProducao.titulo_curto == titulo_curto)
        if codigo_pli:
            query = query.filter(RelatorioProducao.codigo_d20 == codigo_pli)
        existente = query.first()
        if existente:
            return (
                jsonify(
                    {
                        "mensagem": "Já existe relatório com esses dados",
                        "id_producao": existente.id,
                        "duplicado": True,
                        "logs": [
                            {
                                "mensagem": (
                                    "Relatório já existente — reutilizando registro"
                                ),
                                "status": "success",
                            }
                        ],
                    }
                ),
                200,
            )

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    dir_base = os.path.join(base_dir, "storage", "relatorios_base")
    dir_producao = os.path.join(base_dir, "storage", "relatorios_producao")
    os.makedirs(dir_producao, exist_ok=True)

    caminho_base = os.path.join(dir_base, arquivo_base)
    if not os.path.exists(caminho_base):
        return jsonify({"erro": "Arquivo base não encontrado"}), 404

    nome_arquivo = titulo_curto or arquivo_base.replace(".docx", "")
    # Suffix com timestamp para evitar sobrescrita ao reclonar
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    nome_arquivo_seguro = secure_filename(f"{nome_arquivo}_{timestamp}.docx")
    caminho_producao = os.path.join(dir_producao, nome_arquivo_seguro)
    shutil.copy2(caminho_base, caminho_producao)

    relatorio_producao = RelatorioProducao(
        codigo_d20=codigo_pli or "D-20",
        numero_medicao=(
            int(payload["numero_medicao"]) if payload.get("numero_medicao") else None
        ),
        mes_referencia=_parse_mes_referencia_br(payload.get("mes_referencia")),
        periodo_inicio=_parse_data_iso(payload.get("periodo_inicio")),
        periodo_fim=_parse_data_iso(payload.get("periodo_fim")),
        titulo_curto=titulo_curto or None,
        status_id=status_inicial.id,
        criado_por=current_user.id,
        ano_referencia=(
            int(payload["ano_referencia"]) if payload.get("ano_referencia") else None
        ),
        versao_atual="R00",
        bloqueio_edicao=False,
        caminho_template=caminho_producao,
        biblioteca_id=biblioteca_id,
    )
    db.session.add(relatorio_producao)
    db.session.commit()

    logs = [
        {"mensagem": "Validando dados...", "status": "success"},
        {"mensagem": "Copiando arquivo...", "status": "success"},
        {"mensagem": "Criando relatório de produção...", "status": "success"},
        {"mensagem": "Configurando status inicial...", "status": "success"},
        {
            "mensagem": ("Personalizando capa, folha de rosto e versão..."),
            "status": "pending",
        },
        {"mensagem": "Extraindo estrutura de capítulos...", "status": "pending"},
    ]

    # Personalizar capa/folha de rosto/controle de versoes com dados
    # do relatorio recem-criado. Defensivo: erros aqui nao bloqueiam
    # a clonagem — o coordenador pode reaplicar manualmente depois
    # via botoes 'Atualizar Capa' / 'Atualizar Folha de Rosto' no
    # painel do editor.
    try:
        info_capa = aplicar_dados_completos(
            caminho_producao,
            relatorio_producao,
        )
        partes = []
        if info_capa["capa"]["sucesso"]:
            partes.append("capa")
        if info_capa["folha_rosto"]["sucesso"]:
            n_ln = len(info_capa["folha_rosto"].get("linhas_alteradas", []))
            partes.append(f"folha de rosto ({n_ln} campos)")
        if info_capa["controle_versoes"]["sucesso"]:
            partes.append("versão R00")
        if partes:
            logs[4] = {
                "mensagem": (
                    f"Personalizando capa, folha de rosto e versão... "
                    f'OK ({", ".join(partes)})'
                ),
                "status": "success",
            }
        else:
            logs[4] = {
                "mensagem": (
                    "Personalização da capa: nenhum elemento "
                    "reconhecido no template — reaplicar manualmente "
                    "no editor."
                ),
                "status": "warning",
            }
    except Exception as exc:  # pragma: no cover - defesa  # pylint: disable=broad-exception-caught
        logs[4] = {
            "mensagem": (
                f"Personalização da capa falhou (não bloqueia " f"clonagem): {exc}"
            ),
            "status": "warning",
        }

    try:
        doc = Document(caminho_producao)
        # pylint: disable=protected-access
        capitulos_arvore = ServicoExtracaoCanonica._extrair_capitulos(
            doc
        )  # noqa: SLF001, E501

        # Antes de inserir: garantir que não há capítulos existentes
        # para este relatório (defesa contra duplicação por re-clone).
        CapituloDocumento.query.filter_by(id_relatorio=relatorio_producao.id).delete()

        # Numeração de capítulos no nível raiz é INDEPENDENTE por tipo:
        # pré-textuais (SUMÁRIO, APRESENTAÇÃO, ...) não consomem números
        # da contagem dos textuais. Para o relatório típico, o capítulo
        # textual "Apresentação" deve aparecer como "1", não como "2"
        # só porque o SUMÁRIO veio antes na árvore.
        ordem_global = 1  # contador global (preserva ordem absoluta)
        ordem_por_tipo = {"pre_textual": 0, "textual": 0, "pos_textual": 0}
        total = 0
        for cap_raiz in capitulos_arvore:
            tipo_raiz = cap_raiz.get("tipo_elemento", "textual")
            ordem_por_tipo[tipo_raiz] = ordem_por_tipo.get(tipo_raiz, 0) + 1
            _criar_capitulo_recursivo(
                cap_raiz,
                relatorio_producao.id,
                None,
                ordem_por_tipo[tipo_raiz],
                ordem_absoluta=ordem_global,
            )
            ordem_global += 1
            total += 1

        db.session.commit()
        logs[-1] = {
            "mensagem": (
                f"Extraindo estrutura de capítulos... "
                f"({total} raízes; árvore deduplicada)"
            ),
            "status": "success",
        }
    except Exception as e:  # noqa: W0718  # pylint: disable=broad-exception-caught
        db.session.rollback()
        logs[-1] = {"mensagem": f"Erro ao extrair capítulos: {e}", "status": "error"}
        return (
            jsonify(
                {
                    "erro": f"Erro ao extrair capítulos: {e}",
                    "logs": logs,
                }
            ),
            500,
        )

    return jsonify(
        {
            "mensagem": "Clonagem realizada com sucesso",
            "id_producao": relatorio_producao.id,
            "logs": logs,
        }
    )


@relatorio_bp.route("/envio/<int:id_envio>/editar-inline", methods=["PUT"])
@login_required
def editar_envio_inline(id_envio):
    """Edição inline de campos do envio de conteúdo."""
    perfil = session.get("perfil_ativo")
    if perfil not in ("coordenador", "admin"):
        return jsonify({"erro": "Acesso restrito a coordenadores."}), 403

    envio = EnvioConteudo.query.get_or_404(id_envio)
    dados = request.get_json(silent=True) or {}

    campos_permitidos = ["nome_arquivo", "status_envio"]

    try:
        for campo in campos_permitidos:
            if campo in dados:
                setattr(envio, campo, dados[campo])
        db.session.commit()
        return jsonify(
            {
                "mensagem": "Envio atualizado.",
                "dados": {
                    "id": envio.id_envio_conteudo,
                    "nome_arquivo": envio.nome_arquivo,
                    "status_envio": envio.status_envio,
                },
            }
        )
    except Exception as e:  # noqa: W0718  # pylint: disable=broad-exception-caught
        db.session.rollback()
        return jsonify({"erro": f"Erro ao atualizar: {e}"}), 500


@relatorio_bp.route("/producao/<int:id_relatorio>/editar-inline", methods=["PUT"])
@login_required
def editar_relatorio_producao_inline(id_relatorio):
    """Edição inline de campos do relatório de produção."""
    perfil = session.get("perfil_ativo")
    if perfil not in ("coordenador", "admin"):
        return jsonify({"erro": "Acesso restrito a coordenadores."}), 403

    relatorio = RelatorioProducao.query.get_or_404(id_relatorio)
    dados = request.get_json(silent=True) or {}

    campos_texto = ["titulo_curto", "codigo_d20", "versao_atual"]

    try:
        for campo in campos_texto:
            if campo in dados:
                setattr(relatorio, campo, dados[campo])

        if "numero_medicao" in dados and dados["numero_medicao"]:
            relatorio.numero_medicao = int(dados["numero_medicao"])
        if "periodo_inicio" in dados and dados["periodo_inicio"]:
            relatorio.periodo_inicio = datetime.strptime(
                dados["periodo_inicio"], "%Y-%m-%d"
            ).date()
        if "periodo_fim" in dados and dados["periodo_fim"]:
            relatorio.periodo_fim = datetime.strptime(
                dados["periodo_fim"], "%Y-%m-%d"
            ).date()

        relatorio.atualizado_em = datetime.now(timezone.utc)
        db.session.commit()
        return jsonify(
            {
                "mensagem": "Relatório atualizado.",
                "dados": {
                    "id": relatorio.id,
                    "titulo_curto": relatorio.titulo_curto or "",
                    "codigo_d20": relatorio.codigo_d20,
                    "versao_atual": relatorio.versao_atual,
                    "numero_medicao": relatorio.numero_medicao,
                },
            }
        )
    except Exception as e:  # noqa: W0718  # pylint: disable=broad-exception-caught
        db.session.rollback()
        return jsonify({"erro": f"Erro ao atualizar: {e}"}), 500


@relatorio_bp.route("/producao/<int:id_relatorio>/excluir", methods=["POST"])
@login_required
def excluir_relatorio_producao(id_relatorio):
    """Exclui relatório de produção e remove arquivo do storage."""

    perfil = session.get("perfil_ativo")
    if perfil != "coordenador" and perfil != "admin":
        return jsonify({"erro": "Acesso restrito a coordenadores."}), 403

    relatorio = RelatorioProducao.query.get_or_404(id_relatorio)
    titulo = relatorio.titulo_curto or relatorio.codigo_d20 or "Relatório"

    try:
        # Deletar capítulos associados primeiro
        CapituloDocumento.query.filter_by(id_relatorio=id_relatorio).delete()

        # Remover arquivo do storage/relatorios_producao
        if relatorio.caminho_template and os.path.exists(relatorio.caminho_template):
            os.remove(relatorio.caminho_template)

        db.session.delete(relatorio)
        db.session.commit()
        return jsonify({"mensagem": f'Relatório "{titulo}" excluído com sucesso.'})
    except (OSError, IOError) as e:
        db.session.rollback()
        return jsonify({"erro": f"Erro ao excluir relatório: {e}"}), 500


@relatorio_bp.route("/producao/<int:id_relatorio>/gerar-final")
@login_required
def gerar_final(id_relatorio):
    """Finaliza o relatório em produção e entrega o DOCX final.

    Fluxo (pós-Fase 1 do merge in-place):
    1. O DOCX em `caminho_template` JÁ É o documento montado — autores
       fizeram merge in-place de cada capítulo via `servico_merge_docx`.
       Não há reconstrução capítulo a capítulo do banco.
    2. `ServicoFinalizarRelatorio.finalizar` cria um snapshot em
       `storage/relatorios_finalizados/`, calcula checksum, persiste
       `RelatorioFinalizado`, avança status para `finalizado` e
       bloqueia edição.
    3. Devolve o snapshot como download.
    """

    vt = RelatorioProducao.query.get_or_404(id_relatorio)
    try:
        rf = finalizar(
            id_relatorio=vt.id,
            id_usuario=current_user.id,
        )
    except FinalizacaoError as e:
        flash(f"Não foi possível finalizar: {e}", "erro")
        return redirect(url_for("relatorio.detalhe_versao", id_versao=id_relatorio))
    except (OSError, RuntimeError) as e:
        flash(f"Erro inesperado ao finalizar: {e}", "erro")
        return redirect(url_for("relatorio.detalhe_versao", id_versao=id_relatorio))

    return send_file(
        rf.caminho_arquivo,
        as_attachment=True,
        download_name=rf.nome_arquivo,
        mimetype=(
            "application/vnd.openxmlformats-officedocument" ".wordprocessingml.document"
        ),
    )


@relatorio_bp.route("/producao/<int:id_relatorio>/exportar-preview")
@login_required
def exportar_preview(id_relatorio):
    """Gera e baixa um DOCX de preview sem finalizar o relatório."""

    rel = RelatorioProducao.query.get_or_404(id_relatorio)
    try:
        info = gerar_preview(rel)
    except FinalizacaoError as e:
        flash(f"Não foi possível exportar preview: {e}", "erro")
        return redirect(url_for("relatorio.editor_coordenador", id_versao=id_relatorio))
    except (OSError, RuntimeError) as e:
        flash(f"Erro inesperado ao exportar preview: {e}", "erro")
        return redirect(url_for("relatorio.editor_coordenador", id_versao=id_relatorio))

    return send_file(
        info["caminho_arquivo"],
        as_attachment=True,
        download_name=info["nome_arquivo"],
        mimetype=(
            "application/vnd.openxmlformats-officedocument" ".wordprocessingml.document"
        ),
    )


# =====================================================================
# Inserir Sumário / Lista de Figuras / Lista de Tabelas
# (operações explícitas do coordenador — pré-textuais com conteúdo
# já calculado, sem depender de o Word recalcular ao abrir)
# =====================================================================


def _executar_insercao_pre_textual(
    id_relatorio: int,
    operacao,  # callable(caminho, perfil) -> dict
    nome_amigavel: str,  # 'Sumário' / 'Lista de Figuras' / etc.
):
    """Helper comum para as 3 rotas de inserção. Verifica perfil
    coordenador, bloqueio do relatório, executa a operação e devolve
    flash + redirect.
    """
    if session.get("perfil_ativo") not in ("coordenador", "admin"):
        flash("Apenas o coordenador pode inserir esses elementos.", "erro")
        return redirect(url_for("relatorio.detalhe_versao", id_versao=id_relatorio))

    rel = RelatorioProducao.query.get_or_404(id_relatorio)
    if ServicoRelatorio.esta_bloqueado(rel):
        flash(
            f"Relatório já finalizado — não é possível atualizar "
            f"{nome_amigavel}. Crie uma nova versão.",
            "erro",
        )
        return redirect(url_for("relatorio.detalhe_versao", id_versao=id_relatorio))

    if not rel.caminho_template or not os.path.exists(rel.caminho_template):
        flash(
            "DOCX em produção indisponível. Faça upload do template " "primeiro.",
            "erro",
        )
        return redirect(url_for("relatorio.detalhe_versao", id_versao=id_relatorio))

    try:
        perfil = PerfilFormatacao.de_relatorio(rel)
        info = operacao(rel.caminho_template, perfil=perfil)
        flash(
            f"{nome_amigavel} inserido(a): " f'{info.get("entradas", 0)} entradas.',
            "sucesso",
        )
    except (OSError, ValueError, RuntimeError) as e:
        flash(f"Erro ao inserir {nome_amigavel}: {e}", "erro")

    return redirect(url_for("relatorio.detalhe_versao", id_versao=id_relatorio))


@relatorio_bp.route(
    "/producao/<int:id_relatorio>/inserir-sumario",
    methods=["POST"],
)
@login_required
def inserir_sumario_route(id_relatorio):
    """Coordenador insere/atualiza o Sumário pré-preenchido na pré-textual."""
    return _executar_insercao_pre_textual(
        id_relatorio,
        inserir_sumario,
        "Sumário",
    )


@relatorio_bp.route(
    "/producao/<int:id_relatorio>/inserir-lista-figuras",
    methods=["POST"],
)
@login_required
def inserir_lista_figuras_route(id_relatorio):
    """Coordenador insere/atualiza a Lista de Figuras pré-preenchida."""
    return _executar_insercao_pre_textual(
        id_relatorio,
        inserir_lista_figuras,
        "Lista de Figuras",
    )


@relatorio_bp.route(
    "/producao/<int:id_relatorio>/inserir-lista-tabelas",
    methods=["POST"],
)
@login_required
def inserir_lista_tabelas_route(id_relatorio):
    """Coordenador insere/atualiza a Lista de Tabelas pré-preenchida."""
    return _executar_insercao_pre_textual(
        id_relatorio,
        inserir_lista_tabelas,
        "Lista de Tabelas",
    )


@relatorio_bp.route(
    "/producao/<int:id_relatorio>/reindexar-captions",
    methods=["POST"],
)
@login_required
def reindexar_captions_route(id_relatorio):
    """Coordenador reindexa numeração de figuras/tabelas/equações e
    atualiza todas as referências cruzadas (`Figura X.Y`, `Tabela X.Y`, etc.)
    no DOCX em produção.

    É uma operação atômica:
      1. `reindexar_captions` — re-numera todas as legendas marcadas
         e devolve um mapa `texto antigo → novo número` para cada label.
      2. `substituir_referencias` — varre o corpo do DOCX e substitui
         os textos das cross-references usando esse mapa.

    Idempotente — pode ser executada quantas vezes for necessário
    (após cada upload de capítulo, por exemplo).
    """
    if session.get("perfil_ativo") not in ("coordenador", "admin"):
        flash(
            "Apenas o coordenador pode reindexar captions/refs.",
            "erro",
        )
        return redirect(url_for("relatorio.editor_coordenador", id_versao=id_relatorio))

    rel = RelatorioProducao.query.get_or_404(id_relatorio)
    if ServicoRelatorio.esta_bloqueado(rel):
        flash(
            "Relatório finalizado — não é possível reindexar. " "Crie uma nova versão.",
            "erro",
        )
        return redirect(url_for("relatorio.editor_coordenador", id_versao=id_relatorio))

    if not rel.caminho_template or not os.path.exists(rel.caminho_template):
        flash(
            "DOCX em produção indisponível. Faça upload do template " "primeiro.",
            "erro",
        )
        return redirect(url_for("relatorio.editor_coordenador", id_versao=id_relatorio))

    try:
        perfil = PerfilFormatacao.de_relatorio(rel)
        info = reindexar_captions(rel.caminho_template, perfil=perfil)
        mapa = info.get("mapa_labels", {}) if isinstance(info, dict) else {}
        n_refs = substituir_referencias(rel.caminho_template, mapa)
        resolvidas = n_refs.get('tags_resolvidas', 0) if isinstance(n_refs, dict) else 0
        nao_resolvidas = n_refs.get('tags_nao_resolvidas', 0) if isinstance(n_refs, dict) else 0
        sufixo_nao_resolvidas = (
            f', {nao_resolvidas} não resolvida(s)' if nao_resolvidas else ''
        )
        flash(
            f'Reindexação concluída: {info.get("figuras", 0)} figuras, '
            f'{info.get("tabelas", 0)} tabelas, '
            f'{info.get("equacoes", 0)} equações; '
            f'{resolvidas} ref(s) atualizada(s){sufixo_nao_resolvidas}.',
            "sucesso",
        )
    except (OSError, ValueError, RuntimeError) as e:
        flash(f"Erro ao reindexar: {e}", "erro")

    return redirect(url_for("relatorio.editor_coordenador", id_versao=id_relatorio))


@relatorio_bp.route("/producao/<int:id_relatorio>/docx")
@login_required
def baixar_docx_producao(id_relatorio):
    """Serve o DOCX do relatório de produção para visualização.

    O conteúdo é sanitizado em memória (células de tabela vazias ganham
    um parágrafo vazio) para compatibilidade com o editor eigenpal, que
    rejeita estruturas como `tableRow: <>`. O arquivo no disco não é
    modificado.
    """

    relatorio = RelatorioProducao.query.get_or_404(id_relatorio)

    if not relatorio.caminho_template:
        return ("DOCX não disponível", 404)

    if not os.path.exists(relatorio.caminho_template):
        return ("Arquivo não encontrado", 404)

    mimetype = (
        "application/vnd.openxmlformats-officedocument" ".wordprocessingml.document"
    )

    bytes_sanitizados = sanitizar_docx(relatorio.caminho_template)
    if bytes_sanitizados is None:
        # fallback: serve o arquivo como está
        return send_file(
            relatorio.caminho_template,
            as_attachment=False,
            mimetype=mimetype,
        )

    return send_file(
        BytesIO(bytes_sanitizados),
        as_attachment=False,
        mimetype=mimetype,
        download_name=f"relatorio_{id_relatorio}.docx",
    )


@relatorio_bp.route("/producao/upload-docx", methods=["POST"])
def upload_docx_clonagem():
    """Faz upload de DOCX para clonagem."""
    perfil = session.get("perfil_ativo")
    if perfil != "coordenador" and perfil != "admin":
        return jsonify({"erro": "Acesso restrito"}), 403

    arquivo = request.files.get("arquivo_docx")
    if not arquivo or not arquivo.filename.endswith(".docx"):
        return jsonify({"erro": "Arquivo inválido"}), 400

    # Salvar arquivo temporariamente
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    dir_temp = os.path.join(base_dir, "storage", "temp")
    os.makedirs(dir_temp, exist_ok=True)
    nome_seguro = secure_filename(arquivo.filename)
    caminho = os.path.join(dir_temp, nome_seguro)
    arquivo.save(caminho)

    # NOTE: Implementar extração de elementos DOCX
    # Usar ServicoExtracaoCanonica para extrair estrutura

    return jsonify({"mensagem": "Upload realizado", "caminho": caminho})


# ==============================================================
# Envios de Conteúdo
# ==============================================================

# ==============================================================
# Upload, prévia e confirmação do autor
# ==============================================================


@relatorio_bp.route(
    "/versao-trabalho/<int:id_versao>/capitulo/<int:id_capitulo>/upload",
    methods=["GET", "POST"],
)
def upload_conteudo(id_versao, id_capitulo):
    """Tela de upload de conteúdo do autor para um capítulo.

    GET: Retorna o componente de upload para HTMX.
    POST: Processa o upload do arquivo DOCX.

    Gate de autoria: o autor só pode enviar conteúdo para capítulos
    onde ele é o `id_usuario_responsavel`. Coordenadores e admins
    têm acesso irrestrito (podem enviar conteúdo em nome de qualquer
    capítulo, ex.: para correções urgentes).
    """
    versao = ServicoRelatorio.obter_versao_trabalho(id_versao)
    capitulo = CapituloDocumento.query.get_or_404(id_capitulo)
    if not versao or capitulo.id_relatorio != versao.id:
        if request.method == "GET":
            return '<p class="ea__panel-text">Capítulo não encontrado.</p>'
        flash("Capítulo não pertence à versão informada.", "erro")
        return redirect(url_for("relatorio.relatorios_producao"))

    # Bloqueio pós-finalização: nenhum upload é aceito.
    if ServicoRelatorio.esta_bloqueado(versao):
        if request.method == "GET":
            return '<p class="ea__panel-text">Relatório finalizado/bloqueado.</p>'
        flash(
            "Relatório já foi finalizado/bloqueado. Uploads ficam "
            "desabilitados até que uma nova versão seja aberta.",
            "erro",
        )
        return redirect(url_for("relatorio.detalhe_versao", id_versao=id_versao))

    # GET: retorna o componente de upload
    if request.method == "GET":
        envio = EnvioConteudo.query.filter_by(
            id_capitulo_destino=id_capitulo, status_envio="pendente"
        ).first()
        return render_template(
            "components/capitulo/upload_docx.html",
            versao_trabalho=versao,
            capitulo=capitulo,
            envio=envio,
            preview_html=None,
        )

    perfil = session.get("perfil_ativo")
    eh_responsavel = capitulo.id_usuario_responsavel == current_user.id
    if perfil == "autor" and not eh_responsavel:
        flash(
            "Você não é o responsável atribuído por este capítulo. "
            "Apenas o autor designado pode enviar conteúdo aqui.",
            "erro",
        )
        return redirect(url_for("relatorio.versao_trabalho", id_versao=id_versao))

    if perfil == "autor" and capitulo.status_capitulo == "enviado_revisao":
        flash(
            "Este capítulo já foi enviado ao coordenador para revisão. "
            "A edição pelo autor está encerrada.",
            "erro",
        )
        return redirect(url_for("relatorio.editor_autor", id_versao=id_versao))

    if request.method == "POST":
        arquivo = request.files.get("arquivo_docx")
        if not arquivo or not (arquivo.filename or "").endswith(".docx"):
            flash("Envie um arquivo .docx válido.", "erro")
            return redirect(
                url_for(
                    "relatorio.upload_conteudo",
                    id_versao=id_versao,
                    id_capitulo=id_capitulo,
                )
            )
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        try:
            envio = ServicoEnvioAutor.processar_upload(
                id_relatorio=id_versao,
                id_usuario=current_user.id,
                arquivo_storage=arquivo,
                base_dir=base_dir,
                id_capitulo_destino=id_capitulo,
            )
        except (OSError, ValueError) as e:
            flash(f"Falha no upload: {e}", "erro")
            return redirect(
                url_for(
                    "relatorio.upload_conteudo",
                    id_versao=id_versao,
                    id_capitulo=id_capitulo,
                )
            )
        flash("Upload realizado. Revise a prévia e confirme a importação.", "sucesso")
        return redirect(
            url_for(
                "relatorio.editor_autor",
                id_versao=id_versao,
                capitulo=id_capitulo,
            )
        )

    # GET: render tela
    envio = (
        EnvioConteudo.query.filter_by(
            id_relatorio=id_versao,
            id_usuario=current_user.id,
            status_envio="em_previa",
        )
        .order_by(EnvioConteudo.criado_em.desc())
        .first()
    )
    capitulos_nav = ServicoRelatorio.listar_capitulos(id_versao)
    return render_conteudo(
        ["components/capitulo/upload_docx.html"],
        versao_trabalho=versao,
        capitulo=capitulo,
        envio=envio,
        capitulos_nav=capitulos_nav,
        preview_html=None,
    )


@relatorio_bp.route("/envios-conteudo/<int:id_envio>/previa")
def previa_envio(id_envio):
    """Mostra prévias geradas a partir do envio para o autor confirmar."""
    envio = EnvioConteudo.query.get_or_404(id_envio)
    if envio.id_usuario != current_user.id and session.get("perfil_ativo") not in (
        "coordenador",
        "admin",
    ):
        flash("Sem permissão.", "erro")
        return redirect(url_for("principal.index"))

    previas = envio.previsualizacoes
    versao = ServicoRelatorio.obter_versao_trabalho(envio.id_relatorio)

    # Carregar sugestões do envio
    sugestoes = {}
    if envio.sugestoes_json:
        try:
            sugestoes = json.loads(envio.sugestoes_json)
        except (json.JSONDecodeError, TypeError):
            sugestoes = {}

    return render_conteudo(
        ["components/capitulo/previa_envio.html"],
        envio=envio,
        previas=previas,
        versao_trabalho=versao,
        sugestoes=sugestoes,
    )


@relatorio_bp.route(
    "/envios-conteudo/<int:id_envio>/confirmar/<acao>", methods=["POST"]
)
def confirmar_envio(id_envio, acao):
    """Aplica decisão do autor: importar ou rejeitar."""
    envio = EnvioConteudo.query.get_or_404(id_envio)
    if envio.id_usuario != current_user.id and session.get("perfil_ativo") not in (
        "coordenador",
        "admin",
    ):
        flash("Sem permissão.", "erro")
        return redirect(url_for("principal.index"))

    if acao not in ("importar", "rejeitar"):
        flash("Ação inválida.", "erro")
        return redirect(url_for("relatorio.previa_envio", id_envio=id_envio))

    resultado = ServicoEnvioAutor.confirmar(envio=envio, acao=acao)
    if not resultado.get("ok"):
        flash(resultado.get("erro") or "Falha ao processar.", "erro")
        return redirect(url_for("relatorio.previa_envio", id_envio=id_envio))

    if acao == "importar":
        flash(
            f"Importado para {resultado.get('capitulos_atualizados', 0)} "
            f"capítulo(s).",
            "sucesso",
        )
    else:
        flash("Envio rejeitado.", "info")

    return redirect(url_for("relatorio.detalhe_versao", id_versao=envio.id_relatorio))


@relatorio_bp.route(
    "/capitulo/<int:id_capitulo>/aprovar",
    methods=["POST"],
)
def aprovar_capitulo(id_capitulo):
    """Coordenador aprova o conteúdo do capítulo (aplica renomeações
    pendentes nível 1/2 e marca como aprovado)."""
    if session.get("perfil_ativo") not in ("coordenador", "admin"):
        flash("Apenas coordenadores podem aprovar capítulos.", "erro")
        return redirect(url_for("principal.index"))

    capitulo = CapituloDocumento.query.get_or_404(id_capitulo)
    observacao = (request.form.get("observacao") or "").strip()

    resultado = ServicoEnvioAutor.aprovar_capitulo(
        capitulo=capitulo,
        coordenador=current_user,
        observacao=observacao or None,
    )
    if not resultado.get("ok"):
        flash(resultado.get("erro") or "Falha ao aprovar.", "erro")
    else:
        n_renom = len(resultado.get("renomeacoes_aplicadas") or [])
        msg = "Capítulo aprovado."
        if n_renom:
            msg += (
                f" {n_renom} renomeação(ões) aplicada(s) "
                "(banco e DOCX em produção)."
            )
        flash(msg, "sucesso")

    return redirect(
        url_for(
            "relatorio.editor_coordenador",
            id_versao=capitulo.id_relatorio,
        )
    )


@relatorio_bp.route(
    "/capitulo/<int:id_capitulo>/rejeitar",
    methods=["POST"],
)
def rejeitar_capitulo(id_capitulo):
    """Coordenador rejeita o capítulo, devolvendo-o para edição."""
    if session.get("perfil_ativo") not in ("coordenador", "admin"):
        flash("Apenas coordenadores podem rejeitar capítulos.", "erro")
        return redirect(url_for("principal.index"))

    capitulo = CapituloDocumento.query.get_or_404(id_capitulo)
    observacao = (request.form.get("observacao") or "").strip()

    resultado = ServicoEnvioAutor.rejeitar_capitulo(
        capitulo=capitulo,
        coordenador=current_user,
        observacao=observacao or None,
    )
    if not resultado.get("ok"):
        flash(resultado.get("erro") or "Falha ao rejeitar.", "erro")
    else:
        flash(
            "Capítulo devolvido para edição. O autor foi notificado.",
            "info",
        )

    return redirect(
        url_for(
            "relatorio.editor_coordenador",
            id_versao=capitulo.id_relatorio,
        )
    )


@relatorio_bp.route(
    "/envios-conteudo/<int:id_envio>/excluir",
    methods=["POST"],
)
@login_required
def excluir_envio(id_envio):
    """Exclui um envio de conteudo (registro + arquivo no storage).

    Restrito a coordenador/admin (impacta o registro consolidado da
    tabela de envios). O autor remove via "Rejeitar e reenviar" no
    proprio fluxo de upload, que invalida o envio anterior.
    """
    if session.get("perfil_ativo") not in ("coordenador", "admin"):
        flash("Apenas coordenadores podem excluir envios.", "erro")
        return redirect(url_for("principal.index"))

    envio = EnvioConteudo.query.get_or_404(id_envio)
    id_relatorio = envio.id_relatorio

    # Remove arquivo do storage e cascateia previsualizacoes.
    try:
        if envio.caminho_arquivo and os.path.exists(envio.caminho_arquivo):
            os.remove(envio.caminho_arquivo)
    except OSError:
        pass

    for prev in list(envio.previsualizacoes or []):
        db.session.delete(prev)
    db.session.delete(envio)
    db.session.commit()
    flash("Envio excluído.", "sucesso")

    proximo = request.form.get("proximo") or url_for(
        "relatorio.editor_coordenador", id_versao=id_relatorio
    )
    return redirect(proximo)


@relatorio_bp.route("/envios-conteudo/<int:id_envio>/conteudo", methods=["POST"])
def salvar_conteudo_autor(id_envio):
    """Alias de compatibilidade com o template de prévia.

    Aceita texto HTML editado pelo autor antes da confirmação.
    Atualmente, apenas marca o envio como atualizado.
    """
    envio = EnvioConteudo.query.get_or_404(id_envio)
    if envio.id_usuario != current_user.id:
        return jsonify({"erro": "Sem permissão"}), 403
    # Persistência do HTML editado: associa como prévia 'editada'.
    dados = request.get_data(as_text=True) or ""
    if dados:
        prev = PrevisualizacaoConteudo(
            id_envio_conteudo=envio.id_envio_conteudo,
            tipo_previsualizacao="editada",
            resultado_html=dados,
        )
        db.session.add(prev)
        db.session.commit()
    return jsonify({"ok": True})


@relatorio_bp.route("/envios-conteudo")
def listar_envios_conteudo():
    """Lista envios de conteúdo filtrando por relatório."""
    id_relatorio = request.args.get("id_relatorio", type=int)

    if id_relatorio:
        envios = (
            EnvioConteudo.query.filter_by(id_relatorio=id_relatorio)
            .order_by(EnvioConteudo.criado_em.desc())
            .all()
        )
    else:
        envios = []

    return render_conteudo(
        ["components/relatorio/tabela_envios_conteudo.html"], envios=envios
    )


@relatorio_bp.route("/todos-relatorios")
def listar_todos_relatorios():
    """Lista todos os relatórios da VIEW vw_todos_relatorios."""

    conn = db.session.connection()
    result = conn.execute(text("""
        SELECT * FROM vw_todos_relatorios
        ORDER BY data_criacao DESC
    """))

    relatorios = []
    for row in result:
        relatorios.append(
            {
                "id": row.id,
                "tipo_relatorio": row.tipo_relatorio,
                "codigo": row.codigo,
                "titulo": row.titulo,
                "numero_medicao": row.numero_medicao,
                "mes_referencia": row.mes_referencia,
                "ano_referencia": row.ano_referencia,
                "periodo_inicio": row.periodo_inicio,
                "periodo_fim": row.periodo_fim,
                "status_codigo": row.status_codigo,
                "status_descricao": row.status_descricao,
                "data_criacao": row.data_criacao,
                "versao": row.versao,
                "criador_nome": row.criador_nome,
            }
        )

    return render_conteudo(
        ["components/relatorio/tabela_todos_relatorios.html"], relatorios=relatorios
    )
