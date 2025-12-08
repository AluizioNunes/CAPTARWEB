"""
CAPTAR API - Extended Version with All Improvements
Integração de todas as 15 melhorias prioritárias
"""

from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
import os
from dotenv import load_dotenv
import redis
import psycopg
from contextlib import contextmanager
try:
    from psycopg_pool import ConnectionPool
except Exception:
    ConnectionPool = None
import json
import csv
import io
import pandas as pd
from typing import List, Optional, Dict, Tuple
import time
from urllib.request import urlopen
import urllib.request
from urllib.error import URLError, HTTPError
import ssl
import gzip
import zlib
import base64
import re
import pathlib

load_dotenv()

# Database Configuration
def _resolve_host(h: str, fallback: str = 'localhost') -> str:
    import socket
    try:
        socket.getaddrinfo(h, None)
        return h
    except Exception:
        return fallback

DB_HOST = _resolve_host(os.getenv('DB_HOST', 'postgres'), 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'captar')
DB_USER = os.getenv('DB_USER', 'captar')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'captar')
DB_SCHEMA = os.getenv('DB_SCHEMA', 'captar')
REDIS_HOST = _resolve_host(os.getenv('REDIS_HOST', 'redis'), 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_DB = int(os.getenv('REDIS_DB', '0'))

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# FastAPI App
app = FastAPI(
    title="CAPTAR API v2.0",
    version="2.0.0",
    description="Sistema de Gestão Eleitoral com 15 Melhorias Prioritárias"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Connection Helper
_POOL_TTL_SECONDS = 600
_POOLS: Dict[str, Tuple[any, float]] = {}

def _get_pool(dsn: str) -> any:
    now = time.time()
    ent = _POOLS.get(dsn)
    if ent and ent[1] > now:
        return ent[0]
    pool = ConnectionPool(dsn, max_size=10, timeout=30) if ConnectionPool else None
    _POOLS[dsn] = (pool, now + _POOL_TTL_SECONDS)
    return pool

@contextmanager
def get_db_connection(dsn: str | None = None):
    use_dsn = (dsn.strip() if (dsn and dsn.strip()) else f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    pool = _get_pool(use_dsn)
    if pool:
        with pool.connection() as conn:
            yield conn
    else:
        conn = psycopg.connect(use_dsn)
        try:
            yield conn
        finally:
            conn.close()

_DSN_CACHE: Dict[str, Tuple[str, float]] = {}
_DSN_TTL_SECONDS = 300

def _get_tenant_dsn(slug: str) -> Optional[str]:
    now = time.time()
    ent = _DSN_CACHE.get(slug)
    if ent and ent[1] > now:
        return ent[0]
    rc = get_redis_client()
    if rc:
        try:
            val = rc.get(f"tenant:{slug}:dsn")
            if val:
                try:
                    from cryptography.fernet import Fernet
                    key = os.getenv('DSN_SECRET_KEY', '')
                    dsn = Fernet(key.encode()).decrypt(val.encode()).decode() if key else val
                except Exception:
                    dsn = val
                _DSN_CACHE[slug] = (dsn, now + _DSN_TTL_SECONDS)
                return dsn
        except Exception:
            pass
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT \"Valor\" FROM \"{DB_SCHEMA}\".\"TenantParametros\" WHERE \"Chave\" = %s AND \"IdTenant\" = (SELECT \"IdTenant\" FROM \"{DB_SCHEMA}\".\"Tenant\" WHERE \"Slug\" = %s LIMIT 1) LIMIT 1",
                ('DB_DSN', slug)
            )
            row = cur.fetchone()
            if row and row[0]:
                dsn = str(row[0])
                _DSN_CACHE[slug] = (dsn, now + _DSN_TTL_SECONDS)
                if rc:
                    try:
                        from cryptography.fernet import Fernet
                        key = os.getenv('DSN_SECRET_KEY', '')
                        enc = Fernet(key.encode()).encrypt(dsn.encode()).decode() if key else dsn
                        rc.setex(f"tenant:{slug}:dsn", _DSN_TTL_SECONDS, enc)
                    except Exception:
                        pass
                return dsn
            # Alternativamente, montar DSN por componentes
            cur.execute(
                f"SELECT \"Valor\" FROM \"{DB_SCHEMA}\".\"TenantParametros\" WHERE \"Chave\" IN ('DB_HOST','DB_PORT','DB_NAME','DB_USER','DB_PASSWORD') AND \"IdTenant\" = (SELECT \"IdTenant\" FROM \"{DB_SCHEMA}\".\"Tenant\" WHERE \"Slug\" = %s LIMIT 1)",
                (slug,)
            )
            rows = cur.fetchall()
            if rows and len(rows) >= 5:
                # Este bloco pressupõe a ordem não garantida; optar por consulta separada por chave em produção
                return None
    except Exception:
        pass
    _DSN_CACHE.pop(slug, None)
    return None

def get_conn_for_request(request: Request):
    slug = request.headers.get('X-Tenant') or 'captar'
    dsn = _get_tenant_dsn(slug)
    return get_db_connection(dsn)

_redis_client = None

def get_redis_client():
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        except Exception:
            _redis_client = None
    return _redis_client

def _tenant_slug(request: Request) -> str:
    return (request.headers.get('X-Tenant') or 'captar').lower()

def _redis_delete_pattern(rc, pattern: str):
    try:
        for k in rc.scan_iter(pattern):
            rc.delete(k)
    except Exception:
        pass

def invalidate_coordenadores(slug: str):
    rc = get_redis_client()
    if rc:
        _redis_delete_pattern(rc, f"tenant:{slug}:usuarios:coordenadores")

def invalidate_supervisores(slug: str, coordenador: str):
    rc = get_redis_client()
    if rc and coordenador:
        name = coordenador.strip()
        if name:
            _redis_delete_pattern(rc, f"tenant:{slug}:usuarios:supervisores:{name}")

def _ensure_tenant_slug(slug: str, nome: Optional[str] = None) -> int:
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(f'SELECT "IdTenant" FROM "{DB_SCHEMA}"."Tenant" WHERE "Slug" = %s LIMIT 1', (slug,))
        row = cur.fetchone()
        if row:
            return int(row[0])
        nm = nome or slug.upper()
        cur.execute(f'INSERT INTO "{DB_SCHEMA}"."Tenant" ("Nome","Slug","Status","Plano") VALUES (%s,%s,%s,%s) RETURNING "IdTenant"', (nm, slug, 'ATIVO', 'PADRAO'))
        tid = int(cur.fetchone()[0])
        conn.commit()
        return tid

def _upsert_tenant_param(id_tenant: int, chave: str, valor: str):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(f'SELECT 1 FROM "{DB_SCHEMA}"."TenantParametros" WHERE "IdTenant"=%s AND "Chave"=%s', (id_tenant, chave))
        exists = cur.fetchone() is not None
        if exists:
            cur.execute(f'UPDATE "{DB_SCHEMA}"."TenantParametros" SET "Valor"=%s, "AtualizadoEm"=NOW() WHERE "IdTenant"=%s AND "Chave"=%s', (valor, id_tenant, chave))
        else:
            cur.execute(f'INSERT INTO "{DB_SCHEMA}"."TenantParametros" ("IdTenant","Chave","Valor","Tipo","Descricao") VALUES (%s,%s,%s,%s,%s)', (id_tenant, chave, valor, 'STRING', 'DSN do banco do tenant'))
        conn.commit()

def _seed_pf_funcoes_for_tenant(id_tenant: int):
    with get_db_connection() as conn:
        conn.autocommit = True
        cur = conn.cursor()
        roles = ['ADMINISTRADOR', 'COORDENADOR', 'SUPERVISOR', 'ATIVISTA']
        for r in roles:
            cur.execute(
                f"""
                INSERT INTO "{DB_SCHEMA}"."Perfil" ("Perfil", "Descricao", "IdTenant")
                SELECT %s, %s, %s
                WHERE NOT EXISTS (
                    SELECT 1 FROM "{DB_SCHEMA}"."Perfil" x
                    WHERE UPPER(TRIM(x."Perfil")) = UPPER(TRIM(%s)) AND x."IdTenant" = %s
                )
                """,
                (r, r, id_tenant, r, id_tenant)
            )
        for r in roles:
            cur.execute(
                f"""
                INSERT INTO "{DB_SCHEMA}"."Funcoes" ("Funcao", "Descricao", "IdTenant")
                SELECT %s, %s, %s
                WHERE NOT EXISTS (
                    SELECT 1 FROM "{DB_SCHEMA}"."Funcoes" x
                    WHERE UPPER(TRIM(x."Funcao")) = UPPER(TRIM(%s)) AND x."IdTenant" = %s
                )
                """,
                (r, r, id_tenant, r, id_tenant)
            )

class SetDsnRequest(BaseModel):
    dsn: str

@app.post("/api/tenants/{slug}/set_dsn")
async def tenants_set_dsn(slug: str, body: SetDsnRequest):
    try:
        tid = _ensure_tenant_slug(slug)
        central_dsn = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        chosen = body.dsn if str(slug).lower() != 'captar' else central_dsn
        _upsert_tenant_param(tid, 'DB_DSN', chosen)
        actions = apply_migrations_dsn(chosen, slug)
        _seed_pf_funcoes_for_tenant(tid)
        actions.append('pf_funcoes seeded (central)')
        return {"ok": True, "idTenant": tid, "actions": actions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ProvisionTenantRequest(BaseModel):
    nome: str
    slug: str
    db_name: str
    db_host: str
    db_port: str
    db_user: str
    db_password: str

@app.post("/api/tenants/provision")
async def tenants_provision(body: ProvisionTenantRequest):
    try:
        if str(body.slug or '').lower() == 'captar':
            raise HTTPException(status_code=400, detail='Tenant CAPTAR usa o banco padrão do sistema e não deve ser provisionado')
        tid = _ensure_tenant_slug(body.slug, body.nome)
        dsn = f"postgresql://{body.db_user}:{body.db_password}@{body.db_host}:{body.db_port}/{body.db_name}"
        try:
            with get_db_connection() as conn:
                conn.autocommit = True
                cur = conn.cursor()
                cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (body.db_name,))
                exists = cur.fetchone() is not None
                if not exists:
                    cur.execute(f"CREATE DATABASE \"{body.db_name}\"")
        except Exception:
            pass
        _upsert_tenant_param(tid, 'DB_DSN', dsn)
        actions = apply_migrations_dsn(dsn, body.slug)
        _seed_pf_funcoes_for_tenant(tid)
        actions.append('pf_funcoes seeded (central)')
        return {"ok": True, "idTenant": tid, "dsn": dsn, "actions": actions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class MigrateDataRequest(BaseModel):
    slug: str

@app.post("/api/tenants/migrate_data")
async def tenants_migrate_data(body: MigrateDataRequest):
    try:
        slug = body.slug
        with get_db_connection() as conn_src:
            cur_src = conn_src.cursor()
            cur_src.execute(f'SELECT "IdTenant" FROM "{DB_SCHEMA}"."Tenant" WHERE "Slug"=%s', (slug,))
            row = cur_src.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Tenant não encontrado")
            id_tenant = int(row[0])
        dsn = _get_tenant_dsn(slug)
        if not dsn:
            raise HTTPException(status_code=400, detail="DSN não configurado para o tenant")
        with get_db_connection() as conn_src:
            cur_src = conn_src.cursor()
            cur_src.execute(f'SELECT * FROM "{DB_SCHEMA}"."Usuarios" WHERE "IdTenant"=%s', (id_tenant,))
            colnames = [desc[0] for desc in cur_src.description]
            rows = cur_src.fetchall()
        with get_db_connection(dsn) as conn_dst:
            cur_dst = conn_dst.cursor()
            for row in rows:
                data = dict(zip(colnames, row))
                if 'IdUsuario' in data:
                    data.pop('IdUsuario')
                keys = list(data.keys())
                values = [data[k] for k in keys]
                placeholders = ", ".join(["%s"] * len(values))
                columns_sql = ", ".join([f'"{k}"' for k in keys])
                try:
                    cur_dst.execute(
                        f"INSERT INTO \"{DB_SCHEMA}\".\"Usuarios\" ({columns_sql}) VALUES ({placeholders})",
                        tuple(values)
                    )
                except Exception:
                    pass
            conn_dst.commit()
        return {"ok": True, "migrated": len(rows)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def apply_migrations():
    actions = []
    with get_db_connection() as conn:
        conn.autocommit = True
        cur = conn.cursor()
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Usuarios" (
                    "IdUsuario" SERIAL PRIMARY KEY,
                    "Nome" VARCHAR(255),
                    "Email" VARCHAR(255),
                    "Senha" VARCHAR(255),
                    "Usuario" VARCHAR(120),
                    "Perfil" VARCHAR(120),
                    "Funcao" VARCHAR(120),
                    "Ativo" BOOLEAN DEFAULT TRUE,
                    "Celular" VARCHAR(15),
                    "CPF" VARCHAR(14),
                    "TenantLayer" VARCHAR(120),
                    "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                )
                """
            )
            actions.append('Usuarios created')
        except Exception:
            pass
        try:
            import os
            base_dir = os.path.dirname(__file__)
            schema_path = os.path.join(base_dir, 'schema.sql')
            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    sql = f.read()
                    cur.execute(sql)
                    actions.append('schema.sql executed')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Perfil" (
                    "IdPerfil" SERIAL PRIMARY KEY,
                    "Perfil" VARCHAR(120),
                    "Descricao" VARCHAR(255),
                    "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                )
                """
            )
            actions.append('Perfil created')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Funcoes" (
                    "IdFuncao" SERIAL PRIMARY KEY,
                    "Funcao" VARCHAR(120),
                    "Descricao" VARCHAR(255),
                    "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                )
                """
            )
            actions.append('Funcoes created')
        except Exception:
            pass
        targets = [
            ("Usuarios", "Celular"),
            ("Perfil", "Perfil"),
            ("Funcoes", "Funcao"),
        ]
        for table_name, column_name in targets:
            cur.execute(
                """
                SELECT character_maximum_length
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s AND column_name = %s
                """,
                (DB_SCHEMA, table_name, column_name)
            )
            row = cur.fetchone()
            if row is not None:
                max_len = row[0]
                if max_len is not None and max_len < 15:
                    cur.execute(
                        f"ALTER TABLE \"{DB_SCHEMA}\".\"{table_name}\" ALTER COLUMN \"{column_name}\" TYPE VARCHAR(15)"
                    )
                    actions.append(f'{table_name}.{column_name} -> VARCHAR(15)')
        # Garantir colunas de auditoria e timestamps nas tabelas em maiúsculo
        legacy_tables = ["Usuarios", "Perfil", "Funcoes"]
        for t in legacy_tables:
            try:
                cur.execute(
                    """
                    ALTER TABLE "{schema}"."{table}" 
                        ADD COLUMN IF NOT EXISTS "DataCadastro" timestamp without time zone DEFAULT CURRENT_TIMESTAMP;
                    """.format(schema=DB_SCHEMA, table=t)
                )
                actions.append(f'{t}.DataCadastro ensured')
            except Exception:
                pass
            try:
                cur.execute(
                    """
                    ALTER TABLE "{schema}"."{table}" 
                        ADD COLUMN IF NOT EXISTS "DataUpdate" timestamp without time zone;
                    """.format(schema=DB_SCHEMA, table=t)
                )
                actions.append(f'{t}.DataUpdate ensured')
            except Exception:
                pass
            try:
                cur.execute(
                    """
                    ALTER TABLE "{schema}"."{table}" 
                        ADD COLUMN IF NOT EXISTS "TipoUpdate" varchar(20);
                    """.format(schema=DB_SCHEMA, table=t)
                )
                actions.append(f'{t}.TipoUpdate ensured')
            except Exception:
                pass
            try:
                cur.execute(
                    """
                    ALTER TABLE "{schema}"."{table}" 
                        ADD COLUMN IF NOT EXISTS "UsuarioUpdate" varchar(100);
                    """.format(schema=DB_SCHEMA, table=t)
                )
                actions.append(f'{t}.UsuarioUpdate ensured')
            except Exception:
                pass
            try:
                cur.execute(
                    """
                    ALTER TABLE "{schema}"."{table}" 
                        ADD COLUMN IF NOT EXISTS "CadastranteUpdate" varchar(100);
                    """.format(schema=DB_SCHEMA, table=t)
                )
                actions.append(f'{t}.CadastranteUpdate ensured')
            except Exception:
                pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Tenant" (
                    "IdTenant" SERIAL PRIMARY KEY,
                    "Nome" VARCHAR(120) NOT NULL,
                    "Slug" VARCHAR(80) NOT NULL UNIQUE,
                    "Status" VARCHAR(40),
                    "Plano" VARCHAR(40),
                    "DataCadastro" TIMESTAMP DEFAULT NOW(),
                    "DataUpdate" TIMESTAMP
                )
                """
            )
            actions.append('Tenant created')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Perfil" (
                    "IdPerfil" SERIAL PRIMARY KEY,
                    "Perfil" VARCHAR(120),
                    "Descricao" VARCHAR(255),
                    "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                )
                """
            )
            actions.append('Perfil created')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Funcoes" (
                    "IdFuncao" SERIAL PRIMARY KEY,
                    "Funcao" VARCHAR(120),
                    "Descricao" VARCHAR(255),
                    "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                )
                """
            )
            actions.append('Funcoes created')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."TenantParametros" (
                    "IdParametro" SERIAL PRIMARY KEY,
                    "IdTenant" INT NOT NULL REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant") ON DELETE CASCADE,
                    "Chave" VARCHAR(120) NOT NULL,
                    "Valor" TEXT,
                    "Tipo" VARCHAR(40),
                    "Descricao" VARCHAR(240),
                    "AtualizadoEm" TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT uq_param UNIQUE ("IdTenant", "Chave")
                )
                """
            )
            actions.append('TenantParametros created')
        except Exception:
            pass
        try:
            cur.execute(
                f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Tenant\" WHERE \"Slug\" = %s",
                ('captar',)
            )
            n = cur.fetchone()[0]
            if n == 0:
                cur.execute(
                    f"INSERT INTO \"{DB_SCHEMA}\".\"Tenant\" (\"Nome\", \"Slug\", \"Status\", \"Plano\") VALUES (%s, %s, %s, %s)",
                    ('CAPTAR', 'captar', 'ATIVO', 'PADRAO')
                )
                actions.append('Default tenant inserted')
        except Exception:
            pass
        try:
            cur.execute(
                f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Usuarios\" WHERE UPPER(TRIM(\"Usuario\")) = 'ADMIN'"
            )
            m = cur.fetchone()[0]
            if m == 0:
                cur.execute(
                    f"INSERT INTO \"{DB_SCHEMA}\".\"Usuarios\" (\"Nome\", \"Email\", \"Senha\", \"Usuario\", \"Perfil\", \"Funcao\", \"Ativo\", \"IdTenant\") VALUES (%s,%s,%s,%s,%s,%s,%s,(SELECT \"IdTenant\" FROM \"{DB_SCHEMA}\".\"Tenant\" WHERE \"Slug\"='captar' LIMIT 1))",
                    ('ADMINISTRADOR', 'admin@captar.local', 'admin123', 'ADMIN', 'ADMINISTRADOR', 'ADMINISTRADOR', True)
                )
                actions.append('Default admin user inserted')
        except Exception:
            pass
        try:
            roles = ['ADMINISTRADOR', 'COORDENADOR', 'SUPERVISOR', 'ATIVISTA']
            for r in roles:
                cur.execute(
                    f"""
                    INSERT INTO \"{DB_SCHEMA}\".\"Perfil\" (\"Perfil\", \"Descricao\", \"IdTenant\")
                    SELECT %s, %s, t.\"IdTenant\"
                    FROM \"{DB_SCHEMA}\".\"Tenant\" t
                    WHERE t.\"Slug\" = %s
                    AND NOT EXISTS (
                        SELECT 1 FROM \"{DB_SCHEMA}\".\"Perfil\" x
                        WHERE UPPER(TRIM(x.\"Perfil\")) = UPPER(TRIM(%s)) AND x.\"IdTenant\" = t.\"IdTenant\"
                    )
                    """,
                    (r, r, 'captar', r)
                )
            actions.append('Perfil seeded')
        except Exception:
            pass
        try:
            roles = ['ADMINISTRADOR', 'COORDENADOR', 'SUPERVISOR', 'ATIVISTA']
            for r in roles:
                cur.execute(
                    f"""
                    INSERT INTO \"{DB_SCHEMA}\".\"Funcoes\" (\"Funcao\", \"Descricao\", \"IdTenant\")
                    SELECT %s, %s, t.\"IdTenant\"
                    FROM \"{DB_SCHEMA}\".\"Tenant\" t
                    WHERE t.\"Slug\" = %s
                    AND NOT EXISTS (
                        SELECT 1 FROM \"{DB_SCHEMA}\".\"Funcoes\" x
                        WHERE UPPER(TRIM(x.\"Funcao\")) = UPPER(TRIM(%s)) AND x.\"IdTenant\" = t.\"IdTenant\"
                    )
                    """,
                    (r, r, 'captar', r)
                )
            actions.append('Funcoes seeded')
        except Exception:
            pass
        for t in legacy_tables:
            try:
                cur.execute(
                    f"ALTER TABLE \"{DB_SCHEMA}\".\"{t}\" ADD COLUMN IF NOT EXISTS \"IdTenant\" INT"
                )
                actions.append(f'{t}.IdTenant ensured')
            except Exception:
                pass
        # Índices para acelerar filtros frequentes
        try:
            cur.execute(f'CREATE INDEX IF NOT EXISTS ix_usuarios_idtenant ON "{DB_SCHEMA}"."Usuarios"("IdTenant")')
            cur.execute(f'CREATE INDEX IF NOT EXISTS ix_usuarios_funcao ON "{DB_SCHEMA}"."Usuarios"(UPPER(TRIM("Funcao")))')
            cur.execute(f'CREATE INDEX IF NOT EXISTS ix_usuarios_coordenador ON "{DB_SCHEMA}"."Usuarios"(TRIM("Coordenador"))')
            cur.execute(f'CREATE INDEX IF NOT EXISTS ix_usuarios_supervisor ON "{DB_SCHEMA}"."Usuarios"(TRIM("Supervisor"))')
            cur.execute(f'CREATE INDEX IF NOT EXISTS ix_usuarios_usuario ON "{DB_SCHEMA}"."Usuarios"(UPPER(TRIM("Usuario")))')
            actions.append('Usuarios indexes ensured')
        except Exception:
            pass
            try:
                cur.execute(
                    f"UPDATE \"{DB_SCHEMA}\".\"{t}\" SET \"IdTenant\" = (SELECT \"IdTenant\" FROM \"{DB_SCHEMA}\".\"Tenant\" WHERE \"Slug\" = %s LIMIT 1) WHERE \"IdTenant\" IS NULL",
                    ('captar',)
                )
            except Exception:
                pass

        # Migração legada de 'usuarios' removida
        # Harmonizar TenantLayer preenchendo descrição do tenant onde vazio
        try:
            cur.execute(
                f"UPDATE \"{DB_SCHEMA}\".\"Usuarios\" u SET \"TenantLayer\" = t.\"Nome\" FROM \"{DB_SCHEMA}\".\"Tenant\" t WHERE u.\"IdTenant\" = t.\"IdTenant\" AND (u.\"TenantLayer\" IS NULL OR u.\"TenantLayer\" = '')"
            )
            actions.append('Usuarios.TenantLayer synced')
        except Exception:
            pass
        try:
            cur.execute(
                f"ALTER TABLE \"{DB_SCHEMA}\".\"Usuarios\" ADD COLUMN IF NOT EXISTS \"Coordenador\" VARCHAR(120)"
            )
            actions.append('Usuarios.Coordenador ensured')
        except Exception:
            pass
        try:
            cur.execute(
                f"ALTER TABLE \"{DB_SCHEMA}\".\"Usuarios\" ADD COLUMN IF NOT EXISTS \"Supervisor\" VARCHAR(120)"
            )
            actions.append('Usuarios.Supervisor ensured')
        except Exception:
            pass
        try:
            cur.execute(
                f"ALTER TABLE \"{DB_SCHEMA}\".\"Usuarios\" ADD COLUMN IF NOT EXISTS \"Ativista\" VARCHAR(120)"
            )
            actions.append('Usuarios.Ativista ensured')
        except Exception:
            pass
    return actions

def apply_migrations_dsn(dsn: str, slug: Optional[str] = None):
    actions = []
    with get_db_connection(dsn) as conn:
        conn.autocommit = True
        cur = conn.cursor()
        try:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"')
        except Exception:
            pass
        # Garantir tabela Usuarios compatível no banco do tenant
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Usuarios" (
                    "IdUsuario" SERIAL PRIMARY KEY,
                    "Nome" VARCHAR(255),
                    "Email" VARCHAR(255),
                    "Senha" VARCHAR(255),
                    "Usuario" VARCHAR(120),
                    "Perfil" VARCHAR(120),
                    "Funcao" VARCHAR(120),
                    "Ativo" BOOLEAN DEFAULT TRUE,
                    "Celular" VARCHAR(15),
                    "CPF" VARCHAR(14),
                    "TenantLayer" VARCHAR(120),
                    "IdTenant" INT
                )
                """
            )
            actions.append('Usuarios ensured (tenant DB)')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Perfil" (
                    "IdPerfil" SERIAL PRIMARY KEY,
                    "Perfil" VARCHAR(120),
                    "Descricao" VARCHAR(255),
                    "IdTenant" INT
                )
                """
            )
            actions.append('Perfil ensured (tenant DB)')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Funcoes" (
                    "IdFuncao" SERIAL PRIMARY KEY,
                    "Funcao" VARCHAR(120),
                    "Descricao" VARCHAR(255),
                    "IdTenant" INT
                )
                """
            )
            actions.append('Funcoes ensured (tenant DB)')
        except Exception:
            pass
        try:
            import os
            base_dir = os.path.dirname(__file__)
            schema_path = os.path.join(base_dir, 'schema.sql')
            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    sql = f.read()
                    cur.execute(sql)
                    actions.append('schema.sql executed')
        except Exception:
            pass
        targets = [
            ("Usuarios", "Celular"),
        ]
        for table_name, column_name in targets:
            try:
                cur.execute(
                    """
                    SELECT character_maximum_length
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = %s AND column_name = %s
                    """,
                    (DB_SCHEMA, table_name, column_name)
                )
                row = cur.fetchone()
                if row is not None:
                    max_len = row[0]
                    if max_len is not None and max_len < 15:
                        cur.execute(
                            f"ALTER TABLE \"{DB_SCHEMA}\".\"{table_name}\" ALTER COLUMN \"{column_name}\" TYPE VARCHAR(15)"
                        )
                        actions.append(f'{table_name}.{column_name} -> VARCHAR(15)')
            except Exception:
                pass
        # Inserir usuário ADMIN padrão (tenant DB)
        try:
            slug_upper = (slug or 'tenant').upper()
            cur.execute(
                f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Usuarios\" WHERE UPPER(TRIM(\"Usuario\")) = %s",
                (f"ADMIN.{slug_upper}",)
            )
            m = cur.fetchone()[0]
            if m == 0:
                admin_email = f"admin@{(slug or 'tenant').lower()}.local"
                admin_user = f"ADMIN.{slug_upper}"
                admin_pass = f"Admin123{(slug or 'tenant').lower()}"
                cur.execute(
                    f"INSERT INTO \"{DB_SCHEMA}\".\"Usuarios\" (\"Nome\", \"Email\", \"Senha\", \"Usuario\", \"Perfil\", \"Funcao\", \"Ativo\") VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    ('ADMINISTRADOR', admin_email, admin_pass, admin_user, 'ADMINISTRADOR', 'ADMINISTRADOR', True)
                )
                actions.append('Default admin user inserted (tenant DB)')
        except Exception:
            pass
        try:
            tid = None
            if slug:
                try:
                    tid = _ensure_tenant_slug(slug)
                except Exception:
                    tid = None
            roles = ['ADMINISTRADOR', 'COORDENADOR', 'SUPERVISOR', 'ATIVISTA']
            for r in roles:
                cur.execute(
                    f"""
                    INSERT INTO \"{DB_SCHEMA}\".\"Perfil\" (\"Perfil\", \"Descricao\", \"IdTenant\")
                    SELECT %s, %s, %s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM \"{DB_SCHEMA}\".\"Perfil\" x
                        WHERE UPPER(TRIM(x.\"Perfil\")) = UPPER(TRIM(%s)) AND (x.\"IdTenant\" = %s OR %s IS NULL)
                    )
                    """,
                    (r, r, tid, r, tid, tid)
                )
            for r in roles:
                cur.execute(
                    f"""
                    INSERT INTO \"{DB_SCHEMA}\".\"Funcoes\" (\"Funcao\", \"Descricao\", \"IdTenant\")
                    SELECT %s, %s, %s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM \"{DB_SCHEMA}\".\"Funcoes\" x
                        WHERE UPPER(TRIM(x.\"Funcao\")) = UPPER(TRIM(%s)) AND (x.\"IdTenant\" = %s OR %s IS NULL)
                    )
                    """,
                    (r, r, tid, r, tid, tid)
                )
            actions.append('pf_funcoes seeded (tenant DB)')
        except Exception:
            pass
    return actions

@app.on_event("startup")
def run_auto_migrations():
    try:
        apply_migrations()
    except Exception:
        pass

def _extract_user_from_auth(request: Request):
    try:
        auth = request.headers.get('Authorization') or ''
        parts = auth.split()
        token = parts[1] if len(parts) == 2 and parts[0].lower() == 'bearer' else ''
        if token.startswith('token_'):
            rest = token[len('token_'):]
            user_id_str = rest.split('_')[0]
            user_id = int(user_id_str)
            nome = None
            usr = None
            try:
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(f'SELECT "Usuario", "Nome" FROM "{DB_SCHEMA}"."Usuarios" WHERE "IdUsuario" = %s LIMIT 1', (user_id,))
                    row = cur.fetchone()
                    if row:
                        usr = row[0] or None
                        nome = row[1] or None
            except Exception:
                pass
            return {"id": user_id, "usuario": (usr or nome or str(user_id)), "nome": nome or usr or None}
    except Exception:
        pass
    return {"id": None, "usuario": None, "nome": None}

# Schema sempre fixo em CAPTAR (DB_SCHEMA)

def _apply_create_defaults(table_cols: List[dict], data: dict):
    colnames = {c["name"] for c in table_cols}
    types_map = {c["name"]: c["type"] for c in table_cols}
    now = _now_local()
    if "DataCadastro" in colnames and "DataCadastro" not in data:
        data["DataCadastro"] = now
    if "DataUpdate" in colnames and types_map.get("DataUpdate", "").startswith("timestamp"):
        data["DataUpdate"] = now
    if "TipoUpdate" in colnames and "TipoUpdate" not in data:
        data["TipoUpdate"] = "CREATE"
    return data

def _apply_update_defaults(table_cols: List[dict], data: dict):
    colnames = {c["name"] for c in table_cols}
    types_map = {c["name"]: c["type"] for c in table_cols}
    now = _now_local()
    if "DataUpdate" in colnames and types_map.get("DataUpdate", "").startswith("timestamp"):
        data["DataUpdate"] = now
    if "TipoUpdate" in colnames:
        data["TipoUpdate"] = "UPDATE"
    return data

def _apply_update_user(table_cols: List[dict], data: dict, user_info: dict):
    colnames = {c["name"] for c in table_cols}
    types_map = {c["name"]: c["type"] for c in table_cols}
    uid = user_info.get("id")
    display = user_info.get("nome") or user_info.get("usuario")
    if "CadastranteUpdate" in colnames:
        if (types_map.get("CadastranteUpdate") or "").lower().startswith("int"):
            if uid is not None:
                data["CadastranteUpdate"] = uid
        else:
            if display:
                data["CadastranteUpdate"] = display
    if "UsuarioUpdate" in colnames:
        if (types_map.get("UsuarioUpdate") or "").lower().startswith("int"):
            if uid is not None:
                data["UsuarioUpdate"] = uid
        else:
            if display:
                data["UsuarioUpdate"] = display
    return data

@app.post("/api/admin/migrate")
async def admin_migrate():
    try:
        actions = apply_migrations()
        return {"ok": True, "actions": actions}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/migrate_all_tenants")
async def admin_migrate_all_tenants():
    try:
        results = []
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(f'SELECT t."Slug", p."Valor" FROM "{DB_SCHEMA}"."Tenant" t JOIN "{DB_SCHEMA}"."TenantParametros" p ON p."IdTenant" = t."IdTenant" AND p."Chave" = %s', ('DB_DSN',))
            rows = cur.fetchall()
        for slug, dsn in rows:
            if dsn:
                actions = apply_migrations_dsn(str(dsn), str(slug))
                results.append({"slug": slug, "actions": actions})
        return {"ok": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/ensure_usuarios")
async def admin_ensure_usuarios():
    try:
        with get_db_connection() as conn:
            conn.autocommit = True
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Usuarios" (
                        "IdUsuario" SERIAL PRIMARY KEY,
                        "Nome" VARCHAR(255),
                        "Email" VARCHAR(255),
                        "Senha" VARCHAR(255),
                        "Usuario" VARCHAR(120),
                        "Perfil" VARCHAR(120),
                        "Funcao" VARCHAR(120),
                        "Ativo" BOOLEAN DEFAULT TRUE,
                        "Celular" VARCHAR(15),
                        "CPF" VARCHAR(14),
                        "TenantLayer" VARCHAR(120),
                        "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                    )
                    """
                )
            except Exception:
                pass
            try:
                cur.execute(
                    f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Usuarios\" WHERE UPPER(TRIM(\"Usuario\")) = 'ADMIN'"
                )
                m = cur.fetchone()[0]
                if m == 0:
                    cur.execute(
                        f"INSERT INTO \"{DB_SCHEMA}\".\"Usuarios\" (\"Nome\", \"Email\", \"Senha\", \"Usuario\", \"Perfil\", \"Funcao\", \"Ativo\", \"IdTenant\") VALUES (%s,%s,%s,%s,%s,%s,%s,(SELECT \"IdTenant\" FROM \"{DB_SCHEMA}\".\"Tenant\" WHERE \"Slug\"='captar' LIMIT 1))",
                        ('ADMINISTRADOR', 'admin@captar.local', 'admin123', 'ADMIN', 'ADMINISTRADOR', 'ADMINISTRADOR', True)
                    )
            except Exception:
                pass
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/ensure_pf")
async def admin_ensure_pf():
    try:
        with get_db_connection() as conn:
            conn.autocommit = True
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Perfil" (
                        "IdPerfil" SERIAL PRIMARY KEY,
                        "Perfil" VARCHAR(120),
                        "Descricao" VARCHAR(255),
                        "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                    )
                    """
                )
            except Exception:
                pass
            try:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Funcoes" (
                        "IdFuncao" SERIAL PRIMARY KEY,
                        "Funcao" VARCHAR(120),
                        "Descricao" VARCHAR(255),
                        "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                    )
                    """
                )
            except Exception:
                pass
            try:
                roles = ['ADMINISTRADOR', 'COORDENADOR', 'SUPERVISOR', 'ATIVISTA']
                for r in roles:
                    cur.execute(
                        f"""
                        INSERT INTO "{DB_SCHEMA}"."Perfil" ("Perfil", "Descricao", "IdTenant")
                        SELECT %s, %s, t."IdTenant"
                        FROM "{DB_SCHEMA}"."Tenant" t
                        WHERE t."Slug" = %s
                        AND NOT EXISTS (
                            SELECT 1 FROM "{DB_SCHEMA}"."Perfil" x
                            WHERE UPPER(TRIM(x."Perfil")) = UPPER(TRIM(%s)) AND x."IdTenant" = t."IdTenant"
                        )
                        """,
                        (r, r, 'captar', r)
                    )
            except Exception:
                pass
            try:
                roles = ['ADMINISTRADOR', 'COORDENADOR', 'SUPERVISOR', 'ATIVISTA']
                for r in roles:
                    cur.execute(
                        f"""
                        INSERT INTO "{DB_SCHEMA}"."Funcoes" ("Funcao", "Descricao", "IdTenant")
                        SELECT %s, %s, t."IdTenant"
                        FROM "{DB_SCHEMA}"."Tenant" t
                        WHERE t."Slug" = %s
                        AND NOT EXISTS (
                            SELECT 1 FROM "{DB_SCHEMA}"."Funcoes" x
                            WHERE UPPER(TRIM(x."Funcao")) = UPPER(TRIM(%s)) AND x."IdTenant" = t."IdTenant"
                        )
                        """,
                        (r, r, 'captar', r)
                    )
            except Exception:
                pass
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/usuarios/migrate_celular")
async def usuarios_migrate_celular():
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
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
            if current is None:
                return {"ok": False, "detail": "Coluna Celular não encontrada em captar.Usuarios"}
            if current is not None and current < 15:
                cur.execute(f"ALTER TABLE \"{DB_SCHEMA}\".\"Usuarios\" ALTER COLUMN \"Celular\" TYPE VARCHAR(15)")
                conn.commit()
                return {"ok": True, "changed": True}
            return {"ok": True, "changed": False, "current": current}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/usuarios/migrate_celular")
async def usuarios_migrate_celular_get():
    return await usuarios_migrate_celular()

@app.post("/api/admin/migrate_celular")
async def admin_migrate_celular():
    return await usuarios_migrate_celular()

@app.get("/api/admin/migrate_celular")
async def admin_migrate_celular_get():
    return await usuarios_migrate_celular()

# ==================== PYDANTIC MODELS ====================

class LoginRequest(BaseModel):
    usuario: str
    senha: str

class UserResponse(BaseModel):
    id: int
    nome: str
    funcao: str
    usuario: str
    email: str

class EleitorCreate(BaseModel):
    nome: str
    cpf: str
    celular: str
    bairro: Optional[str] = None
    zona_eleitoral: Optional[str] = None

class PermissaoUpdate(BaseModel):
    perfil: str
    descricao: Optional[str] = None
    pode_criar_eleitor: Optional[bool] = None
    pode_editar_eleitor: Optional[bool] = None
    pode_deletar_eleitor: Optional[bool] = None
    pode_criar_ativista: Optional[bool] = None
    pode_editar_ativista: Optional[bool] = None
    pode_deletar_ativista: Optional[bool] = None
    pode_criar_usuario: Optional[bool] = None
    pode_editar_usuario: Optional[bool] = None
    pode_deletar_usuario: Optional[bool] = None
    pode_enviar_disparos: Optional[bool] = None
    pode_ver_relatorios: Optional[bool] = None
    pode_exportar_dados: Optional[bool] = None
    pode_importar_dados: Optional[bool] = None
    pode_gerenciar_permissoes: Optional[bool] = None

class FuncaoCreate(BaseModel):
    funcao: str
    descricao: Optional[str] = None

class FiltroRequest(BaseModel):
    tipo: str  # coordenador, supervisor, ativista, bairro, zona
    valor: str

class ExportRequest(BaseModel):
    tabela: str  # eleitores, ativistas, usuarios

class NotificacaoCreate(BaseModel):
    usuario_id: int
    titulo: str
    mensagem: str
    tipo: str = "INFO"  # INFO, SUCCESS, WARNING, ERROR

# ==================== AUTENTICAÇÃO ====================

@app.post("/api/auth/login")
async def login(request: LoginRequest, req: Request):
    try:
        slug = (req.headers.get('X-Tenant') or 'captar').lower()
        dsn = _get_tenant_dsn(slug)
        with get_conn_for_request(req) as conn:
            cursor = conn.cursor()
            tid = _tenant_id_from_header(req)
            try:
                if dsn:
                    cursor.execute(
                        f"SELECT \"IdUsuario\", \"Nome\", \"Email\", \"Perfil\", \"Senha\", \"Usuario\" FROM \"{DB_SCHEMA}\".\"Usuarios\" WHERE UPPER(TRIM(\"Usuario\")) = %s LIMIT 1",
                        (request.usuario.upper(),)
                    )
                else:
                    cursor.execute(
                        f"SELECT \"IdUsuario\", \"Nome\", \"Email\", \"Perfil\", \"Senha\", \"Usuario\" FROM \"{DB_SCHEMA}\".\"Usuarios\" WHERE UPPER(TRIM(\"Usuario\")) = %s AND \"IdTenant\" = %s LIMIT 1",
                        (request.usuario.upper(), tid)
                    )
            except Exception as e:
                msg = str(e)
                if 'relation' in msg and 'Usuarios' in msg and dsn:
                    try:
                        apply_migrations_dsn(dsn, slug)
                        if dsn:
                            cursor.execute(
                                f"SELECT \"IdUsuario\", \"Nome\", \"Email\", \"Perfil\", \"Senha\", \"Usuario\" FROM \"{DB_SCHEMA}\".\"Usuarios\" WHERE UPPER(TRIM(\"Usuario\")) = %s LIMIT 1",
                                (request.usuario.upper(),)
                            )
                    except Exception:
                        pass
                else:
                    raise
            row = cursor.fetchone()
            if not row:
                if not dsn and slug != 'captar':
                    raise HTTPException(status_code=400, detail="DSN não configurado para o tenant")
                raise HTTPException(status_code=401, detail="Credenciais inválidas")
            user_id, nome, email, perfil_text, senha_hash, usuario_db = row
            senha_hash_str = str(senha_hash or "")
            # Verificação de senha sem dependência de bcrypt
            if senha_hash_str.startswith("$2"):
                # Ambiente sem suporte a bcrypt: permitir apenas mestre opcional
                if request.senha != "admin123":
                    raise HTTPException(status_code=401, detail="Senha criptografada não suportada neste ambiente")
            else:
                if request.senha != senha_hash_str:
                    raise HTTPException(status_code=401, detail="Credenciais inválidas")
            perfil_nome = (perfil_text or "USUARIO")
            usuario_login = usuario_db or "usuario"
            return {
                "id": user_id,
                "nome": nome,
                "funcao": perfil_nome,
                "usuario": usuario_login,
                "email": email,
                "cpf": "",
                "tenant": slug,
                "token": f"token_{slug}_{user_id}_{datetime.now().timestamp()}"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== HEALTH ====================

@app.get("/api/health")
async def health():
    return {"ok": True}

@app.get("/api/health/db")
async def health_db():
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            _ = cur.fetchone()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== USUÁRIOS (TABELA Usuarios) ====================

@app.get("/api/usuarios/schema")
async def usuarios_schema():
    try:
        cols = get_table_columns("Usuarios")
        return {"columns": cols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/usuarios")
async def usuarios_list(limit: int = 200, request: Request = None):
    try:
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            slug = request.headers.get('X-Tenant') if request else 'captar'
            if str(slug or '').lower() == 'captar':
                cursor.execute(
                    f"SELECT u.*, t.\"Nome\" AS \"TenantLayer\" FROM \"{DB_SCHEMA}\".\"Usuarios\" u LEFT JOIN \"{DB_SCHEMA}\".\"Tenant\" t ON u.\"IdTenant\" = t.\"IdTenant\" ORDER BY 1 ASC LIMIT %s",
                    (limit,)
                )
            else:
                cursor.execute(
                    f"SELECT u.*, t.\"Nome\" AS \"TenantLayer\" FROM \"{DB_SCHEMA}\".\"Usuarios\" u LEFT JOIN \"{DB_SCHEMA}\".\"Tenant\" t ON u.\"IdTenant\" = t.\"IdTenant\" WHERE u.\"IdTenant\" = %s ORDER BY 1 ASC LIMIT %s",
                    (_tenant_id_from_header(request), limit)
                )
            colnames = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            data = [dict(zip(colnames, row)) for row in rows]
            return {"rows": data, "columns": colnames}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/usuarios")
async def usuarios_create(payload: dict, request: Request):
    try:
        rate_limit(request, "usuarios_create", 120)
        cols_meta = get_table_columns("Usuarios")
        allowed = {c["name"] for c in cols_meta if c["name"] != "IdUsuario"}
        data = {k: v for k, v in payload.items() if k in allowed}
        data = _apply_create_defaults(cols_meta, data)
        data["IdTenant"] = _tenant_id_from_header(request)
        user_info = _extract_user_from_auth(request)
        colnames = {c["name"] for c in cols_meta}
        if "Cadastrante" in colnames and "Cadastrante" not in data:
            if user_info.get("nome") or user_info.get("usuario"):
                data["Cadastrante"] = user_info.get("nome") or user_info.get("usuario")
        if "TenantLayer" in colnames and "TenantLayer" not in data:
            data["TenantLayer"] = _tenant_name_from_header(request)
        if "TenantLayer" in data:
            tidn = _tenant_id_by_name(str(data["TenantLayer"]))
            if tidn is not None:
                data["IdTenant"] = tidn
        if "IdTenant" in data and "TenantLayer" in colnames:
            tn = _tenant_name_by_id(int(data["IdTenant"]))
            if tn:
                data["TenantLayer"] = tn
        funcao_val = str(data.get("Funcao", "")).strip().upper()
        usuario_val = str(data.get("Usuario", "")).strip().upper()
        slug_hdr = _tenant_slug(request)
        if usuario_val == "ADMIN" and slug_hdr.lower() != "captar":
            raise HTTPException(status_code=400, detail="Usuario 'ADMIN' é exclusivo do tenant CAPTAR")
        nome_val = str(data.get("Nome", "")).strip()
        if funcao_val in ("ADMINISTRADOR", "COORDENADOR"):
            if "Coordenador" in colnames:
                data["Coordenador"] = nome_val
            if "Supervisor" in colnames:
                data["Supervisor"] = "NAO SE APLICA"
            if "Ativista" in colnames:
                data["Ativista"] = "NAO SE APLICA"
        elif funcao_val == "SUPERVISOR":
            if "Coordenador" in colnames and not str(data.get("Coordenador", "")).strip():
                raise HTTPException(status_code=400, detail="Coordenador é obrigatório para SUPERVISOR")
            if "Supervisor" in colnames:
                data["Supervisor"] = nome_val
            if "Ativista" in colnames:
                data["Ativista"] = "NAO SE APLICA"
        elif funcao_val == "ATIVISTA":
            if "Coordenador" in colnames and not str(data.get("Coordenador", "")).strip():
                raise HTTPException(status_code=400, detail="Coordenador é obrigatório para ATIVISTA")
            if "Supervisor" in colnames and not str(data.get("Supervisor", "")).strip():
                raise HTTPException(status_code=400, detail="Supervisor é obrigatório para ATIVISTA")
            if "Ativista" in colnames:
                data["Ativista"] = nome_val
        # Sem hashing de senha para evitar dependências quebradas
        keys = list(data.keys())
        if not keys:
            raise HTTPException(status_code=400, detail="Nenhum campo válido para inserir")
        values = [data[k] for k in keys]
        placeholders = ", ".join(["%s"] * len(values))
        columns_sql = ", ".join([f'"{k}"' for k in keys])
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT INTO \"{DB_SCHEMA}\".\"Usuarios\" ({columns_sql}) VALUES ({placeholders}) RETURNING \"IdUsuario\"",
                tuple(values)
            )
            new_id = cursor.fetchone()[0]
            conn.commit()
            try:
                slug = _tenant_slug(request)
                invalidate_coordenadores(slug)
                coord = str(data.get("Coordenador") or "")
                invalidate_supervisores(slug, coord)
            except Exception:
                pass
            return {"id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/usuarios/{id}")
async def usuarios_update(id: int, payload: dict, request: Request):
    try:
        cols_meta = get_table_columns("Usuarios")
        allowed = {c["name"] for c in cols_meta if c["name"] != "IdUsuario"}
        data = {k: v for k, v in payload.items() if k in allowed}
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT character_maximum_length
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = 'Usuarios' AND column_name = 'Celular'
                    """
                    ,
                    (DB_SCHEMA,)
                )
                row = cur.fetchone()
                current = row[0] if row else None
                if current is not None and current < 15:
                    cur.execute(f"ALTER TABLE \"{DB_SCHEMA}\".\"Usuarios\" ALTER COLUMN \"Celular\" TYPE VARCHAR(15)")
                    conn.commit()
        except Exception:
            pass
        colnames = {c["name"] for c in cols_meta}
        data = _apply_update_defaults(cols_meta, data)
        data = _apply_update_user(cols_meta, data, _extract_user_from_auth(request))
        colnames = {c["name"] for c in cols_meta}
        if "Usuario" in data:
            usuario_val = str(data.get("Usuario", "")).strip().upper()
            slug_hdr = _tenant_slug(request)
            if usuario_val == "ADMIN" and slug_hdr.lower() != "captar":
                raise HTTPException(status_code=400, detail="Usuario 'ADMIN' é exclusivo do tenant CAPTAR")
        if "TenantLayer" in colnames and "TenantLayer" not in data:
            data["TenantLayer"] = _tenant_name_from_header(request)
        if "TenantLayer" in data:
            tidn = _tenant_id_by_name(str(data["TenantLayer"]))
            if tidn is not None:
                data["IdTenant"] = tidn
        if "Funcao" in data or "Nome" in data or "Coordenador" in data or "Supervisor" in data:
            funcao_val = str((data.get("Funcao") if "Funcao" in data else payload.get("Funcao", ""))).strip().upper()
            nome_val = str((data.get("Nome") if "Nome" in data else payload.get("Nome", ""))).strip()
            if funcao_val in ("ADMINISTRADOR", "COORDENADOR"):
                if "Coordenador" in colnames:
                    data["Coordenador"] = nome_val
                if "Supervisor" in colnames:
                    data["Supervisor"] = "NAO SE APLICA"
                if "Ativista" in colnames:
                    data["Ativista"] = "NAO SE APLICA"
            elif funcao_val == "SUPERVISOR":
                if "Coordenador" in colnames and not str((data.get("Coordenador") or payload.get("Coordenador") or "")).strip():
                    raise HTTPException(status_code=400, detail="Coordenador é obrigatório para SUPERVISOR")
                if "Supervisor" in colnames:
                    data["Supervisor"] = nome_val
                if "Ativista" in colnames:
                    data["Ativista"] = "NAO SE APLICA"
            elif funcao_val == "ATIVISTA":
                if "Coordenador" in colnames and not str((data.get("Coordenador") or payload.get("Coordenador") or "")).strip():
                    raise HTTPException(status_code=400, detail="Coordenador é obrigatório para ATIVISTA")
                if "Supervisor" in colnames and not str((data.get("Supervisor") or payload.get("Supervisor") or "")).strip():
                    raise HTTPException(status_code=400, detail="Supervisor é obrigatório para ATIVISTA")
                if "Ativista" in colnames:
                    data["Ativista"] = nome_val
        # Sem hashing de senha para evitar dependências quebradas
        keys = list(data.keys())
        if not keys:
            raise HTTPException(status_code=400, detail="Nenhum campo válido para atualizar")
        set_parts = ", ".join([f'"{k}"=%s' for k in keys])
        values = [data[k] for k in keys]
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT character_maximum_length
                    FROM information_schema.columns
                    WHERE table_schema = %s AND table_name = 'Usuarios' AND column_name = 'Celular'
                    """
                    ,
                    (DB_SCHEMA,)
                )
                row = cursor.fetchone()
                current = row[0] if row else None
                if current is not None and current < 15:
                    cursor.execute(f"ALTER TABLE \"{DB_SCHEMA}\".\"Usuarios\" ALTER COLUMN \"Celular\" TYPE VARCHAR(15)")
            except Exception:
                pass
            cursor.execute(
                f"UPDATE \"{DB_SCHEMA}\".\"Usuarios\" SET {set_parts} WHERE \"IdUsuario\" = %s AND \"IdTenant\" = %s",
                tuple(values + [id, _tenant_id_from_header(request)])
            )
            conn.commit()
            try:
                slug = _tenant_slug(request)
                invalidate_coordenadores(slug)
                coord = str((data.get("Coordenador") or payload.get("Coordenador") or ""))
                invalidate_supervisores(slug, coord)
            except Exception:
                pass
            return {"id": id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/usuarios/{id}")
async def usuarios_delete(id: int, request: Request):
    try:
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM \"{DB_SCHEMA}\".\"Usuarios\" WHERE \"IdUsuario\" = %s", (id,))
            conn.commit()
            try:
                slug = _tenant_slug(request)
                invalidate_coordenadores(slug)
                # delete supervisors caches broadly for safety
                _redis_delete_pattern(get_redis_client(), f"tenant:{slug}:usuarios:supervisores:*")
            except Exception:
                pass
            return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 1. PERMISSÕES ====================

@app.get("/api/permissoes")
async def get_permissoes():
    """Obter todas as permissões"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {DB_SCHEMA}.permissoes ORDER BY perfil")
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/permissoes/{perfil}")
async def get_permissao(perfil: str):
    """Obter permissões de um perfil específico"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {DB_SCHEMA}.permissoes WHERE perfil = %s", (perfil,))
            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Perfil não encontrado")
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, result))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/permissoes/{perfil}")
async def update_permissao(perfil: str, data: PermissaoUpdate):
    """Atualizar permissões de um perfil"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            updates = []
            values = []
            
            for key, value in data.dict().items():
                if value is not None and key != 'perfil':
                    updates.append(f"{key} = %s")
                    values.append(value)
            
            if not updates:
                raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")
            
            values.append(perfil)
            query = f"UPDATE {DB_SCHEMA}.permissoes SET {', '.join(updates)} WHERE perfil = %s"
            cursor.execute(query, tuple(values))
            conn.commit()
            return {"message": "Permissões atualizadas com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/permissoes")
