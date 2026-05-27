"""
Testes para Tarefa 3.4: Validação de Classificação em _validar_precondiciones().

Testa a função _validar_classificacoes_preenchidas() que valida se todos os
capítulos de um relatório têm classificação preenchida antes de executar pipeline.

Requisitos validados: 5.1 (Pré-condições)
Propriedades testadas: Property 7 (Validação de Pré-Condições)
"""

import pytest
from app import db
from app.models import RelatorioProducao, CapituloDocumento, Usuario
from app.services.servico_pipeline_relatorio import ServicoPipelineRelatorio


@pytest.fixture
def usuario_teste(app):
    """Cria usuário para testes."""
    # Encontrar perfil 'autor' na tabela dominios
    from app.models import Dominio
    perfil_autor = db.session.query(Dominio).filter_by(
        tipo='perfil_usuario', valor='autor'
    ).first()
    
    if not perfil_autor:
        # Se não existir, criar
        perfil_autor = Dominio(tipo='perfil_usuario', valor='autor', descricao='Autor')
        db.session.add(perfil_autor)
        db.session.flush()
    
    usuario = Usuario(
        nome='Admin Teste',
        nome_de_usuario='admin_teste',
        email='admin@teste.com',
        senha_hash='hash_teste',
        perfil_id=perfil_autor.id_dominio,
        ativo=True
    )
    db.session.add(usuario)
    db.session.commit()
    return usuario


@pytest.fixture
def relatorio_sincronizado(app, usuario_teste):
    """
    Cria relatório com capítulos que têm classificação preenchida.
    """
    from datetime import date
    from app.models import Dominio
    
    # Criar status para relatório
    status_em_prod = db.session.query(Dominio).filter_by(
        tipo='status_relatorio', valor='em_producao'
    ).first()
    if not status_em_prod:
        status_em_prod = Dominio(tipo='status_relatorio', valor='em_producao', descricao='Em Produção')
        db.session.add(status_em_prod)
        db.session.flush()
    
    relatorio = RelatorioProducao(
        numero_medicao=1,
        mes_referencia=date(2026, 5, 1),
        periodo_inicio=date(2026, 5, 1),
        periodo_fim=date(2026, 5, 31),
        titulo_curto='Relatório Teste Sincronizado',
        status_id=status_em_prod.id_dominio,
        criado_por=usuario_teste.id,
        caminho_template='/tmp/template_teste.docx'
    )
    db.session.add(relatorio)
    db.session.flush()
    
    # Criar capítulos com classificação
    cap1 = CapituloDocumento(
        id_relatorio=relatorio.id,
        ordem_capitulo=1,
        titulo_capitulo='Introdução',
        nivel_capitulo=1,
        tipo_elemento='textual',
        classificacao='pre_textual',  # ✅ Preenchido
        prefixo_indice='',
        status_capitulo='em_edicao',
        id_usuario_responsavel=usuario_teste.id
    )
    
    cap2 = CapituloDocumento(
        id_relatorio=relatorio.id,
        ordem_capitulo=2,
        titulo_capitulo='Metodologia',
        nivel_capitulo=1,
        tipo_elemento='textual',
        classificacao='textual',  # ✅ Preenchido
        prefixo_indice='1',
        status_capitulo='em_edicao',
        id_usuario_responsavel=usuario_teste.id
    )
    
    cap3 = CapituloDocumento(
        id_relatorio=relatorio.id,
        ordem_capitulo=3,
        titulo_capitulo='Anexos',
        nivel_capitulo=1,
        tipo_elemento='textual',
        classificacao='anexo',  # ✅ Preenchido
        prefixo_indice='A',
        status_capitulo='em_edicao',
        id_usuario_responsavel=usuario_teste.id
    )
    
    db.session.add_all([cap1, cap2, cap3])
    db.session.commit()
    
    return relatorio


