-- Executa no banco definido por POSTGRES_DB (captar)
-- Remove o schema public e cria schemas dedicados

CREATE SCHEMA IF NOT EXISTS "captar";
CREATE SCHEMA IF NOT EXISTS "EvolutionAPI";
CREATE SCHEMA IF NOT EXISTS "N8N";

DROP SCHEMA IF EXISTS public CASCADE;

GRANT ALL ON SCHEMA "captar" TO captar;
GRANT ALL ON SCHEMA "EvolutionAPI" TO captar;
GRANT ALL ON SCHEMA "N8N" TO captar;