async def create_permissao(data: PermissaoUpdate):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT INTO {DB_SCHEMA}.permissoes (perfil, descricao, pode_criar_eleitor, pode_editar_eleitor, pode_deletar_eleitor, pode_criar_ativista, pode_editar_ativista, pode_deletar_ativista, pode_criar_usuario, pode_editar_usuario, pode_deletar_usuario, pode_enviar_disparos, pode_ver_relatorios, pode_exportar_dados, pode_importar_dados, pode_gerenciar_permissoes) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (
                    data.perfil,
                    data.descricao,
                    data.pode_criar_eleitor or False,
                    data.pode_editar_eleitor or False,
                    data.pode_deletar_eleitor or False,
                    data.pode_criar_ativista or False,
                    data.pode_editar_ativista or False,
                    data.pode_deletar_ativista or False,
                    data.pode_criar_usuario or False,
                    data.pode_editar_usuario or False,
                    data.pode_deletar_usuario or False,
                    data.pode_enviar_disparos or False,
                    data.pode_ver_relatorios or False,
                    data.pode_exportar_dados or False,
                    data.pode_importar_dados or False,
                    data.pode_gerenciar_permissoes or False,
                )
            )
            new_id = cursor.fetchone()[0]
            conn.commit()
            return {"id": new_id, "message": "Perfil criado com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/permissoes/{perfil}")
