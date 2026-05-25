#!/usr/bin/env python
"""Script para reprocessar estrutura de um envio existente."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models.envio_conteudo import EnvioConteudo
from app.services.servico_envio_autor import ServicoEnvioAutor
from docx import Document

def reprocessar_envio(id_envio):
    """Reprocessa a estrutura de um envio existente."""
    print(f'=== Reprocessando estrutura do envio {id_envio} ===\n')

    app = create_app()

    with app.app_context():
        envio = EnvioConteudo.query.get(id_envio)
        if not envio:
            print(f'✗ Envio {id_envio} não encontrado')
            return

        print(f'✓ Envio encontrado: {envio.nome_arquivo}')

        if not os.path.exists(envio.caminho_arquivo):
            print(f'✗ Arquivo não encontrado: {envio.caminho_arquivo}')
            return

        try:
            doc = Document(envio.caminho_arquivo)
            print(f'✓ DOCX carregado: {len(doc.paragraphs)} parágrafos')

            # Extrair estrutura completa
            estrutura = ServicoEnvioAutor._extrair_estrutura_completa(doc)

            # Salvar no banco
            import json
            envio.sugestoes_json = json.dumps(estrutura)

            from app import db
            db.session.commit()

            print(f'✓ Estrutura salva no banco')
            print(f'  Capítulos: {len(estrutura.get("capitulos", []))}')
            print(f'  Legendas: {list(estrutura.get("legendas", {}).keys())}')

            if estrutura.get("capitulos"):
                print(f'\n  Capítulos encontrados:')
                for i, cap in enumerate(estrutura["capitulos"][:5]):
                    print(f'    {i+1}. {cap.get("indice", "")} {cap.get("titulo", "")} (nível {cap.get("nivel", "")})')

        except Exception as e:
            print(f'✗ Erro: {e}')
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    reprocessar_envio(7)
