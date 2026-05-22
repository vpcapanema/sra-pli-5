-- Migração para adicionar FKs de modelo e biblioteca em relatorios_producao
-- E renomear colunas em tabelas relacionadas

-- Adicionar colunas modelo_id e biblioteca_id em relatorios_producao
ALTER TABLE relatorios_producao 
ADD COLUMN IF NOT EXISTS modelo_id INTEGER REFERENCES modelos_relatorio(id_modelo_relatorio);

ALTER TABLE relatorios_producao 
ADD COLUMN IF NOT EXISTS biblioteca_id INTEGER REFERENCES bibliotecas_formatacao_canonica(id_biblioteca_formatacao_canonica);

-- Renomear coluna id_versao_trabalho para id_relatorio em capitulos_documento
ALTER TABLE capitulos_documento 
RENAME COLUMN id_versao_trabalho TO id_relatorio;

-- Renomear coluna id_versao_trabalho para id_relatorio em revisoes
ALTER TABLE revisoes 
RENAME COLUMN id_versao_trabalho TO id_relatorio;

-- Renomear coluna id_versao_trabalho para id_relatorio em envios_conteudo
ALTER TABLE envios_conteudo 
RENAME COLUMN id_versao_trabalho TO id_relatorio;

-- Renomear coluna id_versao_trabalho para id_relatorio em bloqueios
ALTER TABLE bloqueios 
RENAME COLUMN id_versao_trabalho TO id_relatorio;

-- Adicionar colunas modelo_id, biblioteca_id e status_id em relatorios_finalizados
ALTER TABLE relatorios_finalizados 
ADD COLUMN IF NOT EXISTS modelo_id INTEGER REFERENCES modelos_relatorio(id_modelo_relatorio);

ALTER TABLE relatorios_finalizados 
ADD COLUMN IF NOT EXISTS biblioteca_id INTEGER REFERENCES bibliotecas_formatacao_canonica(id_biblioteca_formatacao_canonica);

ALTER TABLE relatorios_finalizados 
ADD COLUMN IF NOT EXISTS status_id INTEGER REFERENCES dom_status_relatorios(id);
