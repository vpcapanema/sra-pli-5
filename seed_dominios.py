"""Script de seed para dominios do sistema SRA.

Apos a unificacao (migration 006), todas as tabelas de dominio
(`dom_*`) foram fundidas em `public.dominios`. Cada registro e
identificado por `(tipo, valor)`.
"""

from app import create_app, db
from app.models.dominio import Dominio

# Status de relatorio agora vivem em `dominios` com tipo='status_relatorio'.
STATUS_RELATORIO = [
    ('em_producao', 'Em produção', 10),
    ('em_revisao', 'Em revisão', 20),
    ('finalizado', 'Finalizado', 30),
    ('cancelado', 'Cancelado', 90),
]

# Perfis de usuario (anteriormente em dom_perfis_usuario).
PERFIS_USUARIO = [
    ('admin', 'Administrador do sistema', 100),
    ('coordenador', 'Coordenador de relatório', 50),
    ('autor', 'Autor de conteúdo', 10),
]

# Outros dominios (tabela unica `dominios`).
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
    'status_capitulo': [
        ('em_edicao', 'Capítulo em edição pelo autor'),
        ('aguardando_aprovacao', 'Capítulo aguardando aprovação do coordenador'),
        ('aprovado', 'Capítulo aprovado pelo coordenador'),
        ('rejeitado', 'Capítulo rejeitado pelo coordenador'),
    ],
    # Status do ciclo de envio do AUTOR (monitora o comportamento
    # do autor frente ao periodo de envio do relatorio vigente).
    # Distinto de `status_envio` da tabela `envios_conteudo`, que
    # descreve o ciclo de um upload especifico.
    'status_envio_conteudo': [
        ('notificado',
         'Autor notificado da abertura do periodo de envio de conteudo'),
        ('aguardando_envio',
         'Autor leu o e-mail mas ainda nao atribuiu nenhum capitulo'),
        ('em_preparacao',
         'Autor atribuido a algum capitulo (status_capitulo = em_edicao)'),
        ('enviado',
         'Autor enviou conteudo (status_capitulo = aguardando_aprovacao)'),
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
    'tipo_previsualizacao': [
        ('html', 'Pré-visualização em HTML'),
        ('pdf', 'Pré-visualização em PDF'),
    ],
}


def _seed_tipo(tipo, registros):
    """Insere registros (valor, descricao[, ordem]) em `dominios` se
    nao existirem. Retorna a quantidade de novos registros criados.
    """
    inseridos = 0
    for item in registros:
        if len(item) == 3:
            valor, descricao, ordem = item
        else:
            valor, descricao = item
            ordem = 0
        existe = Dominio.query.filter_by(tipo=tipo, valor=valor).first()
        if not existe:
            db.session.add(Dominio(
                tipo=tipo,
                valor=valor,
                descricao=descricao,
                ordem=ordem,
            ))
            inseridos += 1
    return inseridos


app = create_app()

with app.app_context():
    db.create_all()
    INSERIDOS = 0

    INSERIDOS += _seed_tipo('status_relatorio', STATUS_RELATORIO)
    INSERIDOS += _seed_tipo('perfil_usuario', PERFIS_USUARIO)

    for tipo, valores in DOMINIOS.items():
        INSERIDOS += _seed_tipo(tipo, valores)

    db.session.commit()
    total = Dominio.query.count()
    print(f'Seed concluído: {INSERIDOS} novos registros, {total} dominios totais.')