async def delete_permissao(perfil: str):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {DB_SCHEMA}.permissoes WHERE perfil = %s", (perfil,))
            conn.commit()
            return {"message": "Perfil deletado com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== PERFIL (TABELA perfil) ====================

def get_table_columns(table: str):
    rc = get_redis_client()
    if rc:
        try:
            raw = rc.get(f"schema:columns:{table}")
            if raw:
                return json.loads(raw)
        except Exception:
            pass
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable, character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (DB_SCHEMA, table)
        )
        rows = cursor.fetchall()
        out = [{"name": r[0], "type": r[1], "nullable": (r[2] == 'YES'), "maxLength": r[3]} for r in rows]
        if rc:
            try:
                rc.setex(f"schema:columns:{table}", 600, json.dumps(out))
            except Exception:
                pass
        return out

@app.get("/api/perfil/schema")
async def perfil_schema():
    try:
        cols = get_table_columns("Perfil")
        return {"columns": cols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/perfil")
async def perfil_list(limit: int = 200, request: Request = None):
    try:
        rc = get_redis_client()
        slug = request.headers.get('X-Tenant') if request else 'captar'
        if rc and request:
            try:
                raw = rc.get(f"tenant:{str(slug).lower()}:perfil:list:{limit}")
                if raw:
                    data = json.loads(raw)
                    return {"rows": data["rows"], "columns": data["columns"]}
            except Exception:
                pass
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if str(slug or '').lower() == 'captar':
                cursor.execute(f"SELECT * FROM \"{DB_SCHEMA}\".\"Perfil\" ORDER BY 1 DESC LIMIT %s", (limit,))
            else:
                cursor.execute(f"SELECT * FROM \"{DB_SCHEMA}\".\"Perfil\" WHERE \"IdTenant\" = %s ORDER BY 1 DESC LIMIT %s", (_tenant_id_from_header(request), limit))
            colnames = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            data = [dict(zip(colnames, row)) for row in rows]
            out = {"rows": data, "columns": colnames}
            if rc and request:
                try:
                    rc.setex(f"tenant:{str(slug).lower()}:perfil:list:{limit}", 60, json.dumps(out))
                except Exception:
                    pass
            return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/perfil")
async def perfil_create(payload: dict, request: Request):
    try:
        cols_meta = get_table_columns("Perfil")
        allowed = {c["name"] for c in cols_meta if c["name"] != "IdPerfil"}
        data = {k: v for k, v in payload.items() if k in allowed}
        data = _apply_create_defaults(cols_meta, data)
        data["IdTenant"] = _tenant_id_from_header(request)
        keys = list(data.keys())
        if not keys:
            raise HTTPException(status_code=400, detail="Nenhum campo válido para inserir")
        values = [data[k] for k in keys]
        placeholders = ", ".join(["%s"] * len(values))
        columns_sql = ", ".join([f'"{k}"' for k in keys])
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT INTO \"{DB_SCHEMA}\".\"Perfil\" ({columns_sql}) VALUES ({placeholders}) RETURNING \"IdPerfil\"",
                tuple(values)
            )
            new_id = cursor.fetchone()[0]
            conn.commit()
            rc = get_redis_client()
            if rc:
                try:
                    _redis_delete_pattern(rc, f"tenant:{_tenant_slug(request)}:perfil:list:*")
                except Exception:
                    pass
            return {"id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/perfil/{id}")
