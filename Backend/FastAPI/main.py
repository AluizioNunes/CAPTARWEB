"""
CAPTAR API - Extended Version with All Improvements
Integração de todas as 15 melhorias prioritárias
"""

from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, BackgroundTasks, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime, date, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
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
from typing import Any, List, Optional, Dict, Tuple, Union
import time
from urllib.request import urlopen
import urllib.request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, urlunparse
import ssl
import gzip
import zlib
import base64
import re
import pathlib
import aiohttp
import asyncio
import traceback
import uuid
import unicodedata

load_dotenv()

try:
    _MANAUS_TZ = ZoneInfo("America/Manaus") if ZoneInfo else timezone(timedelta(hours=-4))
except Exception:
    _MANAUS_TZ = timezone(timedelta(hours=-4))

def _attach_utc(dt: Any) -> Any:
    try:
        if isinstance(dt, datetime) and dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return dt

# Database Configuration
def _resolve_db_host() -> str:
    import socket
    env = os.getenv('DB_HOST', 'postgres') or 'postgres'
    s = str(env).strip().lower()
    if s in ('localhost', '127.0.0.1'):
        try:
            socket.getaddrinfo('postgres', None)
            return 'postgres'
        except Exception:
            return env
    try:
        socket.getaddrinfo(env, None)
        return env
    except Exception:
        return 'localhost'
def _resolve_host(h: str, fallback: str = 'localhost') -> str:
    import socket
    try:
        socket.getaddrinfo(h, None)
        return h
    except Exception:
        return fallback

DB_HOST = _resolve_db_host()
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

# Static Files
try:
    os.makedirs("static", exist_ok=True)
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    print(f"Warning: Could not mount static directory: {e}")

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

_IMAGE_DATA_URL_RE = re.compile(r'^data:(image/[a-zA-Z0-9.+-]+);base64,(.*)$', re.DOTALL)

def _guess_image_ext(b: bytes) -> str:
    if b.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if b.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if b.startswith(b'GIF87a') or b.startswith(b'GIF89a'):
        return 'gif'
    if b.startswith(b'RIFF') and b[8:12] == b'WEBP':
        return 'webp'
    return 'png'

def _normalize_campanha_imagem(raw: str, tid: int) -> Optional[str]:
    s = str(raw or '').strip()
    if not s:
        return None
    if s.startswith('http://') or s.startswith('https://') or s.startswith('/static/') or s.startswith('static/'):
        return s if s.startswith('/') else f'/{s}'
    if s.startswith('data:'):
        m = _IMAGE_DATA_URL_RE.match(s)
        if not m:
            return None
        mime = m.group(1)
        b64 = m.group(2)
        ext = (mime.split('/')[-1] or 'png').lower()
        if ext == 'jpeg':
            ext = 'jpg'
        data = base64.b64decode(b64)
        os.makedirs(os.path.join(os.getcwd(), 'static', 'campanhas'), exist_ok=True)
        filename = f'{tid}_{uuid.uuid4().hex}.{ext}'
        full_path = os.path.join(os.getcwd(), 'static', 'campanhas', filename)
        with open(full_path, 'wb') as f:
            f.write(data)
        return f'/static/campanhas/{filename}'
    try:
        data = base64.b64decode(s)
    except Exception:
        if s.startswith('/'):
            return s
        return s
    if not data:
        return None
    ext = _guess_image_ext(data)
    os.makedirs(os.path.join(os.getcwd(), 'static', 'campanhas'), exist_ok=True)
    filename = f'{tid}_{uuid.uuid4().hex}.{ext}'
    full_path = os.path.join(os.getcwd(), 'static', 'campanhas', filename)
    with open(full_path, 'wb') as f:
        f.write(data)
    return f'/static/campanhas/{filename}'

@contextmanager
def get_db_connection(dsn: str | None = None):
    use_dsn = (dsn.strip() if (dsn and dsn.strip()) else f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    conn = None
    try:
        conn = psycopg.connect(use_dsn)
    except Exception:
        if not dsn:
            try:
                alt_dsn = f"postgresql://{DB_USER}:{DB_PASSWORD}@postgres:{DB_PORT}/{DB_NAME}"
                conn = psycopg.connect(alt_dsn)
                use_dsn = alt_dsn
            except Exception:
                raise
    try:
        prev_autocommit = conn.autocommit
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f'SET search_path TO "{DB_SCHEMA}", public')
        conn.autocommit = prev_autocommit
        yield conn
        try:
            if not conn.autocommit:
                conn.commit()
        except Exception:
            pass
    except Exception:
        try:
            if not conn.autocommit:
                conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass

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
            s = str(slug).lower()
            cur.execute(f'SELECT "IdTenant","Dsn" FROM "{DB_SCHEMA}"."Tenant" WHERE LOWER("Slug")=%s LIMIT 1', (s,))
            row = cur.fetchone()
            if row:
                idt = int(row[0] or 0)
                dsn = str(row[1] or '')
                if dsn:
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
                return None
    except Exception:
        pass
    _DSN_CACHE.pop(slug, None)
    return None

def get_conn_for_request(request: Request):
    slug = request.headers.get('X-Tenant') or 'captar'
    if str(slug).lower() == 'captar':
        return get_db_connection()
    dsn = _get_dsn_by_slug(str(slug).lower())
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

def rate_limit(request: Request, key: str, window_sec: int = 60, limit: int = 100):
    try:
        rc = get_redis_client()
        slug = request.headers.get('X-Tenant') or 'captar'
        ip = request.client.host if hasattr(request, 'client') and request.client else 'local'
        k = f"rl:{slug}:{key}:{ip}"
        if rc:
            cur = rc.get(k)
            n = int(cur) if cur and str(cur).isdigit() else 0
            n += 1
            if n == 1:
                rc.setex(k, window_sec, str(n))
            else:
                rc.set(k, str(n))
            if n > limit:
                raise HTTPException(status_code=429, detail='Too Many Requests')
    except Exception:
        pass

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

def _set_tenant_dsn(id_tenant: int, dsn: str):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(f'UPDATE "{DB_SCHEMA}"."Tenant" SET "Dsn"=%s, "DbCreatedAt"=COALESCE("DbCreatedAt", NOW()), "DataUpdate"=NOW() WHERE "IdTenant"=%s', (dsn, id_tenant))
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
        _set_tenant_dsn(tid, chosen)
        actions = apply_migrations_dsn(chosen, slug)
        _seed_pf_funcoes_for_tenant(tid)
        actions.append('pf_funcoes seeded (central)')
        return {"ok": True, "idTenant": tid, "actions": actions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== CONFIGURAÇÕES & INTEGRAÇÕES ====================

_EVOLUTION_INSTANCE_COLS: Tuple[List[str], float] = ([], 0.0)

def _evolution_instance_columns(conn) -> List[str]:
    now = time.time()
    cols, exp = _EVOLUTION_INSTANCE_COLS
    if cols and exp > now:
        return cols
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """,
        ("EvolutionAPI", "Instance"),
    )
    rows = cursor.fetchall()
    cols = [str(r[0]) for r in rows] if rows else []
    globals()["_EVOLUTION_INSTANCE_COLS"] = (cols, now + 300.0)
    return cols

def _pick_column(cols: List[str], candidates: List[str]) -> Optional[str]:
    m = {str(c).lower(): str(c) for c in (cols or [])}
    for cand in candidates:
        k = str(cand).lower()
        if k in m:
            return m[k]
    return None

def _evolution_instance_fields(conn) -> Dict[str, Optional[str]]:
    cols = _evolution_instance_columns(conn)
    id_col = _pick_column(cols, ["id", "Id", "ID"])
    name_col = _pick_column(cols, ["name", "Name", "instanceName", "InstanceName"])
    token_col = _pick_column(cols, ["token", "Token", "apiKey", "ApiKey", "apikey"])
    status_col = _pick_column(cols, ["connectionStatus", "ConnectionStatus", "status", "Status"])
    number_col = _pick_column(cols, ["number", "Number", "phone", "phoneNumber", "celular", "whatsapp", "ownerJid"])
    if not id_col or not name_col:
        raise HTTPException(status_code=500, detail='Tabela "EvolutionAPI"."Instance" inválida (colunas ausentes).')
    return {"id": id_col, "name": name_col, "token": token_col, "status": status_col, "number": number_col}

def _get_evolution_base_url(conn) -> str:
    base = str(os.getenv("EVOLUTION_API_BASE", "") or "").strip() or str(os.getenv("WHATSAPP_API_URL", "") or "").strip()
    if base:
        return str(base).rstrip("/")
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s AND lower(table_name) = lower(%s)
            LIMIT 1
            """,
            (DB_SCHEMA, "EvolutionAPIFallback"),
        )
        row = cur.fetchone()
        if row and row[0]:
            safe_schema = str(DB_SCHEMA).replace('"', '""')
            safe_table = str(row[0]).replace('"', '""')
            cur.execute(
                f'SELECT valor FROM "{safe_schema}"."{safe_table}" WHERE chave=%s LIMIT 1',
                ("WHATSAPP_API_URL",),
            )
            row2 = cur.fetchone()
            if row2 and row2[0]:
                return str(row2[0]).strip().rstrip("/")
    except Exception:
        pass
    return "http://evolution_api:4000"

def _list_evolution_instances(conn) -> List[dict]:
    f = _evolution_instance_fields(conn)
    id_sel = f"\"{f['id']}\"::text"
    token_sel = f"\"{f['token']}\"" if f.get("token") else "NULL::text"
    status_sel = f"\"{f['status']}\"" if f.get("status") else "NULL::text"
    number_sel = f"\"{f['number']}\"" if f.get("number") else "NULL::text"
    cursor = conn.cursor()
    cursor.execute(
        f"""
        SELECT {id_sel}, "{f['name']}", {number_sel}, {token_sel}, {status_sel}
        FROM "EvolutionAPI"."Instance"
        ORDER BY "{f['name']}" ASC
        """
    )
    rows = cursor.fetchall() or []
    out = []
    for r in rows:
        out.append(
            {
                "id": str(r[0] or "").strip(),
                "name": str(r[1] or "").strip(),
                "number": str(r[2] or "").strip(),
                "hasToken": bool(str(r[3] or "").strip()),
                "connectionStatus": str(r[4] or "").strip(),
            }
        )
    return out

def _get_evolution_instance(conn, instance_id: Optional[Union[str, int]]) -> Dict[str, Any]:
    f = _evolution_instance_fields(conn)
    id_sel = f"\"{f['id']}\"::text"
    token_sel = f"\"{f['token']}\"" if f.get("token") else "NULL::text"
    status_sel = f"\"{f['status']}\"" if f.get("status") else "NULL::text"
    number_sel = f"\"{f['number']}\"" if f.get("number") else "NULL::text"
    cursor = conn.cursor()
    chosen_id = str(instance_id).strip() if instance_id is not None else ""
    if chosen_id:
        cursor.execute(
            f"""
            SELECT {id_sel}, "{f['name']}", {number_sel}, {token_sel}, {status_sel}
            FROM "EvolutionAPI"."Instance"
            WHERE "{f['id']}"::text=%s
            LIMIT 1
            """,
            (chosen_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Instância Evolution API não encontrada.")
    else:
        row = None
        if f.get("status"):
            try:
                cursor.execute(
                    f"""
                    SELECT {id_sel}, "{f['name']}", {number_sel}, {token_sel}, {status_sel}
                    FROM "EvolutionAPI"."Instance"
                    WHERE "{f['status']}"=%s
                    ORDER BY "{f['name']}" ASC
                    LIMIT 1
                    """,
                    ("CONNECTED",),
                )
                row = cursor.fetchone()
            except Exception:
                row = None
        if not row:
            cursor.execute(
                f"""
                SELECT {id_sel}, "{f['name']}", {number_sel}, {token_sel}, {status_sel}
                FROM "EvolutionAPI"."Instance"
                ORDER BY "{f['name']}" ASC
                LIMIT 1
                """
            )
            row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=500, detail="Nenhuma instância Evolution API encontrada no banco.")
    inst_name = str(row[1] or "").strip()
    number = str(row[2] or "").strip()
    token = str(row[3] or "").strip()
    status = str(row[4] or "").strip()
    if not inst_name:
        raise HTTPException(status_code=500, detail="Instância Evolution API inválida (name vazio).")
    return {"id": str(row[0] or "").strip(), "name": inst_name, "number": number, "token": token, "connectionStatus": status}

def _evolution_base_url_candidates(base_url: str) -> List[str]:
    s = str(base_url or "").strip()
    if not s:
        return []
    if not re.match(r"^https?://", s, re.IGNORECASE):
        s = f"http://{s}"
    p = urlparse(s)
    host = (p.hostname or "").strip().lower()
    scheme = (p.scheme or "http").strip().lower()
    port = p.port
    path = (p.path or "").rstrip("/")
    netloc = p.netloc
    if port is None and p.hostname:
        netloc = p.hostname
    primary = urlunparse((scheme, netloc, path, "", "", "")).rstrip("/")
    out: List[str] = []
    def add(u: str):
        uu = str(u or "").strip().rstrip("/")
        if uu and uu not in out:
            out.append(uu)
    add(primary)
    if scheme == "https":
        add(urlunparse(("http", netloc, path, "", "", "")).rstrip("/"))
    if host == "evolution_api":
        if port == 4400:
            add(urlunparse(("http", "evolution_api:4000", path, "", "", "")).rstrip("/"))
            add(urlunparse(("https", "evolution_api:4000", path, "", "", "")).rstrip("/"))
        if port is None:
            add(urlunparse((scheme, "evolution_api:4000", path, "", "", "")).rstrip("/"))
        if port == 80:
            add(urlunparse((scheme, "evolution_api:4000", path, "", "", "")).rstrip("/"))
        if port == 443:
            add(urlunparse(("http", "evolution_api:4000", path, "", "", "")).rstrip("/"))
    return out

@app.get("/api/integracoes/evolution/instances")
async def integracoes_evolution_instances():
    try:
        with get_db_connection() as conn:
            rows = _list_evolution_instances(conn)
        return {"rows": rows}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class WhatsAppSendRequest(BaseModel):
    phone: str
    message: str
    media_url: Optional[str] = None
    media_type: Optional[str] = "image"
    text_position: Optional[str] = "bottom" # bottom (caption) or top (text then image)
    campanha_id: Optional[int] = None
    contato_nome: Optional[str] = None
    evolution_api_id: Optional[str] = None

@app.post("/api/integrations/whatsapp/send")
async def send_whatsapp_message(data: WhatsAppSendRequest, request: Request):
    try:
        evo = None
        with get_conn_for_request(request) as conn:
            evo = _get_evolution_instance(conn, data.evolution_api_id)
            base_url = _get_evolution_base_url(conn)
        instance = evo["name"]
        api_key = str(evo.get("token") or "").strip() or str(os.getenv("AUTHENTICATION_API_KEY", "") or "").strip()
        if not api_key:
            raise HTTPException(status_code=500, detail="Token da instância Evolution API não encontrado.")
        base_candidates = _evolution_base_url_candidates(base_url)
        if not base_candidates:
            raise HTTPException(status_code=500, detail="Configuração da Evolution API incompleta no servidor.")
            
        # 1.5. Resolve Media URL if local filename
        final_media_url = data.media_url
        if final_media_url:
            s_media = str(final_media_url).strip()
            # If not http/https and not data: -> assume local file in static/campanhas
            if not s_media.startswith('http') and not s_media.startswith('data:'):
                media_base_url = os.getenv("WHATSAPP_MEDIA_BASE_URL")
                if not media_base_url:
                    fastapi_host_port = os.getenv("FASTAPI_HOST_PORT", "8001")
                    media_base_url = f"http://host.docker.internal:{fastapi_host_port}"
                media_base_url = str(media_base_url).rstrip("/")
                if s_media.startswith('/static/') or s_media.startswith('/'):
                    final_media_url = f"{media_base_url}{s_media}"
                elif s_media.startswith('static/'):
                    final_media_url = f"{media_base_url}/{s_media}"
                else:
                    final_media_url = f"{media_base_url}/static/campanhas/{s_media}"
                print(f"Resolved local media path '{s_media}' to '{final_media_url}'")

        # 2. Call Evolution API
        headers = {
            "apikey": api_key,
            "Content-Type": "application/json"
        }

        async with aiohttp.ClientSession() as session:
            last_conn_err = None
            for base_try in base_candidates:
                try:
                    if final_media_url and data.text_position == 'top':
                        msg = str(data.message or '').strip()
                        if msg:
                            url_text = f"{base_try}/message/sendText/{instance}"
                            payload_text = {
                                "number": data.phone,
                                "text": msg,
                                "delay": 1200,
                                "linkPreview": True
                            }
                            print(f"Sending WhatsApp TEXT (TOP) to URL: {url_text}")
                            async with session.post(url_text, json=payload_text, headers=headers, timeout=30) as resp_text:
                                if resp_text.status not in (200, 201):
                                    text = await resp_text.text()
                                    print(f"Evolution API Error (Text): {resp_text.status} - {text}")
                                    code = resp_text.status if resp_text.status < 500 else 502
                                    raise HTTPException(status_code=code, detail=f"Erro na API WhatsApp (Texto): {text}")
                        
                        url_media = f"{base_try}/message/sendMedia/{instance}"
                        print(f"Sending WhatsApp MEDIA (TOP) to URL: {url_media}")
                        payload_media = {
                            "number": data.phone,
                            "mediatype": "image",
                            "media": final_media_url,
                            "delay": 1200,
                            "linkPreview": True
                        }
                        async with session.post(url_media, json=payload_media, headers=headers, timeout=30) as resp_media:
                            if resp_media.status not in (200, 201):
                                text = await resp_media.text()
                                code = resp_media.status if resp_media.status < 500 else 502
                                raise HTTPException(status_code=code, detail=f"Erro na API WhatsApp (Mídia): {text}")
                            resp_json = await resp_media.json()
                            try:
                                with get_conn_for_request(request) as conn_log:
                                    cursor_log = conn_log.cursor()
                                    tid_log = _tenant_id_from_header(request)
                                    cursor_log.execute(
                                        f"""
                                        INSERT INTO "{DB_SCHEMA}"."Disparos"
                                        ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload")
                                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW() AT TIME ZONE 'UTC',%s::jsonb)
                                        """,
                                        (
                                            tid_log,
                                            data.campanha_id,
                                            'WHATSAPP',
                                            'OUT',
                                            _digits_only(data.phone),
                                            (data.contato_nome or None),
                                            (data.message or ''),
                                            (final_media_url or None),
                                            'ENVIADO',
                                            json.dumps(resp_json, ensure_ascii=False),
                                        ),
                                    )
                                    conn_log.commit()
                            except Exception:
                                pass
                            return resp_json

                    if final_media_url:
                        url = f"{base_try}/message/sendMedia/{instance}"
                        print(f"Sending WhatsApp MEDIA (BOTTOM) to URL: {url} with Instance: {instance}")
                        payload = {
                            "number": data.phone,
                            "mediatype": "image",
                            "caption": data.message,
                            "media": final_media_url,
                            "delay": 1200,
                            "linkPreview": True
                        }
                        async with session.post(url, json=payload, headers=headers, timeout=30) as response:
                            if response.status not in (200, 201):
                                text = await response.text()
                                print(f"Evolution API Error: {response.status} - {text}")
                                code = response.status if response.status < 500 else 502
                                raise HTTPException(status_code=code, detail=f"Erro na API WhatsApp: {text}")
                            resp_json = await response.json()
                            try:
                                with get_conn_for_request(request) as conn_log:
                                    cursor_log = conn_log.cursor()
                                    tid_log = _tenant_id_from_header(request)
                                    cursor_log.execute(
                                        f"""
                                        INSERT INTO "{DB_SCHEMA}"."Disparos"
                                        ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload")
                                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW() AT TIME ZONE 'UTC',%s::jsonb)
                                        """,
                                        (
                                            tid_log,
                                            data.campanha_id,
                                            'WHATSAPP',
                                            'OUT',
                                            _digits_only(data.phone),
                                            (data.contato_nome or None),
                                            (data.message or ''),
                                            (final_media_url or None),
                                            'ENVIADO',
                                            json.dumps(resp_json, ensure_ascii=False),
                                        ),
                                    )
                                    conn_log.commit()
                            except Exception:
                                pass
                            return resp_json
                    
                    url = f"{base_try}/message/sendText/{instance}"
                    print(f"Sending WhatsApp TEXT to URL: {url} with Instance: {instance}")
                    payload = {
                        "number": data.phone,
                        "text": data.message,
                        "delay": 1200,
                        "linkPreview": True
                    }
                    async with session.post(url, json=payload, headers=headers, timeout=30) as response:
                        if response.status not in (200, 201):
                            text = await response.text()
                            print(f"Evolution API Error: {response.status} - {text}")
                            code = response.status if response.status < 500 else 502
                            raise HTTPException(status_code=code, detail=f"Erro na API WhatsApp: {text}")
                        resp_json = await response.json()
                        try:
                            with get_conn_for_request(request) as conn_log:
                                cursor_log = conn_log.cursor()
                                tid_log = _tenant_id_from_header(request)
                                cursor_log.execute(
                                    f"""
                                    INSERT INTO "{DB_SCHEMA}"."Disparos"
                                    ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload")
                                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW() AT TIME ZONE 'UTC',%s::jsonb)
                                    """,
                                    (
                                        tid_log,
                                        data.campanha_id,
                                        'WHATSAPP',
                                        'OUT',
                                        _digits_only(data.phone),
                                        (data.contato_nome or None),
                                        (data.message or ''),
                                        None,
                                        'ENVIADO',
                                        json.dumps(resp_json, ensure_ascii=False),
                                    ),
                                )
                                conn_log.commit()
                        except Exception:
                            pass
                        return resp_json
                except HTTPException:
                    raise
                except (aiohttp.ClientConnectorError, aiohttp.ClientConnectionError, asyncio.TimeoutError, OSError) as ce:
                    last_conn_err = ce
                    continue
            if last_conn_err:
                raise HTTPException(status_code=502, detail=f"Falha ao conectar na Evolution API. BaseUrl={base_url}. Tentativas={base_candidates}. Erro={str(last_conn_err)}")
            raise HTTPException(status_code=502, detail="Falha ao enviar mensagem no WhatsApp.")

    except HTTPException as he:
        try:
            with get_conn_for_request(request) as conn_log:
                cursor_log = conn_log.cursor()
                tid_log = _tenant_id_from_header(request)
                cursor_log.execute(
                    f"""
                    INSERT INTO "{DB_SCHEMA}"."Disparos"
                    ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload")
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW() AT TIME ZONE 'UTC',%s::jsonb)
                    """,
                    (
                        tid_log,
                        data.campanha_id,
                        'WHATSAPP',
                        'OUT',
                        _digits_only(data.phone),
                        (data.contato_nome or None),
                        (data.message or ''),
                        (data.media_url or None),
                        'FALHA',
                        json.dumps({"error": he.detail}, ensure_ascii=False),
                    ),
                )
                conn_log.commit()
        except Exception:
            pass
        raise he
    except Exception as e:
        print(f"Error sending whatsapp: {e}")
        traceback.print_exc()
        try:
            with get_conn_for_request(request) as conn_log:
                cursor_log = conn_log.cursor()
                tid_log = _tenant_id_from_header(request)
                cursor_log.execute(
                    f"""
                    INSERT INTO "{DB_SCHEMA}"."Disparos"
                    ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload")
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW() AT TIME ZONE 'UTC',%s::jsonb)
                    """,
                    (
                        tid_log,
                        data.campanha_id,
                        'WHATSAPP',
                        'OUT',
                        _digits_only(data.phone),
                        (data.contato_nome or None),
                        (data.message or ''),
                        (data.media_url or None),
                        'FALHA',
                        json.dumps({"error": str(e)}, ensure_ascii=False),
                    ),
                )
                conn_log.commit()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))

def _digits_only(s: Any) -> str:
    try:
        return ''.join([c for c in str(s or '') if c.isdigit()])
    except Exception:
        return ''

def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    try:
        return str(value)
    except Exception:
        return None

def _format_dt_br(v: Any) -> str:
    try:
        if v is None:
            return ''
        if isinstance(v, datetime):
            if v.tzinfo is not None:
                return v.astimezone(_MANAUS_TZ).strftime('%d/%m/%Y %H:%M:%S')
            return v.strftime('%d/%m/%Y %H:%M:%S')
        if isinstance(v, date):
            return v.strftime('%d/%m/%Y')
        s = str(v)
        if not s:
            return ''
        try:
            dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
            if dt.tzinfo is not None:
                return dt.astimezone(_MANAUS_TZ).strftime('%d/%m/%Y %H:%M:%S')
            return dt.strftime('%d/%m/%Y %H:%M:%S')
        except Exception:
            return s
    except Exception:
        return ''

