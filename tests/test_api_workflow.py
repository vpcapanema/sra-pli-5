"""
Testes do fluxo de workflow da API.
Cobre: permissões, finalizar, aprovar, reprovar, upload, CSRF.
"""
import pytest
from app import create_app, db
from app.models.usuario import Usuario
from app.models.versao_trabalho import VersaoTrabalho
from app.models.relatorio_base import RelatorioBase
from app.models.modelo_relatorio import ModeloRelatorio
from app.models.capitulo_documento import CapituloDocumento


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def setup_dados(app):
    """Cria dados base para testes."""
    with app.app_context():
        # Coordenador
        coord = Usuario(
            nome_completo='Coordenador Teste',
            email='coord@teste.com',
            perfil='coordenador',
            ativo=True
        )
        coord.set_password('123456')
        db.session.add(coord)

        # Autor
        autor = Usuario(
            nome_completo='Autor Teste',
            email='autor@teste.com',
            perfil='autor',
            ativo=True
        )
        autor.set_password('123456')
        db.session.add(autor)

        # Modelo + Relatório + Versão
        modelo = ModeloRelatorio(
            nome_modelo='PLI', ativo=True
        )
        db.session.add(modelo)
        db.session.flush()

        rb = RelatorioBase(
            id_modelo_relatorio=modelo.id_modelo_relatorio,
            titulo='PLI 2024',
            status_relatorio='ativo'
        )
        db.session.add(rb)
        db.session.flush()

        vt = VersaoTrabalho(
            id_relatorio_base=rb.id_relatorio_base,
            titulo='Versão 1',
            status_versao='em_edicao'
        )
        db.session.add(vt)
        db.session.flush()

        cap = CapituloDocumento(
            id_versao_trabalho=vt.id_versao_trabalho,
            titulo_capitulo='Introdução',
            ordem_capitulo=1,
            nivel_capitulo=1,
            id_usuario_responsavel=autor.id_usuario,
            status_capitulo='em_edicao'
        )
        db.session.add(cap)
        db.session.commit()

        return {
            'coord': coord,
            'autor': autor,
            'versao': vt,
            'capitulo': cap,
        }


def _login(client, email, senha, perfil):
    """Helper para login em testes."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(1)
        sess['perfil_ativo'] = perfil
        sess['csrf_token'] = 'test-csrf'


class TestCSRF:
    """Testes de proteção CSRF."""

    def test_mutacao_sem_csrf_bloqueia(self, client, setup_dados):
        _login(client, 'autor@teste.com', '123456', 'autor')
        dados = setup_dados
        resp = client.post(
            f'/api/capitulos/{dados["capitulo"].id_capitulo_documento}'
            '/finalizar',
            json={}
        )
        # Sem header X-CSRF-Token deve bloquear
        assert resp.status_code == 403

    def test_mutacao_com_csrf_ok(self, client, setup_dados):
        dados = setup_dados
        with client.session_transaction() as sess:
            sess['_user_id'] = str(dados['autor'].id_usuario)
            sess['perfil_ativo'] = 'autor'
            sess['csrf_token'] = 'test-csrf'

        resp = client.post(
            f'/api/capitulos/{dados["capitulo"].id_capitulo_documento}'
            '/finalizar',
            json={},
            headers={'X-CSRF-Token': 'test-csrf'}
        )
        assert resp.status_code == 200


class TestPermissoes:
    """Testes de controle de acesso."""

    def test_autor_nao_pode_aprovar(self, client, setup_dados):
        dados = setup_dados
        with client.session_transaction() as sess:
            sess['_user_id'] = str(dados['autor'].id_usuario)
            sess['perfil_ativo'] = 'autor'
            sess['csrf_token'] = 'tk'

        resp = client.post(
            f'/api/capitulos/{dados["capitulo"].id_capitulo_documento}'
            '/aprovar',
            json={},
            headers={'X-CSRF-Token': 'tk'}
        )
        assert resp.status_code == 403

    def test_coordenador_nao_pode_finalizar(self, client, setup_dados):
        dados = setup_dados
        with client.session_transaction() as sess:
            sess['_user_id'] = str(dados['coord'].id_usuario)
            sess['perfil_ativo'] = 'coordenador'
            sess['csrf_token'] = 'tk'

        resp = client.post(
            f'/api/capitulos/{dados["capitulo"].id_capitulo_documento}'
            '/finalizar',
            json={},
            headers={'X-CSRF-Token': 'tk'}
        )
        assert resp.status_code == 403


class TestWorkflow:
    """Testes do fluxo completo."""

    def test_fluxo_finalizar_aprovar(self, client, setup_dados):
        dados = setup_dados

        # 1. Autor finaliza
        with client.session_transaction() as sess:
            sess['_user_id'] = str(dados['autor'].id_usuario)
            sess['perfil_ativo'] = 'autor'
            sess['csrf_token'] = 'tk'

        resp = client.post(
            f'/api/capitulos/{dados["capitulo"].id_capitulo_documento}'
            '/finalizar',
            json={},
            headers={'X-CSRF-Token': 'tk'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'finalizado'

        # 2. Coordenador aprova
        with client.session_transaction() as sess:
            sess['_user_id'] = str(dados['coord'].id_usuario)
            sess['perfil_ativo'] = 'coordenador'
            sess['csrf_token'] = 'tk'

        resp = client.post(
            f'/api/capitulos/{dados["capitulo"].id_capitulo_documento}'
            '/aprovar',
            json={},
            headers={'X-CSRF-Token': 'tk'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'aprovado'

    def test_fluxo_finalizar_reprovar(self, client, setup_dados):
        dados = setup_dados

        # 1. Autor finaliza
        with client.session_transaction() as sess:
            sess['_user_id'] = str(dados['autor'].id_usuario)
            sess['perfil_ativo'] = 'autor'
            sess['csrf_token'] = 'tk'

        resp = client.post(
            f'/api/capitulos/{dados["capitulo"].id_capitulo_documento}'
            '/finalizar',
            json={},
            headers={'X-CSRF-Token': 'tk'}
        )
        assert resp.status_code == 200

        # 2. Coordenador reprova
        with client.session_transaction() as sess:
            sess['_user_id'] = str(dados['coord'].id_usuario)
            sess['perfil_ativo'] = 'coordenador'
            sess['csrf_token'] = 'tk'

        resp = client.post(
            f'/api/capitulos/{dados["capitulo"].id_capitulo_documento}'
            '/reprovar',
            json={'observacao': 'Precisa de mais detalhes'},
            headers={'X-CSRF-Token': 'tk'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'reprovado'
        assert data['observacao_coordenador'] == \
            'Precisa de mais detalhes'


class TestUpload:
    """Testes de upload de conteúdo."""

    def test_upload_respeita_limite(self, client, setup_dados):
        dados = setup_dados
        with client.session_transaction() as sess:
            sess['_user_id'] = str(dados['autor'].id_usuario)
            sess['perfil_ativo'] = 'autor'
            sess['csrf_token'] = 'tk'

        # Arquivo gigante (> 50MB): não podemos criar em teste,
        # mas testar que 1MB funciona
        conteudo = b'PK' + (b'\x00' * 1024 * 1024)
        resp = client.put(
            f'/api/capitulos/{dados["capitulo"].id_capitulo_documento}'
            '/conteudo',
            data=conteudo,
            content_type='application/octet-stream',
            headers={'X-CSRF-Token': 'tk'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['size'] > 0
