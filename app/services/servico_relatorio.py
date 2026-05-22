"""Serviços de domínio para relatórios, modelos e capítulos."""

from app import db
from app.models.modelo_relatorio import ModeloRelatorio
from app.models.relatorio_producao import RelatorioProducao
from app.models.relatorio_finalizado import RelatorioFinalizado
from app.models.relatorio_base import RelatorioBase
from app.models.capitulo_documento import CapituloDocumento


class ServicoRelatorio:
    """Serviço centralizado para operações sobre relatórios e capítulos."""

    # --- Modelo de relatório ---

    @staticmethod
    def listar_modelos(apenas_ativos=True):
        query = ModeloRelatorio.query
        if apenas_ativos:
            query = query.filter_by(ativo=True)
        return query.all()

    @staticmethod
    def criar_modelo(nome_modelo, descricao=None):
        modelo = ModeloRelatorio(
            nome_modelo=nome_modelo,
            descricao=descricao
        )
        db.session.add(modelo)
        db.session.commit()
        return modelo

    @staticmethod
    def criar_modelo_completo(nome_modelo, descricao,
                              ativo, _caminho_docx):
        """
        Cria modelo e relatório base.
        Versão de trabalho é um fluxo separado.
        """
        # 1. Modelo
        modelo = ModeloRelatorio(
            nome_modelo=nome_modelo,
            descricao=descricao,
            ativo=ativo
        )
        db.session.add(modelo)
        db.session.flush()

        # 2. Relatório finalizado (substitui relatorio_base)
        # NOTE: Implementar criação de RelatorioFinalizado
        # relatorio = RelatorioFinalizado(
        #     relatorio_id=modelo.id_modelo_relatorio,
        #     titulo=nome_modelo,
        #     versao='1.0',
        #     artefato_docx=...,
        #     nome_arquivo=...,
        #     finalizado_por=...,
        #     data_finalizacao=db.func.now()
        # )
        # db.session.add(relatorio)
        db.session.commit()
        return modelo

    @staticmethod
    def listar_relatorios_base():
        return RelatorioBase.query.all()

    @staticmethod
    def _criar_capitulos_da_arvore(itens, id_relatorio,
                                   id_pai=None, ordem_inicial=1):
        """Percorre árvore de capítulos e cria registros no banco."""
        ordem = ordem_inicial
        for item in itens:
            capitulo = CapituloDocumento(
                id_relatorio=id_relatorio,
                id_capitulo_pai=id_pai,
                ordem_capitulo=ordem,
                titulo_capitulo=item['titulo'],
                nivel_capitulo=item['nivel'],
                nome_capitulo=item.get('nome') or item['titulo'],
                indice_capitulo=str(item['nivel'])
            )
            db.session.add(capitulo)
            db.session.flush()

            if item.get('filhos'):
                ServicoRelatorio._criar_capitulos_da_arvore(
                    item['filhos'],
                    id_relatorio,
                    capitulo.id_capitulo_documento,
                    1
                )
            ordem += 1

    # --- Relatório finalizado (substitui relatorio base) ---

    @staticmethod
    def listar_relatorios_finalizados():
        try:
            return RelatorioFinalizado.query.all()
        except Exception:
            # Tabela pode não existir ainda
            return []

    @staticmethod
    def obter_relatorio_finalizado(id_relatorio):
        return RelatorioFinalizado.query.get(id_relatorio)

    @staticmethod
    def criar_relatorio_finalizado(relatorio_id, titulo,
                                   versao=None, caminho_arquivo=None):
        # NOTE: Implementar criação de RelatorioFinalizado
        pass

    # --- Relatório de produção (substitui versão de trabalho) ---

    @staticmethod
    def listar_relatorios_producao():
        return RelatorioProducao.query.all()

    @staticmethod
    def listar_versoes_trabalho():
        """Alias para compatibilidade com rotas existentes."""
        return RelatorioProducao.query.all()

    @staticmethod
    def obter_versao_trabalho(id_versao):
        """Alias para compatibilidade com rotas existentes."""
        return RelatorioProducao.query.get(id_versao)

    @staticmethod
    def criar_versao_trabalho(id_relatorio_base, titulo):
        """Alias para compatibilidade com rotas existentes."""
        return ServicoRelatorio.criar_relatorio_producao(
            id_relatorio_base, titulo
        )

    @staticmethod
    def obter_relatorio_producao(id_relatorio):
        return RelatorioProducao.query.get(id_relatorio)

    @staticmethod
    def criar_relatorio_producao(relatorio_id, titulo):
        from flask_login import current_user
        from datetime import date
        from app.models.dominio import DomStatusRelatorio

        # Buscar status 'rascunho' ou usar o primeiro ativo
        status = DomStatusRelatorio.query.filter_by(
            codigo='rascunho'
        ).first()
        if not status:
            status = DomStatusRelatorio.query.filter_by(
                ativo=True
            ).first()

        relatorio = RelatorioProducao(
            modelo_id=relatorio_id,
            titulo_curto=titulo,
            codigo_d20='D-20',
            numero_medicao=1,
            mes_referencia=date.today(),
            periodo_inicio=date.today(),
            periodo_fim=date.today(),
            status_id=status.id if status else 1,
            criado_por=(
                current_user.id if current_user.is_authenticated else None
            )
        )
        db.session.add(relatorio)
        db.session.commit()
        return relatorio

    @staticmethod
    def clonar_capitulos_do_base(_id_relatorio,
                                 _id_relatorio_base_anterior):
        # NOTE: Implementar clonagem usando RelatorioFinalizado
        # anterior = RelatorioFinalizado.query.get(
        #     id_relatorio_base_anterior
        # )
        # if not anterior or not anterior.finalizacoes:
        #     return []
        # versao_anterior = anterior.finalizacoes[-1]
        # capitulos_origem = CapituloDocumento.query.filter_by(
        #     id_relatorio=versao_anterior.id,
        #     id_capitulo_pai=None
        # ).order_by(CapituloDocumento.ordem_capitulo).all()
        # novos = []
        # for cap in capitulos_origem:
        #     novos += ServicoRelatorio._clonar_capitulo(
        #         cap, id_relatorio, None
        #     )
        # db.session.commit()
        # return novos
        return []

    @staticmethod
    def _clonar_capitulo(capitulo, id_relatorio,
                         id_capitulo_pai):
        novo = CapituloDocumento(
            id_relatorio=id_relatorio,
            id_capitulo_pai=id_capitulo_pai,
            ordem_capitulo=capitulo.ordem_capitulo,
            nome_capitulo=capitulo.nome_capitulo,
            titulo_capitulo=capitulo.titulo_capitulo,
            indice_capitulo=capitulo.indice_capitulo,
            nivel_capitulo=capitulo.nivel_capitulo
        )
        db.session.add(novo)
        db.session.flush()

        resultado = [novo]
        for sub in capitulo.subcapitulos:
            resultado += ServicoRelatorio._clonar_capitulo(
                sub, id_relatorio,
                novo.id_capitulo_documento
            )
        return resultado

    # --- Panorama consolidado ---

    @staticmethod
    def panorama():
        # NOTE: Implementar panorama usando RelatorioProducao
        # modelos = ModeloRelatorio.query.filter_by(
        #     ativo=True
        # ).order_by(ModeloRelatorio.nome_modelo).all()
        # linhas = []
        # for modelo in modelos:
        #     for rf in modelo.relatorios_finalizados:
        #         for rp in rf.relatorios_producao:
        #             linhas.append({
        #                 'tipo': modelo.nome_modelo,
        #                 'titulo': rp.titulo_curto,
        #                 'versao_base': rf.versao or '-',
        #                 'status': rp.status.codigo if rp.status else '-',
        #                 'id_versao': rp.id,
        #             })
        #         if not rf.relatorios_producao:
        #             linhas.append({
        #                 'tipo': modelo.nome_modelo,
        #                 'titulo': rf.titulo,
        #                 'versao_base': rf.versao or '-',
        #                 'status': '-',
        #                 'id_versao': None,
        #             })
        # return linhas
        return []

    # --- Capítulos ---

    @staticmethod
    def listar_capitulos(id_relatorio):
        return CapituloDocumento.query.filter_by(
            id_relatorio=id_relatorio,
            id_capitulo_pai=None
        ).order_by(CapituloDocumento.ordem_capitulo).all()

    @staticmethod
    def criar_capitulo(id_relatorio, titulo_capitulo,
                       ordem_capitulo, nivel_capitulo=1,
                       id_capitulo_pai=None,
                       nome_capitulo=None,
                       indice_capitulo=None):
        capitulo = CapituloDocumento(
            id_relatorio=id_relatorio,
            titulo_capitulo=titulo_capitulo,
            ordem_capitulo=ordem_capitulo,
            nivel_capitulo=nivel_capitulo,
            id_capitulo_pai=id_capitulo_pai,
            nome_capitulo=nome_capitulo,
            indice_capitulo=indice_capitulo
        )
        db.session.add(capitulo)
        db.session.commit()
        return capitulo
