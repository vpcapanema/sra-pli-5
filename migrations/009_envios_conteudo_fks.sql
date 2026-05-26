-- 009_envios_conteudo_fks.sql
-- =============================================================
-- Promove `envios_conteudo.status_envio` para FK -> dominios
-- (tipo='status_envio_conteudo') e adiciona `status_capitulo_id`
-- como espelho do estado editorial do capitulo destino
-- (FK -> dominios, tipo='status_capitulo').
--
-- A separacao de responsabilidades fica:
--   - `status_envio_id`     : sobre o AUTOR e o ciclo de envio
--                             (notificado / aguardando_envio /
--                             em_preparacao / enviado).
--   - `status_capitulo_id`  : sobre o CAPITULO destino do envio
--                             (em_edicao / aguardando_aprovacao /
--                             aprovado / rejeitado). Espelha
--                             `capitulo_destino.status_capitulo_id`
--                             para permitir filtros e dashboards
--                             sem JOIN extra.
--
-- A coluna VARCHAR `status_envio` permanece como cache/legado;
-- aplicacoes mais novas devem ler do relacionamento (`Dominio`).
-- =============================================================

BEGIN;

-- 1) Novas colunas (NULL ate o backfill). FKs apontam para dominios.id_dominio.
ALTER TABLE envios_conteudo
    ADD COLUMN IF NOT EXISTS status_envio_id INTEGER
    REFERENCES dominios(id_dominio);

ALTER TABLE envios_conteudo
    ADD COLUMN IF NOT EXISTS status_capitulo_id INTEGER
    REFERENCES dominios(id_dominio);

CREATE INDEX IF NOT EXISTS ix_envios_status_envio_id
    ON envios_conteudo(status_envio_id);
CREATE INDEX IF NOT EXISTS ix_envios_status_capitulo_id
    ON envios_conteudo(status_capitulo_id);

-- 2) Backfill `status_envio_id`.
--    O ciclo antigo da tabela (em_previa / importado / rejeitado /
--    pendente) descrevia o estado de UM upload. O ciclo novo descreve
--    o comportamento do AUTOR. Mapeamento adotado:
--      em_previa  -> em_preparacao    (autor preparando o envio)
--      importado  -> enviado          (autor enviou; coordenador vai
--                                       revisar)
--      rejeitado  -> em_preparacao    (autor precisa preparar de novo)
--      pendente   -> aguardando_envio (autor ainda nao enviou nada)
--      desconhecido / NULL -> aguardando_envio
UPDATE envios_conteudo e
   SET status_envio_id = d.id_dominio
  FROM dominios d
 WHERE d.tipo = 'status_envio_conteudo'
   AND e.status_envio_id IS NULL
   AND d.valor = CASE
        WHEN e.status_envio IN ('em_previa', 'rejeitado') THEN 'em_preparacao'
        WHEN e.status_envio = 'importado'                 THEN 'enviado'
        WHEN e.status_envio = 'pendente'                  THEN 'aguardando_envio'
        ELSE 'aguardando_envio'
   END;

-- 3) Backfill `status_capitulo_id`: copia do capitulo destino quando
--    existir; senao deixa NULL (envio sem destino fixo).
UPDATE envios_conteudo e
   SET status_capitulo_id = c.status_capitulo_id
  FROM capitulos_documento c
 WHERE e.status_capitulo_id IS NULL
   AND e.id_capitulo_destino = c.id_capitulo_documento;

COMMIT;