@pytest.fixture
def relatorio_sem_sincronizar(app, usuario_teste):
    """
    Cria relatório com capítulos SEM classificação preenchida (não sincronizados).
    """
    from datetime import date
    from app.models import Dominio
    
    # Criar status para relatório
    status_em_prod = db.session.query(Dominio).filter_by(
        tipo='status_relatorio', valor='em_producao'
    ).first()
    if not status_em_prod:
        status_em_prod = Dominio(tipo='status_relatorio', valor='em_producao', descricao='Em Produção')
        db.session.add(status_em_prod)
        db.session.flush()
    
    relatorio = RelatorioProducao(
        numero_medicao=2,
        mes_referencia=date(2026, 5, 1),
        periodo_inicio=date(2026, 5, 1),
        periodo_fim=date(2026, 5, 31),
        titulo_curto='Relatório Teste Não Sincronizado',
        status_id=status_em_prod.id_dominio,
        criado_por=usuario_teste.id,
        caminho_template='/tmp/template_teste.docx'
    )
    db.session.add(relatorio)
    db.session.flush()
    
    # Criar capítulos SEM classificação
    cap1 = CapituloDocumento(
        id_relatorio=relatorio.id,
        ordem_capitulo=1,
        titulo_capitulo='Introdução',
        nivel_capitulo=1,
        tipo_elemento='textual',
        classificacao=None,  # ❌ Não preenchido
        prefixo_indice=None,
        status_capitulo='em_edicao',
        id_usuario_responsavel=usuario_teste.id
    )
    
    cap2 = CapituloDocumento(
        id_relatorio=relatorio.id,
        ordem_capitulo=2,
        titulo_capitulo='Metodologia',
        nivel_capitulo=1,
        tipo_elemento='textual',
        classificacao=None,  # ❌ Não preenchido
        prefixo_indice=None,
        status_capitulo='em_edicao',
        id_usuario_responsavel=usuario_teste.id
    )
    
    db.session.add_all([cap1, cap2])
    db.session.commit()
    
    return relatorio


