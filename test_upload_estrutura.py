#!/usr/bin/env python
"""Script para testar upload e extração de estrutura DOCX."""

import os
import sys
import requests

# Configurações
BASE_URL = 'http://localhost:5000'
LOGIN_URL = f'{BASE_URL}/login'
EDITOR_URL = f'{BASE_URL}/relatorio/editor-autor'
UPLOAD_URL = f'{BASE_URL}/relatorio/upload-conteudo'
ESTRUTURA_URL = f'{BASE_URL}/api/envios'

# Credenciais
EMAIL = 'admin@concremat.local'
SENHA = 'admin123'

def test_login():
    """Testa login e retorna session."""
    print('[1] Testando login...')
    session = requests.Session()
    
    # GET na página de login para pegar CSRF token se necessário
    response = session.get(LOGIN_URL)
    print(f'  GET {LOGIN_URL}: {response.status_code}')
    
    # POST para fazer login
    login_data = {
        'email': EMAIL,
        'senha': SENHA,
    }
    response = session.post(LOGIN_URL, data=login_data)
    print(f'  POST {LOGIN_URL}: {response.status_code}')
    
    if response.status_code == 200 or response.status_code == 302:
        print('  ✓ Login realizado com sucesso')
        return session
    else:
        print(f'  ✗ Falha no login: {response.text[:200]}')
        return None

def test_editor_autor(session):
    """Testa acesso ao editor do autor."""
    print('\n[2] Testando acesso ao editor do autor...')
    
    response = session.get(EDITOR_URL)
    print(f'  GET {EDITOR_URL}: {response.status_code}')
    
    if response.status_code == 200:
        print('  ✓ Editor acessado com sucesso')
        return response.text
    else:
        print(f'  ✗ Falha ao acessar editor: {response.text[:200]}')
        return None

def test_upload(session, id_versao, id_capitulo, caminho_docx):
    """Testa upload de DOCX."""
    print(f'\n[3] Testando upload de DOCX...')
    print(f'  Versão: {id_versao}, Capítulo: {id_capitulo}')
    print(f'  Arquivo: {caminho_docx}')
    
    if not os.path.exists(caminho_docx):
        print(f'  ✗ Arquivo não encontrado: {caminho_docx}')
        return None
    
    url = f'{UPLOAD_URL}/{id_versao}/{id_capitulo}'
    
    with open(caminho_docx, 'rb') as f:
        files = {'arquivo_docx': f}
        response = session.post(url, files=files)
    
    print(f'  POST {url}: {response.status_code}')
    
    if response.status_code == 302:
        # Redirect após upload
        print('  ✓ Upload realizado (redirect)')
        return response.headers.get('Location')
    elif response.status_code == 200:
        print('  ✓ Upload realizado')
        return None
    else:
        print(f'  ✗ Falha no upload: {response.text[:200]}')
        return None

def test_estrutura(session, id_envio):
    """Testa extração de estrutura."""
    print(f'\n[4] Testando extração de estrutura do envio {id_envio}...')
    
    url = f'{ESTRUTURA_URL}/{id_envio}/estrutura'
    response = session.get(url)
    
    print(f'  GET {url}: {response.status_code}')
    
    if response.status_code == 200:
        data = response.json()
        print('  ✓ Estrutura retornada com sucesso')
        print(f'  Capítulos: {len(data.get("capitulos", []))}')
        print(f'  Legendas: {data.get("legendas", {})}')
        return data
    else:
        print(f'  ✗ Falha ao obter estrutura: {response.text[:200]}')
        return None

def main():
    """Executa todos os testes."""
    print('=' * 60)
    print('TESTE DE UPLOAD E EXTRAÇÃO DE ESTRUTURA DOCX')
    print('=' * 60)
    
    # Login
    session = test_login()
    if not session:
        sys.exit(1)
    
    # Acessar editor
    editor_html = test_editor_autor(session)
    if not editor_html:
        sys.exit(1)
    
    # Parâmetros do teste (ajuste conforme necessário)
    id_versao = 1  # ID do relatório
    id_capitulo = 1  # ID do capítulo
    caminho_docx = 'teste.docx'  # Caminho para um DOCX de teste
    
    # Upload
    redirect_url = test_upload(session, id_versao, id_capitulo, caminho_docx)
    
    # Se não tiver DOCX de teste, pular upload e testar estrutura de envio existente
    if not redirect_url and not os.path.exists(caminho_docx):
        print('\n  ⚠ Sem arquivo de teste, tentando usar envio existente...')
        # Tentar pegar ID de envio do banco
        print('  ⚠ Você precisa fornecer um ID de envio existente para testar estrutura')
        print('  ⚠ Ou fornecer um arquivo DOCX válido')
        return
    
    # Testar estrutura (precisa de ID do envio)
    # Para isso, precisamos pegar o ID do envio criado ou usar um existente
    print('\n[4] Para testar estrutura, preciso do ID do envio.')
    print('    Execute: docker exec -it sra_postgres psql -U sra_admin -d sra_pli -c "SELECT id_envio_conteudo FROM envios_conteudo ORDER BY criado_em DESC LIMIT 1;"')
    print('    E use o ID retornado para testar a estrutura.')

if __name__ == '__main__':
    main()