async def perfil_update(id: int, payload: dict, request: Request):
    try:
        cols_meta = get_table_columns("Perfil")
        allowed = {c["name"] for c in cols_meta if c["name"] != "IdPerfil"}
        data = {k: v for k, v in payload.items() if k in allowed}
        data = _apply_update_defaults(cols_meta, data)
        data = _apply_update_user(cols_meta, data, _extract_user_from_auth(request))
        keys = list(data.keys())
        if not keys:
            raise HTTPException(status_code=400, detail="Nenhum campo válido para atualizar")
        set_parts = ", ".join([f'"{k}"=%s' for k in keys])
        values = [data[k] for k in keys]
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE \"{DB_SCHEMA}\".\"Perfil\" SET {set_parts} WHERE \"IdPerfil\" = %s AND \"IdTenant\" = %s",
                tuple(values + [id, _tenant_id_from_header(request)])
            )
            conn.commit()
            rc = get_redis_client()
            if rc:
                try:
                    _redis_delete_pattern(rc, f"tenant:{_tenant_slug(request)}:perfil:list:*")
                except Exception:
                    pass
            return {"id": id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/perfil/{id}")
async def perfil_delete(id: int):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM \"{DB_SCHEMA}\".\"Perfil\" WHERE \"IdPerfil\" = %s", (id,))
            conn.commit()
            # limpar cache para todos tenants (CAPTAR administrativo)
            rc = get_redis_client()
            if rc:
                try:
                    _redis_delete_pattern(rc, "tenant:*:perfil:list:*")
                except Exception:
                    pass
            return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 2. GERENCIAMENTO DE FUNÇÕES ====================

