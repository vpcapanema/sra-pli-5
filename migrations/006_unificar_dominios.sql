-- ============================================================
-- 006 — Unifica tabelas de dominio em public.dominios
--
-- Move os registros de:
--   - dom_perfis_usuario (codigo, descricao, nivel_acesso)
--   - dom_status_relatorios (codigo, descricao, ordem)
-- para a tabela generica public.dominios.
--
-- Acoes:
--   1) Adiciona colunas `ordem` e `nivel_acesso` em dominios.
--   2) Apaga registros orfaos pre-existentes que conflitariam:
--      - dominios.tipo='status_relatorio' (4 valores antigos)
--      - dominios.tipo='tipo_perfil' (3 valores antigos com nomes
--        diferentes dos efetivamente usados nas FKs)
--   3) Insere os registros vivos:
--      - dom_perfis_usuario -> dominios.tipo='perfil_usuario'
--      - dom_status_relatorios -> dominios.tipo='status_relatorio'
--      Preserva codigo (em valor), descricao, nivel_acesso e ordem.
--   4) Cria tabela auxiliar de mapeamento id_antigo -> id_novo
--      para reapontar as FKs.
--   5) Reaponta:
--      - usuarios.perfil_id   -> dominios.id_dominio
--      - relatorios_producao.status_id   -> dominios.id_dominio
--      - relatorios_finalizados.status_id -> dominios.id_dominio
--   6) Drop tabelas antigas.
-- ============================================================

BEGIN;

-- 1) Colunas novas
ALTER TABLE dominios
    ADD COLUMN IF NOT EXISTS ordem INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS nivel_acesso INTEGER DEFAULT 0;

-- 2) Limpeza de orfaos
DELETE FROM dominios WHERE tipo = 'status_relatorio';
DELETE FROM dominios WHERE tipo = 'tipo_perfil';

-- 3) Insercao dos dados vivos.
--    Para perfil_usuario: codigo -> valor; descricao; nivel_acesso.
INSERT INTO dominios (tipo, valor, descricao, ativo, nivel_acesso, ordem)
SELECT 'perfil_usuario', codigo, descricao, ativo,
       COALESCE(nivel_acesso, 0), 0
FROM dom_perfis_usuario;

--    Para status_relatorio: codigo -> valor; descricao; ordem.
INSERT INTO dominios (tipo, valor, descricao, ativo, ordem, nivel_acesso)
SELECT 'status_relatorio', codigo, descricao, ativo,
       COALESCE(ordem, 0), 0
FROM dom_status_relatorios;

-- 4) Tabela temporaria de mapeamento id_antigo -> id_novo.
CREATE TEMP TABLE _mapa_perfil AS
SELECT old.id AS id_antigo, novo.id_dominio AS id_novo
FROM dom_perfis_usuario old
JOIN dominios novo
  ON novo.tipo = 'perfil_usuario' AND novo.valor = old.codigo;

CREATE TEMP TABLE _mapa_status_rel AS
SELECT old.id AS id_antigo, novo.id_dominio AS id_novo
FROM dom_status_relatorios old
JOIN dominios novo
  ON novo.tipo = 'status_relatorio' AND novo.valor = old.codigo;

-- 5) Drop FKs antigas, atualiza valores, recria FKs apontando para
--    public.dominios(id_dominio).

-- 5.a) usuarios.perfil_id
ALTER TABLE usuarios
    DROP CONSTRAINT IF EXISTS usuarios_perfil_id_fkey;
UPDATE usuarios u
   SET perfil_id = m.id_novo
  FROM _mapa_perfil m
 WHERE u.perfil_id = m.id_antigo;
ALTER TABLE usuarios
    ADD CONSTRAINT usuarios_perfil_id_fkey
    FOREIGN KEY (perfil_id) REFERENCES dominios (id_dominio);

-- 5.b) relatorios_producao.status_id
ALTER TABLE relatorios_producao
    DROP CONSTRAINT IF EXISTS relatorios_producao_status_id_fkey;
UPDATE relatorios_producao r
   SET status_id = m.id_novo
  FROM _mapa_status_rel m
 WHERE r.status_id = m.id_antigo;
ALTER TABLE relatorios_producao
    ADD CONSTRAINT relatorios_producao_status_id_fkey
    FOREIGN KEY (status_id) REFERENCES dominios (id_dominio);

-- 5.c) relatorios_finalizados.status_id
ALTER TABLE relatorios_finalizados
    DROP CONSTRAINT IF EXISTS relatorios_finalizados_status_id_fkey;
UPDATE relatorios_finalizados r
   SET status_id = m.id_novo
  FROM _mapa_status_rel m
 WHERE r.status_id = m.id_antigo;
ALTER TABLE relatorios_finalizados
    ADD CONSTRAINT relatorios_finalizados_status_id_fkey
    FOREIGN KEY (status_id) REFERENCES dominios (id_dominio);

-- 6) Drop tabelas antigas (agora orfaas).
DROP TABLE IF EXISTS dom_perfis_usuario;
DROP TABLE IF EXISTS dom_status_relatorios;

COMMIT;
