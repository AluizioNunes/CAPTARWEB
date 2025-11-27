import os
import psycopg
from dotenv import load_dotenv

DB_HOST = os.getenv('DB_HOST', 'postgres')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'captar')
DB_USER = os.getenv('DB_USER', 'captar')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'captar')
DB_SCHEMA = os.getenv('DB_SCHEMA', 'captar')

def try_connect():
    last_err = None
    for host in [DB_HOST, 'localhost', '127.0.0.1']:
        try:
            conn = psycopg.connect(host=host, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD)
            return conn
        except Exception as e:
            last_err = e
            continue
    raise last_err

def main():
    load_dotenv()
    conn = try_connect()
    try:
        cur = conn.cursor()
        # Check current length
        cur.execute(
            """
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = 'Usuarios' AND column_name = 'Celular'
            """,
            (DB_SCHEMA,)
        )
        row = cur.fetchone()
        current = row[0] if row else None
        print('Current length:', current)
        if current is None:
            print('Coluna "Celular" não encontrada em captar."Usuarios"')
            return
        if current >= 15:
            print('Nada a fazer: comprimento atual =', current)
            return
        cur.execute(f'ALTER TABLE "{DB_SCHEMA}"."Usuarios" ALTER COLUMN "Celular" TYPE VARCHAR(15)')
        conn.commit()
        print('Alterado: captar."Usuarios"."Celular" -> VARCHAR(15)')
    finally:
        conn.close()

if __name__ == '__main__':
    main()