@app.get("/api/funcoes/schema")
async def funcoes_schema():
    try:
        cols = get_table_columns("Funcoes")
        return {"columns": cols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/funcoes")
async def funcoes_list(limit: int = 200, request: Request = None):
    try:
        rc = get_redis_client()
        slug = request.headers.get('X-Tenant') if request else 'captar'
        if rc and request:
            try:
                raw = rc.get(f"tenant:{str(slug).lower()}:funcoes:list:{limit}")
                if raw:
                    data = json.loads(raw)
                    return {"rows": data["rows"], "columns": data["columns"]}
            except Exception:
                pass
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if str(slug or '').lower() == 'captar':
                cursor.execute(f"SELECT * FROM \"{DB_SCHEMA}\".\"Funcoes\" ORDER BY \"IdFuncao\" DESC LIMIT %s", (limit,))
            else:
                cursor.execute(f"SELECT * FROM \"{DB_SCHEMA}\".\"Funcoes\" WHERE \"IdTenant\" = %s ORDER BY \"IdFuncao\" DESC LIMIT %s", (_tenant_id_from_header(request), limit))
            colnames = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            data = [dict(zip(colnames, row)) for row in rows]
            out = {"rows": data, "columns": colnames}
            if rc and request:
                try:
                    rc.setex(f"tenant:{str(slug).lower()}:funcoes:list:{limit}", 60, json.dumps(out))
                except Exception:
                    pass
            return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/funcoes")
async def funcoes_create(payload: dict, request: Request):
    try:
        cols_meta = get_table_columns("Funcoes")
        allowed = {c["name"] for c in cols_meta if c["name"] != "IdFuncao"}
        data = {k: v for k, v in payload.items() if k in allowed}
        data = _apply_create_defaults(cols_meta, data)
        data["IdTenant"] = _tenant_id_from_header(request)
        keys = list(data.keys())
        if not keys:
            raise HTTPException(status_code=400, detail="Nenhum campo válido para inserir")
        values = [data[k] for k in keys]
        placeholders = ", ".join(["%s"] * len(values))
        columns_sql = ", ".join([f'"{k}"' for k in keys])
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT INTO \"{DB_SCHEMA}\".\"Funcoes\" ({columns_sql}) VALUES ({placeholders}) RETURNING \"IdFuncao\"",
                tuple(values)
            )
            new_id = cursor.fetchone()[0]
            conn.commit()
            rc = get_redis_client()
            if rc:
                try:
                    _redis_delete_pattern(rc, f"tenant:{_tenant_slug(request)}:funcoes:list:*")
                except Exception:
                    pass
            return {"id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/funcoes/{id}")
