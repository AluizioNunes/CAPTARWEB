CREATE TABLE IF NOT EXISTS captar."EvolutionAPI" (
    "IdEvolutionAPI" SERIAL PRIMARY KEY,
    "Nome" VARCHAR(150) NOT NULL,
    "InstanceName" VARCHAR(150) NOT NULL,
    "ApiKey" TEXT NOT NULL,
    "BaseUrl" TEXT NOT NULL,
    "Ativo" BOOLEAN DEFAULT TRUE,
    "Padrao" BOOLEAN DEFAULT FALSE,
    "CriadoEm" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "AtualizadoEm" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM captar."EvolutionAPI") THEN
        INSERT INTO captar."EvolutionAPI" ("Nome","InstanceName","ApiKey","BaseUrl","Ativo","Padrao")
        VALUES ('WC','WC','CHANGE_ME','http://evolution_api:4000',TRUE,TRUE);
    END IF;
END $$;
