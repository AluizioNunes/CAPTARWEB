import psycopg
import sys

candidates = [
    'postgresql://captar:captar@localhost:5432/captar',
    'postgresql://captar:captar@localhost:5432/postgres',
    'postgresql://postgres:postgres@localhost:5432/captar',
    'postgresql://postgres:postgres@localhost:5432/postgres',
]

def main():
    conn = None
    for dsn in candidates:
        try:
            conn = psycopg.connect(dsn, connect_timeout=5)
            print(f"Connected: {dsn}")
            break
        except Exception as e:
            print(f"Failed {dsn}: {e}")
    if conn is None:
        print("ERROR: Could not connect to any candidate DSN")
        sys.exit(1)

    conn.autocommit = True
    cur = conn.cursor()
    cur.execute('CREATE SCHEMA IF NOT EXISTS "captar"')
    cur.execute(
        'CREATE TABLE IF NOT EXISTS "captar"."Tenant" ('
        '"IdTenant" SERIAL PRIMARY KEY,'
        '"Nome" VARCHAR(120) NOT NULL,'
        '"Slug" VARCHAR(80) NOT NULL UNIQUE,'
        '"Status" VARCHAR(40),'
        '"Plano" VARCHAR(40),'
        '"DataCadastro" TIMESTAMP DEFAULT NOW(),'
        '"DataUpdate" TIMESTAMP)'
    )
    cur.execute(
        'INSERT INTO "captar"."Tenant" ("Nome","Slug","Status","Plano") '
        'VALUES (%s,%s,%s,%s) ON CONFLICT ("Slug") DO NOTHING',
        ('CAPTAR','captar','ATIVO','PADRAO')
    )
    cur.execute(
        'CREATE TABLE IF NOT EXISTS "captar"."Perfil" ('
        '"IdPerfil" SERIAL PRIMARY KEY,'
        '"Perfil" VARCHAR(120),'
        '"Descricao" VARCHAR(255),'
        '"IdTenant" INT)'
    )
    cur.execute(
        'CREATE TABLE IF NOT EXISTS "captar"."Funcoes" ('
        '"IdFuncao" SERIAL PRIMARY KEY,'
        '"Funcao" VARCHAR(120),'
        '"Descricao" VARCHAR(255),'
        '"IdTenant" INT)'
    )
    roles = ['ADMINISTRADOR', 'COORDENADOR', 'SUPERVISOR', 'ATIVISTA']
    for r in roles:
        cur.execute(
            'INSERT INTO "captar"."Perfil" ("Perfil","Descricao","IdTenant") '
            'SELECT %s,%s,t."IdTenant" FROM "captar"."Tenant" t '
            'WHERE t."Slug"=%s AND NOT EXISTS ('
            'SELECT 1 FROM "captar"."Perfil" x '
            'WHERE UPPER(TRIM(x."Perfil")) = UPPER(TRIM(%s)) AND x."IdTenant" = t."IdTenant")',
            (r, r, 'captar', r)
        )
    for r in roles:
        cur.execute(
            'INSERT INTO "captar"."Funcoes" ("Funcao","Descricao","IdTenant") '
            'SELECT %s,%s,t."IdTenant" FROM "captar"."Tenant" t '
            'WHERE t."Slug"=%s AND NOT EXISTS ('
            'SELECT 1 FROM "captar"."Funcoes" x '
            'WHERE UPPER(TRIM(x."Funcao")) = UPPER(TRIM(%s)) AND x."IdTenant" = t."IdTenant")',
            (r, r, 'captar', r)
        )
    cur.execute('SELECT "Perfil" FROM "captar"."Perfil" ORDER BY 1')
    print('Perfis:', [row[0] for row in cur.fetchall()])
    cur.execute('SELECT "Funcao" FROM "captar"."Funcoes" ORDER BY 1')
    print('Funcoes:', [row[0] for row in cur.fetchall()])
    cur.close()
    conn.close()

if __name__ == '__main__':
    main()

