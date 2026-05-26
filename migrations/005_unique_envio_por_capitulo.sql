-- ============================================================
-- 005 — Unicidade absoluta de envio_conteudo por (relatorio, capitulo)
--
-- Substitui a regra parcial da migration 004 por uma regra
-- absoluta: a tabela envios_conteudo aceita NO MAXIMO 1 registro
-- por (id_relatorio, id_capitulo_destino), independente do
-- status_envio. Quando um novo upload chega para o mesmo
-- (relatorio, capitulo), o registro anterior eh descartado pela
-- aplicacao em servico_envio_autor._descartar_envios_anteriores.
--
-- Esta migration:
--   1) apaga previsualizacoes dos envios duplicados que serao
--      removidos (mantendo o de maior id_envio_conteudo);
--   2) apaga os envios duplicados;
--   3) limpa previsualizacoes orfas;
--   4) remove o indice parcial criado na 004 (se existir);
--   5) cria UNIQUE INDEX total em (id_relatorio,
--      id_capitulo_destino) WHERE id_capitulo_destino IS NOT NULL.
-- ============================================================

BEGIN;

-- 1) Apaga previsualizacoes dos envios duplicados.
DELETE FROM previsualizacoes_conteudo
WHERE id_envio_conteudo IN (
    WITH ranked AS (
        SELECT
            id_envio_conteudo,
            ROW_NUMBER() OVER (
                PARTITION BY id_relatorio, id_capitulo_destino
                ORDER BY
                    -- Importado tem prioridade total para sobreviver,
                    -- depois pelo id mais recente (ultimo upload).
                    CASE WHEN status_envio = 'importado' THEN 0 ELSE 1 END,
                    id_envio_conteudo DESC
            ) AS rn
        FROM envios_conteudo
        WHERE id_capitulo_destino IS NOT NULL
    )
    SELECT id_envio_conteudo FROM ranked WHERE rn > 1
);

-- 2) Apaga os envios duplicados, preservando 1 por (relatorio, capitulo).
WITH ranked AS (
    SELECT
        id_envio_conteudo,
        ROW_NUMBER() OVER (
            PARTITION BY id_relatorio, id_capitulo_destino
            ORDER BY
                CASE WHEN status_envio = 'importado' THEN 0 ELSE 1 END,
                id_envio_conteudo DESC
        ) AS rn
    FROM envios_conteudo
    WHERE id_capitulo_destino IS NOT NULL
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

-- 4) Remove o indice parcial criado na migration 004 (se existir).
DROP INDEX IF EXISTS ux_envios_importado_por_capitulo;

-- 5) Indice unico TOTAL: 1 envio por (relatorio, capitulo) qualquer
--    que seja o status. Aplica-se onde id_capitulo_destino IS NOT NULL
--    (envios sem destino sao tratados separadamente — historicos).
CREATE UNIQUE INDEX IF NOT EXISTS ux_envios_por_capitulo
    ON envios_conteudo (id_relatorio, id_capitulo_destino)
    WHERE id_capitulo_destino IS NOT NULL;

COMMIT;