def _truncate_text(v: Any, max_len: int = 80) -> str:
    try:
        s = str(v or '')
        s = re.sub(r'\s+', ' ', s).strip()
        if len(s) <= max_len:
            return s
        if max_len <= 3:
            return s[:max_len]
        return s[: max_len - 3] + '...'
    except Exception:
        return ''

def _normalize_resposta_classificacao(v: Any) -> str:
    s = str(v or '').strip().upper()
    if not s:
        return 'AGUARDANDO'
    if s in ('POSITIVO', 'SIM', 'YES', 'TRUE', 'OK'):
        return 'POSITIVO'
    if s in ('NEGATIVO', 'NAO', 'NÃO', 'NO', 'FALSE'):
        return 'NEGATIVO'
    if s in ('AGUARDANDO', 'PENDENTE', 'PENDING', 'WAITING', 'EM_ABERTO'):
        return 'AGUARDANDO'
    return s

def _safe_json_obj(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except Exception:
            return None
    return None

def _contact_phone_raw(c: Any) -> Any:
    if not isinstance(c, dict):
        return None
    return (
        c.get('whatsapp')
        or c.get('celular')
        or c.get('telefone')
        or c.get('phone')
        or c.get('numero')
        or c.get('Número')
        or c.get('Numero')
        or c.get('destino')
        or c.get('Destinatario')
        or c.get('destinatario')
        or c.get('to')
    )

def _contact_name_raw(c: Any) -> Any:
    if not isinstance(c, dict):
        return None
    return (
        c.get('nome')
        or c.get('Nome')
        or c.get('NOME')
        or c.get('nome_destinatario')
        or c.get('nomeDestinatario')
        or c.get('nome_destino')
        or c.get('destinatario_nome')
    )

def _anexo_contacts_list(anexo_obj: Any) -> List[dict]:
    if anexo_obj is None:
        return []
    if isinstance(anexo_obj, list):
        return [x for x in anexo_obj if isinstance(x, dict)]
    if isinstance(anexo_obj, dict):
        contacts = anexo_obj.get('contacts')
        if isinstance(contacts, list):
            return [x for x in contacts if isinstance(x, dict)]
    return []

def _anexo_question(anexo_obj: Any) -> str:
    if not isinstance(anexo_obj, dict):
        return ''
    cfg = anexo_obj.get('config')
    if not isinstance(cfg, dict):
        return ''
    q = cfg.get('question') or cfg.get('pergunta') or cfg.get('texto') or cfg.get('mensagem')
    return str(q or '').strip()

def _campanha_contacts(
    cursor,
    *,
    tid: int,
    campanha_id: int,
    anexo_obj: Any,
    limit: int = 20000,
) -> List[Dict[str, Any]]:
    if isinstance(anexo_obj, dict) and bool(anexo_obj.get('usar_eleitores') or False):
        cursor.execute(
            f"""
            SELECT "Nome", COALESCE(NULLIF("Celular", ''), NULLIF("Telefone", ''))
            FROM "{DB_SCHEMA}"."Eleitores"
            WHERE "IdTenant" = %s
              AND COALESCE(NULLIF("Celular", ''), NULLIF("Telefone", '')) IS NOT NULL
            ORDER BY "IdEleitor" DESC
            LIMIT %s
            """,
            (tid, int(limit)),
        )
        out: List[Dict[str, Any]] = []
        for nome, num in cursor.fetchall() or []:
            numero = _digits_only(num)
            if not numero:
                continue
            out.append({"nome": str(nome or '').strip() or '—', "numero": numero})
        return out

    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for c in _anexo_contacts_list(anexo_obj)[: int(limit)]:
        numero = _digits_only(_contact_phone_raw(c))
        if not numero or numero in seen:
            continue
        seen.add(numero)
        nome = str(_contact_name_raw(c) or '').strip() or '—'
        out.append({"nome": nome, "numero": numero})
    return out

def _campanha_disparos_grid(
    cursor,
    *,
    tid: int,
    campanha_id: int,
    limit_contacts: int = 20000,
    limit_logs: int = 200000,
) -> Tuple[Dict[str, Any], str, Dict[str, int], List[Dict[str, Any]]]:
    def _to_utc_naive(dt: Optional[datetime]) -> Optional[datetime]:
        try:
            if dt is None:
                return None
            if isinstance(dt, datetime) and dt.tzinfo is not None:
                return dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except Exception:
            return dt

    def _parse_iso_dt(v: Any) -> Optional[datetime]:
        try:
            if v is None:
                return None
            if isinstance(v, datetime):
                return _to_utc_naive(v)
            if isinstance(v, (int, float)):
                if v <= 0:
                    return None
                return datetime.utcfromtimestamp(float(v))
            s = str(v or '').strip()
            if not s:
                return None
            try:
                return _to_utc_naive(datetime.fromisoformat(s.replace('Z', '+00:00')))
            except Exception:
                return None
        except Exception:
            return None

    cursor.execute(
        f"""
        SELECT "IdCampanha" as id,
               "NomeCampanha" as nome,
               "Texto" as descricao,
               "Cadastrante" as cadastrante,
               "DataCriacao" as criado_em,
               "DataInicio" as data_inicio,
               "DataFim" as data_fim,
               "AnexoJSON" as anexo_json
        FROM "{DB_SCHEMA}"."Campanhas"
        WHERE "IdCampanha" = %s AND "IdTenant" = %s
        """,
        (int(campanha_id), int(tid)),
    )
    campanha_row = cursor.fetchone()
    if not campanha_row:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    cols_c = [d[0] for d in cursor.description]
    campanha_obj = dict(zip(cols_c, campanha_row))
    for k, v in list(campanha_obj.items()):
        campanha_obj[k] = _attach_utc(v)

    anexo_obj = _safe_json_obj(campanha_obj.get('anexo_json'))
    pergunta = _anexo_question(anexo_obj) or str(campanha_obj.get('descricao') or '').strip()

    contatos = _campanha_contacts(cursor, tid=tid, campanha_id=campanha_id, anexo_obj=anexo_obj, limit=limit_contacts)
    by_num: Dict[str, Dict[str, Any]] = {}
    by_num_last11: Dict[str, Optional[Dict[str, Any]]] = {}
    for c in contatos:
        numero = _digits_only(c.get('numero'))
        if not numero:
            continue
        ent = {
            "numero": numero,
            "nome": str(c.get('nome') or '').strip() or '—',
            "envio_datahora": None,
            "envio_status": None,
            "resposta_datahora": None,
            "resposta_classificacao": None,
            "resposta_texto": None,
        }
        by_num[numero] = ent
        k11 = numero[-11:] if len(numero) > 11 else numero
        prev = by_num_last11.get(k11)
        if prev is None and k11 in by_num_last11:
            continue
        if prev is not None and prev is not ent:
            by_num_last11[k11] = None
        else:
            by_num_last11[k11] = ent

    def _find_ent(numero_digits: str) -> Optional[Dict[str, Any]]:
        if not numero_digits:
            return None
        direct = by_num.get(numero_digits)
        if direct is not None:
            return direct
        k11 = numero_digits[-11:] if len(numero_digits) > 11 else numero_digits
        ent = by_num_last11.get(k11)
        return ent if ent is not None else None

    try:
        for c in _anexo_contacts_list(anexo_obj)[: int(limit_contacts)]:
            if not isinstance(c, dict):
                continue
            numero = _digits_only(_contact_phone_raw(c))
            if not numero:
                continue
            ent = _find_ent(numero)
            if ent is None:
                continue
            nome = str(_contact_name_raw(c) or '').strip()
            if nome:
                ent['nome'] = nome
            status_val = str(c.get('status') or '').strip().lower()
            if status_val == 'success':
                ent['envio_status'] = 'ENVIADO'
                sent_dt = _parse_iso_dt(c.get('enviado_em') or c.get('enviadoEm') or c.get('sent_at') or c.get('sentAt'))
                cur_dt = _to_utc_naive(ent.get('envio_datahora')) if isinstance(ent.get('envio_datahora'), datetime) else None
                if sent_dt and (cur_dt is None or sent_dt >= cur_dt):
                    ent['envio_datahora'] = sent_dt
            elif status_val == 'error':
                if not ent.get('envio_status'):
                    ent['envio_status'] = 'FALHA'
                sent_dt = _parse_iso_dt(c.get('enviado_em') or c.get('enviadoEm') or c.get('sent_at') or c.get('sentAt'))
                if sent_dt and ent.get('envio_datahora') is None:
                    ent['envio_datahora'] = sent_dt

            resposta_val = c.get('resposta')
            if resposta_val is None:
                resposta_val = c.get('response')
            if resposta_val is None:
                resposta_val = c.get('Resposta')
            if resposta_val is None:
                resposta_val = c.get('RESP')
            if resposta_val in (1, '1', True, 'SIM', 'sim', 'S', 's'):
                ent['resposta_classificacao'] = 'POSITIVO'
            elif resposta_val in (2, '2', False, 'NAO', 'NÃO', 'nao', 'não', 'N', 'n'):
                ent['resposta_classificacao'] = 'NEGATIVO'
            responded_dt = _parse_iso_dt(c.get('respondido_em') or c.get('respondidoEm') or c.get('replied_at') or c.get('repliedAt'))
            cur_resp_dt = _to_utc_naive(ent.get('resposta_datahora')) if isinstance(ent.get('resposta_datahora'), datetime) else None
            if responded_dt and (cur_resp_dt is None or responded_dt >= cur_resp_dt):
                ent['resposta_datahora'] = responded_dt
    except Exception:
        pass

    cursor.execute(
        f"""
        SELECT "Direcao" as direcao,
               "Numero" as numero,
               "Nome" as nome,
               "Status" as status,
               "DataHora" as datahora,
               "Mensagem" as mensagem,
               "RespostaClassificacao" as resposta
        FROM "{DB_SCHEMA}"."Disparos"
        WHERE "IdTenant" = %s AND "IdCampanha" = %s
        ORDER BY "IdDisparo" ASC
        LIMIT %s
        """,
        (int(tid), int(campanha_id), int(limit_logs)),
    )
    disp_rows = cursor.fetchall()
    disp_cols = [d[0] for d in cursor.description]
    for r in disp_rows or []:
        d = dict(zip(disp_cols, r))
        numero = _digits_only(d.get('numero'))
        if not numero:
            continue
        ent = _find_ent(numero)
        if ent is None:
            continue
        direcao = str(d.get('direcao') or '').upper()
        datahora = _to_utc_naive(d.get('datahora')) if isinstance(d.get('datahora'), datetime) else d.get('datahora')
        status = str(d.get('status') or '').upper()
        nome = str(d.get('nome') or '').strip()
        mensagem = d.get('mensagem')
        resposta = d.get('resposta')

        if nome and (ent.get('nome') in (None, '', '—')):
            ent['nome'] = nome

        if direcao == 'OUT':
            cur_dt = ent.get('envio_datahora')
            if (cur_dt is None) or (isinstance(datahora, datetime) and isinstance(cur_dt, datetime) and datahora >= cur_dt) or (cur_dt is None and datahora):
                ent['envio_datahora'] = datahora
                ent['envio_status'] = status or '—'
        elif direcao == 'IN':
            cur_dt = ent.get('resposta_datahora')
            if (cur_dt is None) or (isinstance(datahora, datetime) and isinstance(cur_dt, datetime) and datahora >= cur_dt) or (cur_dt is None and datahora):
                ent['resposta_datahora'] = datahora
                ent['resposta_classificacao'] = _normalize_resposta_classificacao(resposta)
                ent['resposta_texto'] = mensagem

    linhas: List[Dict[str, Any]] = []
    for ent in by_num.values():
        if not ent.get('envio_status'):
            ent['envio_status'] = 'PENDENTE'
        if not ent.get('resposta_classificacao'):
            ent['resposta_classificacao'] = 'AGUARDANDO'
        if not ent.get('resposta_texto'):
            ent['resposta_texto'] = '—'
        for k, v in list(ent.items()):
            ent[k] = _attach_utc(v)
        linhas.append(ent)
    linhas.sort(key=lambda x: (str(x.get('nome') or ''), str(x.get('numero') or '')))

    enviados = 0
    falhas = 0
    respostas_qtd = 0
    positivos = 0
    negativos = 0
    aguardando = 0
    for it in linhas:
        envio_status = str(it.get('envio_status') or '').upper()
        if envio_status == 'ENVIADO':
            enviados += 1
        if envio_status == 'FALHA':
            falhas += 1
        if it.get('resposta_datahora'):
            respostas_qtd += 1
        rc = _normalize_resposta_classificacao(it.get('resposta_classificacao'))
        if rc == 'POSITIVO':
            positivos += 1
        elif rc == 'NEGATIVO':
            negativos += 1
        else:
            aguardando += 1

    stats_obj = {
        "enviados": enviados,
        "falhas": falhas,
        "respostas": respostas_qtd,
        "positivos": positivos,
        "negativos": negativos,
        "aguardando": aguardando,
        "total_contatos": len(linhas),
    }
    return campanha_obj, pergunta, stats_obj, linhas

def _find_captar_logo_path() -> Optional[str]:
    candidates: List[Union[str, pathlib.Path]] = []
    env_path = os.getenv('CAPTAR_LOGO_PATH') or ''
    if env_path.strip():
        candidates.append(env_path.strip())

    try:
        here = pathlib.Path(__file__).resolve()
        root = here.parent
        if len(here.parents) >= 3:
            root = here.parents[2]

        candidates.extend([
            root / 'src' / 'images' / 'CAPTAR LOGO OFICIAL.jpg',
            root / 'src' / 'images' / 'CAPTAR LOGO OFICIAL.jpeg',
            root / 'src' / 'images' / 'CAPTAR LOGO OFICIAL.png',
        ])
        candidates.extend([
            pathlib.Path.cwd() / 'src' / 'images' / 'CAPTAR LOGO OFICIAL.jpg',
            pathlib.Path.cwd() / 'src' / 'images' / 'CAPTAR LOGO OFICIAL.jpeg',
            pathlib.Path.cwd() / 'src' / 'images' / 'CAPTAR LOGO OFICIAL.png',
        ])
        candidates.extend([
            here.parent / 'static' / 'captar_logo.jpg',
            here.parent / 'static' / 'captar_logo.png',
        ])
    except Exception:
        pass

    for p in candidates:
        try:
            pp = p if isinstance(p, pathlib.Path) else pathlib.Path(str(p))
            if pp.exists() and pp.is_file():
                return str(pp)
        except Exception:
            continue
    return None

def _static_relatorios_dir() -> str:
    base = os.path.join(os.path.dirname(__file__), 'static', 'relatorios')
    os.makedirs(base, exist_ok=True)
    return base

def _build_comprovante_pdf_bytes(
    *,
    titulo: str,
    campanha: dict,
    pergunta: str,
    stats: dict,
    linhas: List[dict],
    orientation: str = 'portrait',
) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_JUSTIFY
        from reportlab.lib.units import mm
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas as rl_canvas
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dependência ausente para PDF: {e}")

    buffer = io.BytesIO()
    o = str(orientation or 'portrait').strip().lower()
    if o in ('paisagem', 'landscape', 'l'):
        pagesize = landscape(A4)
    else:
        pagesize = A4

    def _pick_fonts() -> Tuple[str, str]:
        base = 'Helvetica'
        bold = 'Helvetica-Bold'
        candidates = [
            ('Arial', 'Arial-Bold', ['arial.ttf', 'Arial.ttf'], ['arialbd.ttf', 'Arial Bold.ttf', 'ArialBD.ttf', 'Arialbd.ttf']),
        ]
        search_dirs = [
            '/usr/share/fonts',
            '/usr/local/share/fonts',
            '/usr/share/fonts/truetype',
            '/usr/share/fonts/truetype/msttcorefonts',
            '/usr/share/fonts/truetype/msttcorefonts-installer',
            '/usr/share/fonts/truetype/liberation',
            '/usr/share/fonts/truetype/dejavu',
        ]

        def find_file(names: List[str]) -> Optional[str]:
            for d in search_dirs:
                try:
                    if not os.path.isdir(d):
                        continue
                    for root, _, files in os.walk(d):
                        fl = {f.lower(): f for f in files}
                        for n in names:
                            hit = fl.get(str(n).lower())
                            if hit:
                                return os.path.join(root, hit)
                except Exception:
                    continue
            return None

        for base_name, bold_name, base_files, bold_files in candidates:
            try:
                base_path = find_file(base_files)
                if not base_path:
                    continue
                try:
                    pdfmetrics.registerFont(TTFont(base_name, base_path))
                except Exception:
                    continue
                base = base_name

                bold_path = find_file(bold_files)
                if bold_path:
                    try:
                        pdfmetrics.registerFont(TTFont(bold_name, bold_path))
                        bold = bold_name
                    except Exception:
                        bold = base_name
                else:
                    bold = base_name
                break
            except Exception:
                continue
        return base, bold

    font_base, font_bold = _pick_fonts()
    generated_dt = datetime.now(_MANAUS_TZ) if _MANAUS_TZ else datetime.now()
    generated_str = _format_dt_br(generated_dt)

    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        leftMargin=8 * mm,
        rightMargin=8 * mm,
        topMargin=30 * mm,
        bottomMargin=14 * mm,
        title=titulo,
    )
    styles = getSampleStyleSheet()
    style_normal = ParagraphStyle(
        'CAPTAR_Normal',
        parent=styles['Normal'],
        fontName=font_base,
        fontSize=9,
        leading=11,
        spaceBefore=0,
        spaceAfter=0,
    )
    style_label = ParagraphStyle(
        'CAPTAR_Label',
        parent=styles['Normal'],
        fontName=font_bold,
        fontSize=9,
        leading=11,
        spaceBefore=0,
        spaceAfter=0,
    )
    style_small = ParagraphStyle(
        'CAPTAR_Small',
        parent=styles['Normal'],
        fontName=font_base,
        fontSize=8,
        leading=10,
        spaceBefore=0,
        spaceAfter=0,
    )
    style_justify = ParagraphStyle(
        'CAPTAR_Justify',
        parent=styles['Normal'],
        fontName=font_base,
        fontSize=9,
        leading=11,
        alignment=TA_JUSTIFY,
        spaceBefore=0,
        spaceAfter=0,
    )

    nome = campanha.get('nome') or ''
    criado_em = _format_dt_br(campanha.get('criado_em') or '')
    campanha_txt = f'{nome} (#{campanha.get("id")})'

    pergunta_hdr = re.sub(r'\s+', ' ', str(_truncate_text(pergunta, 900) if pergunta else '')).strip()
    totals_txt = (
        f'Enviados={int(stats.get("enviados", 0) or 0)} '
        f'Falhas={int(stats.get("falhas", 0) or 0)} '
        f'Respostas={int(stats.get("respostas", 0) or 0)} '
        f'Positivos={int(stats.get("positivos", 0) or 0)} '
        f'Negativos={int(stats.get("negativos", 0) or 0)} '
        f'Aguardando={int(stats.get("aguardando", 0) or 0)}'
    )

    def _truncate_to_width(s: Any, font_name: str, font_size: float, max_w: float) -> str:
        raw = re.sub(r'\s+', ' ', str(s or '')).strip()
        if not raw:
            return ''
        try:
            if pdfmetrics.stringWidth(raw, font_name, font_size) <= max_w:
                return raw
            ell = '...'
            ell_w = pdfmetrics.stringWidth(ell, font_name, font_size)
            if ell_w >= max_w:
                return ell
            lo, hi = 0, len(raw)
            while lo < hi:
                mid = (lo + hi) // 2
                cand = raw[:mid].rstrip() + ell
                if pdfmetrics.stringWidth(cand, font_name, font_size) <= max_w:
                    lo = mid + 1
                else:
                    hi = mid
            cut = max(0, lo - 1)
            return raw[:cut].rstrip() + ell
        except Exception:
            return raw[: max(0, int(len(raw) * 0.6))].rstrip() + '...'

    def draw_header(canvas, doc_obj):
        w, h = doc_obj.pagesize
        canvas.saveState()
        header_top = h - (6 * mm)
        logo_w = 52 * mm
        logo_h = 16 * mm
        logo_x = doc.leftMargin
        logo_y = header_top - logo_h
        logo_path = _find_captar_logo_path()
        if logo_path:
            try:
                img = ImageReader(logo_path)
                canvas.drawImage(
                    img,
                    logo_x,
                    logo_y,
                    width=logo_w,
                    height=logo_h,
                    preserveAspectRatio=True,
                    mask='auto',
                )
            except Exception:
                pass
        title_txt = 'RELATÓRIO DE CAMPANHA'
        title_size = 12
        canvas.setFont(font_bold, title_size)
        canvas.drawRightString(w - doc.rightMargin, header_top - (4 * mm), title_txt)
        right_edge = float(w - doc.rightMargin)

        info_x = logo_x + logo_w + (4 * mm)
        label_size = 8
        value_size = 8
        label_col_w = 24 * mm
        value_x = info_x + label_col_w

        y_campaign = header_top - (6 * mm)
        y_created = header_top - (10 * mm)
        y_msg = header_top - (14 * mm)
        y_status = header_top - (18 * mm)

        max_val_w = max(10 * mm, right_edge - float(value_x))

        canvas.setFont(font_bold, label_size)
        canvas.drawString(info_x, y_campaign, 'CAMPANHA:')
        canvas.setFont(font_base, value_size)
        canvas.drawString(value_x, y_campaign, _truncate_to_width(campanha_txt or '—', font_base, value_size, max_val_w))

        canvas.setFont(font_bold, label_size)
        canvas.drawString(info_x, y_created, 'CRIADO EM:')
        canvas.setFont(font_base, value_size)
        canvas.drawString(value_x, y_created, _truncate_to_width((criado_em or '—'), font_base, value_size, max_val_w))

        canvas.setFont(font_bold, label_size)
        canvas.drawString(info_x, y_msg, 'MENSAGEM:')
        canvas.setFont(font_base, value_size)
        canvas.drawString(value_x, y_msg, _truncate_to_width((pergunta_hdr or '—'), font_base, value_size, max_val_w))

        canvas.setFont(font_bold, label_size)
        canvas.drawString(info_x, y_status, 'STATUS FINAL:')
        canvas.setFont(font_base, value_size)
        canvas.drawString(value_x, y_status, _truncate_to_width((totals_txt or '—'), font_base, value_size, max_val_w))

        canvas.setStrokeColor(colors.lightgrey)
        canvas.line(doc.leftMargin, header_top - (22 * mm), w - doc.rightMargin, header_top - (22 * mm))
        canvas.restoreState()

    left_m = float(doc.leftMargin)
    right_m = float(doc.rightMargin)

    class _NumberedCanvas(rl_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states: List[dict] = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            page_count = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self._draw_footer(page_count)
                rl_canvas.Canvas.showPage(self)
            rl_canvas.Canvas.save(self)

        def _draw_footer(self, page_count: int):
            w, _h = self._pagesize
            y_line = 12 * mm
            y_text = 7.5 * mm
            self.saveState()
            self.setStrokeColor(colors.lightgrey)
            self.setLineWidth(0.5)
            self.line(left_m, y_line, w - right_m, y_line)
            self.setFont(font_base, 8)
            self.drawString(left_m, y_text, f'Gerado em: {generated_str}')
            self.drawRightString(w - right_m, y_text, f'PÁGINA - {int(self._pageNumber):02d}/{int(page_count):02d}')
            self.restoreState()

    elements: List[Any] = []
    elements.append(Spacer(1, 2))

    header = [
        'NOME',
        'NÚMERO',
        'ENVIO (DATA/HORA)',
        'STATUS ENVIO',
        'RESPOSTA',
        'RESPOSTA (DATA/HORA)',
    ]
    data_rows: List[List[Any]] = [header]
    for it in linhas:
        data_rows.append([
            Paragraph(_truncate_text(it.get('nome') or '—', 60) or '—', style_normal),
            Paragraph(_truncate_text(it.get('numero') or '', 30) or '—', style_normal),
            Paragraph(_format_dt_br(it.get('envio_datahora') or ''), style_normal),
            Paragraph(str(it.get('envio_status') or '—').upper(), style_normal),
            Paragraph(str(it.get('resposta_classificacao') or '—').upper(), style_normal),
            Paragraph(_format_dt_br(it.get('resposta_datahora') or ''), style_normal),
        ])

    avail_w = float(getattr(doc, 'width', 0.0) or 0.0)
    col_widths = [
        avail_w * 0.26,
        avail_w * 0.16,
        avail_w * 0.17,
        avail_w * 0.11,
        avail_w * 0.11,
        avail_w * 0.19,
    ]
    table = Table(data_rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f2937')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), font_bold),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f4f6')]),
        ('FONTNAME', (0, 1), (-1, -1), font_base),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(table)

    doc.build(elements, onFirstPage=draw_header, onLaterPages=draw_header, canvasmaker=_NumberedCanvas)
    return buffer.getvalue()