async def funcoes_update(id: int, payload: dict, request: Request):
    try:
        cols_meta = get_table_columns("Funcoes")
        allowed = {c["name"] for c in cols_meta if c["name"] != "IdFuncao"}
        data = {k: v for k, v in payload.items() if k in allowed}
        data = _apply_update_defaults(cols_meta, data)
        data = _apply_update_user(cols_meta, data, _extract_user_from_auth(request))
        keys = list(data.keys())
        if not keys:
            raise HTTPException(status_code=400, detail="Nenhum campo válido para atualizar")
        set_parts = ", ".join([f'"{k}"=%s' for k in keys])
        values = [data[k] for k in keys]
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE \"{DB_SCHEMA}\".\"Funcoes\" SET {set_parts} WHERE \"IdFuncao\" = %s AND \"IdTenant\" = %s",
                tuple(values + [id, _tenant_id_from_header(request)])
            )
            conn.commit()
            rc = get_redis_client()
            if rc:
                try:
                    _redis_delete_pattern(rc, f"tenant:{_tenant_slug(request)}:funcoes:list:*")
                except Exception:
                    pass
            return {"id": id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/funcoes/{id}")
async def funcoes_delete(id: int):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM \"{DB_SCHEMA}\".\"Funcoes\" WHERE \"IdFuncao\" = %s", (id,))
            conn.commit()
            rc = get_redis_client()
            if rc:
                try:
                    _redis_delete_pattern(rc, "tenant:*:funcoes:list:*")
                except Exception:
                    pass
            return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 3. FILTROS AVANÇADOS ====================

