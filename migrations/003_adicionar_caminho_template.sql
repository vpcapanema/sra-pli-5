-- Migração para adicionar coluna caminho_template em relatorios_producao
-- Esta coluna armazena o caminho do arquivo DOCX template usado como base

ALTER TABLE relatorios_producao
ADD COLUMN IF NOT EXISTS caminho_template VARCHAR(500);