def _strip_accents(s: str) -> str:
    try:
        nfkd = unicodedata.normalize('NFKD', str(s or ''))
        return ''.join([c for c in nfkd if not unicodedata.combining(c)])
    except Exception:
        return str(s or '')

def _parse_sim_nao_response(text: Any) -> Optional[int]:
    try:
        raw = str(text or '').strip()
        if not raw:
            return None
        t = _strip_accents(raw).strip().lower()
        t = re.sub(r'\s+', ' ', t)
        if re.match(r'^\(?\s*1\b', t) or t.startswith('1-') or t.startswith('1 ') or t == '1':
            return 1
        if re.match(r'^\(?\s*2\b', t) or t.startswith('2-') or t.startswith('2 ') or t == '2':
            return 2
        if re.search(r'\bsim\b', t) or t in ('s', 'ok', 'yes', 'y'):
            return 1
        if re.search(r'\bnao\b', t) or t in ('n', 'no'):
            return 2
        return None
    except Exception:
        return None

def _extract_evolution_text(payload: Any) -> str:
    try:
        if payload is None:
            return ''
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            for k in ('text', 'message', 'body', 'content', 'mensagem', 'conversation'):
                v = payload.get(k)
                if isinstance(v, str) and v.strip():
                    return v
            data = payload.get('data') or payload.get('event') or payload.get('payload')
            if isinstance(data, dict):
                for k in ('text', 'body', 'content', 'conversation'):
                    v = data.get(k)
                    if isinstance(v, str) and v.strip():
                        return v
                msg = data.get('message')
                if isinstance(msg, dict):
                    for k in ('text', 'body', 'content', 'conversation', 'caption'):
                        v = msg.get(k)
                        if isinstance(v, str) and v.strip():
                            return v
                    ext = msg.get('extendedTextMessage')
                    if isinstance(ext, dict):
                        v = ext.get('text')
                        if isinstance(v, str) and v.strip():
                            return v
                    btn = msg.get('buttonsResponseMessage')
                    if isinstance(btn, dict):
                        for k in ('selectedButtonId', 'selectedDisplayText'):
                            v = btn.get(k)
                            if isinstance(v, str) and v.strip():
                                return v
                    lst = msg.get('listResponseMessage')
                    if isinstance(lst, dict):
                        single = lst.get('singleSelectReply')
                        if isinstance(single, dict):
                            for k in ('selectedRowId', 'title'):
                                v = single.get(k)
                                if isinstance(v, str) and v.strip():
                                    return v
                        v = lst.get('title')
                        if isinstance(v, str) and v.strip():
                            return v
                    tpl = msg.get('templateButtonReplyMessage')
                    if isinstance(tpl, dict):
                        for k in ('selectedId', 'selectedDisplayText'):
                            v = tpl.get(k)
                            if isinstance(v, str) and v.strip():
                                return v
        return ''
    except Exception:
        return ''

def _extract_evolution_number(payload: Any) -> str:
    try:
        if payload is None:
            return ''
        if isinstance(payload, dict):
            data = payload.get('data') or payload.get('event') or payload.get('payload')
            if isinstance(data, dict):
                key = data.get('key')
                if isinstance(key, dict):
                    remote = key.get('remoteJid')
                    if remote and isinstance(remote, str) and '@g.us' in remote:
                        participant = key.get('participant') or data.get('participant')
                        d = _digits_only(participant)
                        if d:
                            return d
                    d = _digits_only(remote)
                    if d:
                        return d
                    participant = key.get('participant') or data.get('participant')
                    d = _digits_only(participant)
                    if d:
                        return d

                for k in ('remoteJid', 'chatId', 'jid', 'sender', 'from', 'number', 'phone'):
                    v = data.get(k)
                    if v:
                        d = _digits_only(v)
                        if d:
                            return d

            key = payload.get('key')
            if isinstance(key, dict):
                remote = key.get('remoteJid')
                if remote and isinstance(remote, str) and '@g.us' in remote:
                    participant = key.get('participant') or payload.get('participant')
                    d = _digits_only(participant)
                    if d:
                        return d
                d = _digits_only(remote)
                if d:
                    return d
                participant = key.get('participant') or payload.get('participant')
                d = _digits_only(participant)
                if d:
                    return d

            for k in ('remoteJid', 'chatId', 'jid', 'sender', 'from', 'number', 'phone'):
                v = payload.get(k)
                if v:
                    d = _digits_only(v)
                    if d:
                        return d
        return ''
    except Exception:
        return ''

def _iter_evolution_events(payload: Any) -> List[Dict[str, Any]]:
    try:
        if payload is None:
            return []
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        if not isinstance(payload, dict):
            return []

        data = payload.get('data') or payload.get('event') or payload.get('payload')
        if isinstance(data, dict):
            msgs = data.get('messages')
            if isinstance(msgs, list) and msgs:
                out: List[Dict[str, Any]] = []
                for m in msgs:
                    if isinstance(m, dict):
                        out.append({"data": m})
                if out:
                    return out
        msgs2 = payload.get('messages')
        if isinstance(msgs2, list) and msgs2:
            out2: List[Dict[str, Any]] = []
            for m in msgs2:
                if isinstance(m, dict):
                    out2.append({"data": m})
            if out2:
                return out2

        return [payload]
    except Exception:
        return []

def _extract_evolution_datetime(payload: Any) -> Optional[datetime]:
    try:
        if payload is None:
            return None
        if isinstance(payload, dict):
            data = payload.get('data') or payload.get('event') or payload.get('payload') or {}
            candidates = []
            if isinstance(data, dict):
                candidates.extend([
                    data.get('messageTimestamp'),
                    data.get('timestamp'),
                    data.get('t'),
                ])
                msg = data.get('message')
                if isinstance(msg, dict):
                    candidates.extend([
                        msg.get('messageTimestamp'),
                        msg.get('timestamp'),
                        msg.get('t'),
                    ])
            candidates.extend([payload.get('messageTimestamp'), payload.get('timestamp'), payload.get('t')])

            for v in candidates:
                if v is None:
                    continue
                if isinstance(v, (int, float)):
                    ts = float(v)
                else:
                    s = str(v).strip()
                    if not s:
                        continue
                    try:
                        ts = float(s)
                    except Exception:
                        continue
                if ts > 10_000_000_000:
                    ts = ts / 1000.0
                if ts <= 0:
                    continue
                return datetime.utcfromtimestamp(ts)
        return None
    except Exception:
        return None

def _match_phone(stored: Any, incoming_digits: str) -> bool:
    def norm_br(d: str) -> str:
        if not d:
            return d
        dd = ''.join([c for c in str(d) if c.isdigit()])
        if len(dd) == 13 and dd.startswith('55') and dd[4] == '9':
            return dd[:4] + dd[5:]
        if len(dd) == 11 and dd[2] == '9':
            return dd[:2] + dd[3:]
        return dd

    a = _digits_only(stored)
    b = _digits_only(incoming_digits)
    if not a or not b:
        return False
    if a == b:
        return True
    if len(a) >= 10 and b.endswith(a[-10:]):
        return True
    if len(b) >= 10 and a.endswith(b[-10:]):
        return True
    an = norm_br(a)
    bn = norm_br(b)
    if an and bn:
        if an == bn:
            return True
        if len(an) >= 10 and bn.endswith(an[-10:]):
            return True
        if len(bn) >= 10 and an.endswith(bn[-10:]):
            return True
    return False

@app.post("/api/integrations/whatsapp/webhook")
async def whatsapp_webhook(payload: Dict[str, Any], request: Request, tenant: Optional[str] = None):
    try:
        slug = (request.headers.get('X-Tenant') or tenant or 'captar').strip() or 'captar'
        try:
            rc = get_redis_client()
            cached = rc.get(f"tenant:id:{slug}") if rc else None
            tid = int(cached) if cached else None
        except Exception:
            tid = None
        if not tid:
            try:
                with get_db_connection() as conn_t:
                    cur_t = conn_t.cursor()
                    cur_t.execute(
                        f"SELECT \"IdTenant\" FROM \"{DB_SCHEMA}\".\"Tenant\" WHERE LOWER(\"Slug\") = LOWER(%s) LIMIT 1",
                        (slug,)
                    )
                    row = cur_t.fetchone()
                    tid = int(row[0]) if row else 1
                try:
                    if rc:
                        rc.setex(f"tenant:id:{slug}", 300, str(tid))
                except Exception:
                    pass
            except Exception:
                tid = 1

        dsn = None
        if str(slug).lower() != 'captar':
            try:
                dsn = _get_dsn_by_slug(str(slug).lower())
            except Exception:
                dsn = None

        with get_db_connection(dsn) as conn:
            cursor = conn.cursor()
            events = _iter_evolution_events(payload)
            if not events:
                return {"ok": True, "ignored": True, "reason": "no_events"}

            cursor.execute(
                f"""
                SELECT d."IdDisparo", d."Numero", d."IdCampanha"
                FROM "{DB_SCHEMA}"."Disparos" d
                JOIN "{DB_SCHEMA}"."Campanhas" c
                  ON c."IdTenant" = d."IdTenant"
                 AND c."IdCampanha" = d."IdCampanha"
                WHERE d."IdTenant" = %s
                  AND d."Canal" = 'WHATSAPP'
                  AND d."Direcao" = 'OUT'
                  AND d."Status" = 'ENVIADO'
                  AND d."IdCampanha" IS NOT NULL
                  AND COALESCE(c."AnexoJSON"->'config'->>'response_mode', '') = 'SIM_NAO'
                ORDER BY d."DataHora" DESC, d."IdDisparo" DESC
                LIMIT 500
                """,
                (tid,),
            )
            out_rows = cursor.fetchall() or []

            updated: List[Dict[str, Any]] = []
            ignored: List[Dict[str, Any]] = []

            for ev in events:
                incoming_text = _extract_evolution_text(ev).strip()
                incoming_digits = _extract_evolution_number(ev)
                if not incoming_text or not incoming_digits:
                    ignored.append({"reason": "missing_text_or_number"})
                    continue

                received_dt = _extract_evolution_datetime(ev) or datetime.utcnow()
                inserted_in_id = None
                try:
                    cursor.execute(
                        f"""
                        INSERT INTO "{DB_SCHEMA}"."Disparos"
                        ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload")
                        VALUES (%s,NULL,%s,%s,%s,NULL,%s,NULL,%s,%s,%s::jsonb)
                        RETURNING "IdDisparo"
                        """,
                        (
                            tid,
                            'WHATSAPP',
                            'IN',
                            str(incoming_digits),
                            incoming_text,
                            'RECEBIDO',
                            received_dt,
                            json.dumps(ev, ensure_ascii=False),
                        ),
                    )
                    row_in = cursor.fetchone()
                    inserted_in_id = int(row_in[0]) if row_in else None
                    conn.commit()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

                resposta = _parse_sim_nao_response(incoming_text)
                if resposta not in (1, 2):
                    ignored.append({"number": incoming_digits, "reason": "not_sim_nao"})
                    continue

                candidates = [(out_id_raw, out_num, campanha_id) for (out_id_raw, out_num, campanha_id) in out_rows if _match_phone(out_num, incoming_digits)]
                if not candidates:
                    ignored.append({"number": incoming_digits, "reason": "no_matching_out_disparo"})
                    continue

                applied = False
                for out_id_raw, out_num, campanha_id in candidates:
                    cursor.execute(
                        f"""
                        SELECT "AnexoJSON", "Positivos", "Negativos", "Enviados"
                        FROM "{DB_SCHEMA}"."Campanhas"
                        WHERE "IdCampanha" = %s AND "IdTenant" = %s
                        FOR UPDATE
                        """,
                        (campanha_id, tid),
                    )
                    locked = cursor.fetchone()
                    if not locked:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        continue

                    anexo = locked[0]
                    positivos = int(locked[1] or 0)
                    negativos = int(locked[2] or 0)
                    enviados = int(locked[3] or 0)

                    if not anexo:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        continue

                    anexo_obj: Any = anexo
                    if isinstance(anexo_obj, str):
                        try:
                            anexo_obj = json.loads(anexo_obj)
                        except Exception:
                            try:
                                conn.rollback()
                            except Exception:
                                pass
                            continue

                    if isinstance(anexo_obj, list):
                        anexo_obj = {"contacts": anexo_obj, "config": {"response_mode": "SIM_NAO"}}

                    if not isinstance(anexo_obj, dict):
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        continue

                    contacts = anexo_obj.get('contacts')
                    if not isinstance(contacts, list):
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        continue

                    idx_match = -1
                    for i, c in enumerate(contacts):
                        if not isinstance(c, dict):
                            continue
                        phone = c.get('whatsapp') or c.get('celular') or c.get('telefone') or c.get('phone')
                        if _match_phone(phone, incoming_digits):
                            idx_match = i
                            break

                    if idx_match < 0:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        continue

                    cur = contacts[idx_match]
                    existing = cur.get('resposta') if isinstance(cur, dict) else None
                    if existing in (1, 2, '1', '2'):
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        continue

                    cur['resposta'] = resposta
                    cur['respondido_em'] = (received_dt or datetime.utcnow()).isoformat()
                    contacts[idx_match] = cur
                    anexo_obj['contacts'] = contacts

                    if resposta == 1:
                        positivos += 1
                    else:
                        negativos += 1

                    aguardando = max(0, enviados - (positivos + negativos))
                    cursor.execute(
                        f"""
                        UPDATE "{DB_SCHEMA}"."Campanhas"
                        SET "AnexoJSON" = %s::jsonb,
                            "Positivos" = %s,
                            "Negativos" = %s,
                            "Aguardando" = %s,
                            "Atualizacao" = NOW()
                        WHERE "IdCampanha" = %s AND "IdTenant" = %s
                        """,
                        (json.dumps(anexo_obj, ensure_ascii=False), positivos, negativos, aguardando, campanha_id, tid),
                    )

                    if inserted_in_id:
                        try:
                            cursor.execute(
                                f"""
                                UPDATE "{DB_SCHEMA}"."Disparos"
                                SET "IdCampanha" = %s,
                                    "RespostaClassificacao" = %s,
                                    "IdDisparoRef" = %s
                                WHERE "IdDisparo" = %s AND "IdTenant" = %s
                                """,
                                (
                                    campanha_id,
                                    ('SIM' if resposta == 1 else 'NAO'),
                                    int(out_id_raw) if out_id_raw is not None else None,
                                    inserted_in_id,
                                    tid,
                                ),
                            )
                        except Exception:
                            pass

                    conn.commit()
                    updated.append({"number": incoming_digits, "campanha_id": campanha_id, "resposta": resposta})
                    applied = True
                    break

                if not applied:
                    ignored.append({"number": incoming_digits, "reason": "no_applicable_campaign"})
                    continue

            return {
                "ok": True,
                "tenant": slug,
                "processed": len(events),
                "updated": updated,
                "ignored": ignored,
            }
    except Exception as e:
        try:
            traceback.print_exc()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))

class RelatorioComprovanteRequest(BaseModel):
    campanha_id: int
    titulo: Optional[str] = None