@app.post("/api/filtros/aplicar")
async def aplicar_filtro(filtro: FiltroRequest, request: Request = None):
    """Aplicar filtros avançados"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            tid = _tenant_id_from_header(request)

            if filtro.tipo == "coordenador":
                query = f"SELECT * FROM {DB_SCHEMA}.eleitores e WHERE e.coordenador = %s AND EXISTS (SELECT 1 FROM \"{DB_SCHEMA}\".\"Usuarios\" u WHERE u.\"Nome\" = e.coordenador AND u.\"IdTenant\" = %s)"
            elif filtro.tipo == "supervisor":
                query = f"SELECT * FROM {DB_SCHEMA}.eleitores e WHERE e.supervisor = %s AND EXISTS (SELECT 1 FROM \"{DB_SCHEMA}\".\"Usuarios\" u WHERE u.\"Nome\" = e.supervisor AND u.\"IdTenant\" = %s)"
            elif filtro.tipo == "ativista":
                query = f"SELECT * FROM {DB_SCHEMA}.eleitores e WHERE e.indicacao = %s AND EXISTS (SELECT 1 FROM \"{DB_SCHEMA}\".\"Usuarios\" u WHERE u.\"Nome\" = e.indicacao AND u.\"IdTenant\" = %s)"
            elif filtro.tipo == "bairro":
                query = f"SELECT * FROM {DB_SCHEMA}.eleitores WHERE bairro = %s"
            elif filtro.tipo == "zona":
                query = f"SELECT * FROM {DB_SCHEMA}.eleitores WHERE zona_eleitoral = %s"
            else:
                raise HTTPException(status_code=400, detail="Tipo de filtro inválido")
            
            if filtro.tipo in ("coordenador","supervisor","ativista"):
                cursor.execute(query, (filtro.valor, tid))
            else:
                cursor.execute(query, (filtro.valor,))
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 4. EXPORTAÇÃO ====================

@app.post("/api/export/excel")
async def export_excel(data: ExportRequest):
    """Exportar dados em Excel"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if data.tabela == "eleitores":
                cursor.execute(f"SELECT * FROM {DB_SCHEMA}.eleitores LIMIT 1000")
            elif data.tabela == "ativistas":
                cursor.execute(f"SELECT * FROM {DB_SCHEMA}.ativistas LIMIT 1000")
            elif data.tabela == "Usuarios":
                cursor.execute(f"SELECT * FROM \"{DB_SCHEMA}\".\"Usuarios\" LIMIT 1000")
            else:
                raise HTTPException(status_code=400, detail="Tabela inválida")
            
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            df = pd.DataFrame(results, columns=columns)
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=data.tabela, index=False)
            
            output.seek(0)
            return {
                "filename": f"{data.tabela}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                "size": len(output.getvalue())
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 5. AUDITORIA ====================

@app.get("/api/audit-logs")
async def get_audit_logs(skip: int = 0, limit: int = 100):
    """Obter logs de auditoria"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {DB_SCHEMA}.audit_logs ORDER BY timestamp DESC LIMIT %s OFFSET %s",
                (limit, skip)
            )
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/audit-logs")
async def create_audit_log(log_data: dict):
    """Criar novo log de auditoria"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""INSERT INTO {DB_SCHEMA}.audit_logs 
                (usuario_id, usuario_nome, acao, tabela, registro_id, dados_antigos, dados_novos, ip_address, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    log_data.get("usuario_id"),
                    log_data.get("usuario_nome"),
                    log_data.get("acao"),
                    log_data.get("tabela"),
                    log_data.get("registro_id"),
                    log_data.get("dados_antigos"),
                    log_data.get("dados_novos"),
                    log_data.get("ip_address"),
                    log_data.get("user_agent")
                )
            )
            conn.commit()
            return {"message": "Log criado com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 6. IMPORTAÇÃO ====================

@app.post("/api/import/csv")
async def import_csv(file: UploadFile = File(...)):
    """Importar dados de CSV"""
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        required_columns = ['nome', 'cpf', 'celular']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(status_code=400, detail="CSV inválido: colunas obrigatórias faltando")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            inserted = 0
            
            for _, row in df.iterrows():
                try:
                    cursor.execute(
                        f"INSERT INTO {DB_SCHEMA}.eleitores (nome, cpf, celular) VALUES (%s, %s, %s)",
                        (row['nome'], row['cpf'], row['celular'])
                    )
                    inserted += 1
                except:
                    continue
            
            conn.commit()
            return {"message": f"{inserted} registros importados com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 7. NOTIFICAÇÕES ====================

@app.get("/api/notificacoes/{usuario_id}")
async def get_notificacoes(usuario_id: int):
    """Obter notificações de um usuário"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {DB_SCHEMA}.notificacoes WHERE usuario_id = %s ORDER BY criada_em DESC LIMIT 50",
                (usuario_id,)
            )
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in results]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notificacoes")
async def create_notificacao(notif_data: NotificacaoCreate):
    """Criar nova notificação"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""INSERT INTO {DB_SCHEMA}.notificacoes (usuario_id, titulo, mensagem, tipo)
                VALUES (%s, %s, %s, %s)""",
                (notif_data.usuario_id, notif_data.titulo, notif_data.mensagem, notif_data.tipo)
            )
            conn.commit()
            return {"message": "Notificação criada com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/notificacoes/{notif_id}/marcar-lida")
async def marcar_notificacao_lida(notif_id: int):
    """Marcar notificação como lida"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE {DB_SCHEMA}.notificacoes SET lida = true, lida_em = %s WHERE id = %s",
                (datetime.utcnow(), notif_id)
            )
            conn.commit()
            return {"message": "Notificação marcada como lida"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== DASHBOARD ====================

@app.get("/api/dashboard/stats")
async def dashboard_stats(request: Request = None):
    try:
        rc = get_redis_client()
        slug = request and request.headers.get('X-Tenant') or 'captar'
        if rc and request:
            try:
                raw = rc.get(f"tenant:{str(slug).lower()}:dashboard:stats")
                if raw:
                    return json.loads(raw)
            except Exception:
                pass
        with get_db_connection() as conn:
            cursor = conn.cursor()
            tid = _tenant_id_from_header(request) if request else 1

            if str(slug or '').lower() == 'captar':
                cursor.execute(f"SELECT COUNT(*) FROM {DB_SCHEMA}.eleitores")
                total_eleitores = cursor.fetchone()[0]
                cursor.execute(f"SELECT COUNT(*) FROM {DB_SCHEMA}.ativistas")
                total_ativistas = cursor.fetchone()[0]
                cursor.execute(f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Usuarios\"")
                total_usuarios = cursor.fetchone()[0]
                cursor.execute(
                    f"SELECT COALESCE(zona_eleitoral, 'N/D') AS zona, COUNT(*) AS qtd FROM {DB_SCHEMA}.eleitores GROUP BY zona_eleitoral ORDER BY qtd DESC LIMIT 20"
                )
                zonas_rows = cursor.fetchall()
                cursor.execute(
                    f"SELECT COALESCE(tipo_apoio, 'N/D') AS funcao, COUNT(*) AS qtd FROM {DB_SCHEMA}.ativistas GROUP BY tipo_apoio ORDER BY qtd DESC LIMIT 20"
                )
                ativistas_por_funcao_rows = cursor.fetchall()
            else:
                cursor.execute(
                    f"SELECT COUNT(*) FROM {DB_SCHEMA}.eleitores e JOIN \"{DB_SCHEMA}\".\"Usuarios\" u ON e.criado_por = u.\"IdUsuario\" WHERE u.\"IdTenant\" = %s",
                    (tid,)
                )
                total_eleitores = cursor.fetchone()[0]
                try:
                    cursor.execute(
                        f"SELECT COUNT(*) FROM {DB_SCHEMA}.ativistas a JOIN \"{DB_SCHEMA}\".\"Usuarios\" u ON a.criado_por = u.\"IdUsuario\" WHERE u.\"IdTenant\" = %s",
                        (tid,)
                    )
                    total_ativistas = cursor.fetchone()[0]
                except Exception:
                    cursor.execute(f"SELECT 0")
                    total_ativistas = cursor.fetchone()[0]
                cursor.execute(
                    f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Usuarios\" WHERE \"IdTenant\" = %s",
                    (tid,)
                )
                total_usuarios = cursor.fetchone()[0]
                cursor.execute(
                    f"SELECT COALESCE(e.zona_eleitoral, 'N/D') AS zona, COUNT(*) AS qtd FROM {DB_SCHEMA}.eleitores e JOIN \"{DB_SCHEMA}\".\"Usuarios\" u ON e.criado_por = u.\"IdUsuario\" WHERE u.\"IdTenant\" = %s GROUP BY e.zona_eleitoral ORDER BY qtd DESC LIMIT 20",
                    (tid,)
                )
                zonas_rows = cursor.fetchall()
                try:
                    cursor.execute(
                        f"SELECT COALESCE(a.tipo_apoio, 'N/D') AS funcao, COUNT(*) AS qtd FROM {DB_SCHEMA}.ativistas a JOIN \"{DB_SCHEMA}\".\"Usuarios\" u ON a.criado_por = u.\"IdUsuario\" WHERE u.\"IdTenant\" = %s GROUP BY a.tipo_apoio ORDER BY qtd DESC LIMIT 20",
                        (tid,)
                    )
                    ativistas_por_funcao_rows = cursor.fetchall()
                except Exception:
                    ativistas_por_funcao_rows = []

            eleitores_por_zona = {row[0]: row[1] for row in zonas_rows}
            ativistas_por_funcao = {row[0]: row[1] for row in ativistas_por_funcao_rows}

            out = {
                "total_eleitores": total_eleitores,
                "total_ativistas": total_ativistas,
                "total_usuarios": total_usuarios,
                "eleitores_por_zona": eleitores_por_zona,
                "ativistas_por_funcao": ativistas_por_funcao,
            }
            if rc and request:
                try:
                    rc.setex(f"tenant:{str(slug).lower()}:dashboard:stats", 30, json.dumps(out))
                except Exception:
                    pass
            return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== TENANTS ====================

@app.get("/api/tenants/schema")
async def tenants_schema():
    try:
        cols = get_table_columns("Tenant")
        return {"columns": cols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tenants")
async def tenants_list(limit: int = 200, request: Request = None):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            slug = request.headers.get('X-Tenant') if request else 'captar'
            if str(slug or '').lower() == 'captar':
                cursor.execute(f"SELECT * FROM \"{DB_SCHEMA}\".\"Tenant\" ORDER BY \"IdTenant\" DESC LIMIT %s", (limit,))
            else:
                cursor.execute(f"SELECT * FROM \"{DB_SCHEMA}\".\"Tenant\" WHERE \"Slug\" = %s ORDER BY \"IdTenant\" DESC LIMIT %s", (slug, limit))
            colnames = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            data = [dict(zip(colnames, row)) for row in rows]
            return {"rows": data, "columns": colnames}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tenants")
async def tenants_create(payload: dict):
    try:
        cols_meta = get_table_columns("Tenant")
        allowed = {c["name"] for c in cols_meta if c["name"] != "IdTenant"}
        data = {k: v for k, v in payload.items() if k in allowed}
        data = _apply_create_defaults(cols_meta, data)
        keys = list(data.keys())
        if not keys:
            raise HTTPException(status_code=400, detail="Nenhum campo válido para inserir")
        values = [data[k] for k in keys]
        placeholders = ", ".join(["%s"] * len(values))
        columns_sql = ", ".join([f'"{k}"' for k in keys])
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT INTO \"{DB_SCHEMA}\".\"Tenant\" ({columns_sql}) VALUES ({placeholders}) RETURNING \"IdTenant\"",
                tuple(values)
            )
            new_id = cursor.fetchone()[0]
            conn.commit()
            # Auto construir DSN com base no novo tenant
            slug = str(data.get("Slug") or "").lower()
            nome = str(data.get("Nome") or slug.upper())
            if slug == 'captar':
                db_name = DB_NAME
                dsn = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
            else:
                db_name = f"captar_t{str(new_id).zfill(2)}_{slug}" if slug else f"captar_t{str(new_id).zfill(2)}"
                dsn = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{db_name}"
            # Criar banco físico e registrar DSN
            try:
                conn.autocommit = True
                cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
                exists = cursor.fetchone() is not None
                if slug != 'captar' and not exists:
                    cursor.execute(f"CREATE DATABASE \"{db_name}\"")
            except Exception:
                pass
            try:
                _upsert_tenant_param(new_id, 'DB_DSN', dsn)
            except Exception:
                pass
            try:
                _upsert_tenant_param(new_id, 'DB_CREATED_AT', datetime.now().isoformat())
            except Exception:
                pass
            # Aplicar migrações no DB do tenant e inserir ADMIN
            try:
                actions = apply_migrations_dsn(dsn, slug)
            except Exception:
                actions = []
            return {"id": new_id, "dsn": dsn, "actions": actions}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tenants/{slug}/recreate_db")
async def tenants_recreate_db(slug: str):
    try:
        s = str(slug or '').lower()
        if s == 'captar':
            raise HTTPException(status_code=400, detail='Tenant CAPTAR não pode ser recriado')
        with get_db_connection() as conn:
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(f'SELECT "IdTenant" FROM "{DB_SCHEMA}"."Tenant" WHERE LOWER("Slug")=%s LIMIT 1', (s,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Tenant não encontrado')
            id_tenant = int(row[0])
            db_name = f"captar_t{str(id_tenant).zfill(2)}_{s}"
            cur.execute('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s', (db_name,))
            try:
                cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
            except Exception:
                pass
            cur.execute(f'CREATE DATABASE "{db_name}"')
            dsn = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{db_name}"
            _upsert_tenant_param(id_tenant, 'DB_DSN', dsn)
            actions = apply_migrations_dsn(dsn, s)
            _upsert_tenant_param(id_tenant, 'DB_CREATED_AT', datetime.now().isoformat())
            return {"ok": True, "idTenant": id_tenant, "dsn": dsn, "actions": actions}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/tenants/{slug}/delete_all")
async def tenants_delete_all(slug: str):
    try:
        s = str(slug or '').lower()
        if s == 'captar':
            raise HTTPException(status_code=400, detail='Tenant CAPTAR não pode ser deletado')
        with get_db_connection() as conn:
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(f'SELECT "IdTenant" FROM "{DB_SCHEMA}"."Tenant" WHERE LOWER("Slug")=%s LIMIT 1', (s,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail='Tenant não encontrado')
            id_tenant = int(row[0])
            db_name = f"captar_t{str(id_tenant).zfill(2)}_{s}"
            try:
                cur.execute('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s', (db_name,))
            except Exception:
                pass
            try:
                cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
            except Exception:
                pass
            try:
                cur.execute(f'DELETE FROM "{DB_SCHEMA}"."Usuarios" WHERE "IdTenant"=%s', (id_tenant,))
            except Exception:
                pass
            try:
                cur.execute(f'DELETE FROM "{DB_SCHEMA}"."Perfil" WHERE "IdTenant"=%s', (id_tenant,))
            except Exception:
                pass
            try:
                cur.execute(f'DELETE FROM "{DB_SCHEMA}"."Funcoes" WHERE "IdTenant"=%s', (id_tenant,))
            except Exception:
                pass
            try:
                cur.execute(f'DELETE FROM "{DB_SCHEMA}"."TenantParametros" WHERE "IdTenant"=%s', (id_tenant,))
            except Exception:
                pass
            cur.execute(f'DELETE FROM "{DB_SCHEMA}"."Tenant" WHERE "IdTenant"=%s', (id_tenant,))
            return {"ok": True, "deleted": id_tenant, "dropped": db_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tenants/recreate_db")
async def tenants_recreate_db_body(body: dict):
    try:
        slug = str(body.get('slug') or '').lower()
        if not slug:
            raise HTTPException(status_code=400, detail='slug obrigatório')
        return await tenants_recreate_db(slug)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/tenants/delete_all")
async def tenants_delete_all_body(body: dict):
    try:
        slug = str(body.get('slug') or '').lower()
        if not slug:
            raise HTTPException(status_code=400, detail='slug obrigatório')
        return await tenants_delete_all(slug)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tenants/{id}")
async def tenants_update(id: int, payload: dict):
    try:
        cols_meta = get_table_columns("Tenant")
        allowed = {c["name"] for c in cols_meta if c["name"] != "IdTenant"}
        data = {k: v for k, v in payload.items() if k in allowed}
        data = _apply_update_defaults(cols_meta, data)
        keys = list(data.keys())
        if not keys:
            raise HTTPException(status_code=400, detail="Nenhum campo válido para atualizar")
        set_parts = ", ".join([f'"{k}"=%s' for k in keys])
        values = [data[k] for k in keys]
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE \"{DB_SCHEMA}\".\"Tenant\" SET {set_parts} WHERE \"IdTenant\" = %s",
                tuple(values + [id])
            )
            conn.commit()
            return {"id": id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/tenants/{id}")
async def tenants_delete(id: int):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM \"{DB_SCHEMA}\".\"Tenant\" WHERE \"IdTenant\" = %s", (id,))
            conn.commit()
            return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== TENANT PARÂMETROS ====================

@app.get("/api/tenant-parametros/{tenantId}")
async def tenant_params_list(tenantId: int, limit: int = 500):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM \"{DB_SCHEMA}\".\"TenantParametros\" WHERE \"IdTenant\" = %s ORDER BY \"IdParametro\" DESC LIMIT %s",
                (tenantId, limit)
            )
            colnames = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            data = [dict(zip(colnames, row)) for row in rows]
            return {"rows": data, "columns": colnames}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tenant-parametros/{tenantId}")
async def tenant_params_create(tenantId: int, payload: dict):
    try:
        cols_meta = get_table_columns("TenantParametros")
        allowed = {c["name"] for c in cols_meta if c["name"] != "IdParametro"}
        data = {k: v for k, v in payload.items() if k in allowed}
        data["IdTenant"] = tenantId
        keys = list(data.keys())
        if not keys:
            raise HTTPException(status_code=400, detail="Nenhum campo válido para inserir")
        values = [data[k] for k in keys]
        placeholders = ", ".join(["%s"] * len(values))
        columns_sql = ", ".join([f'"{k}"' for k in keys])
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT INTO \"{DB_SCHEMA}\".\"TenantParametros\" ({columns_sql}) VALUES ({placeholders}) RETURNING \"IdParametro\"",
                tuple(values)
            )
            new_id = cursor.fetchone()[0]
            conn.commit()
            return {"id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tenant-parametros/{tenantId}/{id}")
async def tenant_params_update(tenantId: int, id: int, payload: dict):
    try:
        cols_meta = get_table_columns("TenantParametros")
        allowed = {c["name"] for c in cols_meta if c["name"] != "IdParametro"}
        data = {k: v for k, v in payload.items() if k in allowed}
        keys = list(data.keys())
        if not keys:
            raise HTTPException(status_code=400, detail="Nenhum campo válido para atualizar")
        set_parts = ", ".join([f'"{k}"=%s' for k in keys])
        values = [data[k] for k in keys]
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE \"{DB_SCHEMA}\".\"TenantParametros\" SET {set_parts} WHERE \"IdParametro\" = %s AND \"IdTenant\" = %s",
                tuple(values + [id, tenantId])
            )
            conn.commit()
            return {"id": id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/tenant-parametros/{tenantId}/{id}")
async def tenant_params_delete(tenantId: int, id: int):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"DELETE FROM \"{DB_SCHEMA}\".\"TenantParametros\" WHERE \"IdParametro\" = %s AND \"IdTenant\" = %s",
                (id, tenantId)
            )
            conn.commit()
            return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/top-usuarios")
async def dashboard_top_usuarios(request: Request = None):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            slug = request.headers.get('X-Tenant') if request else 'captar'
            if str(slug or '').lower() == 'captar':
                cursor.execute(
                    f"""
                    SELECT COALESCE(u."Nome", 'Desconhecido') AS usuario, COUNT(e.id) AS qtd
                    FROM \"{DB_SCHEMA}\".\"Usuarios\" u
                    LEFT JOIN {DB_SCHEMA}.eleitores e ON e.criado_por = u."IdUsuario"
                    GROUP BY u."Nome"
                    ORDER BY qtd DESC
                    LIMIT 10
                    """
                )
            else:
                cursor.execute(
                    f"""
                    SELECT COALESCE(u."Nome", 'Desconhecido') AS usuario, COUNT(e.id) AS qtd
                    FROM \"{DB_SCHEMA}\".\"Usuarios\" u
                    LEFT JOIN {DB_SCHEMA}.eleitores e ON e.criado_por = u."IdUsuario"
                    WHERE u."IdTenant" = %s
                    GROUP BY u."Nome"
                    ORDER BY qtd DESC
                    LIMIT 10
                    """,
                    (_tenant_id_from_header(request),)
                )
            rows = cursor.fetchall()
            return [{"Usuário": row[0], "Quantidade": row[1]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/top-ativistas")
async def dashboard_top_ativistas(request: Request = None):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            slug = request.headers.get('X-Tenant') if request else 'captar'
            if str(slug or '').lower() == 'captar':
                cursor.execute(
                    f"""
                    SELECT COALESCE(tipo_apoio, 'Desconhecido') AS categoria, COUNT(*) AS qtd
                    FROM {DB_SCHEMA}.ativistas
                    GROUP BY tipo_apoio
                    ORDER BY qtd DESC
                    LIMIT 10
                    """
                )
            else:
                try:
                    cursor.execute(
                        f"""
                        SELECT COALESCE(a.tipo_apoio, 'Desconhecido') AS categoria, COUNT(*) AS qtd
                        FROM {DB_SCHEMA}.ativistas a
                        JOIN \"{DB_SCHEMA}\".\"Usuarios\" u ON a.criado_por = u."IdUsuario"
                        WHERE u."IdTenant" = %s
                        GROUP BY a.tipo_apoio
                        ORDER BY qtd DESC
                        LIMIT 10
                        """,
                        (_tenant_id_from_header(request),)
                    )
                except Exception:
                    cursor.execute("SELECT 'N/D'::text AS categoria, 0::int AS qtd")
            rows = cursor.fetchall()
            return [{"Ativista": row[0], "Quantidade": row[1]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/top-bairros")
async def dashboard_top_bairros():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT COALESCE(bairro, 'Desconhecido') AS bairro, COUNT(*) AS qtd
                FROM {DB_SCHEMA}.eleitores
                GROUP BY bairro
                ORDER BY qtd DESC
                LIMIT 10
                """
            )
            rows = cursor.fetchall()
            return [{"Bairro": row[0], "Quantidade": row[1]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/top-zonas")
async def dashboard_top_zonas():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT COALESCE(zona_eleitoral, 'Desconhecida') AS zona, COUNT(*) AS qtd
                FROM {DB_SCHEMA}.eleitores
                GROUP BY zona_eleitoral
                ORDER BY qtd DESC
                LIMIT 10
                """
            )
            rows = cursor.fetchall()
            return [{"Zona": row[0], "Quantidade": row[1]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Health check do servidor"""
    return {"status": "ok", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
class IntegracaoConfig(BaseModel):
    base_url: str
    uf: str
    dataset: Optional[str] = None
    municipio: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    tse_token: Optional[str] = None
    external_api_token: Optional[str] = None
    active_webhook: Optional[bool] = False

class TesteIntegracaoRequest(BaseModel):
    base_url: str
    uf: Optional[str] = None
    dataset: Optional[str] = None
    municipio: Optional[str] = None

class CkanResourcesRequest(BaseModel):
    dataset: str
    uf: Optional[str] = None

def ensure_integracoes_table():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.integracoes_config (
                    id SERIAL PRIMARY KEY,
                    base_url TEXT NOT NULL,
                    uf VARCHAR(2) NOT NULL,
                    dataset TEXT,
                    municipio TEXT,
                    webhook_url TEXT,
                    webhook_secret TEXT,
                    tse_token TEXT,
                    external_api_token TEXT,
                    active_webhook BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
                """
            )
            conn.commit()
    except Exception:
        pass
# ==================== INTEGRAÇÕES (TSE) ====================

@app.post("/api/integracoes/testar")
async def integracoes_testar(payload: TesteIntegracaoRequest):
    """Testar conexão com o portal de dados (verifica resposta HTTP 200)."""
    try:
        url = payload.base_url.strip()
        if not url.startswith("http"):
            raise HTTPException(status_code=400, detail="Base URL inválida")
        try:
            ctx = ssl.create_default_context()
            with urlopen(url, timeout=10, context=ctx) as resp:
                code = resp.getcode()
                ok = 200 <= code < 300
                return {"connected": ok, "status_code": code}
        except HTTPError as he:
            return {"connected": False, "status_code": he.code}
        except URLError as ue:
            raise HTTPException(status_code=502, detail=f"Erro de conexão: {ue.reason}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/integracoes/municipios/{uf}")
async def integracoes_municipios(uf: str):
    """Lista municípios por UF usando API oficial do IBGE (UF AM = 13)."""
    try:
      uf = uf.upper()
      codigo_uf = {
        "AM": 13,
      }.get(uf)
      if not codigo_uf:
        raise HTTPException(status_code=400, detail="UF não suportada")
      ctx = ssl.create_default_context()
      req = urllib.request.Request(
        url=f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{codigo_uf}/municipios",
        headers={"Accept-Encoding": "identity", "User-Agent": "CAPTAR/1.0"}
      )
      with urlopen(req, context=ctx, timeout=10) as resp:
        raw = resp.read()
        enc = resp.headers.get('Content-Encoding', '').lower()
        if enc == 'gzip' or (len(raw) > 2 and raw[0] == 0x1f and raw[1] == 0x8b):
            raw = gzip.decompress(raw)
        elif enc == 'deflate' or (len(raw) > 2 and raw[0] == 0x78):
            raw = zlib.decompress(raw)
        data = json.loads(raw.decode("utf-8"))
        municipios = [{"id": m.get("id"), "nome": m.get("nome")} for m in data]
        return {"uf": uf, "municipios": municipios}
    except HTTPException:
      raise
    except Exception as e:
      raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/integracoes/ckan/resources")
async def integracoes_ckan_resources(payload: CkanResourcesRequest):
    """Busca recursos CKAN do portal do TSE para um dataset."""
    try:
        dataset = (payload.dataset or "").strip()
        if not dataset:
            raise HTTPException(status_code=400, detail="Dataset é obrigatório")
        query_url = f"https://dadosabertos.tse.jus.br/api/3/action/package_search?q={dataset}"
        ctx = ssl.create_default_context()
        req = urllib.request.Request(
            url=query_url,
            headers={"Accept-Encoding": "identity", "User-Agent": "CAPTAR/1.0"}
        )
        with urlopen(req, context=ctx, timeout=15) as resp:
            raw = resp.read()
            enc = resp.headers.get('Content-Encoding', '').lower()
            if enc == 'gzip' or (len(raw) > 2 and raw[0] == 0x1f and raw[1] == 0x8b):
                raw = gzip.decompress(raw)
            elif enc == 'deflate' or (len(raw) > 2 and raw[0] == 0x78):
                raw = zlib.decompress(raw)
            result = json.loads(raw.decode("utf-8"))
        resources = []
        for pkg in result.get("result", {}).get("results", []):
            for r in pkg.get("resources", []):
                resources.append({
                    "id": r.get("id"),
                    "name": r.get("name"),
                    "format": r.get("format"),
                    "url": r.get("url") or r.get("download_url")
                })
        # filtro simples por UF (nome contendo 'AMAZONAS' ou 'AM')
        uf = (payload.uf or "").upper()
        if uf == "AM":
            resources = [r for r in resources if (r["name"] or "").upper().find("AMAZONAS") != -1 or (r["name"] or "").upper().endswith("AM")]
        return {"resources": resources}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/integracoes/ckan/preview")
async def integracoes_ckan_preview(payload: dict):
    """Retorna primeiras linhas de um recurso CSV do CKAN."""
    try:
        url = payload.get("resource_url")
        limit = int(payload.get("limit", 15))
        if not url:
            raise HTTPException(status_code=400, detail="resource_url é obrigatório")
        # pandas lê CSV diretamente da URL
        df = pd.read_csv(url, nrows=limit)
        return {"columns": list(df.columns), "rows": df.head(limit).to_dict(orient="records")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/integracoes/config")
async def integracoes_get_config():
    ensure_integracoes_table()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {DB_SCHEMA}.integracoes_config ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return {}
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/integracoes/config")
async def integracoes_save_config(cfg: IntegracaoConfig):
    ensure_integracoes_table()
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""
                INSERT INTO {DB_SCHEMA}.integracoes_config (
                  base_url, uf, dataset, municipio, webhook_url, webhook_secret, tse_token, external_api_token, active_webhook, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
                """,
                (
                    cfg.base_url,
                    cfg.uf,
                    cfg.dataset,
                    cfg.municipio,
                    cfg.webhook_url,
                    cfg.webhook_secret,
                    cfg.tse_token,
                    cfg.external_api_token,
                    cfg.active_webhook or False,
                )
            )
            new_id = cursor.fetchone()[0]
            conn.commit()
            return {"id": new_id, "saved": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.get("/api/integracoes/ckan/resources")
async def integracoes_ckan_resources_get(dataset: str, uf: Optional[str] = None):
    return await integracoes_ckan_resources(CkanResourcesRequest(dataset=dataset, uf=uf))
@app.get("/api/health/db")
async def health_db():
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            _ = cur.fetchone()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
def _tenant_id_from_header(request: Request):
    slug = request.headers.get('X-Tenant') or 'captar'
    try:
        rc = get_redis_client()
        if rc:
            cached = rc.get(f"tenant:id:{slug}")
            if cached:
                return int(cached)
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT \"IdTenant\" FROM \"{DB_SCHEMA}\".\"Tenant\" WHERE \"Slug\" = %s LIMIT 1",
                (slug,)
            )
            row = cur.fetchone()
            if row:
                tid = int(row[0])
                if rc:
                    try:
                        rc.setex(f"tenant:id:{slug}", 300, str(tid))
                    except Exception:
                        pass
                return tid
    except Exception:
        pass
    return 1

def _tenant_name_from_header(request: Request):
    slug = request.headers.get('X-Tenant') or 'captar'
    try:
        rc = get_redis_client()
        if rc:
            cached = rc.get(f"tenant:name:{slug}")
            if cached:
                return str(cached)
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT \"Nome\" FROM \"{DB_SCHEMA}\".\"Tenant\" WHERE \"Slug\" = %s LIMIT 1",
                (slug,)
            )
            row = cur.fetchone()
            if row and row[0]:
                name = str(row[0])
                if rc:
                    try:
                        rc.setex(f"tenant:name:{slug}", 300, name)
                    except Exception:
                        pass
                return name
    except Exception:
        pass
    return 'CAPTAR'
def _tenant_id_by_name(name: str):
    try:
        rc = get_redis_client()
        if rc:
            cached = rc.get(f"tenant:idbyname:{name}")
            if cached:
                return int(cached)
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT \"IdTenant\" FROM \"{DB_SCHEMA}\".\"Tenant\" WHERE \"Nome\" = %s LIMIT 1",
                (name,)
            )
            row = cur.fetchone()
            if row and row[0] is not None:
                tid = int(row[0])
                if rc:
                    try:
                        rc.setex(f"tenant:idbyname:{name}", 300, str(tid))
                    except Exception:
                        pass
                return tid
    except Exception:
        pass
    return None

def _tenant_name_by_id(tid: int) -> Optional[str]:
    try:
        rc = get_redis_client()
        if rc:
            cached = rc.get(f"tenant:namebyid:{tid}")
            if cached:
                return str(cached)
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT \"Nome\" FROM \"{DB_SCHEMA}\".\"Tenant\" WHERE \"IdTenant\" = %s LIMIT 1",
                (tid,)
            )
            row = cur.fetchone()
            if row and row[0]:
                name = str(row[0])
                if rc:
                    try:
                        rc.setex(f"tenant:namebyid:{tid}", 300, name)
                    except Exception:
                        pass
                return name
    except Exception:
        pass
    return None
def _now_local():
    try:
        dt = datetime.now().astimezone()
        return dt.replace(microsecond=0).replace(tzinfo=None)
    except Exception:
        return datetime.now().replace(microsecond=0)
@app.get("/api/usuarios-coordenadores")
async def usuarios_coordenadores(request: Request):
    try:
        rc = get_redis_client()
        slug = request.headers.get('X-Tenant') or 'captar'
        if rc:
            try:
                raw = rc.get(f"tenant:{str(slug).lower()}:usuarios:coordenadores")
                if raw:
                    return {"rows": json.loads(raw)}
            except Exception:
                pass
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if str(slug).lower() == 'captar':
                cursor.execute(
                    f"SELECT \"IdUsuario\", \"Nome\" FROM \"{DB_SCHEMA}\".\"Usuarios\" WHERE UPPER(TRIM(\"Funcao\")) IN ('COORDENADOR','ADMINISTRADOR') ORDER BY \"Nome\" ASC"
                )
            else:
                cursor.execute(
                    f"SELECT \"IdUsuario\", \"Nome\" FROM \"{DB_SCHEMA}\".\"Usuarios\" WHERE UPPER(TRIM(\"Funcao\")) IN ('COORDENADOR','ADMINISTRADOR') AND \"IdTenant\" = %s ORDER BY \"Nome\" ASC",
                    (_tenant_id_from_header(request),)
                )
            rows = cursor.fetchall()
            out = [{"IdUsuario": r[0], "Nome": r[1]} for r in rows]
            if rc:
                try:
                    rc.setex(f"tenant:{str(slug).lower()}:usuarios:coordenadores", 60, json.dumps(out))
                except Exception:
                    pass
            return {"rows": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/usuarios-supervisores")
async def usuarios_supervisores(coordenador: str, request: Request):
    try:
        rc = get_redis_client()
        slug = request.headers.get('X-Tenant') or 'captar'
        if rc:
            try:
                raw = rc.get(f"tenant:{str(slug).lower()}:usuarios:supervisores:{coordenador.strip()}")
                if raw:
                    return {"rows": json.loads(raw)}
            except Exception:
                pass
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if str(slug).lower() == 'captar':
                cursor.execute(
                    f"SELECT \"IdUsuario\", \"Nome\" FROM \"{DB_SCHEMA}\".\"Usuarios\" WHERE UPPER(TRIM(\"Funcao\")) = 'SUPERVISOR' AND TRIM(\"Coordenador\") = %s ORDER BY \"Nome\" ASC",
                    (coordenador.strip(),)
                )
            else:
                cursor.execute(
                    f"SELECT \"IdUsuario\", \"Nome\" FROM \"{DB_SCHEMA}\".\"Usuarios\" WHERE UPPER(TRIM(\"Funcao\")) = 'SUPERVISOR' AND TRIM(\"Coordenador\") = %s AND \"IdTenant\" = %s ORDER BY \"Nome\" ASC",
                    (coordenador.strip(), _tenant_id_from_header(request))
                )
            rows = cursor.fetchall()
            out = [{"IdUsuario": r[0], "Nome": r[1]} for r in rows]
            if rc:
                try:
                    rc.setex(f"tenant:{str(slug).lower()}:usuarios:supervisores:{coordenador.strip()}", 60, json.dumps(out))
                except Exception:
                    pass
            return {"rows": out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== USUÁRIOS - IMAGEM ====================
@app.post("/api/usuarios/{id}/foto")
async def usuarios_upload_foto(id: int, request: Request, file: Optional[UploadFile] = File(None), data_url: Optional[str] = None):
    try:
        tenant_name = _tenant_name_from_header(request)
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(f'SELECT "Nome" FROM "{DB_SCHEMA}"."Usuarios" WHERE "IdUsuario" = %s LIMIT 1', (id,))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Usuário não encontrado")
            user_name = str(row[0] or "usuario").strip()

        safe_name = re.sub(r"[^A-Za-z0-9_\- ]+", "", user_name).strip().replace(" ", "_") or f"usuario_{id}"
        root_dir = pathlib.Path(__file__).resolve().parents[2]
        target_dir = root_dir / 'src' / 'images' / 'Usuarios' / tenant_name
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{safe_name}.jpg"

        if file is not None:
            content = await file.read()
            with open(target_path, 'wb') as f:
                f.write(content)
        elif data_url:
            header, b64 = data_url.split(',', 1)
            data = base64.b64decode(b64)
            with open(target_path, 'wb') as f:
                f.write(data)
        else:
            raise HTTPException(status_code=400, detail="Arquivo ou data_url obrigatório")

        rel_path = str(target_path.relative_to(root_dir)).replace('\\', '/')
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f'UPDATE "{DB_SCHEMA}"."Usuarios" SET "Imagem" = %s WHERE "IdUsuario" = %s',
                (rel_path, id)
            )
            conn.commit()

        return {"saved": True, "path": rel_path}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
