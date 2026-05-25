"""Serviço de finalização de relatório em produção.

Responsabilidades:

1. Pegar o DOCX da versão atual em `RelatorioProducao.caminho_template`
   — que JÁ É o documento montado (autores fizeram merge in-place de
   seus capítulos via `servico_merge_docx`). Não há mais reconstrução
   capítulo a capítulo a partir do banco.

2. Copiar esse DOCX para
   `storage/relatorios_finalizados/<codigo>_<versao>_<timestamp>.docx`,
   preservando o original em produção (que continua disponível para
   novas iterações se desejado).

3. Calcular checksum SHA-256 do binário do snapshot.

4. Persistir um registro `RelatorioFinalizado` com metadados (código,
   título, medição, período, biblioteca, versão, checksum, caminho,
   data, finalizador).

5. Avançar `RelatorioProducao.status` para 'finalizado' e marcar
   `bloqueio_edicao=True` (impede uploads / merges posteriores na
   mesma versão; a próxima rodada deve clonar de novo ou abrir nova
   versão).

Decisão arquitetural: este serviço NÃO altera o DOCX em produção.
Ele cria uma cópia (snapshot) em local separado para que o histórico
de finalizações seja preservado mesmo que o DOCX em produção
seja eventualmente editado ou excluído.
"""
from __future__ import annotations

import hashlib
import os
import shutil
from datetime import datetime
from typing import Optional

from werkzeug.utils import secure_filename

from app import db
from app.models.dominio import DomStatusRelatorio
from app.models.relatorio_finalizado import RelatorioFinalizado
from app.models.relatorio_producao import RelatorioProducao


DIR_FINALIZADOS = ('storage', 'relatorios_finalizados')


class FinalizacaoError(RuntimeError):
    """Erro de domínio na finalização do relatório."""


def _base_dir() -> str:
    """Raiz do projeto (dois níveis acima deste arquivo)."""
    return os.path.dirname(
        os.path.dirname(os.path.dirname(__file__))
    )


def _checksum_sha256(caminho: str) -> str:
    """Calcula SHA-256 hex de um arquivo, em blocos para evitar
    carregar tudo na memória.
    """
    h = hashlib.sha256()
    with open(caminho, 'rb') as f:
        for bloco in iter(lambda: f.read(65536), b''):
            h.update(bloco)
    return h.hexdigest()


def _nome_snapshot(rel: RelatorioProducao) -> str:
    """Gera nome de arquivo único e descritivo para o snapshot.

    Formato: `<codigo>_<versao>_<YYYYMMDDHHMMSS>.docx`, com
    `secure_filename` para garantir compatibilidade entre SOs.
    """
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    codigo = rel.codigo_d20 or f'rel{rel.id}'
    versao = rel.versao_atual or 'R00'
    bruto = f'{codigo}_{versao}_{timestamp}.docx'
    return secure_filename(bruto)


