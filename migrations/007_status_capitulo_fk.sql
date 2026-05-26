-- 007_status_capitulo_fk.sql
-- =============================================================
-- Promove `capitulos_documento.status_capitulo` (VARCHAR solto)
-- para FK -> public.dominios.id_dominio (tipo='status_capitulo').
--
-- Estrategia (idempotente, sem downtime):
--   1) Garante registros em `dominios` para os 4 valores validos:
--        em_edicao, aguardando_aprovacao, aprovado, rejeitado.
--      ('reprovado' tambem aparece em rota legada — mapeamos como
--      sinonimo de 'rejeitado' no backfill).
--   2) Adiciona coluna `status_capitulo_id` em `capitulos_documento`
--      como FK para `dominios.id_dominio` (NULL inicialmente).
--   3) Backfill: copia o valor textual atual em `status_capitulo`
--      para o id correspondente em `dominios`.
--   4) Cria index e mantem a coluna textual `status_capitulo` por
--      compatibilidade transitoria (a aplicacao continua escrevendo
--      a string; passos seguintes da app vao usar o relacionamento).
--
-- Reversao: drop FK + drop coluna `status_capitulo_id`.
-- =============================================================

BEGIN;

-- 1) Seed dos status em `dominios`.
INSERT INTO dominios (tipo, valor, descricao, ordem, ativo)
SELECT 'status_capitulo', v, d, o, TRUE
FROM (VALUES
    ('em_edicao',            'Capítulo em edição pelo autor',                10),
    ('aguardando_aprovacao', 'Capítulo aguardando aprovação do coordenador', 20),
    ('aprovado',             'Capítulo aprovado pelo coordenador',           30),
    ('rejeitado',            'Capítulo rejeitado pelo coordenador',          40)
) AS s(v, d, o)
WHERE NOT EXISTS (
    SELECT 1 FROM dominios x
     WHERE x.tipo = 'status_capitulo' AND x.valor = s.v
);

-- 2) Coluna FK (NULL ate o backfill).
ALTER TABLE capitulos_documento
    ADD COLUMN IF NOT EXISTS status_capitulo_id INTEGER
    REFERENCES dominios(id_dominio);

CREATE INDEX IF NOT EXISTS ix_cap_doc_status_capitulo_id
    ON capitulos_documento(status_capitulo_id);

-- 3) Backfill: status string -> id_dominio.
--    Tratamos 'reprovado' (rota legada) como sinonimo de 'rejeitado'
--    e 'enviado_revisao' (workflow antigo) como sinonimo de
--    'aguardando_aprovacao'. Status vazio/desconhecido -> 'em_edicao'.
UPDATE capitulos_documento c
   SET status_capitulo_id = d.id_dominio
  FROM dominios d
 WHERE d.tipo = 'status_capitulo'
   AND c.status_capitulo_id IS NULL
   AND d.valor = CASE
        WHEN c.status_capitulo IN ('em_edicao', 'aguardando_aprovacao',
                                   'aprovado', 'rejeitado')
            THEN c.status_capitulo
        WHEN c.status_capitulo = 'reprovado'        THEN 'rejeitado'
        WHEN c.status_capitulo = 'enviado_revisao'  THEN 'aguardando_aprovacao'
        WHEN c.status_capitulo = 'finalizado'       THEN 'aprovado'
        ELSE 'em_edicao'
   END;

COMMIT;
