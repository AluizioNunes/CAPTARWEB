import os
from dotenv import load_dotenv
import psycopg

def main():
    load_dotenv()
    db_host = os.getenv('DB_HOST', 'postgres')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'captar')
    db_user = os.getenv('DB_USER', 'captar')
    db_password = os.getenv('DB_PASSWORD', 'captar')
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')

    with open(schema_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    candidates = [db_host, 'localhost', '127.0.0.1']
    conn = None
    last_err = None
    for host in candidates:
        try:
            conn = psycopg.connect(host=host, port=db_port, dbname=db_name, user=db_user, password=db_password)
            break
        except Exception as e:
            last_err = e
            continue
    if conn is None:
        raise last_err
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        print('Schema executed successfully')
    finally:
        conn.close()

if __name__ == '__main__':
    main()