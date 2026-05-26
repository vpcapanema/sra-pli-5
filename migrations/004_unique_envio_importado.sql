-- ============================================================
-- 004 — Unicidade de envio_conteudo por (relatorio, capitulo)
--
-- Regra de negocio: cada capitulo/subcapitulo de um relatorio
-- pode ter no maximo 1 envio com status_envio = 'importado'.
-- Quando um novo conteudo eh importado para o mesmo capitulo,
-- o registro 'importado' anterior eh descartado pela aplicacao
-- (servico_envio_autor._descartar_envio_importado_anterior).
-- Esta migration:
--   1) limpa previsualizacoes dos envios que vamos remover;
--   2) limpa eventuais duplicatas que ja existem (mantendo o
--      mais recente por id_envio_conteudo);
--   3) limpa previsualizacoes orfas remanescentes;
--   4) cria UNIQUE INDEX parcial sobre (id_relatorio,
--      id_capitulo_destino) WHERE status_envio = 'importado'.
--
-- Observacao: envios em 'em_previa' nao sao restritos pelo
-- indice — eles sao rascunhos descartaveis. A aplicacao tambem
-- descarta em_previa anteriores ao receber novo upload do mesmo
-- (relatorio, capitulo).
-- ============================================================

BEGIN;

-- 1) Apaga previsualizacoes dos envios duplicados que serao removidos.
DELETE FROM previsualizacoes_conteudo
WHERE id_envio_conteudo IN (
    WITH ranked AS (
        SELECT
            id_envio_conteudo,
            ROW_NUMBER() OVER (
                PARTITION BY id_relatorio, id_capitulo_destino
                ORDER BY id_envio_conteudo DESC
            ) AS rn
        FROM envios_conteudo
        WHERE status_envio = 'importado'
          AND id_capitulo_destino IS NOT NULL
    )
    SELECT id_envio_conteudo FROM ranked WHERE rn > 1
);

-- 2) Apaga as duplicatas, mantendo o registro mais recente
--    (max(id_envio_conteudo)) por (id_relatorio, id_capitulo_destino).
WITH ranked AS (
    SELECT
        id_envio_conteudo,
        ROW_NUMBER() OVER (
            PARTITION BY id_relatorio, id_capitulo_destino
            ORDER BY id_envio_conteudo DESC
        ) AS rn
    FROM envios_conteudo
    WHERE status_envio = 'importado'
      AND id_capitulo_destino IS NOT NULL
)
DELETE FROM envios_conteudo
WHERE id_envio_conteudo IN (
    SELECT id_envio_conteudo FROM ranked WHERE rn > 1
);

-- 3) Limpa previsualizacoes orfas remanescentes.
DELETE FROM previsualizacoes_conteudo
WHERE id_envio_conteudo NOT IN (
    SELECT id_envio_conteudo FROM envios_conteudo
);

-- 4) Indice unico parcial: garante 1 unico 'importado' por
--    (relatorio, capitulo). Aplica-se apenas onde
--    id_capitulo_destino IS NOT NULL e status_envio = 'importado'.
CREATE UNIQUE INDEX IF NOT EXISTS ux_envios_importado_por_capitulo
    ON envios_conteudo (id_relatorio, id_capitulo_destino)
    WHERE status_envio = 'importado'
      AND id_capitulo_destino IS NOT NULL;

COMMIT;
