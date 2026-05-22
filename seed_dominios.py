from app import create_app, db
from app.models.dominio import Dominio
from app.models.relatorio_finalizado import RelatorioFinalizado

DOMINIOS = {
    'status_relatorio': [
        ('rascunho', 'Relatório em elaboração'),
        ('em_revisao', 'Relatório em revisão'),
        ('aprovado', 'Relatório aprovado'),
        ('publicado', 'Relatório publicado'),
    ],
    'status_versao': [
        ('rascunho', 'Versão em elaboração'),
        ('em_revisao', 'Versão em revisão'),
        ('aprovada', 'Versão aprovada'),
    ],
    'status_envio': [
        ('pendente', 'Aguardando processamento'),
        ('processando', 'Em processamento'),
        ('concluido', 'Processamento concluído'),
        ('erro', 'Erro no processamento'),
    ],
    'status_revisao': [
        ('pendente', 'Revisão pendente'),
        ('aprovada', 'Revisão aprovada'),
        ('rejeitada', 'Revisão rejeitada'),
    ],
    'tipo_elemento': [
        ('paragrafo', 'Parágrafo de texto'),
        ('tabela', 'Tabela'),
        ('figura', 'Figura ou imagem'),
        ('lista', 'Lista ordenada ou não ordenada'),
        ('equacao', 'Equação ou fórmula'),
    ],
    'tipo_acao_revisao': [
        ('aprovar', 'Aprovar conteúdo'),
        ('rejeitar', 'Rejeitar conteúdo'),
        ('solicitar_correcao', 'Solicitar correção ao autor'),
    ],
    'tipo_notificacao': [
        ('envio', 'Notificação de envio de conteúdo'),
        ('revisao', 'Notificação de revisão'),
        ('bloqueio', 'Notificação de bloqueio'),
    ],
    'formato_numeracao': [
        ('arabico', 'Numeração arábica (1, 2, 3)'),
        ('romano', 'Numeração romana (I, II, III)'),
        ('alfa_maiusculo', 'Alfabética maiúscula (A, B, C)'),
        ('alfa_minusculo', 'Alfabética minúscula (a, b, c)'),
    ],
    'origem_configuracao': [
        ('auto_detectado', 'Extraído automaticamente do modelo'),
        ('manual', 'Definido manualmente pelo coordenador'),
    ],
    'tipo_entidade_numeracao': [
        ('capitulo', 'Capítulo'),
        ('subcapitulo', 'Subcapítulo'),
        ('tabela', 'Tabela'),
        ('figura', 'Figura'),
        ('equacao', 'Equação'),
        ('lista', 'Lista'),
    ],
    'tipo_perfil': [
        ('administrador', 'Administrador do sistema'),
        ('coordenador', 'Coordenador de relatório'),
        ('autor', 'Autor de conteúdo'),
    ],
    'tipo_previsualizacao': [
        ('html', 'Pré-visualização em HTML'),
        ('pdf', 'Pré-visualização em PDF'),
    ],
}

app = create_app()

with app.app_context():
    db.create_all()
    inseridos = 0
    for tipo, valores in DOMINIOS.items():
        for valor, descricao in valores:
            existe = Dominio.query.filter_by(
                tipo=tipo, valor=valor
            ).first()
            if not existe:
                db.session.add(Dominio(
                    tipo=tipo,
                    valor=valor,
                    descricao=descricao
                ))
                inseridos += 1
    db.session.commit()
    total = Dominio.query.count()
    print(f'Seed concluído: {inseridos} novos, {total} total.')
