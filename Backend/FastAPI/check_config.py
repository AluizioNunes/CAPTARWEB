import psycopg
import os

try:
    conn = psycopg.connect('postgresql://captar:captar@localhost:5440/captar')
    cur = conn.cursor()
    cur.execute('SELECT id, name, number, "connectionStatus" FROM "EvolutionAPI"."Instance" ORDER BY name ASC')
    rows = cur.fetchall()
    print("EvolutionAPI.Instance rows:", rows)
    conn.close()
except Exception as e:
    print(e)
