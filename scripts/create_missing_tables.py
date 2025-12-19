import os
import psycopg

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'captar')
DB_USER = os.getenv('DB_USER', 'captar')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'captar')
DB_SCHEMA = os.getenv('DB_SCHEMA', 'captar')

dsn = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

with psycopg.connect(dsn) as conn:
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"')
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Eleitores" (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(255),
            cpf VARCHAR(14),
            celular VARCHAR(20),
            bairro VARCHAR(120),
            zona_eleitoral VARCHAR(120),
            criado_por INT,
            "IdTenant" INT,
            "DataCadastro" TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Ativistas" (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(255),
            tipo_apoio VARCHAR(120),
            criado_por INT,
            "IdTenant" INT,
            "DataCadastro" TIMESTAMP DEFAULT NOW()
        )
    """)
    print('Tables ensured')
