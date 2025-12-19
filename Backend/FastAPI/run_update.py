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
    
    # Force localhost if running from host machine and not inside container
    # But checking if we can connect to 'postgres' usually fails on host unless mapped in hosts file
    # We should try localhost first if we are on the host machine
    
    candidates = ['localhost', '127.0.0.1', db_host]
    
    # Adjust port if running on host (docker-compose maps 5440:5432)
    # The default env might say 5432, but on host it is 5440
    # Let's try 5440 for localhost
    
    sql_path = os.path.join(os.path.dirname(__file__), 'update_evolution_config.sql')

    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    conn = None
    last_err = None
    
    # Try localhost:5440 first (typical dev setup)
    try:
        print(f"Trying localhost:5440...")
        conn = psycopg.connect(host='localhost', port='5440', dbname=db_name, user=db_user, password=db_password)
    except Exception as e:
        print(f"Failed localhost:5440: {e}")
        # Try env vars
        try:
             print(f"Trying {db_host}:{db_port}...")
             conn = psycopg.connect(host=db_host, port=db_port, dbname=db_name, user=db_user, password=db_password)
        except Exception as e2:
             print(f"Failed {db_host}:{db_port}: {e2}")
             last_err = e2

    if conn is None:
        print("Could not connect to database.")
        raise last_err

    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        print('Configuration updated successfully')
    finally:
        conn.close()

if __name__ == '__main__':
    main()
