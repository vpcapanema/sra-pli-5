"""Testes do fluxo de envio do autor: upload, prévia, confirmação,
geração do relatório final, e do bug-fix de deduplicação na clonagem.
"""
import io
import os
import tempfile

import pytest
from docx import Document

from app import create_app, db
from app.models.dominio import DomPerfilUsuario, DomStatusRelatorio
from app.models.usuario import Usuario
from app.models.relatorio_producao import RelatorioProducao
from app.models.capitulo_documento import CapituloDocumento
from app.models.envio_conteudo import EnvioConteudo
from app.services.servico_envio_autor import ServicoEnvioAutor
from app.services.servico_extracao_canonica import ServicoExtracaoCanonica


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        # Seed mínimo
        db.session.add(
            DomPerfilUsuario(codigo='autor', descricao='Autor')
        )
        db.session.add(
            DomPerfilUsuario(codigo='coordenador', descricao='Coord')
        )
        db.session.add(
            DomStatusRelatorio(codigo='em_producao', descricao='EP')
        )
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def dados(app):
    perfil_autor = DomPerfilUsuario.query.filter_by(
        codigo='autor'
    ).first()
    status = DomStatusRelatorio.query.first()
    u = Usuario(
        nome='Autor T',
        email='a@t.com',
        nome_de_usuario='autort',
        senha_hash='x',
        perfil_id=perfil_autor.id,
        ativo=True,
    )
    db.session.add(u)
    db.session.flush()

    rp = RelatorioProducao(
        codigo_d20='D-20', numero_medicao=1,
        mes_referencia=__import__('datetime').date.today(),
        periodo_inicio=__import__('datetime').date.today(),
        periodo_fim=__import__('datetime').date.today(),
        titulo_curto='Teste', status_id=status.id,
        criado_por=u.id, versao_atual='R00',
    )
    db.session.add(rp)
    db.session.flush()

    c1 = CapituloDocumento(
        id_relatorio=rp.id, titulo_capitulo='Introdução',
        ordem_capitulo=1, nivel_capitulo=1, indice_capitulo='1',
        tipo_elemento='textual', id_usuario_responsavel=u.id,
    )
    c2 = CapituloDocumento(
        id_relatorio=rp.id, titulo_capitulo='Metodologia',
        ordem_capitulo=2, nivel_capitulo=1, indice_capitulo='2',
        tipo_elemento='textual', id_usuario_responsavel=u.id,
    )
    db.session.add_all([c1, c2])
    db.session.commit()
    return {
        'usuario_id': u.id,
        'relatorio_id': rp.id,
        'cap_ids': [c1.id_capitulo_documento, c2.id_capitulo_documento],
    }


def _criar_docx_simples(headings, paragrafos_por_heading=2):
    """Cria um DOCX em memória com cabeçalhos e parágrafos."""
    d = Document()
    for h in headings:
        d.add_heading(h, level=1)
        for k in range(paragrafos_por_heading):
            d.add_paragraph(f'Parágrafo {k+1} de {h}')
    buf = io.BytesIO()
    d.save(buf)
    buf.seek(0)
    return buf


class _FakeUpload:
    """Imita werkzeug FileStorage para testes."""
    def __init__(self, buf, filename):
        self._buf = buf
        self.filename = filename

    def save(self, path):
        with open(path, 'wb') as f:
            f.write(self._buf.getvalue())


def test_upload_e_previa_geram_segmento_por_capitulo(app, dados, tmp_path):
    buf = _criar_docx_simples(['Introdução', 'Metodologia'])
    fake = _FakeUpload(buf, 'envio.docx')
    envio = ServicoEnvioAutor.processar_upload(
        id_relatorio=dados['relatorio_id'],
        id_usuario=dados['usuario_id'],
        arquivo_storage=fake,
        base_dir=str(tmp_path),
        id_capitulo_destino=dados['cap_ids'][0],
    )
    previas = envio.previsualizacoes
    tipos = {p.tipo_previsualizacao for p in previas}
    assert 'parcial' in tipos
    cap_ids = {p.caminho_saida for p in previas if p.caminho_saida}
    assert len(cap_ids) == 2


def test_confirmar_importa_conteudo_nos_capitulos(app, dados, tmp_path):
    buf = _criar_docx_simples(['Introdução', 'Metodologia'])
    fake = _FakeUpload(buf, 'envio.docx')
    envio = ServicoEnvioAutor.processar_upload(
        id_relatorio=dados['relatorio_id'],
        id_usuario=dados['usuario_id'],
        arquivo_storage=fake,
        base_dir=str(tmp_path),
    )
    resultado = ServicoEnvioAutor.confirmar(envio=envio, acao='importar')
    assert resultado['ok'] is True
    assert resultado['capitulos_atualizados'] == 2
    for cap_id in dados['cap_ids']:
        cap = CapituloDocumento.query.get(cap_id)
        assert cap.conteudo_docx is not None
        assert len(cap.conteudo_docx) > 0
    envio_db = EnvioConteudo.query.get(envio.id_envio_conteudo)
    assert envio_db.status_envio == 'importado'


def test_confirmar_rejeitar_nao_altera_capitulos(app, dados, tmp_path):
    buf = _criar_docx_simples(['Introdução'])
    fake = _FakeUpload(buf, 'envio.docx')
    envio = ServicoEnvioAutor.processar_upload(
        id_relatorio=dados['relatorio_id'],
        id_usuario=dados['usuario_id'],
        arquivo_storage=fake,
        base_dir=str(tmp_path),
    )
    ServicoEnvioAutor.confirmar(envio=envio, acao='rejeitar')
    for cap_id in dados['cap_ids']:
        cap = CapituloDocumento.query.get(cap_id)
        assert cap.conteudo_docx is None
    envio_db = EnvioConteudo.query.get(envio.id_envio_conteudo)
    assert envio_db.status_envio == 'rejeitado'


