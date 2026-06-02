#!/usr/bin/env python
"""Script para reprocessar estrutura de um envio existente."""

import json
import os
import traceback

from docx import Document

from app import create_app
from app import db
from app.models.envio_conteudo import EnvioConteudo
from app.services.servico_envio_autor import ServicoEnvioAutor


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
            estrutura = ServicoEnvioAutor.extrair_estrutura_completa(doc)

            # Salvar no banco
            envio.sugestoes_json = json.dumps(estrutura)
            db.session.commit()

            print('✓ Estrutura salva no banco')
            print(f'  Capítulos: {len(estrutura.get("capitulos", []))}')
            print(f'  Legendas: {list(estrutura.get("legendas", {}).keys())}')

            if estrutura.get("capitulos"):
                print('\n  Capítulos encontrados:')
                for i, cap in enumerate(estrutura["capitulos"][:5]):
                    print(
                        f'    {i + 1}. {cap.get("indice", "")} '
                        f'{cap.get("titulo", "")} '
                        f'(nível {cap.get("nivel", "")})'
                    )

        except Exception as e:
            print(f'✗ Erro: {e}')
            traceback.print_exc()


if __name__ == '__main__':
    reprocessar_envio(7)
