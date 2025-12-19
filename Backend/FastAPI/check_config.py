import psycopg
import os

try:
    conn = psycopg.connect('postgresql://captar:captar@localhost:5440/captar')
    cur = conn.cursor()
    cur.execute("SELECT chave, valor FROM captar.configuracoes WHERE chave IN ('WHATSAPP_INSTANCE_NAME', 'WHATSAPP_API_KEY', 'WHATSAPP_API_URL')")
    rows = cur.fetchall()
    print("Configs found:", rows)
    conn.close()
except Exception as e:
    print(e)