class TestValidarClassificacoesPreenchidas:
    """Suite de testes para _validar_classificacoes_preenchidas()."""
    
    def test_classificacoes_preenchidas_retorna_valido(self, relatorio_sincronizado):
        """
        Test: Quando todos os capítulos têm classificação preenchida,
        validação retorna sucesso.
        
        **Valida: Requisito 5.1, Property 7**
        """
        resultado = ServicoPipelineRelatorio._validar_classificacoes_preenchidas(
            relatorio_sincronizado.id
        )
        
        assert resultado['valido'] is True, "Deve validar com sucesso"
        assert len(resultado['motivos_rejeicao']) == 0, "Não deve ter motivos de rejeição"
        assert resultado['total_capitulos'] == 3, "Deve detectar 3 capítulos"
        assert resultado['capitulos_validos'] == 3, "Todos 3 capítulos devem ser válidos"
        assert len(resultado['capitulos_sem_classificacao']) == 0, "Nenhum deve estar sem classificação"
    
    def test_classificacoes_nao_preenchidas_retorna_invalido(self, relatorio_sem_sincronizar):
        """
        Test: Quando capítulos não têm classificação preenchida,
        validação retorna erro com mensagem amigável.
        
        **Valida: Requisito 5.1, Property 7**
        """
        resultado = ServicoPipelineRelatorio._validar_classificacoes_preenchidas(
            relatorio_sem_sincronizar.id
        )
        
        assert resultado['valido'] is False, "Deve rejeitar"
        assert len(resultado['motivos_rejeicao']) > 0, "Deve listar motivos"
        assert resultado['total_capitulos'] == 2, "Deve detectar 2 capítulos"
        assert resultado['capitulos_validos'] == 0, "Nenhum deve ser válido"
        assert len(resultado['capitulos_sem_classificacao']) == 2, "Ambos devem estar sem classificação"
        
        # Verificar mensagem humanizada
        mensagem = resultado['motivos_rejeicao'][0]
        assert "2 capítulos" in mensagem or "2 capítulo" in mensagem, "Deve mencionar quantidade"
        assert "Introdução" in mensagem or "Sincronize" in mensagem, "Deve dar sugestão"
    
    def test_relatorio_inexistente_retorna_erro(self, app):
        """
        Test: Quando relatório não existe, validação retorna erro específico.
        
        **Valida: Requisito 5.1**
        """
        resultado = ServicoPipelineRelatorio._validar_classificacoes_preenchidas(
            relatorio_id=99999
        )
        
        assert resultado['valido'] is False
        assert len(resultado['motivos_rejeicao']) > 0
        assert "não encontrado" in resultado['motivos_rejeicao'][0].lower()
    
    def test_relatorio_sem_capitulos_retorna_mensagem(self, app, usuario_teste):
        """
        Test: Quando relatório não tem capítulos sincronizados,
        retorna mensagem pedindo sincronização.
        
        **Valida: Requisito 5.1**
        """
        from datetime import date
        from app.models import Dominio
        
        # Criar status
        status_em_prod = db.session.query(Dominio).filter_by(
            tipo='status_relatorio', valor='em_producao'
        ).first()
        if not status_em_prod:
            status_em_prod = Dominio(tipo='status_relatorio', valor='em_producao', descricao='Em Produção')
            db.session.add(status_em_prod)
            db.session.flush()
        
        relatorio = RelatorioProducao(
            numero_medicao=3,
            mes_referencia=date(2026, 5, 1),
            periodo_inicio=date(2026, 5, 1),
            periodo_fim=date(2026, 5, 31),
            titulo_curto='Relatório Vazio',
            status_id=status_em_prod.id_dominio,
            criado_por=usuario_teste.id,
            caminho_template='/tmp/template_teste.docx'
        )
        db.session.add(relatorio)
        db.session.commit()
        
        resultado = ServicoPipelineRelatorio._validar_classificacoes_preenchidas(
            relatorio.id
        )
        
        assert resultado['valido'] is False
        assert len(resultado['motivos_rejeicao']) > 0
        assert "Sincronizar" in resultado['motivos_rejeicao'][0] or "sincronizar" in resultado['motivos_rejeicao'][0].lower()
    
    def test_classificacao_vazia_detectada(self, app, usuario_teste):
        """
        Test: Classificação vazia ou apenas espaços é detectada como inválida.
        
        **Valida: Requisito 5.1**
        """
        from datetime import date
        from app.models import Dominio
        
        # Criar status
        status_em_prod = db.session.query(Dominio).filter_by(
            tipo='status_relatorio', valor='em_producao'
        ).first()
        if not status_em_prod:
            status_em_prod = Dominio(tipo='status_relatorio', valor='em_producao', descricao='Em Produção')
            db.session.add(status_em_prod)
            db.session.flush()
        
        relatorio = RelatorioProducao(
            numero_medicao=4,
            mes_referencia=date(2026, 5, 1),
            periodo_inicio=date(2026, 5, 1),
            periodo_fim=date(2026, 5, 31),
            titulo_curto='Teste Classificação Vazia',
            status_id=status_em_prod.id_dominio,
            criado_por=usuario_teste.id,
            caminho_template='/tmp/template_teste.docx'
        )
        db.session.add(relatorio)
        db.session.flush()
        
        # Criar capítulo com classificação vazia (string vazia)
        cap = CapituloDocumento(
            id_relatorio=relatorio.id,
            ordem_capitulo=1,
            titulo_capitulo='Capítulo',
            nivel_capitulo=1,
            tipo_elemento='textual',
            classificacao='',  # ❌ Vazio
            prefixo_indice=None,
            status_capitulo='em_edicao',
            id_usuario_responsavel=usuario_teste.id
        )
        db.session.add(cap)
        db.session.commit()
        
        resultado = ServicoPipelineRelatorio._validar_classificacoes_preenchidas(
            relatorio.id
        )
        
        assert resultado['valido'] is False
        assert len(resultado['capitulos_sem_classificacao']) == 1
        assert resultado['capitulos_sem_classificacao'][0]['id'] == cap.id_capitulo_documento
    
    def test_estrutura_dict_retornado(self, relatorio_sincronizado):
        """
        Test: Resultado sempre contém estrutura completa de dict.
        
        **Valida: Property 3 (Coerência de Estrutura)**
        """
        resultado = ServicoPipelineRelatorio._validar_classificacoes_preenchidas(
            relatorio_sincronizado.id
        )
        
        # Verificar campos obrigatórios
        campos_obrigatorios = [
            'valido',
            'motivos_rejeicao',
            'capitulos_sem_classificacao',
            'total_capitulos',
            'capitulos_validos'
        ]
        
        for campo in campos_obrigatorios:
            assert campo in resultado, f"Campo '{campo}' faltando no resultado"
        
        # Verificar tipos
        assert isinstance(resultado['valido'], bool)
        assert isinstance(resultado['motivos_rejeicao'], list)
        assert isinstance(resultado['capitulos_sem_classificacao'], list)
        assert isinstance(resultado['total_capitulos'], int)
        assert isinstance(resultado['capitulos_validos'], int)


