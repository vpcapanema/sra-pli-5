"""Script de seed para dominios do sistema SRA."""

from app import create_app, db
from app.models.dominio import Dominio, DomStatusRelatorio

# Status de relatório usa tabela específica dom_status_relatorios
STATUS_RELATORIO = [
    ('em_producao', 'Em produção', 10),
    ('em_revisao', 'Em revisão', 20),
    ('finalizado', 'Finalizado', 30),
    ('cancelado', 'Cancelado', 90),
]

# Outros dominios usam tabela generica dominios
DOMINIOS = {
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
    INSERIDOS = 0

    # Seed de status de relatorio (tabela dom_status_relatorios)
    for codigo, descricao, ordem in STATUS_RELATORIO:
        existe = DomStatusRelatorio.query.filter_by(codigo=codigo).first()
        if not existe:
            db.session.add(DomStatusRelatorio(
                codigo=codigo,
                descricao=descricao,
                ordem=ordem
            ))
            INSERIDOS += 1

    # Seed de outros dominios (tabela dominios)
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
                INSERIDOS += 1

    db.session.commit()
    total_status = DomStatusRelatorio.query.count()
    total_dominios = Dominio.query.count()
    print(f'Seed concluído: {INSERIDOS} novos, {total_status} status_relatorio, {total_dominios} dominios.')