@app.get("/api/disparos")
async def disparos_list(limit: int = 1000, campanha_id: Optional[int] = None, numero: Optional[str] = None, request: Request = None):
    try:
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            tid = _tenant_id_from_header(request)
            where = ['"IdTenant" = %s']
            values: List[Any] = [tid]
            if campanha_id is not None:
                where.append('"IdCampanha" = %s')
                values.append(int(campanha_id))
            if numero:
                where.append('"Numero" ILIKE %s')
                values.append(f"%{_digits_only(numero)}%")
            cursor.execute(
                f"""
                SELECT "IdDisparo" as id,
                       "Canal" as canal,
                       "Numero" as destino,
                       "Nome" as nome,
                       "Direcao" as direcao,
                       "Status" as status,
                       "DataHora" as datahora,
                       "IdCampanha" as campanha_id,
                       "Mensagem" as mensagem,
                       "Imagem" as imagem,
                       "RespostaClassificacao" as resposta
                FROM "{DB_SCHEMA}"."Disparos"
                WHERE {' AND '.join(where)}
                ORDER BY "IdDisparo" DESC
                LIMIT %s
                """,
                tuple(values + [int(limit)]),
            )
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            out_rows: List[Dict[str, Any]] = []
            for r in rows or []:
                d = dict(zip(cols, r))
                for k, v in list(d.items()):
                    d[k] = _attach_utc(v)
                out_rows.append(d)
            return {"rows": out_rows, "columns": cols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/campanhas/{id}/disparos-grid")
async def campanhas_disparos_grid(id: int, request: Request, limit_contacts: int = 20000):
    try:
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            tid = _tenant_id_from_header(request)
            campanha_obj, pergunta, stats_obj, linhas = _campanha_disparos_grid(
                cursor,
                tid=tid,
                campanha_id=int(id),
                limit_contacts=int(limit_contacts),
            )
            cols = ["nome", "numero", "envio_datahora", "envio_status", "resposta_classificacao", "resposta_datahora", "resposta_texto"]
            return {"campanha": campanha_obj, "pergunta": pergunta, "stats": stats_obj, "rows": linhas, "columns": cols}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/relatorios")
async def relatorios_list(limit: int = 200, campanha_id: Optional[int] = None, request: Request = None):
    try:
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            tid = _tenant_id_from_header(request)
            where = ['"IdTenant" = %s']
            values: List[Any] = [tid]
            if campanha_id is not None:
                where.append('"IdCampanha" = %s')
                values.append(int(campanha_id))
            cursor.execute(
                f"""
                SELECT "IdRelatorio" as id,
                       "IdCampanha" as campanha_id,
                       "Titulo" as titulo,
                       "Tipo" as tipo,
                       "CriadoEm" as criado_em,
                       "CriadoPor" as criado_por
                FROM "{DB_SCHEMA}"."Relatorios"
                WHERE {' AND '.join(where)}
                ORDER BY "IdRelatorio" DESC
                LIMIT %s
                """,
                tuple(values + [int(limit)]),
            )
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            out_rows: List[Dict[str, Any]] = []
            for r in rows or []:
                d = dict(zip(cols, r))
                for k, v in list(d.items()):
                    d[k] = _attach_utc(v)
                out_rows.append(d)
            return {"rows": out_rows, "columns": cols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/relatorios/{id}")
async def relatorios_get(id: int, request: Request):
    try:
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            tid = _tenant_id_from_header(request)
            cursor.execute(
                f"""
                SELECT "IdRelatorio" as id,
                       "IdCampanha" as campanha_id,
                       "Titulo" as titulo,
                       "Tipo" as tipo,
                       "Parametros" as parametros,
                       "Dados" as dados,
                       "CriadoEm" as criado_em,
                       "CriadoPor" as criado_por
                FROM "{DB_SCHEMA}"."Relatorios"
                WHERE "IdRelatorio" = %s AND "IdTenant" = %s
                """,
                (int(id), tid),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Relatório não encontrado")
            cols = [d[0] for d in cursor.description]
            d = dict(zip(cols, row))
            for k, v in list(d.items()):
                d[k] = _attach_utc(v)
            return d
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/relatorios/{id}/pdf")
async def relatorios_get_pdf(id: int, request: Request, orientation: str = 'portrait'):
    try:
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            tid = _tenant_id_from_header(request)
            cursor.execute(
                f"""
                SELECT "IdRelatorio" as id,
                       "IdCampanha" as campanha_id,
                       "Titulo" as titulo,
                       "Tipo" as tipo
                FROM "{DB_SCHEMA}"."Relatorios"
                WHERE "IdRelatorio" = %s AND "IdTenant" = %s
                """,
                (int(id), tid),
            )
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Relatório não encontrado")
            cols = [d[0] for d in cursor.description]
            rel = dict(zip(cols, row))
            if str(rel.get('tipo') or '').upper() != 'COMPROVANTE':
                raise HTTPException(status_code=400, detail="Relatório não é do tipo comprovante")

            campanha_id = int(rel.get('campanha_id') or 0)
            campanha_obj, pergunta, stats_obj, linhas = _campanha_disparos_grid(
                cursor,
                tid=tid,
                campanha_id=campanha_id,
            )
            titulo = str(rel.get('titulo') or f'Comprovante - Campanha {campanha_id}')
            o = str(orientation or 'portrait').strip().lower()
            if o not in ('portrait', 'landscape', 'retrato', 'paisagem', 'p', 'l'):
                raise HTTPException(status_code=400, detail="Parâmetro orientation inválido")
            pdf_bytes = _build_comprovante_pdf_bytes(
                titulo=titulo,
                campanha=campanha_obj,
                pergunta=pergunta,
                stats=stats_obj,
                linhas=linhas,
                orientation=o,
            )
            filename = f'comprovante_campanha_{campanha_id}_relatorio_{int(id)}.pdf'
            headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
            return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/relatorios/comprovante")
async def relatorios_comprovante(body: RelatorioComprovanteRequest, request: Request):
    try:
        user_info = _extract_user_from_auth(request)
        tid = _tenant_id_from_header(request)
        criado_por = user_info.get('nome') or user_info.get('email') or str(user_info.get('id', ''))
        campanha_id = int(body.campanha_id)
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            campanha_obj, pergunta, stats_obj, linhas = _campanha_disparos_grid(
                cursor,
                tid=tid,
                campanha_id=campanha_id,
            )
            titulo = body.titulo or f'Comprovante - Campanha {campanha_id}'
            parametros = {"campanha_id": campanha_id}
            campanha_small = {
                "id": campanha_obj.get("id"),
                "nome": campanha_obj.get("nome"),
                "descricao": campanha_obj.get("descricao"),
                "cadastrante": campanha_obj.get("cadastrante"),
                "criado_em": campanha_obj.get("criado_em"),
                "data_inicio": campanha_obj.get("data_inicio"),
                "data_fim": campanha_obj.get("data_fim"),
            }
            dados = {"campanha": campanha_small, "pergunta": pergunta, "stats": stats_obj, "linhas": linhas}

            cursor.execute(
                f"""
                INSERT INTO "{DB_SCHEMA}"."Relatorios"
                ("IdTenant","IdCampanha","Titulo","Tipo","Parametros","Dados","CriadoEm","CriadoPor")
                VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,NOW() AT TIME ZONE 'UTC',%s)
                RETURNING "IdRelatorio"
                """,
                (
                    tid,
                    campanha_id,
                    titulo,
                    'COMPROVANTE',
                    json.dumps(_json_safe(parametros), ensure_ascii=False),
                    json.dumps(_json_safe(dados), ensure_ascii=False),
                    criado_por,
                ),
            )
            new_id = int(cursor.fetchone()[0])
            conn.commit()
            return {"id": new_id, "dados": dados}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 5. CAMPANHAS ====================

class CampanhaCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None
    status: Optional[Union[bool, str]] = True
    meta: Optional[int] = 0
    enviados: Optional[int] = 0
    nao_enviados: Optional[int] = 0
    positivos: Optional[int] = 0
    negativos: Optional[int] = 0
    aguardando: Optional[int] = 0
    anexo_json: Optional[Union[str, Dict, List]] = None
    imagem: Optional[str] = None
    usar_eleitores: Optional[bool] = False
    recorrencia_ativa: Optional[bool] = False
    total_blocos: Optional[int] = 5
    mensagens_por_bloco: Optional[int] = 500
    blocos_por_dia: Optional[int] = 1
    intervalo_min_seg: Optional[int] = 5
    intervalo_max_seg: Optional[int] = 120
    bloco_atual: Optional[int] = 0
    proxima_execucao: Optional[str] = None
    
class CampanhaUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None
    status: Optional[Union[bool, str]] = None
    meta: Optional[int] = None
    enviados: Optional[int] = None
    nao_enviados: Optional[int] = None
    positivos: Optional[int] = None
    negativos: Optional[int] = None
    aguardando: Optional[int] = None
    anexo_json: Optional[Union[str, Dict, List]] = None
    imagem: Optional[str] = None
    recorrencia_ativa: Optional[bool] = None
    total_blocos: Optional[int] = None
    mensagens_por_bloco: Optional[int] = None
    blocos_por_dia: Optional[int] = None
    intervalo_min_seg: Optional[int] = None
    intervalo_max_seg: Optional[int] = None
    bloco_atual: Optional[int] = None
    proxima_execucao: Optional[str] = None

@app.get("/api/campanhas/schema")
async def campanhas_schema():
    try:
        # Retorna schema compatível com o frontend (baseado na nova tabela, mapeado para legacy keys)
        return {
            "columns": [
                {"name": "id", "type": "integer", "nullable": False},
                {"name": "nome", "type": "string", "nullable": False},
                {"name": "descricao", "type": "text", "nullable": True},
                {"name": "data_inicio", "type": "date", "nullable": True},
                {"name": "data_fim", "type": "date", "nullable": True},
                {"name": "status", "type": "boolean", "nullable": True},
                {"name": "meta", "type": "integer", "nullable": True},
                {"name": "enviados", "type": "integer", "nullable": True},
                {"name": "nao_enviados", "type": "integer", "nullable": True},
                {"name": "positivos", "type": "integer", "nullable": True},
                {"name": "negativos", "type": "integer", "nullable": True},
                {"name": "aguardando", "type": "integer", "nullable": True},
                {"name": "recorrencia_ativa", "type": "boolean", "nullable": True},
                {"name": "total_blocos", "type": "integer", "nullable": True},
                {"name": "mensagens_por_bloco", "type": "integer", "nullable": True},
                {"name": "blocos_por_dia", "type": "integer", "nullable": True},
                {"name": "intervalo_min_seg", "type": "integer", "nullable": True},
                {"name": "intervalo_max_seg", "type": "integer", "nullable": True},
                {"name": "bloco_atual", "type": "integer", "nullable": True},
                {"name": "proxima_execucao", "type": "timestamp", "nullable": True},
                {"name": "created_at", "type": "timestamp", "nullable": True},
                {"name": "updated_at", "type": "timestamp", "nullable": True},
                {"name": "cadastrante", "type": "string", "nullable": True},
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/campanhas")
async def campanhas_list(limit: int = 1000, request: Request = None):
    try:
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            tid = _tenant_id_from_header(request)
            
            # Verificar se tabela existe
            try:
                cursor.execute(f"SELECT 1 FROM \"{DB_SCHEMA}\".\"Campanhas\" LIMIT 1")
            except:
                conn.rollback()
                return {"rows": [], "columns": []}

            cursor.execute(
                f"""
                SELECT "IdCampanha" as id, "NomeCampanha" as nome, "Texto" as descricao, 
                       "DataInicio" as data_inicio, "DataFim" as data_fim, "Status" as status, 
                       "Meta" as meta, "Enviados" as enviados, "NaoEnviados" as nao_enviados, 
                       "Positivos" as positivos, "Negativos" as negativos, "Aguardando" as aguardando,
                       "RecorrenciaAtiva" as recorrencia_ativa,
                       "TotalBlocos" as total_blocos,
                       "MensagensPorBloco" as mensagens_por_bloco,
                       "BlocosPorDia" as blocos_por_dia,
                       "IntervaloMinSeg" as intervalo_min_seg,
                       "IntervaloMaxSeg" as intervalo_max_seg,
                       "BlocoAtual" as bloco_atual,
                       "ProximaExecucao" as proxima_execucao,
                       "Cadastrante" as cadastrante, "DataCriacao" as created_at, "Atualizacao" as updated_at, 
                       "AnexoJSON" as conteudo_arquivo, "Imagem" as imagem
                FROM "{DB_SCHEMA}"."Campanhas" 
                WHERE "IdTenant" = %s
                ORDER BY "IdCampanha" DESC LIMIT %s
                """,
                (tid, limit)
            )
            colnames = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            data = []
            for row in rows:
                d = dict(zip(colnames, row))
                # Map conteudo_arquivo (AnexoJSON) to string if it's a dict/list (for frontend compatibility)
                if isinstance(d.get('conteudo_arquivo'), (dict, list)):
                    d['conteudo_arquivo'] = json.dumps(d['conteudo_arquivo'])
                
                # Extract usar_eleitores from conteudo_arquivo if present
                d['usar_eleitores'] = False
                if d.get('conteudo_arquivo'):
                    try:
                        ca = d['conteudo_arquivo']
                        if isinstance(ca, str):
                            ca_obj = json.loads(ca)
                            if isinstance(ca_obj, dict) and ca_obj.get('usar_eleitores'):
                                d['usar_eleitores'] = True
                        elif isinstance(ca, dict) and ca.get('usar_eleitores'):
                             d['usar_eleitores'] = True
                    except:
                        pass

                data.append(d)
            
            return {"rows": data, "columns": colnames}
    except Exception as e:
        print(f"Error listing campanhas: {e}")
        return {"rows": [], "columns": []}

@app.post("/api/campanhas")
async def campanhas_create(campanha: CampanhaCreate, request: Request):
    try:
        user_info = _extract_user_from_auth(request)
        tid = _tenant_id_from_header(request)
        cadastrante = user_info.get('nome') or user_info.get('email') or str(user_info.get('id', 'Unknown'))
        
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            # AnexoJSON handling
            anexo_json = None
            if campanha.anexo_json:
                if isinstance(campanha.anexo_json, (dict, list)):
                    anexo_json = json.dumps(campanha.anexo_json)
                else:
                    anexo_json = campanha.anexo_json
            elif campanha.usar_eleitores:
                 # If using eleitores, we can store a marker or config in AnexoJSON
                 anexo_json = json.dumps({"source": "eleitores", "usar_eleitores": True})
            
            # Status handling (ensure boolean)
            status_val = True
            if campanha.status is not None:
                if isinstance(campanha.status, bool):
                    status_val = campanha.status
                else:
                    s_str = str(campanha.status).lower()
                    if s_str in ('false', '0', 'inativo', 'off'):
                        status_val = False
                    else:
                        status_val = True

            imagem_db = None
            if campanha.imagem:
                imagem_db = _normalize_campanha_imagem(campanha.imagem, tid)

            recorrencia_ativa = bool(campanha.recorrencia_ativa or False)
            total_blocos = int(campanha.total_blocos or 5)
            mensagens_por_bloco = int(campanha.mensagens_por_bloco or 500)
            blocos_por_dia = int(campanha.blocos_por_dia or 1)
            intervalo_min_seg = int(campanha.intervalo_min_seg or 5)
            intervalo_max_seg = int(campanha.intervalo_max_seg or 120)
            bloco_atual = int(campanha.bloco_atual or 0)
            proxima_execucao = campanha.proxima_execucao

            cursor.execute(
                f"""
                INSERT INTO "{DB_SCHEMA}"."Campanhas" 
                ("NomeCampanha", "Texto", "DataInicio", "DataFim", "Status", 
                 "Meta", "Enviados", "NaoEnviados", "Positivos", "Negativos", "Aguardando", 
                 "Cadastrante", "DataCriacao", "Atualizacao", "AnexoJSON", "Imagem",
                 "RecorrenciaAtiva", "TotalBlocos", "MensagensPorBloco", "BlocosPorDia",
                 "IntervaloMinSeg", "IntervaloMaxSeg", "BlocoAtual", "ProximaExecucao",
                 "IdTenant")
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s::jsonb, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING "IdCampanha"
                """,
                (
                    campanha.nome, 
                    campanha.descricao, 
                    campanha.data_inicio, 
                    campanha.data_fim, 
                    status_val,
                    campanha.meta,
                    campanha.enviados,
                    campanha.nao_enviados,
                    campanha.positivos,
                    campanha.negativos,
                    campanha.aguardando,
                    cadastrante,
                    anexo_json,
                    imagem_db,
                    recorrencia_ativa,
                    total_blocos,
                    mensagens_por_bloco,
                    blocos_por_dia,
                    intervalo_min_seg,
                    intervalo_max_seg,
                    bloco_atual,
                    proxima_execucao,
                    tid
                )
            )
            new_id = cursor.fetchone()[0]
            conn.commit()
            return {"id": new_id, "message": "Campanha criada com sucesso"}
    except Exception as e:
        print(f"Error creating campanha: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/campanhas/{id}")
async def campanhas_update(id: int, campanha: CampanhaUpdate, request: Request):
    try:
        tid = _tenant_id_from_header(request)
        data = campanha.dict(exclude_unset=True)
        if not data:
             raise HTTPException(status_code=400, detail="Nenhum dado para atualizar")
        
        # Map frontend keys to DB columns
        key_map = {
            'nome': 'NomeCampanha',
            'descricao': 'Texto',
            'data_inicio': 'DataInicio',
            'data_fim': 'DataFim',
            'status': 'Status',
            'meta': 'Meta',
            'enviados': 'Enviados',
            'nao_enviados': 'NaoEnviados',
            'positivos': 'Positivos',
            'negativos': 'Negativos',
            'aguardando': 'Aguardando',
            'anexo_json': 'AnexoJSON',
            'imagem': 'Imagem',
            'recorrencia_ativa': 'RecorrenciaAtiva',
            'total_blocos': 'TotalBlocos',
            'mensagens_por_bloco': 'MensagensPorBloco',
            'blocos_por_dia': 'BlocosPorDia',
            'intervalo_min_seg': 'IntervaloMinSeg',
            'intervalo_max_seg': 'IntervaloMaxSeg',
            'bloco_atual': 'BlocoAtual',
            'proxima_execucao': 'ProximaExecucao'
        }
        
        # Ensure AnexoJSON is serialized
        if 'anexo_json' in data and data['anexo_json'] is not None:
             if not isinstance(data['anexo_json'], str):
                 data['anexo_json'] = json.dumps(data['anexo_json'])

        # Ensure Status is boolean
        if 'status' in data and data['status'] is not None:
             if not isinstance(data['status'], bool):
                 s_str = str(data['status']).lower()
                 data['status'] = False if s_str in ('false', '0', 'inativo', 'off') else True

        if 'imagem' in data and data['imagem'] is not None:
            data['imagem'] = _normalize_campanha_imagem(data['imagem'], tid)

        set_parts = []
        values = []
        for k, v in data.items():
            if k in key_map:
                if k == 'anexo_json':
                     set_parts.append(f"\"{key_map[k]}\" = %s::jsonb")
                elif k == 'proxima_execucao':
                     set_parts.append(f"\"{key_map[k]}\" = %s::timestamp")
                else:
                     set_parts.append(f"\"{key_map[k]}\" = %s")
                values.append(v)
            
        values.append(id)
        
        # Multi-tenant safety
        tid = _tenant_id_from_header(request)
        values.append(tid)

        if not set_parts:
             return {"message": "Nenhum campo válido para atualizar"}
        
        query = f"UPDATE \"{DB_SCHEMA}\".\"Campanhas\" SET {', '.join(set_parts)}, \"Atualizacao\" = NOW() WHERE \"IdCampanha\" = %s AND \"IdTenant\" = %s"
        
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(values))
            conn.commit()
            return {"id": id, "message": "Campanha atualizada com sucesso"}
    except Exception as e:
        print(f"Error updating campanha: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/campanhas/{id}")
async def campanhas_delete(id: int, request: Request):
    try:
        tid = _tenant_id_from_header(request)
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"DELETE FROM \"{DB_SCHEMA}\".\"Campanhas\" WHERE \"IdCampanha\" = %s AND \"IdTenant\" = %s", 
                (id, tid)
            )
            conn.commit()
            return {"message": "Campanha removida com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/campanhas/{id}/anexo")
async def campanhas_upload_anexo(id: int, request: Request, file: UploadFile = File(...), type: Optional[str] = Form(None)):
    try:
        tid = _tenant_id_from_header(request)
        content_bytes = await file.read()
        content_str = None
        filename_lower = file.filename.lower()
        
        # Processamento de arquivos de dados (JSON, CSV, Excel)
        if filename_lower.endswith(('.json', '.csv', '.xls', '.xlsx')):
            try:
                df = None
                
                # JSON
                if filename_lower.endswith('.json'):
                    try:
                        df = pd.read_json(io.BytesIO(content_bytes))
                    except ValueError:
                        # Fallback: tentar carregar com json lib e criar DataFrame
                        json_obj = json.loads(content_bytes)
                        df = pd.DataFrame(json_obj)
                
                # CSV
                elif filename_lower.endswith('.csv'):
                    # Detecção rudimentar de encoding
                    try:
                        text_content = content_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        text_content = content_bytes.decode('latin-1')
                    
                    # Detecção de separador
                    sep = ','
                    if ';' in text_content[:1024] and text_content[:1024].count(';') > text_content[:1024].count(','):
                        sep = ';'
                        
                    df = pd.read_csv(io.StringIO(text_content), sep=sep)
                
                # Excel
                elif filename_lower.endswith(('.xls', '.xlsx')):
                    df = pd.read_excel(io.BytesIO(content_bytes))
                
                if df is not None:
                    # Limpeza básica
                    df = df.fillna('')
                    # Converter para JSON string (lista de objetos)
                    content_str = df.to_json(orient='records', force_ascii=False, date_format='iso')
                    print(f"Arquivo processado com sucesso. Registros: {len(df)}")
            except Exception as e:
                print(f"Erro ao processar arquivo de dados {file.filename}: {str(e)}")
                # Não interromper, pois pode ser apenas um anexo PDF ou outro
                pass
        
        # Se for imagem, salvar em static/campanhas/
        image_path = None
        if type == 'imagem' or file.content_type.startswith('image/'):
             import os
             import uuid
             ext = file.filename.split('.')[-1]
             filename = f"{tid}_{id}_{uuid.uuid4()}.{ext}"
             static_dir = os.path.join(os.getcwd(), "static", "campanhas")
             os.makedirs(static_dir, exist_ok=True)
             with open(os.path.join(static_dir, filename), "wb") as f:
                 f.write(content_bytes)
             image_path = f"/static/campanhas/{filename}"

        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            # Se tiver conteúdo JSON processado, salvar
            if content_str:
                existing_config: Any = {}
                existing_other: Any = {}
                try:
                    cursor.execute(
                        f"SELECT \"AnexoJSON\" FROM \"{DB_SCHEMA}\".\"Campanhas\" WHERE \"IdCampanha\" = %s AND \"IdTenant\" = %s",
                        (id, tid)
                    )
                    row = cursor.fetchone()
                    existing = row[0] if row else None
                    existing_obj: Any = existing
                    if isinstance(existing_obj, str):
                        try:
                            existing_obj = json.loads(existing_obj)
                        except Exception:
                            existing_obj = None
                    if isinstance(existing_obj, dict):
                        cfg = existing_obj.get('config')
                        if isinstance(cfg, dict):
                            existing_config = cfg
                        existing_other = {k: v for k, v in existing_obj.items() if k not in ('contacts',)}
                    else:
                        existing_other = {}
                except Exception:
                    existing_config = {}
                    existing_other = {}

                try:
                    records_obj: Any = json.loads(content_str)
                except Exception:
                    records_obj = []
                if not isinstance(records_obj, list):
                    records_obj = []

                new_anexo: Any = {}
                if isinstance(existing_other, dict) and existing_other:
                    new_anexo = {**existing_other}
                new_anexo['contacts'] = records_obj
                if not isinstance(new_anexo.get('config'), dict):
                    new_anexo['config'] = existing_config if isinstance(existing_config, dict) else {}

                cursor.execute(
                    f"UPDATE \"{DB_SCHEMA}\".\"Campanhas\" SET \"AnexoJSON\" = %s::jsonb WHERE \"IdCampanha\" = %s AND \"IdTenant\" = %s",
                    (json.dumps(new_anexo, ensure_ascii=False), id, tid)
                )
            
            # Se tiver imagem, salvar path
            if image_path:
                 cursor.execute(
                    f"UPDATE \"{DB_SCHEMA}\".\"Campanhas\" SET \"Imagem\" = %s WHERE \"IdCampanha\" = %s AND \"IdTenant\" = %s",
                    (image_path, id, tid)
                )
                
            conn.commit()
            
        return {"message": "Upload realizado com sucesso", "image_path": image_path}
    except Exception as e:
        print(f"Error uploading anexo: {e}")
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
        _set_tenant_dsn(tid, dsn)
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
        try:
            conn.rollback()
        except Exception:
            pass
        conn.autocommit = True
        cur = conn.cursor()
        try:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"')
            actions.append('Schema ensured')
        except Exception:
            pass
        try:
            cur.execute(f'DROP TABLE IF EXISTS {DB_SCHEMA}.usuarios CASCADE')
            actions.append('Dropped legacy table captar.usuarios (lowercase)')
        except Exception:
            pass
        try:
            cur.execute(f'DROP TABLE IF EXISTS "{DB_SCHEMA}"."usuarios" CASCADE')
            actions.append('Dropped legacy table "captar"."usuarios" (lowercase, quoted)')
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
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Eleitores" (
                    "IdEleitor" SERIAL PRIMARY KEY,
                    "Nome" VARCHAR(255) NOT NULL,
                    "CPF" VARCHAR(14),
                    "DataNascimento" DATE,
                    "Email" VARCHAR(255),
                    "Telefone" VARCHAR(20),
                    "Celular" VARCHAR(20),
                    "CEP" VARCHAR(10),
                    "Endereco" VARCHAR(255),
                    "Numero" VARCHAR(10),
                    "Complemento" VARCHAR(100),
                    "Bairro" VARCHAR(100),
                    "Cidade" VARCHAR(100),
                    "UF" CHAR(2),
                    "ZonaEleitoral" VARCHAR(10),
                    "SecaoEleitoral" VARCHAR(10),
                    "TituloEleitor" VARCHAR(20),
                    "LocalVotacao" TEXT,
                    "EnderecoLocalVotacao" TEXT,
                    "Ativo" BOOLEAN DEFAULT TRUE,
                    "Observacoes" TEXT,
                    "DataCadastro" TIMESTAMP DEFAULT NOW(),
                    "DataUpdate" TIMESTAMP,
                    "Cadastrante" VARCHAR(255),
                    "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant"),
                    "TenantLayer" VARCHAR(50)
                )
                """
            )
            actions.append('Eleitores created')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Ativistas" (
                    "IdAtivista" SERIAL PRIMARY KEY,
                    "Nome" VARCHAR(255) NOT NULL,
                    "CPF" VARCHAR(14),
                    "DataNascimento" DATE,
                    "Email" VARCHAR(255),
                    "Telefone" VARCHAR(20),
                    "Celular" VARCHAR(20),
                    "CEP" VARCHAR(10),
                    "Endereco" VARCHAR(255),
                    "Numero" VARCHAR(10),
                    "Complemento" VARCHAR(100),
                    "Bairro" VARCHAR(100),
                    "Cidade" VARCHAR(100),
                    "UF" CHAR(2),
                    "TipoApoio" VARCHAR(50),
                    "AreaAtuacao" VARCHAR(100),
                    "Habilidades" TEXT,
                    "Disponibilidade" TEXT,
                    "Ativo" BOOLEAN DEFAULT TRUE,
                    "Observacoes" TEXT,
                    "DataCadastro" TIMESTAMP DEFAULT NOW(),
                    "DataUpdate" TIMESTAMP,
                    "Cadastrante" VARCHAR(255),
                    "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant"),
                    "TenantLayer" VARCHAR(50)
                )
                """
            )
            actions.append('Ativistas created')
        except Exception:
            pass
        # legacy schema.sql execution removed to avoid recreating lowercase 'usuarios'
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
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Candidatos" (
                    "IdCandidato" SERIAL PRIMARY KEY,
                    "Nome" VARCHAR(255) NOT NULL,
                    "Numero" INT,
                    "Partido" VARCHAR(120),
                    "Cargo" VARCHAR(120),
                    "Foto" TEXT,
                    "Ativo" BOOLEAN DEFAULT TRUE,
                    "DataCadastro" TIMESTAMP DEFAULT NOW(),
                    "DataUpdate" TIMESTAMP,
                    "TipoUpdate" VARCHAR(20),
                    "UsuarioUpdate" VARCHAR(100),
                    "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                )
                """
            )
            actions.append('Candidatos created')
        except Exception:
            pass
        try:
            cur.execute(f'CREATE INDEX IF NOT EXISTS ix_candidatos_idtenant ON "{DB_SCHEMA}"."Candidatos"("IdTenant")')
            actions.append('Candidatos index ensured')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Eleicoes" (
                    "IdEleicao" SERIAL PRIMARY KEY,
                    "Nome" VARCHAR(255) NOT NULL,
                    "Ano" INT,
                    "Turno" INT,
                    "Cargo" VARCHAR(120),
                    "DataInicio" TIMESTAMP,
                    "DataFim" TIMESTAMP,
                    "Ativo" BOOLEAN DEFAULT TRUE,
                    "DataCadastro" TIMESTAMP DEFAULT NOW(),
                    "DataUpdate" TIMESTAMP,
                    "TipoUpdate" VARCHAR(20),
                    "UsuarioUpdate" VARCHAR(100),
                    "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                )
                """
            )
            actions.append('Eleicoes created')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Eleitores" (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(255),
                    cpf VARCHAR(14),
                    celular VARCHAR(20),
                    bairro VARCHAR(120),
                    zona_eleitoral VARCHAR(120),
                    criado_por INT REFERENCES "{DB_SCHEMA}"."Usuarios"("IdUsuario"),
                    "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant"),
                    "DataCadastro" TIMESTAMP DEFAULT NOW(),
                    "DataUpdate" TIMESTAMP,
                    "TipoUpdate" VARCHAR(20),
                    "UsuarioUpdate" VARCHAR(100)
                )
                """
            )
            actions.append('Eleitores created')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Ativistas" (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(255),
                    tipo_apoio VARCHAR(120),
                    criado_por INT REFERENCES "{DB_SCHEMA}"."Usuarios"("IdUsuario"),
                    "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant"),
                    "DataCadastro" TIMESTAMP DEFAULT NOW(),
                    "DataUpdate" TIMESTAMP,
                    "TipoUpdate" VARCHAR(20),
                    "UsuarioUpdate" VARCHAR(100)
                )
                """
            )
            actions.append('Ativistas created')
        except Exception:
            pass
        try:
            cur.execute(f'CREATE INDEX IF NOT EXISTS ix_eleicoes_idtenant ON "{DB_SCHEMA}"."Eleicoes"("IdTenant")')
            actions.append('Eleicoes index ensured')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Metas" (
                    "IdMeta" SERIAL PRIMARY KEY,
                    "IdCandidato" INT,
                    "Numero" INT,
                    "Partido" VARCHAR(120),
                    "Cargo" VARCHAR(120),
                    "IdEleicao" INT,
                    "DataInicio" TIMESTAMP,
                    "DataFim" TIMESTAMP,
                    "MetaVotos" INT,
                    "MetaDisparos" INT,
                    "MetaAprovacao" INT,
                    "MetaRejeicao" INT,
                    "Ativo" BOOLEAN DEFAULT TRUE,
                    "DataCadastro" TIMESTAMP DEFAULT NOW(),
                    "DataUpdate" TIMESTAMP,
                    "TipoUpdate" VARCHAR(20),
                    "UsuarioUpdate" VARCHAR(100),
                    "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                )
                """
            )
            actions.append('Metas created')
        except Exception:
            pass
        try:
            cur.execute(f'CREATE INDEX IF NOT EXISTS ix_metas_idtenant ON "{DB_SCHEMA}"."Metas"("IdTenant")')
            actions.append('Metas index ensured')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Candidatos" (
                    "IdCandidato" SERIAL PRIMARY KEY,
                    "Nome" VARCHAR(255) NOT NULL,
                    "Numero" INT,
                    "Partido" VARCHAR(120),
                    "Cargo" VARCHAR(120),
                    "Foto" TEXT,
                    "Ativo" BOOLEAN DEFAULT TRUE,
                    "DataCadastro" TIMESTAMP DEFAULT NOW(),
                    "DataUpdate" TIMESTAMP,
                    "TipoUpdate" VARCHAR(20),
                    "UsuarioUpdate" VARCHAR(100)
                )
                """
            )
            actions.append('Candidatos created')
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
            cur.execute(f'ALTER TABLE "{DB_SCHEMA}"."Tenant" ADD COLUMN IF NOT EXISTS "Dsn" TEXT')
            actions.append('Tenant.Dsn ensured')
        except Exception:
            pass
        try:
            cur.execute(f'ALTER TABLE "{DB_SCHEMA}"."Tenant" ADD COLUMN IF NOT EXISTS "DbCreatedAt" TIMESTAMP')
            actions.append('Tenant.DbCreatedAt ensured')
        except Exception:
            pass
        try:
            cur.execute(
                """
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = 'TenantParametros'
                """,
                (DB_SCHEMA,)
            )
            exists = cur.fetchone() is not None
            if exists:
                cur.execute(
                    f"""
                    UPDATE "{DB_SCHEMA}"."Tenant" t
                    SET "Dsn" = p."Valor"
                    FROM "{DB_SCHEMA}"."TenantParametros" p
                    WHERE p."IdTenant" = t."IdTenant" AND p."Chave" = 'DB_DSN' 
                      AND (t."Dsn" IS NULL OR t."Dsn" = '')
                    """
                )
        except Exception:
            pass
        try:
            cur.execute(f'DROP TABLE IF EXISTS "{DB_SCHEMA}"."TenantParametros" CASCADE')
            actions.append('TenantParametros dropped')
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

        # -----------------------------------------------------------
        # CAMPANHAS MIGRATION
        # -----------------------------------------------------------
        try:
            # Create table with new schema
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Campanhas" (
                    "IdCampanha" SERIAL PRIMARY KEY,
                    "NomeCampanha" VARCHAR(500),
                    "Texto" TEXT,
                    "DataInicio" DATE,
                    "DataFim" DATE,
                    "Status" BOOLEAN DEFAULT TRUE,
                    "Meta" INTEGER DEFAULT 0,
                    "Enviados" INTEGER DEFAULT 0,
                    "NaoEnviados" INTEGER DEFAULT 0,
                    "Positivos" INTEGER DEFAULT 0,
                    "Negativos" INTEGER DEFAULT 0,
                    "Aguardando" INTEGER DEFAULT 0,
                    "Cadastrante" VARCHAR(500),
                    "DataCriacao" TIMESTAMP DEFAULT NOW(),
                    "Atualizacao" TIMESTAMP,
                    "AnexoJSON" JSONB,
                    "Imagem" TEXT,
                    "RecorrenciaAtiva" BOOLEAN DEFAULT FALSE,
                    "TotalBlocos" INTEGER DEFAULT 5,
                    "MensagensPorBloco" INTEGER DEFAULT 500,
                    "BlocosPorDia" INTEGER DEFAULT 1,
                    "IntervaloMinSeg" INTEGER DEFAULT 5,
                    "IntervaloMaxSeg" INTEGER DEFAULT 120,
                    "BlocoAtual" INTEGER DEFAULT 0,
                    "ProximaExecucao" TIMESTAMP,
                    "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                )
                """
            )
            actions.append('Campanhas created')
            
            try:
                # Ensure columns exist (if table existed but missed some columns)
                campanha_cols = [
                    ('"Meta"', 'INTEGER DEFAULT 0'),
                    ('"Enviados"', 'INTEGER DEFAULT 0'),
                    ('"NaoEnviados"', 'INTEGER DEFAULT 0'),
                    ('"Positivos"', 'INTEGER DEFAULT 0'),
                    ('"Negativos"', 'INTEGER DEFAULT 0'),
                    ('"Aguardando"', 'INTEGER DEFAULT 0'),
                    ('"Cadastrante"', 'VARCHAR(500)'),
                    ('"AnexoJSON"', 'JSONB'),
                    ('"Imagem"', 'TEXT'),
                    ('"RecorrenciaAtiva"', 'BOOLEAN DEFAULT FALSE'),
                    ('"TotalBlocos"', 'INTEGER DEFAULT 5'),
                    ('"MensagensPorBloco"', 'INTEGER DEFAULT 500'),
                    ('"BlocosPorDia"', 'INTEGER DEFAULT 1'),
                    ('"IntervaloMinSeg"', 'INTEGER DEFAULT 5'),
                    ('"IntervaloMaxSeg"', 'INTEGER DEFAULT 120'),
                    ('"BlocoAtual"', 'INTEGER DEFAULT 0'),
                    ('"ProximaExecucao"', 'TIMESTAMP')
                ]
                for col_name, col_type in campanha_cols:
                    try:
                        cur.execute(
                            f"ALTER TABLE \"{DB_SCHEMA}\".\"Campanhas\" ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                        )
                    except Exception:
                        pass
                        
                actions.append('Campanhas schema updated')
            except Exception as e:
                actions.append(f'Campanhas alter error: {str(e)}')

        except Exception as e:
            actions.append(f'Campanhas error: {str(e)}')
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Disparos" (
                    "IdDisparo" SERIAL PRIMARY KEY,
                    "IdTenant" INT,
                    "IdCampanha" INT,
                    "Canal" VARCHAR(40) DEFAULT 'WHATSAPP',
                    "Direcao" VARCHAR(10) DEFAULT 'OUT',
                    "Numero" VARCHAR(40),
                    "Nome" VARCHAR(255),
                    "Mensagem" TEXT,
                    "Imagem" TEXT,
                    "Status" VARCHAR(40),
                    "DataHora" TIMESTAMP DEFAULT NOW(),
                    "IdDisparoRef" INT,
                    "RespostaClassificacao" VARCHAR(40),
                    "Payload" JSONB
                )
                """
            )
            try:
                cur.execute(f'CREATE INDEX IF NOT EXISTS "idx_disparos_tenant_datahora" ON "{DB_SCHEMA}"."Disparos" ("IdTenant", "DataHora" DESC)')
            except Exception:
                pass
            try:
                cur.execute(f'CREATE INDEX IF NOT EXISTS "idx_disparos_tenant_campanha_numero" ON "{DB_SCHEMA}"."Disparos" ("IdTenant", "IdCampanha", "Numero")')
            except Exception:
                pass
            actions.append('Disparos ensured')
        except Exception:
            pass
        try:
            disparos_cols = [
                ('"IdTenant"', 'INT'),
                ('"IdCampanha"', 'INT'),
                ('"Canal"', "VARCHAR(40) DEFAULT 'WHATSAPP'"),
                ('"Direcao"', "VARCHAR(10) DEFAULT 'OUT'"),
                ('"Numero"', 'VARCHAR(40)'),
                ('"Nome"', 'VARCHAR(255)'),
                ('"Mensagem"', 'TEXT'),
                ('"Imagem"', 'TEXT'),
                ('"Status"', 'VARCHAR(40)'),
                ('"DataHora"', 'TIMESTAMP DEFAULT NOW()'),
                ('"IdDisparoRef"', 'INT'),
                ('"RespostaClassificacao"', 'VARCHAR(40)'),
                ('"Payload"', 'JSONB'),
            ]
            for col_name, col_type in disparos_cols:
                try:
                    cur.execute(
                        f"ALTER TABLE \"{DB_SCHEMA}\".\"Disparos\" ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                    )
                except Exception:
                    pass
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Relatorios" (
                    "IdRelatorio" SERIAL PRIMARY KEY,
                    "IdTenant" INT,
                    "IdCampanha" INT,
                    "Titulo" VARCHAR(255),
                    "Tipo" VARCHAR(80),
                    "Parametros" JSONB,
                    "Dados" JSONB,
                    "CriadoEm" TIMESTAMP DEFAULT NOW(),
                    "CriadoPor" VARCHAR(255)
                )
                """
            )
            try:
                cur.execute(f'CREATE INDEX IF NOT EXISTS "idx_relatorios_tenant_criadoem" ON "{DB_SCHEMA}"."Relatorios" ("IdTenant", "CriadoEm" DESC)')
            except Exception:
                pass
            try:
                cur.execute(f'CREATE INDEX IF NOT EXISTS "idx_relatorios_tenant_campanha" ON "{DB_SCHEMA}"."Relatorios" ("IdTenant", "IdCampanha")')
            except Exception:
                pass
            actions.append('Relatorios ensured')
        except Exception:
            pass
            
    return actions

def apply_migrations_dsn(dsn: str, slug: Optional[str] = None):
    actions = []
    with get_db_connection(dsn) as conn:
        try:
            conn.rollback()
        except Exception:
            pass
        conn.autocommit = True
        cur = conn.cursor()
        try:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"')
        except Exception:
            pass
        try:
            cur.execute(f'DROP TABLE IF EXISTS {DB_SCHEMA}.usuarios CASCADE')
            actions.append('Dropped legacy table captar.usuarios (lowercase) in tenant DB')
        except Exception:
            pass
        try:
            cur.execute(f'DROP TABLE IF EXISTS "{DB_SCHEMA}"."usuarios" CASCADE')
            actions.append('Dropped legacy table "captar"."usuarios" (lowercase, quoted) in tenant DB')
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
            cur.execute(f"ALTER TABLE \"{DB_SCHEMA}\".\"Usuarios\" ADD COLUMN IF NOT EXISTS \"DataCadastro\" timestamp without time zone DEFAULT CURRENT_TIMESTAMP")
            actions.append('Usuarios.DataCadastro ensured (tenant DB)')
        except Exception:
            pass
        try:
            cur.execute(f"ALTER TABLE \"{DB_SCHEMA}\".\"Usuarios\" ADD COLUMN IF NOT EXISTS \"DataUpdate\" timestamp without time zone")
            actions.append('Usuarios.DataUpdate ensured (tenant DB)')
        except Exception:
            pass
        try:
            cur.execute(f"ALTER TABLE \"{DB_SCHEMA}\".\"Usuarios\" ADD COLUMN IF NOT EXISTS \"TipoUpdate\" varchar(20)")
            actions.append('Usuarios.TipoUpdate ensured (tenant DB)')
        except Exception:
            pass
        try:
            cur.execute(f"ALTER TABLE \"{DB_SCHEMA}\".\"Usuarios\" ADD COLUMN IF NOT EXISTS \"UsuarioUpdate\" varchar(100)")
            actions.append('Usuarios.UsuarioUpdate ensured (tenant DB)')
        except Exception:
            pass
        try:
            cur.execute(f"ALTER TABLE \"{DB_SCHEMA}\".\"Usuarios\" ADD COLUMN IF NOT EXISTS \"CadastranteUpdate\" varchar(100)")
            actions.append('Usuarios.CadastranteUpdate ensured (tenant DB)')
        except Exception:
            pass
        try:
            cur.execute(f"ALTER TABLE \"{DB_SCHEMA}\".\"Usuarios\" ADD COLUMN IF NOT EXISTS \"Coordenador\" VARCHAR(120)")
            actions.append('Usuarios.Coordenador ensured (tenant DB)')
        except Exception:
            pass
        try:
            cur.execute(f"ALTER TABLE \"{DB_SCHEMA}\".\"Usuarios\" ADD COLUMN IF NOT EXISTS \"Supervisor\" VARCHAR(120)")
            actions.append('Usuarios.Supervisor ensured (tenant DB)')
        except Exception:
            pass
        try:
            cur.execute(f"ALTER TABLE \"{DB_SCHEMA}\".\"Usuarios\" ADD COLUMN IF NOT EXISTS \"Ativista\" VARCHAR(120)")
            actions.append('Usuarios.Ativista ensured (tenant DB)')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Candidatos" (
                    "IdCandidato" SERIAL PRIMARY KEY,
                    "Nome" VARCHAR(255) NOT NULL,
                    "Numero" INT,
                    "Partido" VARCHAR(120),
                    "Cargo" VARCHAR(120),
                    "Foto" TEXT,
                    "Ativo" BOOLEAN DEFAULT TRUE,
                    "DataCadastro" TIMESTAMP DEFAULT NOW(),
                    "DataUpdate" TIMESTAMP,
                    "TipoUpdate" VARCHAR(20),
                    "UsuarioUpdate" VARCHAR(100),
                    "IdTenant" INT
                )
                """
            )
            actions.append('Candidatos ensured (tenant DB)')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Eleicoes" (
                    "IdEleicao" SERIAL PRIMARY KEY,
                    "Nome" VARCHAR(255) NOT NULL,
                    "Ano" INT,
                    "Turno" INT,
                    "Cargo" VARCHAR(120),
                    "DataInicio" TIMESTAMP,
                    "DataFim" TIMESTAMP,
                    "Ativo" BOOLEAN DEFAULT TRUE,
                    "DataCadastro" TIMESTAMP DEFAULT NOW(),
                    "DataUpdate" TIMESTAMP,
                    "TipoUpdate" VARCHAR(20),
                    "UsuarioUpdate" VARCHAR(100),
                    "IdTenant" INT
                )
                """
            )
            actions.append('Eleicoes ensured (tenant DB)')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Metas" (
                    "IdMeta" SERIAL PRIMARY KEY,
                    "IdCandidato" INT,
                    "Numero" INT,
                    "Partido" VARCHAR(120),
                    "Cargo" VARCHAR(120),
                    "IdEleicao" INT,
                    "DataInicio" TIMESTAMP,
                    "DataFim" TIMESTAMP,
                    "MetaVotos" INT,
                    "MetaDisparos" INT,
                    "MetaAprovacao" INT,
                    "MetaRejeicao" INT,
                    "Ativo" BOOLEAN DEFAULT TRUE,
                    "DataCadastro" TIMESTAMP DEFAULT NOW(),
                    "DataUpdate" TIMESTAMP,
                    "TipoUpdate" VARCHAR(20),
                    "UsuarioUpdate" VARCHAR(100),
                    "IdTenant" INT
                )
                """
            )
            actions.append('Metas ensured (tenant DB)')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Eleitores" (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(255),
                    cpf VARCHAR(14),
                    celular VARCHAR(20),
                    bairro VARCHAR(120),
                    zona_eleitoral VARCHAR(120),
                    criado_por INT,
                    "IdTenant" INT,
                    "DataCadastro" TIMESTAMP DEFAULT NOW(),
                    "DataUpdate" TIMESTAMP,
                    "TipoUpdate" VARCHAR(20),
                    "UsuarioUpdate" VARCHAR(100)
                )
                """
            )
            actions.append('Eleitores ensured (tenant DB)')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Ativistas" (
                    id SERIAL PRIMARY KEY,
                    nome VARCHAR(255),
                    tipo_apoio VARCHAR(120),
                    criado_por INT,
                    "IdTenant" INT,
                    "DataCadastro" TIMESTAMP DEFAULT NOW(),
                    "DataUpdate" TIMESTAMP,
                    "TipoUpdate" VARCHAR(20),
                    "UsuarioUpdate" VARCHAR(100)
                )
                """
            )
            actions.append('Ativistas ensured (tenant DB)')
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
        # legacy schema.sql execution removed to avoid recreating lowercase 'usuarios' in tenant DB
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

        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Campanhas" (
                    "IdCampanha" SERIAL PRIMARY KEY,
                    "NomeCampanha" VARCHAR(500),
                    "Texto" TEXT,
                    "DataInicio" DATE,
                    "DataFim" DATE,
                    "Status" BOOLEAN DEFAULT TRUE,
                    "Meta" INTEGER DEFAULT 0,
                    "Enviados" INTEGER DEFAULT 0,
                    "NaoEnviados" INTEGER DEFAULT 0,
                    "Positivos" INTEGER DEFAULT 0,
                    "Negativos" INTEGER DEFAULT 0,
                    "Aguardando" INTEGER DEFAULT 0,
                    "Cadastrante" VARCHAR(500),
                    "DataCriacao" TIMESTAMP DEFAULT NOW(),
                    "Atualizacao" TIMESTAMP,
                    "AnexoJSON" JSONB,
                    "Imagem" TEXT,
                    "RecorrenciaAtiva" BOOLEAN DEFAULT FALSE,
                    "TotalBlocos" INTEGER DEFAULT 5,
                    "MensagensPorBloco" INTEGER DEFAULT 500,
                    "BlocosPorDia" INTEGER DEFAULT 1,
                    "IntervaloMinSeg" INTEGER DEFAULT 5,
                    "IntervaloMaxSeg" INTEGER DEFAULT 120,
                    "BlocoAtual" INTEGER DEFAULT 0,
                    "ProximaExecucao" TIMESTAMP,
                    "IdTenant" INT
                )
                """
            )
            campanha_cols = [
                ('"RecorrenciaAtiva"', 'BOOLEAN DEFAULT FALSE'),
                ('"TotalBlocos"', 'INTEGER DEFAULT 5'),
                ('"MensagensPorBloco"', 'INTEGER DEFAULT 500'),
                ('"BlocosPorDia"', 'INTEGER DEFAULT 1'),
                ('"IntervaloMinSeg"', 'INTEGER DEFAULT 5'),
                ('"IntervaloMaxSeg"', 'INTEGER DEFAULT 120'),
                ('"BlocoAtual"', 'INTEGER DEFAULT 0'),
                ('"ProximaExecucao"', 'TIMESTAMP')
            ]
            for col_name, col_type in campanha_cols:
                try:
                    cur.execute(
                        f"ALTER TABLE \"{DB_SCHEMA}\".\"Campanhas\" ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                    )
                except Exception:
                    pass
            actions.append('Campanhas ensured (tenant DB)')
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Disparos" (
                    "IdDisparo" SERIAL PRIMARY KEY,
                    "IdTenant" INT,
                    "IdCampanha" INT,
                    "Canal" VARCHAR(40) DEFAULT 'WHATSAPP',
                    "Direcao" VARCHAR(10) DEFAULT 'OUT',
                    "Numero" VARCHAR(40),
                    "Nome" VARCHAR(255),
                    "Mensagem" TEXT,
                    "Imagem" TEXT,
                    "Status" VARCHAR(40),
                    "DataHora" TIMESTAMP DEFAULT NOW(),
                    "IdDisparoRef" INT,
                    "RespostaClassificacao" VARCHAR(40),
                    "Payload" JSONB
                )
                """
            )
            try:
                cur.execute(f'CREATE INDEX IF NOT EXISTS "idx_disparos_tenant_datahora" ON "{DB_SCHEMA}"."Disparos" ("IdTenant", "DataHora" DESC)')
            except Exception:
                pass
            try:
                cur.execute(f'CREATE INDEX IF NOT EXISTS "idx_disparos_tenant_campanha_numero" ON "{DB_SCHEMA}"."Disparos" ("IdTenant", "IdCampanha", "Numero")')
            except Exception:
                pass
            actions.append('Disparos ensured (tenant DB)')
        except Exception:
            pass
        try:
            disparos_cols = [
                ('"IdTenant"', 'INT'),
                ('"IdCampanha"', 'INT'),
                ('"Canal"', "VARCHAR(40) DEFAULT 'WHATSAPP'"),
                ('"Direcao"', "VARCHAR(10) DEFAULT 'OUT'"),
                ('"Numero"', 'VARCHAR(40)'),
                ('"Nome"', 'VARCHAR(255)'),
                ('"Mensagem"', 'TEXT'),
                ('"Imagem"', 'TEXT'),
                ('"Status"', 'VARCHAR(40)'),
                ('"DataHora"', 'TIMESTAMP DEFAULT NOW()'),
                ('"IdDisparoRef"', 'INT'),
                ('"RespostaClassificacao"', 'VARCHAR(40)'),
                ('"Payload"', 'JSONB'),
            ]
            for col_name, col_type in disparos_cols:
                try:
                    cur.execute(
                        f"ALTER TABLE \"{DB_SCHEMA}\".\"Disparos\" ADD COLUMN IF NOT EXISTS {col_name} {col_type}"
                    )
                except Exception:
                    pass
        except Exception:
            pass
        try:
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Relatorios" (
                    "IdRelatorio" SERIAL PRIMARY KEY,
                    "IdTenant" INT,
                    "IdCampanha" INT,
                    "Titulo" VARCHAR(255),
                    "Tipo" VARCHAR(80),
                    "Parametros" JSONB,
                    "Dados" JSONB,
                    "CriadoEm" TIMESTAMP DEFAULT NOW(),
                    "CriadoPor" VARCHAR(255)
                )
                """
            )
            try:
                cur.execute(f'CREATE INDEX IF NOT EXISTS "idx_relatorios_tenant_criadoem" ON "{DB_SCHEMA}"."Relatorios" ("IdTenant", "CriadoEm" DESC)')
            except Exception:
                pass
            try:
                cur.execute(f'CREATE INDEX IF NOT EXISTS "idx_relatorios_tenant_campanha" ON "{DB_SCHEMA}"."Relatorios" ("IdTenant", "IdCampanha")')
            except Exception:
                pass
            actions.append('Relatorios ensured (tenant DB)')
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
            admin_user = f"ADMIN.{slug_upper}"
            cur.execute(
                f"SELECT \"IdUsuario\" FROM \"{DB_SCHEMA}\".\"Usuarios\" WHERE UPPER(TRIM(\"Usuario\")) = 'ADMIN' LIMIT 1"
            )
            row_fix = cur.fetchone()
            if row_fix:
                cur.execute(
                    f"UPDATE \"{DB_SCHEMA}\".\"Usuarios\" SET \"Usuario\" = %s, \"Senha\" = %s WHERE \"IdUsuario\" = %s",
                    (admin_user, 'admin123', int(row_fix[0]))
                )
                actions.append('Default admin user adjusted (tenant DB)')
            if m == 0:
                admin_email = f"admin@{(slug or 'tenant').lower()}.local"
                admin_pass = 'admin123'
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

@app.post("/api/admin/ensure_eleitores_ativistas")
async def admin_ensure_eleitores_ativistas():
    try:
        with get_db_connection() as conn:
            try:
                conn.rollback()
            except Exception:
                pass
            conn.autocommit = True
            cur = conn.cursor()
            try:
                cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{DB_SCHEMA}"')
            except Exception:
                pass
            try:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Eleitores" (
                        id SERIAL PRIMARY KEY,
                        nome VARCHAR(255),
                        cpf VARCHAR(14),
                        celular VARCHAR(20),
                        bairro VARCHAR(120),
                        zona_eleitoral VARCHAR(120),
                        criado_por INT REFERENCES "{DB_SCHEMA}"."Usuarios"("IdUsuario"),
                        "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant"),
                        "DataCadastro" TIMESTAMP DEFAULT NOW(),
                        "DataUpdate" TIMESTAMP,
                        "TipoUpdate" VARCHAR(20),
                        "UsuarioUpdate" VARCHAR(100)
                    )
                    """
                )
            except Exception:
                pass
            try:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Ativistas" (
                        id SERIAL PRIMARY KEY,
                        nome VARCHAR(255),
                        tipo_apoio VARCHAR(120),
                        criado_por INT REFERENCES "{DB_SCHEMA}"."Usuarios"("IdUsuario"),
                        "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant"),
                        "DataCadastro" TIMESTAMP DEFAULT NOW(),
                        "DataUpdate" TIMESTAMP,
                        "TipoUpdate" VARCHAR(20),
                        "UsuarioUpdate" VARCHAR(100)
                    )
                    """
                )
            except Exception:
                pass
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/migrate_all_tenants")
async def admin_migrate_all_tenants():
    try:
        results = []
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(f'SELECT t."Slug", t."Dsn", t."IdTenant" FROM "{DB_SCHEMA}"."Tenant" t')
            rows = cur.fetchall()
        for slug, dsn, idt in rows:
            slug_s = str(slug or '')
            idn = int(idt or 0)
            dsn_s = str(dsn or '')
            if not dsn_s:
                dsn_s = _ensure_tenant_database(slug_s, idn)
            actions = apply_migrations_dsn(dsn_s, slug_s)
            results.append({"slug": slug_s, "actions": actions})
        return {"ok": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/ensure_usuarios")
async def admin_ensure_usuarios():
    try:
        with get_db_connection() as conn:
            try:
                conn.rollback()
            except Exception:
                pass
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
        slug = request.headers.get('X-Tenant') if request else 'captar'
        view = request.headers.get('X-View-Tenant') if request else None
        s = str(slug or '').lower()
        if s != 'captar':
            tid = _tenant_id_from_header(request)
            with get_conn_for_request(request) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"SELECT u.* FROM \"{DB_SCHEMA}\".\"Usuarios\" u WHERE \"IdTenant\" = %s ORDER BY 1 ASC LIMIT %s",
                    (tid, limit)
                )
                colnames = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                data = [dict(zip(colnames, row)) for row in rows]
                tn = _tenant_name_from_header(request)
                for d in data:
                    d['TenantLayer'] = tn
                if 'TenantLayer' not in colnames:
                    colnames.append('TenantLayer')
                return {"rows": data, "columns": colnames}
        # s == 'captar'
        # optional view filter
        view_s = str(view or '').lower()
        if view_s:
            if view_s == 'captar':
                with get_db_connection() as conn_c:
                    cur_c = conn_c.cursor()
                    tid_c = _ensure_tenant_slug('captar')
                    cur_c.execute(f"SELECT u.* FROM \"{DB_SCHEMA}\".\"Usuarios\" u WHERE \"IdTenant\" = %s ORDER BY 1 ASC LIMIT %s", (tid_c, limit))
                    cols_c = [d[0] for d in cur_c.description]
                    rows_c = cur_c.fetchall()
                    data = [dict(zip(cols_c, r)) for r in rows_c]
                    for d in data:
                        d['TenantLayer'] = 'CAPTAR'
                    if 'TenantLayer' not in cols_c:
                        cols_c.append('TenantLayer')
                    return {"rows": data, "columns": cols_c}
            dsn = _get_dsn_by_slug(view_s)
            if dsn:
                try:
                    tid_t = _ensure_tenant_slug(view_s)
                    with get_db_connection(dsn) as conn_t:
                        cur_t = conn_t.cursor()
                        cur_t.execute(f"SELECT u.* FROM \"{DB_SCHEMA}\".\"Usuarios\" u WHERE \"IdTenant\" = %s ORDER BY 1 ASC LIMIT %s", (tid_t, limit))
                        cols_t = [d[0] for d in cur_t.description]
                        rows_t = cur_t.fetchall()
                        data = [dict(zip(cols_t, r)) for r in rows_t]
                        name = view_s.upper()
                        try:
                            with get_db_connection() as conn_c2:
                                c2 = conn_c2.cursor()
                                c2.execute(f'SELECT "Nome" FROM "{DB_SCHEMA}"."Tenant" WHERE LOWER("Slug")=%s LIMIT 1', (view_s,))
                                rw = c2.fetchone()
                                if rw and rw[0]:
                                    name = str(rw[0]).upper()
                        except Exception:
                            pass
                        for d in data:
                            d['TenantLayer'] = name
                        if 'TenantLayer' not in cols_t:
                            cols_t.append('TenantLayer')
                        return {"rows": data, "columns": cols_t}
                except Exception:
                    pass
        # aggregate all tenants
        union_cols = set()
        out_rows = []
        # CAPTAR central rows
        with get_db_connection() as conn_c:
            cur_c = conn_c.cursor()
            try:
                if not view_s or view_s == 'captar':
                    tid_c = _ensure_tenant_slug('captar')
                    cur_c.execute(
                        f"SELECT u.* FROM \"{DB_SCHEMA}\".\"Usuarios\" u WHERE \"IdTenant\" = %s ORDER BY 1 ASC LIMIT %s",
                        (tid_c, limit)
                    )
                    cols_c = [d[0] for d in cur_c.description]
                    union_cols.update(cols_c)
                    rows_c = cur_c.fetchall()
                    for r in rows_c:
                        d = dict(zip(cols_c, r))
                        d['TenantLayer'] = 'CAPTAR'
                        out_rows.append(d)
            except Exception:
                pass
            # tenants via DSN
            cur_c.execute(f'SELECT t."Slug", t."Nome", t."Dsn", t."IdTenant" FROM "{DB_SCHEMA}"."Tenant" t WHERE t."Dsn" IS NOT NULL')
            tenants = cur_c.fetchall()
        for slug_row, nome_row, dsn_row, id_tenant_row in tenants:
            try:
                dsn = str(dsn_row or '')
                if not dsn:
                    continue
                if view_s and str(slug_row or '').lower() != view_s:
                    continue
                with get_db_connection(dsn) as conn_t:
                    cur_t = conn_t.cursor()
                    cur_t.execute(
                        f"SELECT u.* FROM \"{DB_SCHEMA}\".\"Usuarios\" u WHERE \"IdTenant\" = %s ORDER BY 1 ASC LIMIT %s",
                        (id_tenant_row, limit)
                    )
                    cols_t = [d[0] for d in cur_t.description]
                    union_cols.update(cols_t)
                    rows_t = cur_t.fetchall()
                    for r in rows_t:
                        d = dict(zip(cols_t, r))
                        d['TenantLayer'] = str(nome_row or slug_row or '').upper() or 'TENANT'
                        out_rows.append(d)
            except Exception:
                pass
        union_cols.add('TenantLayer')
        all_cols = list(union_cols)
        # normalize rows to include all columns
        for r in out_rows:
            for c in all_cols:
                if c not in r:
                    r[c] = None
        return {"rows": out_rows, "columns": all_cols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/usuarios")
async def usuarios_create(payload: dict, request: Request):
    try:
        rate_limit(request, "usuarios_create", 120)
        slug_hdr = _tenant_slug(request)
        dsn_cur = _get_tenant_dsn(slug_hdr)
        cols_meta = get_table_columns("Usuarios")
        if dsn_cur:
            try:
                with get_db_connection(dsn_cur) as conn_cols:
                    cm = _get_table_columns_for_conn(conn_cols, "Usuarios")
                    if cm:
                        cols_meta = cm
            except Exception:
                pass
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
        with get_conn_for_request(request) as conn_check:
            cur0 = conn_check.cursor()
            tid = _tenant_id_from_header(request)
            cur0.execute(f'SELECT "Usuario" FROM "{DB_SCHEMA}"."Usuarios" WHERE "IdUsuario" = %s AND "IdTenant" = %s LIMIT 1', (id, tid))
            row0 = cur0.fetchone()
            if row0:
                u0 = str(row0[0] or '').strip().upper()
                if u0 == 'ADMIN' or u0.startswith('ADMIN.'):
                    raise HTTPException(status_code=403, detail='Usuário padrão do sistema não pode ser alterado')
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
        tid = _tenant_id_from_header(request)
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            cursor.execute(f'SELECT "Usuario" FROM "{DB_SCHEMA}"."Usuarios" WHERE "IdUsuario" = %s AND "IdTenant" = %s LIMIT 1', (id, tid))
            r0 = cursor.fetchone()
            if r0:
                u0 = str(r0[0] or '').strip().upper()
                if u0 == 'ADMIN' or u0.startswith('ADMIN.'):
                    raise HTTPException(status_code=403, detail='Usuário padrão do sistema não pode ser removido')
            cursor.execute(f"DELETE FROM \"{DB_SCHEMA}\".\"Usuarios\" WHERE \"IdUsuario\" = %s AND \"IdTenant\" = %s", (id, tid))
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
async def update_permissao(perfil: str, data: PermissaoUpdate, request: Request):
    """Atualizar permissões de um perfil"""
    try:
        slug = _tenant_slug(request)
        if slug.lower() != 'captar':
            raise HTTPException(status_code=403, detail="Apenas o tenant principal pode gerenciar permissões globais")
        
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/permissoes")
async def create_permissao(data: PermissaoUpdate, request: Request):
    try:
        slug = _tenant_slug(request)
        if slug.lower() != 'captar':
            raise HTTPException(status_code=403, detail="Apenas o tenant principal pode gerenciar permissões globais")

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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/permissoes/{perfil}")
async def delete_permissao(perfil: str, request: Request):
    try:
        slug = _tenant_slug(request)
        if slug.lower() != 'captar':
            raise HTTPException(status_code=403, detail="Apenas o tenant principal pode gerenciar permissões globais")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {DB_SCHEMA}.permissoes WHERE perfil = %s", (perfil,))
            conn.commit()
            return {"message": "Perfil deletado com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== PERFIL (TABELA perfil) ====================

def get_table_columns(table: str):
    # Map lowercase table names to capitalized ones for specific tables
    if table.lower() in ['eleitores', 'ativistas', 'campanhas']:
        table = table.capitalize()
        
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

def _get_dsn_by_slug(slug: str):
    try:
        s = str(slug or '').lower()
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(f'SELECT t."IdTenant" FROM "{DB_SCHEMA}"."Tenant" t WHERE LOWER(t."Slug")=%s LIMIT 1', (s,))
            row = cur.fetchone()
            if not row:
                return None
            idt = int(row[0])
            cur.execute(f'SELECT "Dsn" FROM "{DB_SCHEMA}"."Tenant" WHERE "IdTenant"=%s LIMIT 1', (idt,))
            r2 = cur.fetchone()
            if r2 and r2[0]:
                return str(r2[0])
            return None
    except Exception:
        return None
def _aggregate_table_all_tenants(table: str, limit: int = 500):
    union_cols = set()
    out_rows = []
    # Ensure table name is capitalized for the new schema
    table_name = table.capitalize()
    try:
        with get_db_connection() as conn_c:
            cur_c = conn_c.cursor()
            try:
                tid_c = _ensure_tenant_slug('captar')
                cur_c.execute(f"SELECT * FROM \"{DB_SCHEMA}\".\"{table_name}\" WHERE \"IdTenant\" = %s ORDER BY 1 ASC LIMIT %s", (tid_c, limit))
                cols_c = [d[0] for d in cur_c.description]
                union_cols.update(cols_c)
                rows_c = cur_c.fetchall()
                for r in rows_c:
                    d = dict(zip(cols_c, r))
                    d['TenantLayer'] = 'CAPTAR'
                    out_rows.append(d)
            except Exception:
                pass
            tenants = _list_tenants_with_dsn()
        for slug_row, nome_row, dsn_row, idt_row in tenants:
            try:
                dsn = str(dsn_row or '')
                if not dsn:
                    continue
                with get_db_connection(dsn) as conn_t:
                    cur_t = conn_t.cursor()
                    cur_t.execute(f"SELECT * FROM \"{DB_SCHEMA}\".\"{table_name}\" WHERE \"IdTenant\" = %s ORDER BY 1 ASC LIMIT %s", (idt_row, limit))
                    cols_t = [d[0] for d in cur_t.description]
                    union_cols.update(cols_t)
                    rows_t = cur_t.fetchall()
                    for r in rows_t:
                        d = dict(zip(cols_t, r))
                        d['TenantLayer'] = str(nome_row or slug_row or '').upper() or 'TENANT'
                        out_rows.append(d)
            except Exception:
                pass
    except Exception:
        pass
    union_cols.add('TenantLayer')
    all_cols = list(union_cols)
    for r in out_rows:
        for c in all_cols:
            if c not in r:
                r[c] = None
    return out_rows, all_cols

def _get_table_columns_for_conn(conn, table: str):
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT column_name, data_type, is_nullable, character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (DB_SCHEMA, table)
        )
        rows = cur.fetchall()
        return [{"name": r[0], "type": r[1], "nullable": (r[2] == 'YES'), "maxLength": r[3]} for r in rows]
    except Exception:
        return []

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
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            if str(slug or '').lower() == 'captar':
                tid = _ensure_tenant_slug('captar')
                cursor.execute(f"SELECT * FROM \"{DB_SCHEMA}\".\"Perfil\" WHERE \"IdTenant\" = %s ORDER BY 1 DESC LIMIT %s", (tid, limit))
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
        with get_conn_for_request(request) as conn:
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
        
        with get_conn_for_request(request) as conn:
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
async def perfil_delete(id: int, request: Request):
    try:
        tid = _tenant_id_from_header(request)
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM \"{DB_SCHEMA}\".\"Perfil\" WHERE \"IdPerfil\" = %s AND \"IdTenant\" = %s", (id, tid))
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
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            if str(slug or '').lower() == 'captar':
                tid = _ensure_tenant_slug('captar')
                cursor.execute(f"SELECT * FROM \"{DB_SCHEMA}\".\"Funcoes\" WHERE \"IdTenant\" = %s ORDER BY \"IdFuncao\" DESC LIMIT %s", (tid, limit))
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
        with get_conn_for_request(request) as conn:
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
        with get_conn_for_request(request) as conn:
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
async def funcoes_delete(id: int, request: Request):
    try:
        tid = _tenant_id_from_header(request)
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM \"{DB_SCHEMA}\".\"Funcoes\" WHERE \"IdFuncao\" = %s AND \"IdTenant\" = %s", (id, tid))
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
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            tid = _tenant_id_from_header(request)

            if filtro.tipo == "coordenador":
                query = f"SELECT * FROM \"{DB_SCHEMA}\".\"Eleitores\" e WHERE e.coordenador = %s AND EXISTS (SELECT 1 FROM \"{DB_SCHEMA}\".\"Usuarios\" u WHERE u.\"Nome\" = e.coordenador AND u.\"IdTenant\" = %s)"
            elif filtro.tipo == "supervisor":
                query = f"SELECT * FROM \"{DB_SCHEMA}\".\"Eleitores\" e WHERE e.supervisor = %s AND EXISTS (SELECT 1 FROM \"{DB_SCHEMA}\".\"Usuarios\" u WHERE u.\"Nome\" = e.supervisor AND u.\"IdTenant\" = %s)"
            elif filtro.tipo == "ativista":
                query = f"SELECT * FROM \"{DB_SCHEMA}\".\"Eleitores\" e WHERE e.indicacao = %s AND EXISTS (SELECT 1 FROM \"{DB_SCHEMA}\".\"Usuarios\" u WHERE u.\"Nome\" = e.indicacao AND u.\"IdTenant\" = %s)"
            elif filtro.tipo == "bairro":
                query = f"SELECT * FROM \"{DB_SCHEMA}\".\"Eleitores\" WHERE bairro = %s AND \"IdTenant\" = %s"
            elif filtro.tipo == "zona":
                query = f"SELECT * FROM \"{DB_SCHEMA}\".\"Eleitores\" WHERE zona_eleitoral = %s AND \"IdTenant\" = %s"
            else:
                raise HTTPException(status_code=400, detail="Tipo de filtro inválido")
            
            if filtro.tipo in ("coordenador","supervisor","ativista"):
                cursor.execute(query, (filtro.valor, tid))
            else:
                cursor.execute(query, (filtro.valor, tid))
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
                cursor.execute(f"SELECT * FROM \"{DB_SCHEMA}\".\"Eleitores\" LIMIT 1000")
            elif data.tabela == "ativistas":
                cursor.execute(f"SELECT * FROM \"{DB_SCHEMA}\".\"Ativistas\" LIMIT 1000")
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
                        f"INSERT INTO \"{DB_SCHEMA}\".\"Eleitores\" (nome, cpf, celular) VALUES (%s, %s, %s)",
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
async def marcar_notificacao_lida(notif_id: int, request: Request):
    """Marcar notificação como lida"""
    try:
        tid = _tenant_id_from_header(request)
        with get_conn_for_request(request) as conn:
            cursor = conn.cursor()
            # Ensure we only update notifications belonging to users of the current tenant
            cursor.execute(
                f"""
                UPDATE {DB_SCHEMA}.notificacoes n
                SET lida = true, lida_em = %s
                FROM {DB_SCHEMA}.usuarios u
                WHERE n.usuario_id = u.id AND n.id = %s AND u."IdTenant" = %s
                """,
                (datetime.utcnow(), notif_id, tid)
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
        view = request and request.headers.get('X-View-Tenant') or None
        if rc and request:
            try:
                cache_key = f"tenant:{str(slug).lower()}:dashboard:stats:{(str(view or '').lower() or 'all')}"
                raw = rc.get(cache_key)
                if raw:
                    return json.loads(raw)
            except Exception:
                pass
        with get_db_connection() as conn:
            try:
                conn.rollback()
            except Exception:
                pass
            conn.autocommit = True
            cursor = conn.cursor()
            tid = _tenant_id_from_header(request) if request else 1
            s = str(slug or '').lower()

            if s != 'captar':
                try:
                    cursor.execute(
                        f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Eleitores\" e JOIN \"{DB_SCHEMA}\".\"Usuarios\" u ON e.criado_por = u.\"IdUsuario\" WHERE u.\"IdTenant\" = %s",
                        (tid,)
                    )
                    total_eleitores = cursor.fetchone()[0]
                except Exception:
                    total_eleitores = 0
                try:
                    cursor.execute(
                        f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Ativistas\" a JOIN \"{DB_SCHEMA}\".\"Usuarios\" u ON a.criado_por = u.\"IdUsuario\" WHERE u.\"IdTenant\" = %s",
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
                    f"SELECT COALESCE(e.zona_eleitoral, 'N/D') AS zona, COUNT(*) AS qtd FROM \"{DB_SCHEMA}\".\"Eleitores\" e JOIN \"{DB_SCHEMA}\".\"Usuarios\" u ON e.criado_por = u.\"IdUsuario\" WHERE u.\"IdTenant\" = %s GROUP BY e.zona_eleitoral ORDER BY qtd DESC LIMIT 20",
                    (tid,)
                )
                zonas_rows = cursor.fetchall()
                try:
                    cursor.execute(
                        f"SELECT COALESCE(a.tipo_apoio, 'N/D') AS funcao, COUNT(*) AS qtd FROM \"{DB_SCHEMA}\".\"Ativistas\" a JOIN \"{DB_SCHEMA}\".\"Usuarios\" u ON a.criado_por = u.\"IdUsuario\" WHERE u.\"IdTenant\" = %s GROUP BY a.tipo_apoio ORDER BY qtd DESC LIMIT 20",
                        (tid,)
                    )
                    ativistas_por_funcao_rows = cursor.fetchall()
                except Exception:
                    ativistas_por_funcao_rows = []
            else:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Eleitores\"")
                    total_eleitores = cursor.fetchone()[0]
                except Exception:
                    total_eleitores = 0
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Ativistas\"")
                    total_ativistas = cursor.fetchone()[0]
                except Exception:
                    total_ativistas = 0
                cursor.execute(f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Usuarios\"")
                total_usuarios = cursor.fetchone()[0]
                try:
                    cursor.execute(
                        f"SELECT COALESCE(zona_eleitoral, 'N/D') AS zona, COUNT(*) AS qtd FROM \"{DB_SCHEMA}\".\"Eleitores\" GROUP BY zona_eleitoral ORDER BY qtd DESC LIMIT 20"
                    )
                    zonas_rows = cursor.fetchall()
                except Exception:
                    zonas_rows = []
                try:
                    cursor.execute(
                        f"SELECT COALESCE(tipo_apoio, 'N/D') AS funcao, COUNT(*) AS qtd FROM \"{DB_SCHEMA}\".\"Ativistas\" GROUP BY tipo_apoio ORDER BY qtd DESC LIMIT 20"
                    )
                    ativistas_por_funcao_rows = cursor.fetchall()
                except Exception:
                    ativistas_por_funcao_rows = []
                view_s = str(view or '').lower()
                if view_s:
                    if view_s == 'captar':
                        # já central
                        pass
                    else:
                        dsn = _get_dsn_by_slug(view_s)
                        if dsn:
                            try:
                                total_eleitores = 0
                                total_ativistas = 0
                                total_usuarios = 0
                                zonas_rows = []
                                ativistas_por_funcao_rows = []
                                with get_db_connection(dsn) as conn_t:
                                    cur_t = conn_t.cursor()
                                    try:
                                        cur_t.execute(f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Eleitores\"")
                                        total_eleitores = int(cur_t.fetchone()[0])
                                    except Exception:
                                        pass
                                    try:
                                        cur_t.execute(f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Ativistas\"")
                                        total_ativistas = int(cur_t.fetchone()[0])
                                    except Exception:
                                        pass
                                    try:
                                        cur_t.execute(f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Usuarios\"")
                                        total_usuarios = int(cur_t.fetchone()[0])
                                    except Exception:
                                        pass
                                    try:
                                        cur_t.execute(
                                            f"SELECT COALESCE(zona_eleitoral, 'N/D') AS zona, COUNT(*) AS qtd FROM \"{DB_SCHEMA}\".\"Eleitores\" GROUP BY zona_eleitoral ORDER BY qtd DESC LIMIT 20"
                                        )
                                        zonas_rows = cur_t.fetchall()
                                    except Exception:
                                        pass
                                    try:
                                        cur_t.execute(
                                            f"SELECT COALESCE(tipo_apoio, 'N/D') AS funcao, COUNT(*) AS qtd FROM \"{DB_SCHEMA}\".\"Ativistas\" GROUP BY tipo_apoio ORDER BY qtd DESC LIMIT 20"
                                        )
                                        ativistas_por_funcao_rows = cur_t.fetchall()
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                if not (str(view or '').strip()):
                    tenants = _list_tenants_with_dsn()
                    for slug_row, nome_row, dsn_row in tenants:
                        try:
                            dsn = str(dsn_row or '')
                            if not dsn:
                                continue
                            with get_db_connection(dsn) as conn_t:
                                cur_t = conn_t.cursor()
                                try:
                                    cur_t.execute(f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Eleitores\"")
                                    total_eleitores += int(cur_t.fetchone()[0])
                                except Exception:
                                    pass
                                try:
                                    cur_t.execute(f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Ativistas\"")
                                    total_ativistas += int(cur_t.fetchone()[0])
                                except Exception:
                                    pass
                                try:
                                    cur_t.execute(f"SELECT COUNT(*) FROM \"{DB_SCHEMA}\".\"Usuarios\"")
                                    total_usuarios += int(cur_t.fetchone()[0])
                                except Exception:
                                    pass
                                try:
                                    cur_t.execute(
                                        f"SELECT COALESCE(zona_eleitoral, 'N/D') AS zona, COUNT(*) AS qtd FROM \"{DB_SCHEMA}\".\"Eleitores\" GROUP BY zona_eleitoral"
                                    )
                                    add_z = cur_t.fetchall()
                                    zonas_rows += add_z
                                except Exception:
                                    pass
                                try:
                                    cur_t.execute(
                                        f"SELECT COALESCE(tipo_apoio, 'N/D') AS funcao, COUNT(*) AS qtd FROM \"{DB_SCHEMA}\".\"Ativistas\" GROUP BY tipo_apoio"
                                    )
                                    add_a = cur_t.fetchall()
                                    ativistas_por_funcao_rows += add_a
                                except Exception:
                                    pass
                        except Exception:
                            pass

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
                    cache_key = f"tenant:{str(slug).lower()}:dashboard:stats:{(str(view or '').lower() or 'all')}"
                    rc.setex(cache_key, 30, json.dumps(out))
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
                _set_tenant_dsn(new_id, dsn)
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
            _set_tenant_dsn(id_tenant, dsn)
            actions = apply_migrations_dsn(dsn, s)
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
            cur.execute(f'DELETE FROM "{DB_SCHEMA}"."Tenant" WHERE "IdTenant"=%s', (id_tenant,))
            return {"ok": True, "deleted": id_tenant, "dropped": db_name}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tenants/recreate_db")
async def tenants_recreate_db_body(body: dict, request: Request):
    try:
        slug_hdr = _tenant_slug(request)
        if slug_hdr.lower() != 'captar':
            raise HTTPException(status_code=403, detail="Apenas o tenant principal pode gerenciar tenants")

        slug = str(body.get('slug') or '').lower()
        if not slug:
            raise HTTPException(status_code=400, detail='slug obrigatório')
        return await tenants_recreate_db(slug)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/tenants/delete_all")
async def tenants_delete_all_body(body: dict, request: Request):
    try:
        slug_hdr = _tenant_slug(request)
        if slug_hdr.lower() != 'captar':
            raise HTTPException(status_code=403, detail="Apenas o tenant principal pode gerenciar tenants")

        slug = str(body.get('slug') or '').lower()
        if not slug:
            raise HTTPException(status_code=400, detail='slug obrigatório')
        return await tenants_delete_all(slug)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tenants/{id}")
async def tenants_update(id: int, payload: dict, request: Request):
    try:
        slug_hdr = _tenant_slug(request)
        if slug_hdr.lower() != 'captar':
            raise HTTPException(status_code=403, detail="Apenas o tenant principal pode gerenciar tenants")

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
async def tenants_delete(id: int, request: Request):
    try:
        slug_hdr = _tenant_slug(request)
        if slug_hdr.lower() != 'captar':
            raise HTTPException(status_code=403, detail="Apenas o tenant principal pode gerenciar tenants")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM \"{DB_SCHEMA}\".\"Tenant\" WHERE \"IdTenant\" = %s", (id,))
            conn.commit()
            return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Tenant parâmetros removidos

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
                    LEFT JOIN \"{DB_SCHEMA}\".\"Eleitores\" e ON e.criado_por = u."IdUsuario"
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
                    LEFT JOIN \"{DB_SCHEMA}\".\"Eleitores\" e ON e.criado_por = u."IdUsuario"
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
                    FROM "{DB_SCHEMA}"."Ativistas"
                    GROUP BY tipo_apoio
                    ORDER BY qtd DESC
                    LIMIT 10
                    """
                )
            else:
                try:
                    cursor.execute(
                        f"""
                        SELECT COALESCE(a."TipoApoio", 'Desconhecido') AS categoria, COUNT(*) AS qtd
                        FROM "{DB_SCHEMA}"."Ativistas" a
                        JOIN "{DB_SCHEMA}"."Usuarios" u ON a."Cadastrante" = u."Nome"
                        WHERE u."IdTenant" = %s
                        GROUP BY a."TipoApoio"
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
                FROM \"{DB_SCHEMA}\".\"Eleitores\"
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
                FROM \"{DB_SCHEMA}\".\"Eleitores\"
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

def _mask_key(k: str) -> str:
    s = str(k or "")
    if len(s) <= 10:
        return "*" * len(s) if s else ""
    return s[:6] + ("*" * (len(s) - 10)) + s[-4:]

@app.get("/api/integracoes/evolution/key")
async def integracoes_evolution_key(request: Request):
    try:
        with get_conn_for_request(request) as conn:
            inst = _get_evolution_instance(conn, None)
            val = str(inst.get("token") or "").strip() or str(os.getenv("AUTHENTICATION_API_KEY", "") or "").strip()
            return {"hasKey": bool(val), "keyMasked": _mask_key(val), "evolution_api_id": inst["id"]}
    except HTTPException as he:
        return {"hasKey": False, "keyMasked": "", "error": he.detail}

@app.get("/api/integracoes/evolution/test")
async def integracoes_evolution_test(request: Request, evolution_api_id: Optional[int] = None):
    try:
        with get_conn_for_request(request) as conn:
            inst = _get_evolution_instance(conn, evolution_api_id)
            base = _get_evolution_base_url(conn)
        key = str(inst.get("token") or "").strip() or str(os.getenv("AUTHENTICATION_API_KEY", "") or "").strip()
        req = urllib.request.Request(
            url=base,
            headers={"apikey": key, "Accept": "application/json", "Accept-Encoding": "identity", "User-Agent": "CAPTAR/1.0"}
        )
        ctx = ssl.create_default_context()
        with urlopen(req, context=ctx, timeout=10) as resp:
            code = resp.getcode()
            raw = resp.read()
            enc = resp.headers.get("Content-Encoding", "").lower()
            if enc == "gzip" or (len(raw) > 2 and raw[0] == 0x1F and raw[1] == 0x8B):
                raw = gzip.decompress(raw)
            elif enc == "deflate" or (len(raw) > 2 and raw[0] == 0x78):
                raw = zlib.decompress(raw)
            msg = {}
            try:
                msg = json.loads(raw.decode("utf-8"))
            except Exception:
                msg = {"text": raw.decode("utf-8", errors="ignore")}
            ok = 200 <= code < 300
            return {"ok": ok, "status_code": code, "message": msg.get("message") or msg.get("status") or "", "version": msg.get("version") or ""}
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
def _list_tenants_with_dsn():
    out = []
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(f'SELECT t."Slug", t."Nome", t."Dsn", t."IdTenant" FROM "{DB_SCHEMA}"."Tenant" t WHERE t."Dsn" IS NOT NULL AND t."Dsn" <> \'\'')
            rows = cur.fetchall()
            for r in rows:
                slug = str(r[0] or '')
                nome = str(r[1] or '')
                dsn = str(r[2] or '')
                idt = int(r[3] or 0)
                if dsn:
                    out.append((slug, nome, dsn, idt))
    except Exception:
        pass
    return out

def _ensure_tenant_database(slug: str, idtenant: int) -> str:
    host = os.getenv('DB_HOST', 'postgres')
    port = os.getenv('DB_PORT', '5432')
    user = os.getenv('DB_USER', 'captar')
    pwd = os.getenv('DB_PASSWORD', 'captar')
    s = str(slug or '').lower()
    dbname = f"captar_t{str(int(idtenant or 0)).zfill(2)}_{s}"
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT 1 FROM pg_database WHERE datname = %s', (dbname,))
            ok = cur.fetchone() is not None
            if not ok:
                try:
                    cur.execute(f'CREATE DATABASE "{dbname}"')
                except Exception:
                    pass
    except Exception:
        pass
    return f"postgresql://{user}:{pwd}@{host}:{port}/{dbname}"
@app.get("/api/eleitores")
async def eleitores_list(limit: int = 500, request: Request = None):
    try:
        slug = request and request.headers.get('X-Tenant') or 'captar'
        view = request and request.headers.get('X-View-Tenant') or None
        s = str(slug or '').lower()
        if s != 'captar':
            tid = _tenant_id_from_header(request)
            with get_conn_for_request(request) as conn:
                cur = conn.cursor()
                cur.execute(f"SELECT e.* FROM \"{DB_SCHEMA}\".\"Eleitores\" e WHERE \"IdTenant\" = %s ORDER BY 1 ASC LIMIT %s", (tid, limit))
                cols = [d[0] for d in cur.description]
                rows = cur.fetchall()
                data = [dict(zip(cols, r)) for r in rows]
                tn = _tenant_name_from_header(request)
                for d in data:
                    d['TenantLayer'] = tn
                if 'TenantLayer' not in cols:
                    cols.append('TenantLayer')
                return {"rows": data, "columns": cols}
        view_s = str(view or '').lower()
        if view_s:
            if view_s == 'captar':
                with get_db_connection() as conn_c:
                    cur_c = conn_c.cursor()
                    tid = _ensure_tenant_slug('captar')
                    cur_c.execute(f"SELECT e.* FROM \"{DB_SCHEMA}\".\"Eleitores\" e WHERE \"IdTenant\" = %s ORDER BY 1 ASC LIMIT %s", (tid, limit))
                    cols_c = [d[0] for d in cur_c.description]
                    rows_c = cur_c.fetchall()
                    data = [dict(zip(cols_c, r)) for r in rows_c]
                    for d in data:
                        d['TenantLayer'] = 'CAPTAR'
                    if 'TenantLayer' not in cols_c:
                        cols_c.append('TenantLayer')
                    return {"rows": data, "columns": cols_c}
            dsn = _get_dsn_by_slug(view_s)
            if dsn:
                try:
                    idt = None
                    try:
                        with get_db_connection() as conn_meta:
                            cur_meta = conn_meta.cursor()
                            cur_meta.execute(f'SELECT "IdTenant" FROM "{DB_SCHEMA}"."Tenant" WHERE LOWER("Slug") = %s', (view_s,))
                            row_meta = cur_meta.fetchone()
                            idt = row_meta[0] if row_meta else None
                    except Exception:
                        pass
                    with get_db_connection(dsn) as conn_t:
                        cur_t = conn_t.cursor()
                        if idt:
                            cur_t.execute(f"SELECT e.* FROM \"{DB_SCHEMA}\".\"Eleitores\" e WHERE \"IdTenant\" = %s ORDER BY 1 ASC LIMIT %s", (idt, limit))
                        else:
                            cur_t.execute(f"SELECT e.* FROM \"{DB_SCHEMA}\".\"Eleitores\" e ORDER BY 1 ASC LIMIT %s", (limit,))
                        cols_t = [d[0] for d in cur_t.description]
                        rows_t = cur_t.fetchall()
                        data = [dict(zip(cols_t, r)) for r in rows_t]
                        name = view_s.upper()
                        try:
                            with get_db_connection() as conn_c2:
                                c2 = conn_c2.cursor()
                                c2.execute(f'SELECT "Nome" FROM "{DB_SCHEMA}"."Tenant" WHERE LOWER("Slug")=%s LIMIT 1', (view_s,))
                                rw = c2.fetchone()
                                if rw and rw[0]:
                                    name = str(rw[0]).upper()
                        except Exception:
                            pass
                        for d in data:
                            d['TenantLayer'] = name
                        if 'TenantLayer' not in cols_t:
                            cols_t.append('TenantLayer')
                        return {"rows": data, "columns": cols_t}
                except Exception:
                    pass
        rows, cols = _aggregate_table_all_tenants('eleitores', limit)
        return {"rows": rows, "columns": cols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ativistas")
async def ativistas_list(limit: int = 500, request: Request = None):
    try:
        slug = request and request.headers.get('X-Tenant') or 'captar'
        view = request and request.headers.get('X-View-Tenant') or None
        s = str(slug or '').lower()
        if s != 'captar':
            tid = _tenant_id_from_header(request)
            with get_conn_for_request(request) as conn:
                cur = conn.cursor()
                cur.execute(f"SELECT a.* FROM \"{DB_SCHEMA}\".\"Ativistas\" a WHERE \"IdTenant\" = %s ORDER BY 1 ASC LIMIT %s", (tid, limit))
                cols = [d[0] for d in cur.description]
                rows = cur.fetchall()
                data = [dict(zip(cols, r)) for r in rows]
                tn = _tenant_name_from_header(request)
                for d in data:
                    d['TenantLayer'] = tn
                if 'TenantLayer' not in cols:
                    cols.append('TenantLayer')
                return {"rows": data, "columns": cols}
        view_s = str(view or '').lower()
        if view_s:
            if view_s == 'captar':
                with get_db_connection() as conn_c:
                    cur_c = conn_c.cursor()
                    tid = _ensure_tenant_slug('captar')
                    cur_c.execute(f"SELECT a.* FROM \"{DB_SCHEMA}\".\"Ativistas\" a WHERE \"IdTenant\" = %s ORDER BY 1 ASC LIMIT %s", (tid, limit))
                    cols_c = [d[0] for d in cur_c.description]
                    rows_c = cur_c.fetchall()
                    data = [dict(zip(cols_c, r)) for r in rows_c]
                    for d in data:
                        d['TenantLayer'] = 'CAPTAR'
                    if 'TenantLayer' not in cols_c:
                        cols_c.append('TenantLayer')
                    return {"rows": data, "columns": cols_c}
            dsn = _get_dsn_by_slug(view_s)
            if dsn:
                try:
                    idt = None
                    try:
                        with get_db_connection() as conn_meta:
                            cur_meta = conn_meta.cursor()
                            cur_meta.execute(f'SELECT "IdTenant" FROM "{DB_SCHEMA}"."Tenant" WHERE LOWER("Slug") = %s', (view_s,))
                            row_meta = cur_meta.fetchone()
                            idt = row_meta[0] if row_meta else None
                    except Exception:
                        pass
                    with get_db_connection(dsn) as conn_t:
                        cur_t = conn_t.cursor()
                        if idt:
                            cur_t.execute(f"SELECT a.* FROM \"{DB_SCHEMA}\".\"Ativistas\" a WHERE \"IdTenant\" = %s ORDER BY 1 ASC LIMIT %s", (idt, limit))
                        else:
                            cur_t.execute(f"SELECT a.* FROM \"{DB_SCHEMA}\".\"Ativistas\" a ORDER BY 1 ASC LIMIT %s", (limit,))
                        cols_t = [d[0] for d in cur_t.description]
                        rows_t = cur_t.fetchall()
                        data = [dict(zip(cols_t, r)) for r in rows_t]
                        name = view_s.upper()
                        try:
                            with get_db_connection() as conn_c2:
                                c2 = conn_c2.cursor()
                                c2.execute(f'SELECT "Nome" FROM "{DB_SCHEMA}"."Tenant" WHERE LOWER("Slug")=%s LIMIT 1', (view_s,))
                                rw = c2.fetchone()
                                if rw and rw[0]:
                                    name = str(rw[0]).upper()
                        except Exception:
                            pass
                        for d in data:
                            d['TenantLayer'] = name
                        if 'TenantLayer' not in cols_t:
                            cols_t.append('TenantLayer')
                        return {"rows": data, "columns": cols_t}
                except Exception:
                    pass
        rows, cols = _aggregate_table_all_tenants('ativistas', limit)
        return {"rows": rows, "columns": cols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/candidatos")
async def candidatos_list(limit: int = 200, request: Request = None):
    try:
        s = (request and request.headers.get('X-Tenant') or 'captar').lower()
        view = (request and request.headers.get('X-View-Tenant') or '').lower()
        if s != 'captar':
            dsn_self = _get_dsn_by_slug(s)
            if not dsn_self:
                return {"rows": [], "columns": []}
            with get_db_connection(dsn_self) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Candidatos" (
                            "IdCandidato" SERIAL PRIMARY KEY,
                            "Nome" VARCHAR(255) NOT NULL,
                            "Numero" INT,
                            "Partido" VARCHAR(120),
                            "Cargo" VARCHAR(120),
                            "Foto" TEXT,
                            "Ativo" BOOLEAN DEFAULT TRUE,
                            "DataCadastro" TIMESTAMP DEFAULT NOW(),
                            "DataUpdate" TIMESTAMP,
                            "TipoUpdate" VARCHAR(20),
                            "UsuarioUpdate" VARCHAR(100),
                            "IdTenant" INT
                        )
                        """
                    )
                except Exception:
                    pass
                cur.execute(f'SELECT c.* FROM "{DB_SCHEMA}"."Candidatos" c ORDER BY 1 ASC LIMIT %s', (limit,))
                cols = [d[0] for d in cur.description]
                rows = cur.fetchall()
                tn = _tenant_name_from_header(request)
                data = [dict(zip(cols, r)) for r in rows]
                for d in data:
                    d['TenantLayer'] = tn
                if 'TenantLayer' not in cols:
                    cols.append('TenantLayer')
                return {"rows": data, "columns": cols}
        # CAPTAR
        if view:
            if view == 'captar':
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    try:
                        cur.execute(
                            f"""
                            CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Candidatos" (
                                "IdCandidato" SERIAL PRIMARY KEY,
                                "Nome" VARCHAR(255) NOT NULL,
                                "Numero" INT,
                                "Partido" VARCHAR(120),
                                "Cargo" VARCHAR(120),
                                "Foto" TEXT,
                                "Ativo" BOOLEAN DEFAULT TRUE,
                                "DataCadastro" TIMESTAMP DEFAULT NOW(),
                                "DataUpdate" TIMESTAMP,
                                "TipoUpdate" VARCHAR(20),
                                "UsuarioUpdate" VARCHAR(100),
                                "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                            )
                            """
                        )
                    except Exception:
                        pass
                    cur.execute(f'SELECT c.* FROM "{DB_SCHEMA}"."Candidatos" c ORDER BY 1 ASC LIMIT %s', (limit,))
                    cols = [d[0] for d in cur.description]
                    rows = cur.fetchall()
                    data = [dict(zip(cols, r)) for r in rows]
                    for d in data:
                        d['TenantLayer'] = 'CAPTAR'
                    if 'TenantLayer' not in cols:
                        cols.append('TenantLayer')
                    return {"rows": data, "columns": cols}
            dsn = _get_dsn_by_slug(view)
            if dsn:
                with get_db_connection(dsn) as conn:
                    cur = conn.cursor()
                    try:
                        cur.execute(
                            f"""
                            CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Candidatos" (
                                "IdCandidato" SERIAL PRIMARY KEY,
                                "Nome" VARCHAR(255) NOT NULL,
                                "Numero" INT,
                                "Partido" VARCHAR(120),
                                "Cargo" VARCHAR(120),
                                "Foto" TEXT,
                                "Ativo" BOOLEAN DEFAULT TRUE,
                                "DataCadastro" TIMESTAMP DEFAULT NOW(),
                                "DataUpdate" TIMESTAMP,
                                "TipoUpdate" VARCHAR(20),
                                "UsuarioUpdate" VARCHAR(100),
                                "IdTenant" INT
                            )
                            """
                        )
                    except Exception:
                        pass
                    cur.execute(f'SELECT c.* FROM "{DB_SCHEMA}"."Candidatos" c ORDER BY 1 ASC LIMIT %s', (limit,))
                    cols = [d[0] for d in cur.description]
                    rows = cur.fetchall()
                    data = [dict(zip(cols, r)) for r in rows]
                    name = view.upper()
                    for d in data:
                        d['TenantLayer'] = name
                    if 'TenantLayer' not in cols:
                        cols.append('TenantLayer')
                    return {"rows": data, "columns": cols}
        union_cols = set()
        out_rows = []
        with get_db_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Candidatos" (
                        "IdCandidato" SERIAL PRIMARY KEY,
                        "Nome" VARCHAR(255) NOT NULL,
                        "Numero" INT,
                        "Partido" VARCHAR(120),
                        "Cargo" VARCHAR(120),
                        "Foto" TEXT,
                        "Ativo" BOOLEAN DEFAULT TRUE,
                        "DataCadastro" TIMESTAMP DEFAULT NOW(),
                        "DataUpdate" TIMESTAMP,
                        "TipoUpdate" VARCHAR(20),
                        "UsuarioUpdate" VARCHAR(100),
                        "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                    )
                    """
                )
            except Exception:
                pass
            tid = _ensure_tenant_slug('captar')
            cur.execute(f'SELECT c.* FROM "{DB_SCHEMA}"."Candidatos" c WHERE "IdTenant" = %s ORDER BY 1 ASC LIMIT %s', (tid, limit))
            cols_c = [d[0] for d in cur.description]
            union_cols.update(cols_c)
            rows_c = cur.fetchall()
            for r in rows_c:
                d = dict(zip(cols_c, r))
                d['TenantLayer'] = 'CAPTAR'
                out_rows.append(d)
        for slug_row, nome_row, dsn_row, idt_row in _list_tenants_with_dsn():
            if not dsn_row:
                continue
            with get_db_connection(dsn_row) as conn:
                cur = conn.cursor()
                cur.execute(f'SELECT c.* FROM "{DB_SCHEMA}"."Candidatos" c WHERE "IdTenant" = %s ORDER BY 1 ASC LIMIT %s', (idt_row, limit))
                cols_t = [d[0] for d in cur.description]
                union_cols.update(cols_t)
                rows_t = cur.fetchall()
                for r in rows_t:
                    d = dict(zip(cols_t, r))
                    d['TenantLayer'] = (nome_row or slug_row or '').upper() or 'TENANT'
                    out_rows.append(d)
        union_cols.add('TenantLayer')
        all_cols = list(union_cols)
        for r in out_rows:
            for c in all_cols:
                if c not in r:
                    r[c] = None
        return {"rows": out_rows, "columns": all_cols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/eleicoes")
async def eleicoes_list(limit: int = 200, request: Request = None):
    try:
        s = (request and request.headers.get('X-Tenant') or 'captar').lower()
        view = (request and request.headers.get('X-View-Tenant') or '').lower()
        if s != 'captar':
            dsn_self = _get_dsn_by_slug(s)
            if not dsn_self:
                return {"rows": [], "columns": []}
            with get_db_connection(dsn_self) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Eleicoes" (
                            "IdEleicao" SERIAL PRIMARY KEY,
                            "Nome" VARCHAR(255) NOT NULL,
                            "Ano" INT,
                            "Turno" INT,
                            "Cargo" VARCHAR(120),
                            "DataInicio" TIMESTAMP,
                            "DataFim" TIMESTAMP,
                            "Ativo" BOOLEAN DEFAULT TRUE,
                            "DataCadastro" TIMESTAMP DEFAULT NOW(),
                            "DataUpdate" TIMESTAMP,
                            "TipoUpdate" VARCHAR(20),
                            "UsuarioUpdate" VARCHAR(100),
                            "IdTenant" INT
                        )
                        """
                    )
                except Exception:
                    pass
                cur.execute(f'SELECT e.* FROM "{DB_SCHEMA}"."Eleicoes" e ORDER BY 1 ASC LIMIT %s', (limit,))
                cols = [d[0] for d in cur.description]
                rows = cur.fetchall()
                tn = _tenant_name_from_header(request)
                data = [dict(zip(cols, r)) for r in rows]
                for d in data:
                    d['TenantLayer'] = tn
                if 'TenantLayer' not in cols:
                    cols.append('TenantLayer')
                return {"rows": data, "columns": cols}
        if view:
            if view == 'captar':
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    try:
                        cur.execute(
                            f"""
                            CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Eleicoes" (
                                "IdEleicao" SERIAL PRIMARY KEY,
                                "Nome" VARCHAR(255) NOT NULL,
                                "Ano" INT,
                                "Turno" INT,
                                "Cargo" VARCHAR(120),
                                "DataInicio" TIMESTAMP,
                                "DataFim" TIMESTAMP,
                                "Ativo" BOOLEAN DEFAULT TRUE,
                                "DataCadastro" TIMESTAMP DEFAULT NOW(),
                                "DataUpdate" TIMESTAMP,
                                "TipoUpdate" VARCHAR(20),
                                "UsuarioUpdate" VARCHAR(100),
                                "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                            )
                            """
                        )
                    except Exception:
                        pass
                    cur.execute(f'SELECT e.* FROM "{DB_SCHEMA}"."Eleicoes" e ORDER BY 1 ASC LIMIT %s', (limit,))
                    cols = [d[0] for d in cur.description]
                    rows = cur.fetchall()
                    data = [dict(zip(cols, r)) for r in rows]
                    for d in data:
                        d['TenantLayer'] = 'CAPTAR'
                    if 'TenantLayer' not in cols:
                        cols.append('TenantLayer')
                    return {"rows": data, "columns": cols}
            dsn = _get_dsn_by_slug(view)
            if dsn:
                with get_db_connection(dsn) as conn:
                    cur = conn.cursor()
                    try:
                        cur.execute(
                            f"""
                            CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Eleicoes" (
                                "IdEleicao" SERIAL PRIMARY KEY,
                                "Nome" VARCHAR(255) NOT NULL,
                                "Ano" INT,
                                "Turno" INT,
                                "Cargo" VARCHAR(120),
                                "DataInicio" TIMESTAMP,
                                "DataFim" TIMESTAMP,
                                "Ativo" BOOLEAN DEFAULT TRUE,
                                "DataCadastro" TIMESTAMP DEFAULT NOW(),
                                "DataUpdate" TIMESTAMP,
                                "TipoUpdate" VARCHAR(20),
                                "UsuarioUpdate" VARCHAR(100),
                                "IdTenant" INT
                            )
                            """
                        )
                    except Exception:
                        pass
                    cur.execute(f'SELECT e.* FROM "{DB_SCHEMA}"."Eleicoes" e ORDER BY 1 ASC LIMIT %s', (limit,))
                    cols = [d[0] for d in cur.description]
                    rows = cur.fetchall()
                    data = [dict(zip(cols, r)) for r in rows]
                    name = view.upper()
                    for d in data:
                        d['TenantLayer'] = name
                    if 'TenantLayer' not in cols:
                        cols.append('TenantLayer')
                    return {"rows": data, "columns": cols}
        union_cols = set()
        out_rows = []
        with get_db_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Eleicoes" (
                        "IdEleicao" SERIAL PRIMARY KEY,
                        "Nome" VARCHAR(255) NOT NULL,
                        "Ano" INT,
                        "Turno" INT,
                        "Cargo" VARCHAR(120),
                        "DataInicio" TIMESTAMP,
                        "DataFim" TIMESTAMP,
                        "Ativo" BOOLEAN DEFAULT TRUE,
                        "DataCadastro" TIMESTAMP DEFAULT NOW(),
                        "DataUpdate" TIMESTAMP,
                        "TipoUpdate" VARCHAR(20),
                        "UsuarioUpdate" VARCHAR(100),
                        "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                    )
                    """
                )
            except Exception:
                pass
            tid = _ensure_tenant_slug('captar')
            cur.execute(f'SELECT e.* FROM "{DB_SCHEMA}"."Eleicoes" e WHERE "IdTenant" = %s ORDER BY 1 ASC LIMIT %s', (tid, limit))
            cols_c = [d[0] for d in cur.description]
            union_cols.update(cols_c)
            rows_c = cur.fetchall()
            for r in rows_c:
                d = dict(zip(cols_c, r))
                d['TenantLayer'] = 'CAPTAR'
                out_rows.append(d)
        for slug_row, nome_row, dsn_row, idt_row in _list_tenants_with_dsn():
            if not dsn_row:
                continue
            with get_db_connection(dsn_row) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Eleicoes" (
                            "IdEleicao" SERIAL PRIMARY KEY,
                            "Nome" VARCHAR(255) NOT NULL,
                            "Ano" INT,
                            "Turno" INT,
                            "Cargo" VARCHAR(120),
                            "DataInicio" TIMESTAMP,
                            "DataFim" TIMESTAMP,
                            "Ativo" BOOLEAN DEFAULT TRUE,
                            "DataCadastro" TIMESTAMP DEFAULT NOW(),
                            "DataUpdate" TIMESTAMP,
                            "TipoUpdate" VARCHAR(20),
                            "UsuarioUpdate" VARCHAR(100),
                            "IdTenant" INT
                        )
                        """
                    )
                except Exception:
                    pass
                cur.execute(f'SELECT e.* FROM "{DB_SCHEMA}"."Eleicoes" e WHERE "IdTenant" = %s ORDER BY 1 ASC LIMIT %s', (idt_row, limit))
                cols_t = [d[0] for d in cur.description]
                union_cols.update(cols_t)
                rows_t = cur.fetchall()
                for r in rows_t:
                    d = dict(zip(cols_t, r))
                    d['TenantLayer'] = (nome_row or slug_row or '').upper() or 'TENANT'
                    out_rows.append(d)
        union_cols.add('TenantLayer')
        all_cols = list(union_cols)
        for r in out_rows:
            for c in all_cols:
                if c not in r:
                    r[c] = None
        return {"rows": out_rows, "columns": all_cols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metas")
async def metas_list(limit: int = 200, request: Request = None):
    try:
        s = (request and request.headers.get('X-Tenant') or 'captar').lower()
        view = (request and request.headers.get('X-View-Tenant') or '').lower()
        if s != 'captar':
            dsn_self = _get_dsn_by_slug(s)
            if not dsn_self:
                return {"rows": [], "columns": []}
            with get_db_connection(dsn_self) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Metas" (
                            "IdMeta" SERIAL PRIMARY KEY,
                            "IdCandidato" INT,
                            "Numero" INT,
                            "Partido" VARCHAR(120),
                            "Cargo" VARCHAR(120),
                            "IdEleicao" INT,
                            "DataInicio" TIMESTAMP,
                            "DataFim" TIMESTAMP,
                            "MetaVotos" INT,
                            "MetaDisparos" INT,
                            "MetaAprovacao" INT,
                            "MetaRejeicao" INT,
                            "Ativo" BOOLEAN DEFAULT TRUE,
                            "DataCadastro" TIMESTAMP DEFAULT NOW(),
                            "DataUpdate" TIMESTAMP,
                            "TipoUpdate" VARCHAR(20),
                            "UsuarioUpdate" VARCHAR(100),
                            "IdTenant" INT
                        )
                        """
                    )
                except Exception:
                    pass
                cur.execute(f'SELECT m.* FROM "{DB_SCHEMA}"."Metas" m ORDER BY 1 ASC LIMIT %s', (limit,))
                cols = [d[0] for d in cur.description]
                rows = cur.fetchall()
                tn = _tenant_name_from_header(request)
                data = [dict(zip(cols, r)) for r in rows]
                for d in data:
                    d['TenantLayer'] = tn
                if 'TenantLayer' not in cols:
                    cols.append('TenantLayer')
                return {"rows": data, "columns": cols}
        if view:
            if view == 'captar':
                with get_db_connection() as conn:
                    cur = conn.cursor()
                    try:
                        cur.execute(
                            f"""
                            CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Metas" (
                                "IdMeta" SERIAL PRIMARY KEY,
                                "IdCandidato" INT,
                                "Numero" INT,
                                "Partido" VARCHAR(120),
                                "Cargo" VARCHAR(120),
                                "IdEleicao" INT,
                                "DataInicio" TIMESTAMP,
                                "DataFim" TIMESTAMP,
                                "MetaVotos" INT,
                                "MetaDisparos" INT,
                                "MetaAprovacao" INT,
                                "MetaRejeicao" INT,
                                "Ativo" BOOLEAN DEFAULT TRUE,
                                "DataCadastro" TIMESTAMP DEFAULT NOW(),
                                "DataUpdate" TIMESTAMP,
                                "TipoUpdate" VARCHAR(20),
                                "UsuarioUpdate" VARCHAR(100),
                                "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                            )
                            """
                        )
                    except Exception:
                        pass
                    cur.execute(f'SELECT m.* FROM "{DB_SCHEMA}"."Metas" m ORDER BY 1 ASC LIMIT %s', (limit,))
                    cols = [d[0] for d in cur.description]
                    rows = cur.fetchall()
                    data = [dict(zip(cols, r)) for r in rows]
                    for d in data:
                        d['TenantLayer'] = 'CAPTAR'
                    if 'TenantLayer' not in cols:
                        cols.append('TenantLayer')
                    return {"rows": data, "columns": cols}
            dsn = _get_dsn_by_slug(view)
            if dsn:
                with get_db_connection(dsn) as conn:
                    cur = conn.cursor()
                    try:
                        cur.execute(
                            f"""
                            CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Metas" (
                                "IdMeta" SERIAL PRIMARY KEY,
                                "IdCandidato" INT,
                                "Numero" INT,
                                "Partido" VARCHAR(120),
                                "Cargo" VARCHAR(120),
                                "IdEleicao" INT,
                                "DataInicio" TIMESTAMP,
                                "DataFim" TIMESTAMP,
                                "MetaVotos" INT,
                                "MetaDisparos" INT,
                                "MetaAprovacao" INT,
                                "MetaRejeicao" INT,
                                "Ativo" BOOLEAN DEFAULT TRUE,
                                "DataCadastro" TIMESTAMP DEFAULT NOW(),
                                "DataUpdate" TIMESTAMP,
                                "TipoUpdate" VARCHAR(20),
                                "UsuarioUpdate" VARCHAR(100),
                                "IdTenant" INT
                            )
                            """
                        )
                    except Exception:
                        pass
                    cur.execute(f'SELECT m.* FROM "{DB_SCHEMA}"."Metas" m ORDER BY 1 ASC LIMIT %s', (limit,))
                    cols = [d[0] for d in cur.description]
                    rows = cur.fetchall()
                    data = [dict(zip(cols, r)) for r in rows]
                    name = view.upper()
                    for d in data:
                        d['TenantLayer'] = name
                    if 'TenantLayer' not in cols:
                        cols.append('TenantLayer')
                    return {"rows": data, "columns": cols}
        union_cols = set()
        out_rows = []
        with get_db_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Metas" (
                        "IdMeta" SERIAL PRIMARY KEY,
                        "IdCandidato" INT,
                        "Numero" INT,
                        "Partido" VARCHAR(120),
                        "Cargo" VARCHAR(120),
                        "IdEleicao" INT,
                        "DataInicio" TIMESTAMP,
                        "DataFim" TIMESTAMP,
                        "MetaVotos" INT,
                        "MetaDisparos" INT,
                        "MetaAprovacao" INT,
                        "MetaRejeicao" INT,
                        "Ativo" BOOLEAN DEFAULT TRUE,
                        "DataCadastro" TIMESTAMP DEFAULT NOW(),
                        "DataUpdate" TIMESTAMP,
                        "TipoUpdate" VARCHAR(20),
                        "UsuarioUpdate" VARCHAR(100),
                        "IdTenant" INT REFERENCES "{DB_SCHEMA}"."Tenant"("IdTenant")
                    )
                    """
                )
            except Exception:
                pass
            tid = _ensure_tenant_slug('captar')
            cur.execute(f'SELECT m.* FROM "{DB_SCHEMA}"."Metas" m WHERE "IdTenant" = %s ORDER BY 1 ASC LIMIT %s', (tid, limit))
            cols_c = [d[0] for d in cur.description]
            union_cols.update(cols_c)
            rows_c = cur.fetchall()
            for r in rows_c:
                d = dict(zip(cols_c, r))
                d['TenantLayer'] = 'CAPTAR'
                out_rows.append(d)
        for slug_row, nome_row, dsn_row, idt_row in _list_tenants_with_dsn():
            if not dsn_row:
                continue
            with get_db_connection(dsn_row) as conn:
                cur = conn.cursor()
                try:
                    cur.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Metas" (
                            "IdMeta" SERIAL PRIMARY KEY,
                            "IdCandidato" INT,
                            "Numero" INT,
                            "Partido" VARCHAR(120),
                            "Cargo" VARCHAR(120),
                            "IdEleicao" INT,
                            "DataInicio" TIMESTAMP,
                            "DataFim" TIMESTAMP,
                            "MetaVotos" INT,
                            "MetaDisparos" INT,
                            "MetaAprovacao" INT,
                            "MetaRejeicao" INT,
                            "Ativo" BOOLEAN DEFAULT TRUE,
                            "DataCadastro" TIMESTAMP DEFAULT NOW(),
                            "DataUpdate" TIMESTAMP,
                            "TipoUpdate" VARCHAR(20),
                            "UsuarioUpdate" VARCHAR(100),
                            "IdTenant" INT
                        )
                        """
                    )
                except Exception:
                    pass
                cur.execute(f'SELECT m.* FROM "{DB_SCHEMA}"."Metas" m WHERE "IdTenant" = %s ORDER BY 1 ASC LIMIT %s', (idt_row, limit))
                cols_t = [d[0] for d in cur.description]
                union_cols.update(cols_t)
                rows_t = cur.fetchall()
                for r in rows_t:
                    d = dict(zip(cols_t, r))
                    d['TenantLayer'] = (nome_row or slug_row or '').upper() or 'TENANT'
                    out_rows.append(d)
        union_cols.add('TenantLayer')
        all_cols = list(union_cols)
        for r in out_rows:
            for c in all_cols:
                if c not in r:
                    r[c] = None
        return {"rows": out_rows, "columns": all_cols}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/metas")
async def metas_create(payload: dict, request: Request = None):
    try:
        cols_meta = get_table_columns("Metas")
        allowed = {c["name"] for c in cols_meta if c["name"] != "IdMeta"}
        data = {k: v for k, v in payload.items() if k in allowed}
        data = _apply_create_defaults(cols_meta, data)
        try:
            tid = _tenant_id_from_header(request)
            nm = _tenant_name_from_header(request)
            data["IdTenant"] = tid
            data["TenantLayer"] = nm
        except Exception:
            pass
        keys = list(data.keys())
        if not keys:
            raise HTTPException(status_code=400, detail="Sem campos válidos")
        # ensure tenancy fields
        try:
            tid = _tenant_id_from_header(request)
            nm = _tenant_name_from_header(request)
            if 'IdTenant' not in keys:
                keys.append('IdTenant')
                data['IdTenant'] = tid
            if 'TenantLayer' not in keys:
                keys.append('TenantLayer')
                data['TenantLayer'] = nm
        except Exception:
            pass
        values = [data[k] for k in keys]
        placeholders = ", ".join(["%s"] * len(values))
        columns_sql = ", ".join([f'"{k}"' for k in keys])
        s = (request and request.headers.get('X-Tenant') or 'captar').lower()
        view = (request and request.headers.get('X-View-Tenant') or '').lower()
        target_conn = None
        if s != 'captar':
            target_conn = get_conn_for_request(request)
        elif view:
            if view == 'captar':
                target_conn = get_db_connection()
            else:
                dsn = _get_dsn_by_slug(view)
                if dsn:
                    target_conn = get_db_connection(dsn)
        else:
            target_conn = get_db_connection()
        with target_conn as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Metas" (
                        "IdMeta" SERIAL PRIMARY KEY,
                        "IdCandidato" INT,
                        "Numero" INT,
                        "Partido" VARCHAR(120),
                        "Cargo" VARCHAR(120),
                        "IdEleicao" INT,
                        "DataInicio" TIMESTAMP,
                        "DataFim" TIMESTAMP,
                        "MetaVotos" INT,
                        "MetaDisparos" INT,
                        "MetaAprovacao" INT,
                        "MetaRejeicao" INT,
                        "Ativo" BOOLEAN DEFAULT TRUE,
                        "DataCadastro" TIMESTAMP DEFAULT NOW(),
                        "DataUpdate" TIMESTAMP,
                        "TipoUpdate" VARCHAR(20),
                        "UsuarioUpdate" VARCHAR(100),
                        "IdTenant" INT
                    )
                    """
                )
            except Exception:
                pass
            cur.execute(
                f"INSERT INTO \"{DB_SCHEMA}\".\"Metas\" ({columns_sql}) VALUES ({placeholders}) RETURNING \"IdMeta\"",
                tuple(values)
            )
            new_id = cur.fetchone()[0]
            conn.commit()
            return {"id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/metas/{id}")