class TestValidarPrecondiciones:
    """Suite de testes para _validar_precondiciones()."""
    
    def test_precondiciones_validas_passam(self, relatorio_sincronizado):
        """
        Test: Quando relatório está sincronizado, validação de pré-condições passa.
        
        **Valida: Requisito 5.1, Property 7**
        """
        uploads_dict = {}  # Não há uploads por enquanto
        
        resultado = ServicoPipelineRelatorio._validar_precondiciones(
            relatorio_sincronizado.id,
            uploads_dict
        )
        
        assert resultado['valido'] is True, "Deve passar validação com capítulos sincronizados"
        assert len(resultado['motivos_rejeicao']) == 0
    
    def test_precondiciones_faltam_classificacao(self, relatorio_sem_sincronizar):
        """
        Test: Quando capítulos não têm classificação, validação de pré-condições falha.
        
        **Valida: Requisito 5.1, Property 7**
        """
        uploads_dict = {}
        
        resultado = ServicoPipelineRelatorio._validar_precondiciones(
            relatorio_sem_sincronizar.id,
            uploads_dict
        )
        
        assert resultado['valido'] is False, "Deve rejeitar sem classificações"
        assert len(resultado['motivos_rejeicao']) > 0
    
    def test_precondiciones_upload_capitulo_inexistente(self, relatorio_sincronizado):
        """
        Test: Upload para capítulo inexistente é rejeitado.
        
        **Valida: Requisito 5.1**
        """
        uploads_dict = {99999: b'conteudo_fake'}  # ID inexistente
        
        resultado = ServicoPipelineRelatorio._validar_precondiciones(
            relatorio_sincronizado.id,
            uploads_dict
        )
        
        assert resultado['valido'] is False
        assert any("não pertence" in msg for msg in resultado['motivos_rejeicao'])
    
    def test_mensagens_amigaveis_faltam_classificacao(self, relatorio_sem_sincronizar):
        """
        Test: Mensagens de erro são amigáveis e úteis ao coordenador.
        
        **Valida: Requisito 5.1, Property 9 (Segurança em Mensagens)**
        """
        resultado = ServicoPipelineRelatorio._validar_precondiciones(
            relatorio_sem_sincronizar.id,
            {}
        )
        
        # Deve conter sugestões de ação
        assert resultado.get('proximos_passos') == ['sincronizar'] or \
               any('sincronizar' in msg.lower() for msg in resultado['motivos_rejeicao']), \
               "Deve sugerir sincronizar"
        
        # Não deve conter caminhos absolutos ou dados técnicos
        for msg in resultado['motivos_rejeicao']:
            assert '/app/models' not in msg, "Não deve expor caminhos de código"
            assert '\\' not in msg or 'Libere' in msg, "Não deve expor caminhos de arquivo (exceto instruções)"


class TestIntegracaoValidacaoComPipeline:
    """Testes de integração da validação com o pipeline."""
    
    def test_validacao_classif_e_precond_coerentes(self, relatorio_sincronizado):
        """
        Test: Se classificação valida, pré-condições também validam.
        
        **Valida: Property 3 (Coerência)**
        """
        # Verificar classificação
        class_resultado = ServicoPipelineRelatorio._validar_classificacoes_preenchidas(
            relatorio_sincronizado.id
        )
        
        # Verificar pré-condições
        precond_resultado = ServicoPipelineRelatorio._validar_precondiciones(
            relatorio_sincronizado.id,
            {}
        )
        
        # Se classificação passa, pré-condições também devem passar
        assert class_resultado['valido'] == precond_resultado['valido'], \
            "Validações devem ser coerentes"
    
    def test_proximos_passos_estruturado(self, relatorio_sem_sincronizar):
        """
        Test: Campo 'proximos_passos' é estruturado para integração com UI.
        
        **Valida: Requisito 5.1**
        """
        resultado = ServicoPipelineRelatorio._validar_precondiciones(
            relatorio_sem_sincronizar.id,
            {}
        )
        
        assert 'proximos_passos' in resultado
        assert isinstance(resultado['proximos_passos'], list)
        
        # Deve conter ações conhecidas
        if resultado['proximos_passos']:
            for passo in resultado['proximos_passos']:
                assert passo in ['sincronizar', 'liberar_disco', 'verificar_template'], \
                    f"Passo '{passo}' desconhecido"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
