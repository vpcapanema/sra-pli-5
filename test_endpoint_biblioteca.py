#!/usr/bin/env python
"""
Teste end-to-end do endpoint POST /biblioteca-relatorios-base.
Dispara o formulário de criação de modelo com upload DOCX real
e verifica se Modelo + Relatório Base são criados no banco.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models.usuario import Usuario
from app.models.modelo_relatorio import ModeloRelatorio
from app.models.relatorio_base import RelatorioBase
from app.models.versao_trabalho import VersaoTrabalho

DOCX_PATH = os.path.join(
    "D:", "REPOSITORIOS", "sra-pli-5", "docs",
    "D20-15 - R00 - 18052026_LF.docx"
)


def main():
    app = create_app()
    client = app.test_client()

    with app.app_context():
        print("=" * 60)
        print("TESTE ENDPOINT: /configuracoes/biblioteca-relatorios-base")
        print("=" * 60)

        # 1. Criar usuário admin de teste
        print("\n[1] Criando usuário admin de teste...")
        email_teste = "teste.admin@example.com"
        senha_teste = "123456"
        usuario = Usuario.query.filter_by(
            email=email_teste, perfil="admin"
        ).first()
        if not usuario:
            usuario = Usuario(
                nome_completo="Teste Admin",
                email=email_teste,
                perfil="admin",
                senha_hash=generate_password_hash(senha_teste),
                ativo=True,
            )
            db.session.add(usuario)
            db.session.commit()
            print(f"OK: Usuário criado ID={usuario.id_usuario}")
        else:
            print(f"OK: Usuário existente ID={usuario.id_usuario}")

        # 2. Login
        print("\n[2] Fazendo login...")
        resp = client.post(
            "/login",
            data={
                "email": email_teste,
                "senha": senha_teste,
                "tipo_perfil": "admin",
            },
            follow_redirects=True,
        )
        if resp.status_code == 200:
            print("OK: Login realizado")
        else:
            print(f"ERRO: Login falhou (status={resp.status_code})")
            return

        # 3. Verificar arquivo DOCX
        print("\n[3] Verificando arquivo DOCX...")
        if not os.path.exists(DOCX_PATH):
            print(f"ERRO: Arquivo não encontrado: {DOCX_PATH}")
            return
        tamanho = os.path.getsize(DOCX_PATH)
        print(f"OK: Arquivo encontrado ({tamanho} bytes)")

        # 4. Disparar POST multipart no endpoint
        print("\n[4] Disparando POST /biblioteca-relatorios-base...")
        with open(DOCX_PATH, "rb") as f:
            data = {
                "nome_modelo": "D20-15 Teste Endpoint",
                "descricao": "Teste via endpoint com DOCX real",
                "ativo": "on",
            }
            data["arquivo_docx"] = (f, "D20-15.docx")
            resp = client.post(
                "/configuracoes/biblioteca-relatorios-base",
                data=data,
                content_type="multipart/form-data",
            )

        print(f"OK: Resposta status={resp.status_code}")
        print(f"    Location={resp.headers.get('Location', 'N/A')}")
        if resp.status_code == 302:
            print("    -> Redirect após criação (esperado)")

        # 5. Verificar banco
        print("\n[5] Verificando registros no banco...")
        modelo = ModeloRelatorio.query.filter_by(
            nome_modelo="D20-15 Teste Endpoint"
        ).first()
        if modelo:
            print(f"OK: Modelo ID={modelo.id_modelo_relatorio}")
            rb = RelatorioBase.query.filter_by(
                id_modelo_relatorio=modelo.id_modelo_relatorio
            ).first()
            if rb:
                print(f"OK: Relatório Base ID={rb.id_relatorio_base}")
                print(f"    Título: {rb.titulo}")
                print(f"    Versão: {rb.versao}")
                print(f"    Arquivo: {rb.caminho_arquivo}")
            else:
                print("ERRO: Relatório base não criado")

            vt = VersaoTrabalho.query.filter_by(
                id_relatorio_base=rb.id_relatorio_base if rb else None
            ).first()
            if vt:
                print(f"AVISO: Versão Trabalho ID={vt.id_versao_trabalho}")
                print("      (Não deveria existir — fluxo separado)")
            else:
                print("OK: Nenhuma versão de trabalho criada (correto)")
        else:
            print("ERRO: Modelo não encontrado no banco")
            print(f"    Resposta flash: {resp.data.decode()[:200]}")

        # 6. Limpeza
        print("\n[6] Limpando registros de teste...")
        if modelo:
            RelatorioBase.query.filter_by(
                id_modelo_relatorio=modelo.id_modelo_relatorio
            ).delete()
            db.session.delete(modelo)
            db.session.commit()
            print("OK: Registros removidos")

        print("\n" + "=" * 60)
        print("TESTE CONCLUÍDO")
        print("=" * 60)


if __name__ == "__main__":
    main()