async def metas_update(id: int, payload: dict, request: Request = None):
    try:
        cols_meta = get_table_columns("Metas")
        allowed = {c["name"] for c in cols_meta if c["name"] != "IdMeta"}
        data = {k: v for k, v in payload.items() if k in allowed}
        data = _apply_update_defaults(cols_meta, data)
        keys = list(data.keys())
        if not keys:
            raise HTTPException(status_code=400, detail="Sem campos válidos")
        set_parts = ", ".join([f'"{k}"=%s' for k in keys])
        values = [data[k] for k in keys]
        
        # Get tenant ID for safety
        tid = _tenant_id_from_header(request)

        s = (request and request.headers.get('X-Tenant') or 'captar').lower()
        view = (request and request.headers.get('X-View-Tenant') or '').lower()
        target_conn = None
        if s != 'captar':
            target_conn = get_conn_for_request(request)
        elif view:
            if view == 'captar':
                target_conn = get_db_connection()
            else:
                dsn = _get_dsn_by_slug(view)
                if dsn:
                    target_conn = get_db_connection(dsn)
        else:
            target_conn = get_db_connection()
        with target_conn as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Metas" (
                        "IdMeta" SERIAL PRIMARY KEY,
                        "IdCandidato" INT,
                        "Numero" INT,
                        "Partido" VARCHAR(120),
                        "Cargo" VARCHAR(120),
                        "IdEleicao" INT,
                        "DataInicio" TIMESTAMP,
                        "DataFim" TIMESTAMP,
                        "MetaVotos" INT,
                        "MetaDisparos" INT,
                        "MetaAprovacao" INT,
                        "MetaRejeicao" INT,
                        "Ativo" BOOLEAN DEFAULT TRUE,
                        "DataCadastro" TIMESTAMP DEFAULT NOW(),
                        "DataUpdate" TIMESTAMP,
                        "TipoUpdate" VARCHAR(20),
                        "UsuarioUpdate" VARCHAR(100),
                        "IdTenant" INT
                    )
                    """
                )
            except Exception:
                pass
            cur.execute(
                f"UPDATE \"{DB_SCHEMA}\".\"Metas\" SET {set_parts} WHERE \"IdMeta\" = %s AND \"IdTenant\" = %s",
                tuple(values + [id, tid])
            )
            conn.commit()
            return {"id": id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/metas/{id}")
async def metas_delete(id: int, request: Request = None):
    try:
        tid = _tenant_id_from_header(request)
        s = (request and request.headers.get('X-Tenant') or 'captar').lower()
        view = (request and request.headers.get('X-View-Tenant') or '').lower()
        target_conn = None
        if s != 'captar':
            target_conn = get_conn_for_request(request)
        elif view:
            if view == 'captar':
                target_conn = get_db_connection()
            else:
                dsn = _get_dsn_by_slug(view)
                if dsn:
                    target_conn = get_db_connection(dsn)
        else:
            target_conn = get_db_connection()
        with target_conn as conn:
            cur = conn.cursor()
            cur.execute(f'DELETE FROM "{DB_SCHEMA}"."Metas" WHERE "IdMeta" = %s AND "IdTenant" = %s', (id, tid))
            conn.commit()
            return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/eleicoes")
async def eleicoes_create(payload: dict, request: Request = None):
    try:
        cols_meta = get_table_columns("Eleicoes")
        allowed = {c["name"] for c in cols_meta if c["name"] != "IdEleicao"}
        data = {k: v for k, v in payload.items() if k in allowed}
        data = _apply_create_defaults(cols_meta, data)
        try:
            tid = _tenant_id_from_header(request)
            nm = _tenant_name_from_header(request)
            data["IdTenant"] = tid
            data["TenantLayer"] = nm
        except Exception:
            pass
        keys = list(data.keys())
        if not keys:
            raise HTTPException(status_code=400, detail="Sem campos válidos")
        try:
            tid = _tenant_id_from_header(request)
            nm = _tenant_name_from_header(request)
            if 'IdTenant' not in keys:
                keys.append('IdTenant')
                data['IdTenant'] = tid
            if 'TenantLayer' not in keys:
                keys.append('TenantLayer')
                data['TenantLayer'] = nm
        except Exception:
            pass
        values = [data[k] for k in keys]
        placeholders = ", ".join(["%s"] * len(values))
        columns_sql = ", ".join([f'"{k}"' for k in keys])
        s = (request and request.headers.get('X-Tenant') or 'captar').lower()
        view = (request and request.headers.get('X-View-Tenant') or '').lower()
        target_conn = None
        if s != 'captar':
            target_conn = get_conn_for_request(request)
        elif view:
            if view == 'captar':
                target_conn = get_db_connection()
            else:
                dsn = _get_dsn_by_slug(view)
                if dsn:
                    target_conn = get_db_connection(dsn)
        else:
            target_conn = get_db_connection()
        with target_conn as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Eleicoes" (
                        "IdEleicao" SERIAL PRIMARY KEY,
                        "Nome" VARCHAR(255) NOT NULL,
                        "Ano" INT,
                        "Turno" INT,
                        "Cargo" VARCHAR(120),
                        "DataInicio" TIMESTAMP,
                        "DataFim" TIMESTAMP,
                        "Ativo" BOOLEAN DEFAULT TRUE,
                        "DataCadastro" TIMESTAMP DEFAULT NOW(),
                        "DataUpdate" TIMESTAMP,
                        "TipoUpdate" VARCHAR(20),
                        "UsuarioUpdate" VARCHAR(100),
                        "IdTenant" INT
                    )
                    """
                )
            except Exception:
                pass
            cur.execute(
                f"INSERT INTO \"{DB_SCHEMA}\".\"Eleicoes\" ({columns_sql}) VALUES ({placeholders}) RETURNING \"IdEleicao\"",
                tuple(values)
            )
            new_id = cur.fetchone()[0]
            conn.commit()
            return {"id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/eleicoes/{id}")
