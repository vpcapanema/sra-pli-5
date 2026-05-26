-- 008_dominios_status_envio_conteudo.sql
-- =============================================================
-- Cria os registros de dominio para o ciclo de envio de conteudo
-- do AUTOR (monitora o comportamento do autor em relacao ao envio,
-- nao o ciclo do upload em si — esse continua em
-- `envios_conteudo.status_envio`).
--
-- Os 4 valores serao consumidos quando o modulo de notificacoes
-- externas for implementado. Por enquanto, apenas o catalogo eh
-- registrado em `public.dominios`.
--
-- Transicoes esperadas (referencia para a fase posterior):
--   notificado        -> aguardando_envio: autor leu o e-mail.
--   aguardando_envio  -> em_preparacao:    autor (ou coordenador)
--                                          atribuiu o autor a algum
--                                          capitulo. status_capitulo
--                                          do(s) capitulo(s) deve
--                                          estar = 'em_edicao'.
--   em_preparacao     -> enviado:          autor enviou conteudo
--                                          para revisao do
--                                          coordenador. status_capitulo
--                                          deve estar =
--                                          'aguardando_aprovacao'.
--
-- Idempotente: nao re-insere se os pares (tipo, valor) ja existirem.
-- =============================================================

BEGIN;

INSERT INTO dominios (tipo, valor, descricao, ordem, ativo)
SELECT 'status_envio_conteudo', v, d, o, TRUE
FROM (VALUES
    ('notificado',
     'Autor notificado da abertura do periodo de envio de conteudo do relatorio vigente',
     10),
    ('aguardando_envio',
     'Autor leu o e-mail mas ainda nao acessou o sistema nem atribuiu nenhum capitulo',
     20),
    ('em_preparacao',
     'Autor atribuido a pelo menos um capitulo (status_capitulo = em_edicao)',
     30),
    ('enviado',
     'Autor enviou conteudo para revisao do coordenador (status_capitulo = aguardando_aprovacao)',
     40)
) AS s(v, d, o)
WHERE NOT EXISTS (
    SELECT 1 FROM dominios x
     WHERE x.tipo = 'status_envio_conteudo' AND x.valor = s.v
);

COMMIT;