def test_extracao_deduplica_titulos_repetidos(app):
    d = Document()
    d.add_paragraph('SUMÁRIO')
    d.add_paragraph('Introdução')
    d.add_paragraph('Metodologia')
    d.add_heading('Introdução', level=1)
    d.add_paragraph('texto')
    d.add_heading('Metodologia', level=1)
    d.add_paragraph('texto')

    buf = io.BytesIO()
    d.save(buf)
    with tempfile.NamedTemporaryFile(
        suffix='.docx', delete=False
    ) as tmp:
        tmp.write(buf.getvalue())
        caminho = tmp.name
    try:
        doc = Document(caminho)
        arvore = ServicoExtracaoCanonica._extrair_capitulos(doc)
        titulos = [n['titulo'].strip().lower() for n in arvore]
        assert titulos.count('introdução') == 1
        assert titulos.count('metodologia') == 1
    finally:
        os.unlink(caminho)


def test_endpoint_baixar_envio_docx(app, dados, tmp_path):
    """Endpoint /api/envios/<id>/docx devolve o DOCX original."""
    buf = _criar_docx_simples(['Introdução'])
    fake = _FakeUpload(buf, 'envio.docx')
    envio = ServicoEnvioAutor.processar_upload(
        id_relatorio=dados['relatorio_id'],
        id_usuario=dados['usuario_id'],
        arquivo_storage=fake,
        base_dir=str(tmp_path),
    )
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(dados['usuario_id'])
        sess['perfil_ativo'] = 'autor'
        sess['csrf_token'] = 'tk'

    resp = client.get(
        f'/api/envios/{envio.id_envio_conteudo}/docx'
    )
    assert resp.status_code == 200
    assert resp.data[:2] == b'PK'  # DOCX zip


def test_endpoint_baixar_segmento_docx(app, dados, tmp_path):
    """Endpoint /api/envios/<id>/capitulos/<id_cap>/docx devolve
    segmento DOCX classificado por heading."""
    buf = _criar_docx_simples(['Introdução', 'Metodologia'])
    fake = _FakeUpload(buf, 'envio.docx')
    envio = ServicoEnvioAutor.processar_upload(
        id_relatorio=dados['relatorio_id'],
        id_usuario=dados['usuario_id'],
        arquivo_storage=fake,
        base_dir=str(tmp_path),
    )
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(dados['usuario_id'])
        sess['perfil_ativo'] = 'autor'
        sess['csrf_token'] = 'tk'

    resp = client.get(
        f'/api/envios/{envio.id_envio_conteudo}'
        f'/capitulos/{dados["cap_ids"][0]}/docx'
    )
    assert resp.status_code == 200
    assert resp.data[:2] == b'PK'
    # O segmento abre e contém os parágrafos da Introdução
    out_doc = Document(io.BytesIO(resp.data))
    textos = ' '.join(p.text for p in out_doc.paragraphs)
    assert 'Parágrafo' in textos


def test_endpoint_salvar_segmento_docx_html(app, dados, tmp_path):
    """PUT /api/envios/.../capitulos/.../docx aceita HTML editado."""
    buf = _criar_docx_simples(['Introdução'])
    fake = _FakeUpload(buf, 'envio.docx')
    envio = ServicoEnvioAutor.processar_upload(
        id_relatorio=dados['relatorio_id'],
        id_usuario=dados['usuario_id'],
        arquivo_storage=fake,
        base_dir=str(tmp_path),
    )
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(dados['usuario_id'])
        sess['perfil_ativo'] = 'autor'
        sess['csrf_token'] = 'tk'

    html = '<h1>Introdução editada</h1><p>Novo conteúdo do autor</p>'
    resp = client.put(
        f'/api/envios/{envio.id_envio_conteudo}'
        f'/capitulos/{dados["cap_ids"][0]}/docx',
        data=html.encode('utf-8'),
        content_type='text/html',
        headers={'X-CSRF-Token': 'tk'},
    )
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload['ok'] is True
    assert payload['size'] > 0
    cap = CapituloDocumento.query.get(dados['cap_ids'][0])
    assert cap.conteudo_docx is not None
    out_doc = Document(io.BytesIO(cap.conteudo_docx))
    textos = ' '.join(p.text for p in out_doc.paragraphs)
    assert 'Novo conteúdo do autor' in textos


def test_gerar_docx_versao_fallback(app, dados):
    d = Document()
    d.add_paragraph('Conteúdo do autor')
    buf = io.BytesIO()
    d.save(buf)
    cap = CapituloDocumento.query.get(dados['cap_ids'][0])
    cap.conteudo_docx = buf.getvalue()
    db.session.commit()

    from app.routes.api import _gerar_docx_versao
    rp = RelatorioProducao.query.get(dados['relatorio_id'])
    out = _gerar_docx_versao(rp)
    assert isinstance(out, (bytes, bytearray))
    assert len(out) > 1000
    doc_out = Document(io.BytesIO(out))
    textos = ' '.join(p.text for p in doc_out.paragraphs)
    assert 'Conteúdo do autor' in textos
    assert 'Introdução' in textos
