import os
from dotenv import load_dotenv
import psycopg

def main():
    load_dotenv()
    db_name = os.getenv('DB_NAME', 'captar')
    db_user = os.getenv('DB_USER', 'captar')
    db_password = os.getenv('DB_PASSWORD', 'captar')
    
    conn = psycopg.connect(host='localhost', port='5440', dbname=db_name, user=db_user, password=db_password)
    cur = conn.cursor()
    
    print("Schemas:")
    cur.execute("SELECT schema_name FROM information_schema.schemata")
    for row in cur.fetchall():
        print(row)
        
    print("\nTables in 'captar':")
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'captar'")
    tables = cur.fetchall()
    for row in tables:
        print(row)

    conn.close()

if __name__ == '__main__':
    main()