async def eleicoes_update(id: int, payload: dict, request: Request = None):
    try:
        cols_meta = get_table_columns("Eleicoes")
        allowed = {c["name"] for c in cols_meta if c["name"] != "IdEleicao"}
        data = {k: v for k, v in payload.items() if k in allowed}
        data = _apply_update_defaults(cols_meta, data)
        keys = list(data.keys())
        if not keys:
            raise HTTPException(status_code=400, detail="Sem campos válidos")
        set_parts = ", ".join([f'"{k}"=%s' for k in keys])
        values = [data[k] for k in keys]
        
        # Get tenant ID for safety
        tid = _tenant_id_from_header(request)

        s = (request and request.headers.get('X-Tenant') or 'captar').lower()
        view = (request and request.headers.get('X-View-Tenant') or '').lower()
        target_conn = None
        if s != 'captar':
            target_conn = get_conn_for_request(request)
        elif view:
            if view == 'captar':
                target_conn = get_db_connection()
            else:
                dsn = _get_dsn_by_slug(view)
                if dsn:
                    target_conn = get_db_connection(dsn)
        else:
            target_conn = get_db_connection()
        with target_conn as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Eleicoes" (
                        "IdEleicao" SERIAL PRIMARY KEY,
                        "Nome" VARCHAR(255) NOT NULL,
                        "Ano" INT,
                        "Turno" INT,
                        "Cargo" VARCHAR(120),
                        "DataInicio" TIMESTAMP,
                        "DataFim" TIMESTAMP,
                        "Ativo" BOOLEAN DEFAULT TRUE,
                        "DataCadastro" TIMESTAMP DEFAULT NOW(),
                        "DataUpdate" TIMESTAMP,
                        "TipoUpdate" VARCHAR(20),
                        "UsuarioUpdate" VARCHAR(100),
                        "IdTenant" INT
                    )
                    """
                )
            except Exception:
                pass
            cur.execute(
                f"UPDATE \"{DB_SCHEMA}\".\"Eleicoes\" SET {set_parts} WHERE \"IdEleicao\" = %s AND \"IdTenant\" = %s",
                tuple(values + [id, tid])
            )
            conn.commit()
            return {"id": id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/eleicoes/{id}")
async def eleicoes_delete(id: int, request: Request = None):
    try:
        tid = _tenant_id_from_header(request)
        s = (request and request.headers.get('X-Tenant') or 'captar').lower()
        view = (request and request.headers.get('X-View-Tenant') or '').lower()
        target_conn = None
        if s != 'captar':
            target_conn = get_conn_for_request(request)
        elif view:
            if view == 'captar':
                target_conn = get_db_connection()
            else:
                dsn = _get_dsn_by_slug(view)
                if dsn:
                    target_conn = get_db_connection(dsn)
        else:
            target_conn = get_db_connection()
        with target_conn as conn:
            cur = conn.cursor()
            cur.execute(f'DELETE FROM "{DB_SCHEMA}"."Eleicoes" WHERE "IdEleicao" = %s AND "IdTenant" = %s', (id, tid))
            conn.commit()
            return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/candidatos")
async def candidatos_create(payload: dict, request: Request = None):
    try:
        cols_meta = get_table_columns("Candidatos")
        allowed = {c["name"] for c in cols_meta if c["name"] != "IdCandidato"}
        data = {k: v for k, v in payload.items() if k in allowed}
        data = _apply_create_defaults(cols_meta, data)
        try:
            tid = _tenant_id_from_header(request)
            nm = _tenant_name_from_header(request)
            data["IdTenant"] = tid
            data["TenantLayer"] = nm
        except Exception:
            pass
        foto = str(data.get('Foto') or '')
        if foto:
            ok_type = foto.startswith('data:image/')
            approx = int(len(foto) * 3 / 4)
            if (not ok_type) or approx > (2 * 1024 * 1024):
                raise HTTPException(status_code=400, detail='Foto inválida (tipo ou tamanho)')
        keys = list(data.keys())
        if not keys:
            raise HTTPException(status_code=400, detail="Sem campos válidos")
        try:
            tid = _tenant_id_from_header(request)
            nm = _tenant_name_from_header(request)
            if 'IdTenant' not in keys:
                keys.append('IdTenant')
                data['IdTenant'] = tid
            if 'TenantLayer' not in keys:
                keys.append('TenantLayer')
                data['TenantLayer'] = nm
        except Exception:
            pass
        values = [data[k] for k in keys]
        placeholders = ", ".join(["%s"] * len(values))
        columns_sql = ", ".join([f'"{k}"' for k in keys])
        s = (request and request.headers.get('X-Tenant') or 'captar').lower()
        view = (request and request.headers.get('X-View-Tenant') or '').lower()
        target_conn = None
        if s != 'captar':
            target_conn = get_conn_for_request(request)
        elif view:
            if view == 'captar':
                target_conn = get_db_connection()
            else:
                dsn = _get_dsn_by_slug(view)
                if dsn:
                    target_conn = get_db_connection(dsn)
        else:
            target_conn = get_db_connection()
        with target_conn as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Candidatos" (
                        "IdCandidato" SERIAL PRIMARY KEY,
                        "Nome" VARCHAR(255) NOT NULL,
                        "Numero" INT,
                        "Partido" VARCHAR(120),
                        "Cargo" VARCHAR(120),
                        "Foto" TEXT,
                        "Ativo" BOOLEAN DEFAULT TRUE,
                        "DataCadastro" TIMESTAMP DEFAULT NOW(),
                        "DataUpdate" TIMESTAMP,
                        "TipoUpdate" VARCHAR(20),
                        "UsuarioUpdate" VARCHAR(100),
                        "IdTenant" INT
                    )
                    """
                )
            except Exception:
                pass
            cur.execute(
                f"INSERT INTO \"{DB_SCHEMA}\".\"Candidatos\" ({columns_sql}) VALUES ({placeholders}) RETURNING \"IdCandidato\"",
                tuple(values)
            )
            new_id = cur.fetchone()[0]
            conn.commit()
            return {"id": new_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/candidatos/{id}")
async def candidatos_update(id: int, payload: dict, request: Request = None):
    try:
        cols_meta = get_table_columns("Candidatos")
        allowed = {c["name"] for c in cols_meta if c["name"] != "IdCandidato"}
        data = {k: v for k, v in payload.items() if k in allowed}
        data = _apply_update_defaults(cols_meta, data)
        foto = str(data.get('Foto') or '')
        if foto:
            ok_type = foto.startswith('data:image/')
            approx = int(len(foto) * 3 / 4)
            if (not ok_type) or approx > (2 * 1024 * 1024):
                raise HTTPException(status_code=400, detail='Foto inválida (tipo ou tamanho)')
        keys = list(data.keys())
        if not keys:
            raise HTTPException(status_code=400, detail="Sem campos válidos")
        set_parts = ", ".join([f'"{k}"=%s' for k in keys])
        values = [data[k] for k in keys]
        
        # Get tenant ID for safety
        tid = _tenant_id_from_header(request)

        s = (request and request.headers.get('X-Tenant') or 'captar').lower()
        view = (request and request.headers.get('X-View-Tenant') or '').lower()
        target_conn = None
        if s != 'captar':
            target_conn = get_conn_for_request(request)
        elif view:
            if view == 'captar':
                target_conn = get_db_connection()
            else:
                dsn = _get_dsn_by_slug(view)
                if dsn:
                    target_conn = get_db_connection(dsn)
        else:
            target_conn = get_db_connection()
        with target_conn as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{DB_SCHEMA}"."Candidatos" (
                        "IdCandidato" SERIAL PRIMARY KEY,
                        "Nome" VARCHAR(255) NOT NULL,
                        "Numero" INT,
                        "Partido" VARCHAR(120),
                        "Cargo" VARCHAR(120),
                        "Foto" TEXT,
                        "Ativo" BOOLEAN DEFAULT TRUE,
                        "DataCadastro" TIMESTAMP DEFAULT NOW(),
                        "DataUpdate" TIMESTAMP,
                        "TipoUpdate" VARCHAR(20),
                        "UsuarioUpdate" VARCHAR(100),
                        "IdTenant" INT
                    )
                    """
                )
            except Exception:
                pass
            cur.execute(
                f"UPDATE \"{DB_SCHEMA}\".\"Candidatos\" SET {set_parts} WHERE \"IdCandidato\" = %s AND \"IdTenant\" = %s",
                tuple(values + [id, tid])
            )
            conn.commit()
            return {"id": id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/candidatos/{id}")
async def candidatos_delete(id: int, request: Request = None):
    try:
        tid = _tenant_id_from_header(request)
        s = (request and request.headers.get('X-Tenant') or 'captar').lower()
        view = (request and request.headers.get('X-View-Tenant') or '').lower()
        target_conn = None
        if s != 'captar':
            target_conn = get_conn_for_request(request)
        elif view:
            if view == 'captar':
                target_conn = get_db_connection()
            else:
                dsn = _get_dsn_by_slug(view)
                if dsn:
                    target_conn = get_db_connection(dsn)
        else:
            target_conn = get_db_connection()
        with target_conn as conn:
            cur = conn.cursor()
            cur.execute(f'DELETE FROM "{DB_SCHEMA}"."Candidatos" WHERE "IdCandidato" = %s AND "IdTenant" = %s', (id, tid))
            conn.commit()
            return {"deleted": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
