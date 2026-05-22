"""
Teste end-to-end do fluxo Biblioteca de Relatórios Base.
Usa o DOCX fornecido para criar modelo, relatório base, versão de trabalho
e capítulos extraídos automaticamente.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.services.servico_relatorio import ServicoRelatorio
from app.services.servico_extracao_canonica import ServicoExtracaoCanonica
from app.models.modelo_relatorio import ModeloRelatorio
from app.models.relatorio_base import RelatorioBase
from app.models.versao_trabalho import VersaoTrabalho
from app.models.capitulo_documento import CapituloDocumento
from docx import Document

DOCX_PATH = r"D:\REPOSITORIOS\sra-pli-5\docs\D20-15 - R00 - 18052026_LF.docx"


def main():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("TESTE: Biblioteca de Relatórios Base")
        print("=" * 60)

        # 1. Verificar arquivo
        print("\n[1] Verificando arquivo DOCX...")
        if not os.path.exists(DOCX_PATH):
            print(f"ERRO: Arquivo não encontrado: {DOCX_PATH}")
            return
        print(f"OK: Arquivo encontrado ({os.path.getsize(DOCX_PATH)} bytes)")

        # 2. Testar extração canônica de capítulos (sem banco)
        print("\n[2] Testando extração de capítulos do DOCX...")
        doc = Document(DOCX_PATH)
        arvore = ServicoExtracaoCanonica._extrair_capitulos(doc)
        print(f"OK: {len(arvore)} capítulos de nível 1 extraídos")
        for cap in arvore:
            print(f"    - {cap['titulo']} (nivel={cap['nivel']})")
            if cap.get('filhos'):
                for sub in cap['filhos']:
                    print(f"      └─ {sub['titulo']} (nivel={sub['nivel']})")

        # 3. Criar modelo completo (modelo + relatório base + versão + capítulos)
        print("\n[3] Criando modelo completo via servico...")
        modelo = ServicoRelatorio.criar_modelo_completo(
            nome_modelo="D20-15 - R00 - Teste",
            descricao="Modelo de teste gerado a partir do DOCX D20-15",
            ativo=True,
            caminho_docx=DOCX_PATH
        )
        print(f"OK: Modelo criado ID={modelo.id_modelo_relatorio}")

        # 4. Verificar Relatório Base
        print("\n[4] Verificando Relatório Base criado...")
        rb = RelatorioBase.query.filter_by(
            id_modelo_relatorio=modelo.id_modelo_relatorio
        ).first()
        if rb:
            print(f"OK: Relatório Base ID={rb.id_relatorio_base}")
            print(f"    Título: {rb.titulo}")
            print(f"    Versão: {rb.versao}")
            print(f"    Status: {rb.status_relatorio}")
            print(f"    Arquivo: {rb.caminho_arquivo}")
        else:
            print("ERRO: Relatório base não encontrado")
            return

        # 5. Verificar Versão de Trabalho
        print("\n[5] Verificando Versão de Trabalho criada...")
        vt = VersaoTrabalho.query.filter_by(
            id_relatorio_base=rb.id_relatorio_base
        ).first()
        if vt:
            print(f"OK: Versão de Trabalho ID={vt.id_versao_trabalho}")
            print(f"    Título: {vt.titulo}")
            print(f"    Status: {vt.status_versao}")
        else:
            print("ERRO: Versão de trabalho não encontrada")
            return

        # 6. Verificar Capítulos
        print("\n[6] Verificando Capítulos extraídos...")
        capitulos = CapituloDocumento.query.filter_by(
            id_versao_trabalho=vt.id_versao_trabalho,
            id_capitulo_pai=None
        ).order_by(CapituloDocumento.ordem_capitulo).all()

        if not capitulos:
            print("ERRO: Nenhum capítulo encontrado")
            return

        print(f"OK: {len(capitulos)} capítulos principais no banco")
        for cap in capitulos:
            print(f"    [{cap.ordem_capitulo}] {cap.titulo_capitulo}")
            print(f"         nível={cap.nivel_capitulo}, status={cap.status_capitulo}")
            subs = CapituloDocumento.query.filter_by(
                id_capitulo_pai=cap.id_capitulo_documento
            ).order_by(CapituloDocumento.ordem_capitulo).all()
            for sub in subs:
                print(f"      └─ {sub.titulo_capitulo} (nível={sub.nivel_capitulo})")

        # 7. Resumo
        total_capitulos = CapituloDocumento.query.filter_by(
            id_versao_trabalho=vt.id_versao_trabalho
        ).count()

        print("\n" + "=" * 60)
        print("RESUMO DO TESTE")
        print("=" * 60)
        print(f"Modelo Relatório : ID {modelo.id_modelo_relatorio}")
        print(f"Relatório Base   : ID {rb.id_relatorio_base}")
        print(f"Versão Trabalho  : ID {vt.id_versao_trabalho}")
        print(f"Total Capítulos  : {total_capitulos}")
        print("\nSTATUS: SUCESSO")
        print("Todos os registros foram criados corretamente.")
        print("=" * 60)

        # Limpa registros de teste (opcional — comentar para manter)
        print("\n[LIMPEZA] Removendo registros de teste...")
        CapituloDocumento.query.filter_by(
            id_versao_trabalho=vt.id_versao_trabalho
        ).delete()
        db.session.delete(vt)
        db.session.delete(rb)
        db.session.delete(modelo)
        db.session.commit()
        print("OK: Registros de teste removidos.")


if __name__ == '__main__':
    main()