def finalizar(
    id_relatorio: int,
    id_usuario: int,
    avancar_status: bool = True,
    bloquear_edicao: bool = True,
) -> RelatorioFinalizado:
    """Finaliza o relatório: cria snapshot, persiste `RelatorioFinalizado`
    e atualiza estado do `RelatorioProducao`.

    Parâmetros:
    - `id_relatorio`: id do `RelatorioProducao`
    - `id_usuario`: id do usuário responsável (autenticado)
    - `avancar_status`: muda `status` para 'finalizado' (default True)
    - `bloquear_edicao`: marca `bloqueio_edicao=True` (default True)

    Retorna o `RelatorioFinalizado` recém-criado (já commitado).

    Levanta `FinalizacaoError` se o relatório não tiver
    `caminho_template` ou se o arquivo não existir no disco.
    """
    rel = RelatorioProducao.query.get(id_relatorio)
    if not rel:
        raise FinalizacaoError(
            f'RelatorioProducao id={id_relatorio} não encontrado.'
        )
    if not rel.caminho_template:
        raise FinalizacaoError(
            'Relatório não possui caminho_template definido. '
            'Foi clonado corretamente?'
        )
    if not os.path.exists(rel.caminho_template):
        raise FinalizacaoError(
            f'Arquivo DOCX em produção não encontrado: '
            f'{rel.caminho_template}'
        )

    # 1. Construir perfil de formatação a partir da biblioteca
    # canônica vinculada ao relatório. Esse perfil propaga estilos,
    # separadores e posições das legendas para os serviços abaixo,
    # garantindo fidelidade visual ao DOCX modelo.
    try:
        from app.services.servico_perfil_formatacao import PerfilFormatacao
        perfil = PerfilFormatacao.de_relatorio(rel)
    except (OSError, ValueError, RuntimeError):
        perfil = None

    # 1a. Fase 2 — Reindexar legendas (figuras/tabelas/equações) e
    # substituir cross-references no corpo do texto. Passe final para
    # garantir consistência após qualquer edição manual entre o último
    # merge e a finalização.
    try:
        from app.services.servico_captioning import reindexar_captions
        from app.services.servico_cross_refs import substituir_referencias
        resultado_caps = reindexar_captions(
            rel.caminho_template, perfil=perfil
        )
        mapa = resultado_caps.get('mapa_labels', {}) if isinstance(
            resultado_caps, dict
        ) else {}
        substituir_referencias(rel.caminho_template, mapa)
    except (OSError, ValueError, RuntimeError):
        # Não bloquear finalização por falha de captioning/cross-refs.
        pass

    # 1b. Fase 3 — TOC/Listas NAO sao inseridas automaticamente na
    # finalizacao. Sao operacoes EXPLICITAS do coordenador via UI:
    #   - POST /relatorio/producao/<id>/inserir-sumario
    #   - POST /relatorio/producao/<id>/inserir-lista-figuras
    #   - POST /relatorio/producao/<id>/inserir-lista-tabelas
    # O conteudo e pre-calculado e nao depende de "Word recalcular ao
    # abrir". O coordenador deve ter inserido os 3 antes de finalizar.

    # 1. Copiar para storage/relatorios_finalizados/
    dir_finalizados = os.path.join(_base_dir(), *DIR_FINALIZADOS)
    os.makedirs(dir_finalizados, exist_ok=True)
    nome_dest = _nome_snapshot(rel)
    caminho_snapshot = os.path.join(dir_finalizados, nome_dest)
    shutil.copy2(rel.caminho_template, caminho_snapshot)

    # 2. Checksum do snapshot
    checksum = _checksum_sha256(caminho_snapshot)

    # 3. Status 'finalizado' (busca por código; pode não existir em
    # ambientes antigos sem a migration `add_finalizado_status`).
    status_finalizado: Optional[DomStatusRelatorio] = (
        DomStatusRelatorio.query.filter_by(codigo='finalizado').first()
    )

    # 4. Persistir RelatorioFinalizado (snapshot dos metadados)
    rf = RelatorioFinalizado(
        relatorio_id=rel.id,
        modelo_id=rel.modelo_id,
        biblioteca_id=rel.biblioteca_id,
        status_id=status_finalizado.id if status_finalizado else None,
        nome_arquivo=nome_dest,
        caminho_arquivo=caminho_snapshot,
        finalizado_por=id_usuario,
        checksum_docx=checksum,
        codigo=rel.codigo_d20,
        titulo=rel.titulo_curto,
        mes_referencia=rel.mes_referencia,
        ano_referencia=rel.ano_referencia,
        periodo_inicio=rel.periodo_inicio,
        periodo_fim=rel.periodo_fim,
        numero_medicao=rel.numero_medicao,
        versao=rel.versao_atual or 'R00',
    )
    db.session.add(rf)

    # 5. Atualizar estado do RelatorioProducao
    if avancar_status and status_finalizado:
        rel.status_id = status_finalizado.id
    if bloquear_edicao:
        rel.bloqueio_edicao = True

    db.session.commit()
    return rf
