from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime, date, timezone, timedelta
from typing import Any, List, Optional, Dict, Tuple, Union, Callable

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

import os
import json
import time
import re
import ssl
import gzip
import zlib
import base64
import hashlib
import asyncio
import traceback
import mimetypes
import urllib.request
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, urlunparse

import aiohttp

try:
    _MANAUS_TZ = ZoneInfo("America/Manaus") if ZoneInfo else timezone(timedelta(hours=-4))
except Exception:
    _MANAUS_TZ = timezone(timedelta(hours=-4))

def _sanitize_media_base_url(raw: Any) -> str:
    try:
        s = str(raw or "").strip().rstrip("/")
        if not s:
            return ""
        try:
            p = urlparse(s)
            if p.port in (5173, 5174, 4173, 3000):
                return ""
        except Exception:
            pass
        return s
    except Exception:
        return ""

def _request_public_base_url(request: Request) -> str:
    try:
        xf_proto = str(request.headers.get("x-forwarded-proto") or "").strip()
        xf_host = str(request.headers.get("x-forwarded-host") or "").strip()
        xf_prefix = str(request.headers.get("x-forwarded-prefix") or "").strip()
        if xf_proto and xf_host:
            base = f"{xf_proto}://{xf_host}"
            if xf_prefix:
                if not xf_prefix.startswith("/"):
                    xf_prefix = f"/{xf_prefix}"
                base = f"{base}{xf_prefix}"
            return _sanitize_media_base_url(base)
    except Exception:
        pass
    try:
        origin = str(request.headers.get("origin") or "").strip()
        if origin.startswith("http://") or origin.startswith("https://"):
            return _sanitize_media_base_url(origin)
    except Exception:
        pass
    try:
        referer = str(request.headers.get("referer") or "").strip()
        if referer.startswith("http://") or referer.startswith("https://"):
            p = urlparse(referer)
            if p.scheme and p.netloc:
                return _sanitize_media_base_url(f"{p.scheme}://{p.netloc}")
    except Exception:
        pass
    return ""

def _is_localish_base_url(u: str) -> bool:
    try:
        s = str(u or "").strip()
        if not s:
            return True
        p = urlparse(s)
        host = str(p.hostname or "").strip().lower()
        if not host:
            return True
        if host in ("localhost", "127.0.0.1", "0.0.0.0", "fastapi", "nginx", "host.docker.internal"):
            return True
        if host.endswith(".local"):
            return True
        return False
    except Exception:
        return True

def _is_loopback_url(u: str) -> bool:
    try:
        s = str(u or "").strip()
        if not s:
            return True
        p = urlparse(s)
        host = str(p.hostname or "").strip().lower()
        return host in ("localhost", "127.0.0.1", "0.0.0.0")
    except Exception:
        return True


def register_evolution_routes(
    app: FastAPI,
    get_db_connection: Callable[..., Any],
    get_conn_for_request: Callable[[Request], Any],
    db_schema: str,
    get_redis_client: Callable[[], Any],
    get_dsn_by_slug: Callable[[str], Optional[str]],
    mask_key: Callable[[str], str],
):
    DB_SCHEMA = db_schema
    _get_dsn_by_slug = get_dsn_by_slug
    _EVOLUTION_INSTANCE_COLS: Tuple[List[str], float] = ([], 0.0)

    def _tenant_slug_from_header(request: Request) -> str:
        try:
            raw = str(request.headers.get("X-Tenant") or "captar")
            raw = raw.strip() or "captar"
            slug = (raw.split("/", 1)[0] or "captar").strip().lower() or "captar"
            return slug
        except Exception:
            return "captar"

    def _tenant_id_from_header(request: Request) -> int:
        slug = _tenant_slug_from_header(request)
        try:
            rc = get_redis_client()
        except Exception:
            rc = None
        try:
            cached = rc.get(f"tenant:id:{slug}") if rc else None
            if cached:
                return int(cached)
        except Exception:
            pass
        try:
            with get_db_connection() as conn_t:
                cur_t = conn_t.cursor()
                cur_t.execute(
                    f'SELECT "IdTenant" FROM "{DB_SCHEMA}"."Tenant" WHERE LOWER("Slug") = LOWER(%s) LIMIT 1',
                    (slug,),
                )
                row = cur_t.fetchone()
                tid = int(row[0]) if row and row[0] is not None else 1
            try:
                if rc:
                    rc.setex(f"tenant:id:{slug}", 300, str(tid))
            except Exception:
                pass
            return tid
        except Exception:
            return 1

    def _evolution_instance_columns(conn) -> List[str]:
        nonlocal _EVOLUTION_INSTANCE_COLS
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
        _EVOLUTION_INSTANCE_COLS = (cols, now + 300.0)
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
            db_host = str(os.getenv("DB_HOST", "") or "").strip().lower()
            ev_port = str(os.getenv("EV_API_HOST_PORT", "") or "").strip()
            if db_host in ("localhost", "127.0.0.1", "0.0.0.0") and ev_port.isdigit():
                return f"http://localhost:{ev_port}"
        except Exception:
            pass
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
            try:
                conn.rollback()
            except Exception:
                pass
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
                    try:
                        conn.rollback()
                    except Exception:
                        pass
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
        try:
            db_host = str(os.getenv("DB_HOST", "") or "").strip().lower()
            ev_port = str(os.getenv("EV_API_HOST_PORT", "") or "").strip()
            if db_host in ("localhost", "127.0.0.1", "0.0.0.0") and ev_port.isdigit():
                s = f"http://localhost:{ev_port}"
        except Exception:
            pass
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
        if path.lower().endswith("/api"):
            add(urlunparse((scheme, netloc, path[:-4], "", "", "")).rstrip("/"))
        else:
            add(urlunparse((scheme, netloc, f"{path}/api" if path else "/api", "", "", "")).rstrip("/"))
        if path.lower().endswith("/api/v1"):
            add(urlunparse((scheme, netloc, path[:-7], "", "", "")).rstrip("/"))
        else:
            add(urlunparse((scheme, netloc, f"{path}/api/v1" if path else "/api/v1", "", "", "")).rstrip("/"))
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
            if "too many clients" in str(e).lower():
                raise HTTPException(status_code=503, detail="Banco de dados sem conexões disponíveis (too many clients).")
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

    def _extract_evolution_message_id(payload: Any) -> str:
        try:
            if payload is None:
                return ''
            if isinstance(payload, str):
                return payload.strip()
            if isinstance(payload, dict):
                def _pick_str(v: Any) -> str:
                    if isinstance(v, str) and v.strip():
                        return v.strip()
                    return ''

                def _get_path(obj: Any, path: Tuple[str, ...]) -> str:
                    cur: Any = obj
                    for k in path:
                        if not isinstance(cur, dict):
                            return ''
                        cur = cur.get(k)
                    return _pick_str(cur)

                for path in (
                    ('key', 'id'),
                    ('data', 'key', 'id'),
                    ('payload', 'key', 'id'),
                    ('event', 'key', 'id'),
                    ('data', 'message', 'key', 'id'),
                    ('message', 'key', 'id'),
                    ('data', 'keyId'),
                    ('data', 'key_id'),
                    ('keyId',),
                    ('key_id',),
                    ('data', 'messageId'),
                    ('data', 'message_id'),
                    ('messageId',),
                    ('message_id',),
                ):
                    v = _get_path(payload, path)
                    if v:
                        return v

                data = payload.get('data') or payload.get('payload')
                if isinstance(data, dict):
                    v = _get_path(data, ('key', 'id'))
                    if v:
                        return v
                    for k in ('keyId', 'key_id', 'messageId', 'message_id'):
                        v2 = _pick_str(data.get(k))
                        if v2:
                            return v2

                v = _pick_str(payload.get('id'))
                if v:
                    return v
                if isinstance(data, dict):
                    v = _pick_str(data.get('id'))
                    if v:
                        return v
            return ''
        except Exception:
            return ''

    def _extract_evolution_key_id(payload: Any) -> str:
        try:
            if payload is None:
                return ''
            if isinstance(payload, str):
                return ''
            if isinstance(payload, dict):
                for k in ('keyId', 'key_id'):
                    v = payload.get(k)
                    if isinstance(v, str) and v.strip():
                        return v.strip()
                key = payload.get('key')
                if isinstance(key, dict):
                    v = key.get('id')
                    if isinstance(v, str) and v.strip():
                        return v.strip()
                data = payload.get('data') or payload.get('payload')
                if isinstance(data, dict):
                    for k in ('keyId', 'key_id'):
                        v = data.get(k)
                        if isinstance(v, str) and v.strip():
                            return v.strip()
                    key2 = data.get('key')
                    if isinstance(key2, dict):
                        v = key2.get('id')
                        if isinstance(v, str) and v.strip():
                            return v.strip()
            return ''
        except Exception:
            return ''

    def _extract_evolution_status(payload: Any) -> Tuple[Optional[str], Optional[int]]:
        try:
            if payload is None:
                return None, None
            if isinstance(payload, dict):
                data = payload.get('data') if isinstance(payload.get('data'), dict) else None
                candidates = []
                if data:
                    candidates.extend([data.get('status'), data.get('ack')])
                    upd = data.get('update')
                    if isinstance(upd, dict):
                        candidates.extend([upd.get('status'), upd.get('ack')])
                    receipt = data.get('receipt') or data.get('receiptUpdate')
                    if isinstance(receipt, dict):
                        candidates.extend([receipt.get('status'), receipt.get('ack')])
                    candidates.extend([data.get('messageStatus'), data.get('message_status')])
                    msg = data.get('message')
                    if isinstance(msg, dict):
                        candidates.extend([msg.get('status'), msg.get('ack')])
                        upd2 = msg.get('update')
                        if isinstance(upd2, dict):
                            candidates.extend([upd2.get('status'), upd2.get('ack')])
                candidates.extend([payload.get('status'), payload.get('ack')])

                for v in candidates:
                    if v is None:
                        continue
                    if isinstance(v, (int, float)):
                        ack = int(v)
                        return None, ack
                    s = str(v or '').strip()
                    if not s:
                        continue
                    if s.isdigit():
                        return None, int(s)
                    return s.upper(), None
            return None, None
        except Exception:
            return None, None

    def _extract_presence_status(payload: Any) -> Optional[str]:
        try:
            if payload is None or not isinstance(payload, dict):
                return None
            data = payload.get('data')
            if not isinstance(data, dict):
                data = payload
            for k in ('lastKnownPresence', 'presence', 'state'):
                v = data.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip().lower()
            presences = data.get('presences')
            if isinstance(presences, dict):
                for _jid, p in presences.items():
                    if isinstance(p, dict):
                        v = p.get('lastKnownPresence') or p.get('presence')
                        if isinstance(v, str) and v.strip():
                            return v.strip().lower()
            return None
        except Exception:
            return None

    def _extract_from_me(payload: Any) -> Optional[bool]:
        try:
            if payload is None:
                return None
            if isinstance(payload, dict):
                data = payload.get('data') or payload.get('event') or payload.get('payload')
                if isinstance(data, dict):
                    key = data.get('key')
                    if isinstance(key, dict) and 'fromMe' in key:
                        return bool(key.get('fromMe'))
                    if 'fromMe' in data:
                        return bool(data.get('fromMe'))
                key2 = payload.get('key')
                if isinstance(key2, dict) and 'fromMe' in key2:
                    return bool(key2.get('fromMe'))
                if 'fromMe' in payload:
                    return bool(payload.get('fromMe'))
            return None
        except Exception:
            return None

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
            normalized_phone = _digits_only(data.phone)
            if not normalized_phone:
                raise HTTPException(status_code=400, detail="Telefone inválido para envio.")
            media_type = str(data.media_type or "image").strip().lower() or "image"
            if media_type not in ("image", "document", "video", "audio"):
                media_type = "image"
            base_candidates = _evolution_base_url_candidates(base_url)
            if not base_candidates:
                raise HTTPException(status_code=500, detail="Configuração da Evolution API incompleta no servidor.")
            
            # 1.5. Resolve Media URL if local filename
            final_media_url = data.media_url
            if final_media_url:
                s_media = str(final_media_url).strip()
                if s_media.startswith("data:"):
                    try:
                        m = re.match(r"^data:([^;]+);base64,(.+)$", s_media, flags=re.IGNORECASE | re.DOTALL)
                        if m:
                            mime = str(m.group(1) or "").strip().lower()
                            b64 = str(m.group(2) or "").strip()
                            b64 = re.sub(r"\s+", "", b64)
                            if mime.startswith("image/") and b64:
                                ext = ".bin"
                                if mime in ("image/jpeg", "image/jpg"):
                                    ext = ".jpg"
                                elif mime == "image/png":
                                    ext = ".png"
                                elif mime == "image/webp":
                                    ext = ".webp"
                                elif mime == "image/gif":
                                    ext = ".gif"
                                h = hashlib.sha256(b64.encode("utf-8")).hexdigest()[:32]
                                filename = f"inline_{h}{ext}"
                                base_dir = os.path.join(os.path.dirname(__file__), "static", "campanhas", "_inline")
                                os.makedirs(base_dir, exist_ok=True)
                                file_path = os.path.join(base_dir, filename)
                                if not os.path.isfile(file_path):
                                    raw = base64.b64decode(b64 + "===")
                                    with open(file_path, "wb") as f:
                                        f.write(raw)
                                final_media_url = f"/static/campanhas/_inline/{filename}"
                                s_media = str(final_media_url).strip()
                    except Exception:
                        pass
                # If not http/https and not data: -> assume local file in static/campanhas
                if not s_media.startswith('http') and not s_media.startswith('data:'):
                    evo_is_local = False
                    evo_container = False
                    try:
                        evo_is_local = any(_is_localish_base_url(x) for x in (base_candidates or []))
                    except Exception:
                        evo_is_local = False
                    try:
                        db_host = str(os.getenv("DB_HOST", "") or "").strip().lower()
                        ev_port = str(os.getenv("EV_API_HOST_PORT", "") or "").strip()
                        if db_host in ("localhost", "127.0.0.1", "0.0.0.0") and ev_port.isdigit():
                            evo_container = True
                    except Exception:
                        evo_container = False

                    cfg_media_base_url = str(os.getenv("WHATSAPP_MEDIA_BASE_URL") or "").strip().rstrip("/")
                    req_public = _request_public_base_url(request)
                    public_base = str(os.getenv("PUBLIC_BASE_URL") or os.getenv("CAPTAR_PUBLIC_BASE_URL") or "").strip().rstrip("/")

                    media_base_url = ""
                    evo_hostnames: set[str] = set()
                    if not cfg_media_base_url:
                        try:
                            evo_hostnames = {str(urlparse(x).hostname or "").strip().lower() for x in (base_candidates or [])}
                            if "evolution_api" in evo_hostnames:
                                cfg_media_base_url = "http://fastapi:8000"
                        except Exception:
                            pass
                    if not evo_hostnames:
                        try:
                            evo_hostnames = {str(urlparse(x).hostname or "").strip().lower() for x in (base_candidates or [])}
                        except Exception:
                            evo_hostnames = set()
                    evo_docker = ("evolution_api" in evo_hostnames)
                    if cfg_media_base_url:
                        cfg_loopback = False
                        evo_non_loopback = False
                        try:
                            cfg_host = str(urlparse(cfg_media_base_url).hostname or "").strip().lower()
                            if cfg_host in ("localhost", "127.0.0.1", "0.0.0.0"):
                                cfg_loopback = True
                        except Exception:
                            cfg_loopback = False
                        if cfg_loopback:
                            try:
                                for u in (base_candidates or []):
                                    h = str(urlparse(u).hostname or "").strip().lower()
                                    if h and h not in ("localhost", "127.0.0.1", "0.0.0.0"):
                                        evo_non_loopback = True
                                        break
                            except Exception:
                                evo_non_loopback = False
                        if cfg_loopback and evo_non_loopback:
                            cfg_media_base_url = ""
                        if cfg_loopback and evo_container:
                            cfg_media_base_url = ""

                        if cfg_media_base_url:
                            if evo_is_local:
                                media_base_url = cfg_media_base_url
                            elif evo_docker and not _is_loopback_url(cfg_media_base_url):
                                media_base_url = cfg_media_base_url
                                try:
                                    cfg_p2 = urlparse(cfg_media_base_url)
                                    cfg_h2 = str(cfg_p2.hostname or "").strip().lower()
                                    if cfg_h2 == "fastapi":
                                        hp = str(os.getenv("FASTAPI_HOST_PORT", "") or "").strip()
                                        if hp.isdigit():
                                            media_base_url = f"{str(cfg_p2.scheme or 'http').lower()}://host.docker.internal:{hp}"
                                except Exception:
                                    media_base_url = cfg_media_base_url
                            elif not _is_localish_base_url(cfg_media_base_url):
                                media_base_url = cfg_media_base_url

                    if not media_base_url and evo_container:
                        fastapi_host_port = os.getenv("FASTAPI_HOST_PORT", "8000")
                        media_base_url = f"http://host.docker.internal:{fastapi_host_port}"
                    if not media_base_url and not evo_is_local and not evo_container:
                        if public_base.startswith("http://") or public_base.startswith("https://"):
                            media_base_url = public_base
                        elif req_public:
                            media_base_url = req_public

                    if not media_base_url:
                        media_base_url = req_public
                    if not media_base_url:
                        try:
                            media_base_url = _sanitize_media_base_url(request.base_url)
                        except Exception:
                            media_base_url = ""
                    if not media_base_url:
                        fastapi_host_port = os.getenv("FASTAPI_HOST_PORT", "8000")
                        media_base_url = f"http://host.docker.internal:{fastapi_host_port}"
                    media_base_url = str(media_base_url).rstrip("/")
                    if s_media.startswith('/static/') or s_media.startswith('/'):
                        final_media_url = f"{media_base_url}{s_media}"
                    elif s_media.startswith('static/'):
                        final_media_url = f"{media_base_url}/{s_media}"
                    else:
                        final_media_url = f"{media_base_url}/static/campanhas/{s_media}"
                    print(f"Resolved local media path '{s_media}' to '{final_media_url}'")

            media_mimetype = ""
            media_filename = ""
            if final_media_url:
                try:
                    u = str(final_media_url or "").strip()
                    path = ""
                    try:
                        if u.lower().startswith("http://") or u.lower().startswith("https://"):
                            path = str(urlparse(u).path or "")
                        else:
                            path = u
                    except Exception:
                        path = u
                    base = os.path.basename(path or "")
                    if base:
                        media_filename = base
                    guess_target = media_filename or path
                    mt, _enc = mimetypes.guess_type(guess_target)
                    if mt:
                        media_mimetype = str(mt)
                except Exception:
                    media_mimetype = ""
                    media_filename = ""
                if not media_mimetype:
                    if media_type == "image":
                        media_mimetype = "image/jpeg"
                    elif media_type == "video":
                        media_mimetype = "video/mp4"
                    elif media_type == "audio":
                        media_mimetype = "audio/mpeg"
                    else:
                        media_mimetype = "application/octet-stream"
                if not media_filename:
                    ext = ".bin"
                    if media_type == "image":
                        ext = ".jpg"
                    elif media_type == "video":
                        ext = ".mp4"
                    elif media_type == "audio":
                        ext = ".mp3"
                    media_filename = f"media{ext}"

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
                                    "number": normalized_phone,
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
                                    try:
                                        resp_text_json = await resp_text.json()
                                    except Exception:
                                        try:
                                            resp_text_json = {"raw": await resp_text.text()}
                                        except Exception:
                                            resp_text_json = {"raw": ""}
                                    try:
                                        message_id_text = _extract_evolution_message_id(resp_text_json) or None
                                        with get_conn_for_request(request) as conn_log:
                                            cursor_log = conn_log.cursor()
                                            tid_log = _tenant_id_from_header(request)
                                            cursor_log.execute(
                                                f"""
                                                INSERT INTO "{DB_SCHEMA}"."Disparos"
                                                ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload","MessageId","EvolutionInstance")
                                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW() AT TIME ZONE 'UTC',%s::jsonb,%s,%s)
                                                """,
                                                (
                                                    tid_log,
                                                    data.campanha_id,
                                                    'WHATSAPP',
                                                    'OUT',
                                                    _digits_only(data.phone),
                                                    (data.contato_nome or None),
                                                    msg,
                                                    None,
                                                    'ENVIADO',
                                                    json.dumps(resp_text_json, ensure_ascii=False),
                                                    message_id_text,
                                                    str(instance or '').strip() or None,
                                                ),
                                            )
                                            conn_log.commit()
                                    except Exception:
                                        pass
                        
                            url_media = f"{base_try}/message/sendMedia/{instance}"
                            print(f"Sending WhatsApp MEDIA (TOP) to URL: {url_media}")
                            payload_media = {
                                "number": normalized_phone,
                                "mediatype": media_type,
                                "mimetype": media_mimetype,
                                "fileName": media_filename,
                                "media": final_media_url,
                                "delay": 1200,
                                "linkPreview": True
                            }
                            async with session.post(url_media, json=payload_media, headers=headers, timeout=30) as resp_media:
                                if resp_media.status not in (200, 201):
                                    text = await resp_media.text()
                                    code = resp_media.status if resp_media.status < 500 else 502
                                    raise HTTPException(
                                        status_code=code,
                                        detail=f"Erro na API WhatsApp (Mídia): status={resp_media.status} url={url_media} media={final_media_url} resp={text}",
                                    )
                                resp_json = await resp_media.json()
                                try:
                                    message_id = _extract_evolution_message_id(resp_json) or None
                                    with get_conn_for_request(request) as conn_log:
                                        cursor_log = conn_log.cursor()
                                        tid_log = _tenant_id_from_header(request)
                                        cursor_log.execute(
                                            f"""
                                            INSERT INTO "{DB_SCHEMA}"."Disparos"
                                            ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload","MessageId","EvolutionInstance")
                                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW() AT TIME ZONE 'UTC',%s::jsonb,%s,%s)
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
                                                message_id,
                                                str(instance or '').strip() or None,
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
                                "number": normalized_phone,
                                "mediatype": media_type,
                                "mimetype": media_mimetype,
                                "fileName": media_filename,
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
                                    raise HTTPException(
                                        status_code=code,
                                        detail=f"Erro na API WhatsApp: status={response.status} url={url} media={final_media_url} resp={text}",
                                    )
                                resp_json = await response.json()
                                try:
                                    message_id = _extract_evolution_message_id(resp_json) or None
                                    with get_conn_for_request(request) as conn_log:
                                        cursor_log = conn_log.cursor()
                                        tid_log = _tenant_id_from_header(request)
                                        cursor_log.execute(
                                            f"""
                                            INSERT INTO "{DB_SCHEMA}"."Disparos"
                                            ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload","MessageId","EvolutionInstance")
                                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW() AT TIME ZONE 'UTC',%s::jsonb,%s,%s)
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
                                                message_id,
                                                str(instance or '').strip() or None,
                                            ),
                                        )
                                        conn_log.commit()
                                except Exception:
                                    pass
                                return resp_json
                    
                        url = f"{base_try}/message/sendText/{instance}"
                        print(f"Sending WhatsApp TEXT to URL: {url} with Instance: {instance}")
                        payload = {
                            "number": normalized_phone,
                            "text": data.message,
                            "delay": 1200,
                            "linkPreview": True
                        }
                        async with session.post(url, json=payload, headers=headers, timeout=30) as response:
                            if response.status not in (200, 201):
                                text = await response.text()
                                print(f"Evolution API Error: {response.status} - {text}")
                                code = response.status if response.status < 500 else 502
                                raise HTTPException(
                                    status_code=code,
                                    detail=f"Erro na API WhatsApp: status={response.status} url={url} resp={text}",
                                )
                            resp_json = await response.json()
                            try:
                                message_id = _extract_evolution_message_id(resp_json) or None
                                with get_conn_for_request(request) as conn_log:
                                    cursor_log = conn_log.cursor()
                                    tid_log = _tenant_id_from_header(request)
                                    cursor_log.execute(
                                        f"""
                                        INSERT INTO "{DB_SCHEMA}"."Disparos"
                                        ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload","MessageId","EvolutionInstance")
                                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW() AT TIME ZONE 'UTC',%s::jsonb,%s,%s)
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
                                            message_id,
                                            str(instance or '').strip() or None,
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

    class WhatsAppNumbersCheckRequest(BaseModel):
        numbers: List[str]
        evolution_api_id: Optional[str] = None

    @app.post("/api/integrations/whatsapp/whatsapp-numbers")
    async def whatsapp_check_numbers(payload: WhatsAppNumbersCheckRequest, request: Request):
        try:
            try:
                with get_conn_for_request(request) as conn:
                    try:
                        if not conn.autocommit:
                            conn.rollback()
                    except Exception:
                        pass
                    prev_autocommit = conn.autocommit
                    conn.autocommit = True
                    try:
                        evo = _get_evolution_instance(conn, payload.evolution_api_id)
                        base_url = _get_evolution_base_url(conn)
                    finally:
                        try:
                            conn.autocommit = prev_autocommit
                        except Exception:
                            pass
            except HTTPException as he:
                detail = str(getattr(he, "detail", "") or "")
                if he.status_code == 500 and (
                    "Token da instância Evolution API não encontrado" in detail
                    or "Configuração da Evolution API incompleta no servidor" in detail
                ):
                    return {"rows": [], "instance": "none"}
                raise

            instance = evo["name"]
            api_key = str(evo.get("token") or "").strip() or str(os.getenv("AUTHENTICATION_API_KEY", "") or "").strip()
            if not api_key:
                return {"rows": [], "instance": instance}
            base_candidates = _evolution_base_url_candidates(base_url)
            if not base_candidates:
                return {"rows": [], "instance": instance}

            nums: List[str] = []
            seen: set[str] = set()
            for n in payload.numbers or []:
                d = _digits_only(n)
                if not d or d in seen:
                    continue
                seen.add(d)
                nums.append(d)
            if not nums:
                return {"rows": [], "instance": instance}

            headers = {"apikey": api_key, "Content-Type": "application/json"}
            last_err: Any = None
            async with aiohttp.ClientSession() as session:
                for base_try in base_candidates:
                    try:
                        url = f"{base_try}/chat/whatsappNumbers/{instance}"
                        async with session.post(url, json={"numbers": nums}, headers=headers, timeout=30) as resp:
                            raw = await resp.text()
                            if resp.status not in (200, 201):
                                last_err = raw
                                continue
                            try:
                                data = json.loads(raw) if raw else {}
                            except Exception:
                                data = {}
                            items = []
                            if isinstance(data, list):
                                items = data
                            elif isinstance(data, dict):
                                dd = data.get("data")
                                if isinstance(dd, list):
                                    items = dd
                                else:
                                    items = [data]
                            out_rows: List[Dict[str, Any]] = []
                            for idx, it in enumerate(items):
                                if not isinstance(it, dict):
                                    continue
                                num = _digits_only(it.get("number") or it.get("remoteJid") or it.get("jid") or it.get("jidOptions") or it.get("id") or "")
                                if not num and idx < len(nums):
                                    num = nums[idx]
                                exists = it.get("exists")
                                if exists is None:
                                    exists = it.get("isWhatsapp")
                                out_rows.append(
                                    {
                                        "number": num,
                                        "is_whatsapp": bool(exists),
                                        "jid": str(it.get("jid") or it.get("remoteJid") or "") or None,
                                    }
                                )
                            return {"rows": out_rows, "instance": instance}
                    except HTTPException:
                        raise
                    except (aiohttp.ClientConnectorError, aiohttp.ClientConnectionError, asyncio.TimeoutError, OSError) as ce:
                        last_err = ce
                        continue
            return {"rows": [], "instance": instance}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    class WhatsAppPresenceCacheRequest(BaseModel):
        numbers: List[str]

    @app.post("/api/integrations/whatsapp/presence-cache")
    async def whatsapp_presence_cache(payload: WhatsAppPresenceCacheRequest, request: Request):
        try:
            tid = _tenant_id_from_header(request)
            try:
                rc = get_redis_client()
            except Exception:
                rc = None
            out_rows: List[Dict[str, Any]] = []
            seen: set[str] = set()
            for n in payload.numbers or []:
                d = _digits_only(n)
                if not d or d in seen:
                    continue
                seen.add(d)
                pres = None
                if rc:
                    try:
                        v = rc.get(f"wa:presence:{tid}:{d}")
                        if v is not None:
                            pres = (v.decode("utf-8") if hasattr(v, "decode") else str(v)).strip() or None
                    except Exception:
                        pres = None
                out_rows.append({"number": d, "presence": pres})
            return {"rows": out_rows}
        except Exception as e:
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
                "entregue_em": None,
                "visualizado_em": None,
                "resposta_datahora": None,
                "resposta_classificacao": None,
                "resposta_texto": None,
                "__envio_src__": None,
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
                        ent['__envio_src__'] = 'ANEXO'
                elif status_val == 'error':
                    if not ent.get('envio_status'):
                        ent['envio_status'] = 'FALHA'
                    sent_dt = _parse_iso_dt(c.get('enviado_em') or c.get('enviadoEm') or c.get('sent_at') or c.get('sentAt'))
                    if sent_dt and ent.get('envio_datahora') is None:
                        ent['envio_datahora'] = sent_dt
                        ent['__envio_src__'] = 'ANEXO'

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
                   "RespostaClassificacao" as resposta,
                   "EntregueEm" as entregue_em,
                   "VisualizadoEm" as visualizado_em,
                   COALESCE(
                     NULLIF("Payload"->>'keyId',''),
                     NULLIF("Payload"->'key'->>'id',''),
                     NULLIF("Payload"->'data'->>'keyId',''),
                     NULLIF("Payload"->'data'->'key'->>'id',''),
                     NULLIF("MessageId",''),
                     NULLIF("Payload"->>'messageId',''),
                     NULLIF("Payload"->'data'->>'messageId',''),
                     NULLIF("Payload"->>'id',''),
                     NULLIF("Payload"->'data'->>'id','')
                   ) as message_id
            FROM "{DB_SCHEMA}"."Disparos"
            WHERE "IdTenant" = %s AND "IdCampanha" = %s
            ORDER BY "IdDisparo" ASC
            LIMIT %s
            """,
            (int(tid), int(campanha_id), int(limit_logs)),
        )
        disp_rows = cursor.fetchall()
        disp_cols = [d[0] for d in cursor.description]

        delivered_ts: Dict[str, datetime] = {}
        read_ts: Dict[str, datetime] = {}
        try:
            msg_ids_needed: List[str] = []
            seen_mid: set[str] = set()
            for r in disp_rows or []:
                d0 = dict(zip(disp_cols, r))
                if str(d0.get('direcao') or '').upper() != 'OUT':
                    continue
                mid = str(d0.get('message_id') or '').strip()
                if not mid:
                    continue
                if d0.get('entregue_em') is not None and d0.get('visualizado_em') is not None:
                    continue
                if mid in seen_mid:
                    continue
                seen_mid.add(mid)
                msg_ids_needed.append(mid)

            if msg_ids_needed:
                delivered_ts, read_ts = _load_messageupdate_receipts(cursor, msg_ids=msg_ids_needed)
                _apply_receipts_to_disparos(cursor, tid=int(tid), delivered_ts=delivered_ts, read_ts=read_ts, campanha_id=int(campanha_id))
                try:
                    cursor.connection.commit()
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
                           "RespostaClassificacao" as resposta,
                           "EntregueEm" as entregue_em,
                           "VisualizadoEm" as visualizado_em,
                           COALESCE(
                             NULLIF("Payload"->>'keyId',''),
                             NULLIF("Payload"->'key'->>'id',''),
                             NULLIF("Payload"->'data'->>'keyId',''),
                             NULLIF("Payload"->'data'->'key'->>'id',''),
                             NULLIF("MessageId",''),
                             NULLIF("Payload"->>'messageId',''),
                             NULLIF("Payload"->'data'->>'messageId',''),
                             NULLIF("Payload"->>'id',''),
                             NULLIF("Payload"->'data'->>'id','')
                           ) as message_id
                    FROM "{DB_SCHEMA}"."Disparos"
                    WHERE "IdTenant" = %s AND "IdCampanha" = %s
                    ORDER BY "IdDisparo" ASC
                    LIMIT %s
                    """,
                    (int(tid), int(campanha_id), int(limit_logs)),
                )
                disp_rows = cursor.fetchall()
                disp_cols = [d[0] for d in cursor.description]
        except Exception:
            try:
                cursor.connection.rollback()
            except Exception:
                pass

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
                envio_src = str(ent.get('__envio_src__') or '')
                is_newer_send = (cur_dt is None) or (envio_src == 'ANEXO') or (isinstance(datahora, datetime) and isinstance(cur_dt, datetime) and datahora >= cur_dt) or (cur_dt is None and datahora)
                if is_newer_send:
                    ent['envio_datahora'] = datahora
                    ent['envio_status'] = status or '—'
                    ent['entregue_em'] = None
                    ent['visualizado_em'] = None
                    ent['__envio_src__'] = 'DISPAROS'
                d_ent = d.get('entregue_em')
                if isinstance(d_ent, datetime):
                    d_ent = _to_utc_naive(d_ent)
                d_vis = d.get('visualizado_em')
                if isinstance(d_vis, datetime):
                    d_vis = _to_utc_naive(d_vis)
                mid = str(d.get('message_id') or '').strip()
                if mid and is_newer_send:
                    rts = read_ts.get(mid)
                    dts = delivered_ts.get(mid)
                    if d_vis is None and rts is not None:
                        d_vis = rts
                    if d_ent is None:
                        if dts is not None:
                            d_ent = dts
                        elif rts is not None:
                            d_ent = rts
                    if d_vis is not None and d_ent is not None and d_vis == d_ent and rts is not None and rts != d_vis:
                        d_vis = rts
                    if d_vis is not None and d_ent is not None and d_vis == d_ent and dts is not None and dts != d_ent:
                        d_ent = dts
                if is_newer_send and isinstance(ent.get('envio_datahora'), datetime):
                    envio_dt = _to_utc_naive(ent.get('envio_datahora'))
                    if isinstance(d_ent, datetime) and envio_dt and d_ent < envio_dt:
                        d_ent = envio_dt
                    if isinstance(d_vis, datetime):
                        floor_dt = d_ent if isinstance(d_ent, datetime) else envio_dt
                        if floor_dt and d_vis < floor_dt:
                            d_vis = floor_dt
                if is_newer_send:
                    if d_ent is not None:
                        ent['entregue_em'] = d_ent
                    if d_vis is not None:
                        ent['visualizado_em'] = d_vis
                    try:
                        cur_status = str(ent.get('envio_status') or '').upper()
                        if cur_status != 'FALHA':
                            if ent.get('visualizado_em'):
                                ent['envio_status'] = 'VISUALIZADO'
                            elif ent.get('entregue_em'):
                                ent['envio_status'] = 'ENTREGUE'
                    except Exception:
                        pass
            elif direcao == 'IN':
                cur_dt = ent.get('resposta_datahora')
                if (cur_dt is None) or (isinstance(datahora, datetime) and isinstance(cur_dt, datetime) and datahora >= cur_dt) or (cur_dt is None and datahora):
                    ent['resposta_datahora'] = datahora
                    ent['resposta_classificacao'] = _normalize_resposta_classificacao(resposta)
                    ent['resposta_texto'] = mensagem
                try:
                    vis = ent.get('visualizado_em')
                    entg = ent.get('entregue_em')
                    resp_dt = ent.get('resposta_datahora')
                    if resp_dt and vis and resp_dt < vis and (entg is None or vis == entg):
                        ent['visualizado_em'] = resp_dt
                except Exception:
                    pass

        linhas: List[Dict[str, Any]] = []
        for ent in by_num.values():
            if not ent.get('envio_status'):
                ent['envio_status'] = 'PENDENTE'
            if not ent.get('resposta_classificacao'):
                ent['resposta_classificacao'] = 'AGUARDANDO'
            if not ent.get('resposta_texto'):
                ent['resposta_texto'] = '—'
            ent.pop('__envio_src__', None)
            try:
                entg = ent.get('entregue_em')
                vis = ent.get('visualizado_em')
                if isinstance(entg, datetime) and isinstance(vis, datetime) and vis < entg:
                    ent['entregue_em'] = vis
            except Exception:
                pass
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
        entregues = 0
        visualizados = 0
        for it in linhas:
            envio_status = str(it.get('envio_status') or '').upper()
            if envio_status in ('ENVIADO', 'ENTREGUE', 'VISUALIZADO', 'LIDO', 'READ'):
                enviados += 1
            if envio_status == 'FALHA':
                falhas += 1
            if it.get('resposta_datahora'):
                respostas_qtd += 1
            if it.get('entregue_em'):
                entregues += 1
            if it.get('visualizado_em'):
                visualizados += 1
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
            "entregues": entregues,
            "visualizados": visualizados,
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

        anexo_obj_pdf = _safe_json_obj(campanha.get('anexo_json')) if isinstance(campanha, dict) else None
        cfg_pdf = (anexo_obj_pdf.get('config') if isinstance(anexo_obj_pdf, dict) else None) if isinstance(anexo_obj_pdf, dict) else None
        aguardar_respostas_pdf = str((cfg_pdf or {}).get('response_mode') or '').strip().upper() == 'SIM_NAO' if isinstance(cfg_pdf, dict) else False

        header = ['NOME', 'NÚMERO', 'ENVIO (DATA/HORA)', 'STATUS ENVIO', 'ENTREGUE', 'VISUALIZADO', 'STATUS DA MENSAGEM']
        if aguardar_respostas_pdf:
            header.extend(['RESPOSTA', 'RESPOSTA (DATA/HORA)'])
        data_rows: List[List[Any]] = [header]
        for it in linhas:
            recebido = bool(it.get('entregue_em'))
            visualizado = bool(it.get('visualizado_em'))
            if not recebido:
                msg_status = 'NÃO RECEBIDO'
            elif visualizado:
                msg_status = 'RECEBIDO / VISUALIZADO'
            else:
                msg_status = 'RECEBIDO / AGUARDANDO VISUALIZAÇÃO'
            row = [
                Paragraph(_truncate_text(it.get('nome') or '—', 60) or '—', style_normal),
                Paragraph(_truncate_text(it.get('numero') or '', 30) or '—', style_normal),
                Paragraph(_format_dt_br(it.get('envio_datahora') or ''), style_normal),
                Paragraph(str(it.get('envio_status') or '—').upper(), style_normal),
                Paragraph(_format_dt_br(it.get('entregue_em') or ''), style_normal),
                Paragraph(_format_dt_br(it.get('visualizado_em') or ''), style_normal),
                Paragraph(_truncate_text(msg_status, 40) or msg_status, style_normal),
            ]
            if aguardar_respostas_pdf:
                row.extend([
                    Paragraph(str(it.get('resposta_classificacao') or '—').upper(), style_normal),
                    Paragraph(_format_dt_br(it.get('resposta_datahora') or ''), style_normal),
                ])
            data_rows.append(row)

        avail_w = float(getattr(doc, 'width', 0.0) or 0.0)
        if aguardar_respostas_pdf:
            col_widths = [avail_w * 0.20, avail_w * 0.12, avail_w * 0.11, avail_w * 0.09, avail_w * 0.10, avail_w * 0.10, avail_w * 0.11, avail_w * 0.07, avail_w * 0.10]
        else:
            col_widths = [avail_w * 0.24, avail_w * 0.14, avail_w * 0.15, avail_w * 0.10, avail_w * 0.11, avail_w * 0.11, avail_w * 0.15]
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
            if isinstance(data, list) and data:
                return [x for x in data if isinstance(x, dict)]
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
                        data.get('date_time'),
                        data.get('timestamp'),
                        data.get('t'),
                        data.get('messageTimestamp'),
                    ])
                    msg = data.get('message')
                    if isinstance(msg, dict):
                        candidates.extend([
                            msg.get('date_time'),
                            msg.get('timestamp'),
                            msg.get('t'),
                            msg.get('messageTimestamp'),
                        ])
                candidates.extend([payload.get('date_time'), payload.get('timestamp'), payload.get('t'), payload.get('messageTimestamp')])

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
                            dt = _parse_iso_dt(s)
                            if dt:
                                return dt
                            continue
                    if ts > 10_000_000_000:
                        ts = ts / 1000.0
                    if ts <= 0:
                        continue
                    return datetime.fromtimestamp(ts, tz=timezone.utc).replace(tzinfo=None)
            return None
        except Exception:
            return None

    def _load_messageupdate_receipts(cursor, *, msg_ids: List[str]) -> Tuple[Dict[str, datetime], Dict[str, datetime]]:
        delivered_ts: Dict[str, datetime] = {}
        read_ts: Dict[str, datetime] = {}
        if not msg_ids:
            return delivered_ts, read_ts

        def _cuid_dt(v: Any) -> Optional[datetime]:
            try:
                s = str(v or '').strip()
                if not s.startswith('c') or len(s) < 10:
                    return None
                ts36 = s[1:9]
                ts_ms = int(ts36, 36)
                if ts_ms <= 0:
                    return None
                return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).replace(tzinfo=None)
            except Exception:
                return None

        rows: List[Tuple[Any, Any, Any, Any, Any, Any]] = []
        try:
            cursor.execute(
                """
                SELECT mu.id, mu."keyId", mu."messageId", mu.status, m."messageTimestamp" as message_ts, mu."createdAt" as created_at
                FROM "EvolutionAPI"."MessageUpdate" mu
                LEFT JOIN "EvolutionAPI"."Message" m
                  ON m.id = mu."messageId"
                WHERE (mu."keyId" = ANY(%s) OR mu."messageId" = ANY(%s))
                """,
                (msg_ids, msg_ids),
            )
            rows = cursor.fetchall() or []
        except Exception:
            cursor.execute(
                """
                SELECT mu.id, mu."keyId", mu."messageId", mu.status, m."messageTimestamp" as message_ts
                FROM "EvolutionAPI"."MessageUpdate" mu
                LEFT JOIN "EvolutionAPI"."Message" m
                  ON m.id = mu."messageId"
                WHERE (mu."keyId" = ANY(%s) OR mu."messageId" = ANY(%s))
                """,
                (msg_ids, msg_ids),
            )
            rows = [(a, b, c, d, e, None) for (a, b, c, d, e) in (cursor.fetchall() or [])]
        seen_mid = set([str(x or '').strip() for x in msg_ids if str(x or '').strip()])
        for mu_id, key_id, message_id, st, message_ts, created_at in rows:
            s = str(st or '').upper()
            ts_dt: Optional[datetime] = None
            if created_at is not None:
                if isinstance(created_at, datetime):
                    ts_dt = created_at.replace(tzinfo=None) if created_at.tzinfo is not None else created_at
                else:
                    ts_dt = _parse_iso_dt(created_at)
            if ts_dt is None:
                ts_dt = _cuid_dt(mu_id)
            if ts_dt is None and isinstance(message_ts, (int, float)):
                ts_val = float(message_ts)
                if ts_val > 10_000_000_000:
                    ts_val = ts_val / 1000.0
                if ts_val > 0:
                    ts_dt = datetime.fromtimestamp(ts_val, tz=timezone.utc).replace(tzinfo=None)
            if not ts_dt:
                continue
            ids: List[str] = []
            if isinstance(key_id, str) and key_id.strip() and key_id.strip() in seen_mid:
                ids.append(key_id.strip())
            if isinstance(message_id, str) and message_id.strip() and message_id.strip() in seen_mid:
                ids.append(message_id.strip())
            if not ids:
                continue
            ack: Optional[int] = None
            if isinstance(st, (int, float)):
                try:
                    ack = int(st)
                except Exception:
                    ack = None
            elif s.isdigit():
                try:
                    ack = int(s)
                except Exception:
                    ack = None

            is_read = (ack is not None and ack >= 3) or ('READ' in s) or ('SEEN' in s) or ('VISUAL' in s)
            is_delivered = (ack is not None and ack >= 2) or is_read or ('DELIVER' in s) or ('RECEIV' in s) or (s in ('DELIVERY_ACK', 'DELIVERED', 'DELIVERY'))
            if not is_delivered and not is_read:
                continue
            for mid in ids:
                if is_delivered:
                    prev = delivered_ts.get(mid)
                    if prev is None or ts_dt > prev:
                        delivered_ts[mid] = ts_dt
                if is_read:
                    prev_r = read_ts.get(mid)
                    if prev_r is None or ts_dt > prev_r:
                        read_ts[mid] = ts_dt
        return delivered_ts, read_ts

    def _apply_receipts_to_disparos(
        cursor,
        *,
        tid: int,
        delivered_ts: Dict[str, datetime],
        read_ts: Dict[str, datetime],
        campanha_id: Optional[int] = None,
    ) -> None:
        if not delivered_ts and not read_ts:
            return
        read_list = list(sorted(read_ts.keys()))
        delivered_only = list(sorted(set(delivered_ts.keys()) - set(read_ts.keys())))
        if read_list:
            read_times = [read_ts.get(x) for x in read_list]
            delivered_times_for_read = [delivered_ts.get(x) for x in read_list]
            where_campanha = 'AND d."IdCampanha" = %s' if campanha_id is not None else ''
            params: List[Any] = [read_list, read_times, delivered_times_for_read, int(tid)]
            if campanha_id is not None:
                params.append(int(campanha_id))
            cursor.execute(
                f"""
                WITH upd AS (
                  SELECT * FROM UNNEST(%s::text[], %s::timestamp[], %s::timestamp[]) AS t(message_id, read_ts, delivered_ts)
                )
                UPDATE "{DB_SCHEMA}"."Disparos" d
                SET "EntregueEm" = CASE
                      WHEN COALESCE(upd.delivered_ts, upd.read_ts) IS NULL THEN d."EntregueEm"
                      ELSE
                        CASE
                          WHEN d."EntregueEm" IS NULL THEN GREATEST(COALESCE(upd.delivered_ts, upd.read_ts), COALESCE(d."DataHora", COALESCE(upd.delivered_ts, upd.read_ts)))
                          WHEN d."EntregueEm" < GREATEST(COALESCE(upd.delivered_ts, upd.read_ts), COALESCE(d."DataHora", COALESCE(upd.delivered_ts, upd.read_ts))) THEN GREATEST(COALESCE(upd.delivered_ts, upd.read_ts), COALESCE(d."DataHora", COALESCE(upd.delivered_ts, upd.read_ts)))
                          ELSE d."EntregueEm"
                        END
                    END,
                    "VisualizadoEm" = CASE
                      WHEN upd.read_ts IS NULL THEN d."VisualizadoEm"
                      ELSE
                        CASE
                          WHEN d."VisualizadoEm" IS NULL THEN GREATEST(upd.read_ts, COALESCE(d."DataHora", upd.read_ts), COALESCE(upd.delivered_ts, upd.read_ts, d."DataHora"), COALESCE(d."EntregueEm", d."DataHora", upd.read_ts))
                          WHEN d."VisualizadoEm" < GREATEST(upd.read_ts, COALESCE(d."DataHora", upd.read_ts), COALESCE(upd.delivered_ts, upd.read_ts, d."DataHora"), COALESCE(d."EntregueEm", d."DataHora", upd.read_ts)) THEN GREATEST(upd.read_ts, COALESCE(d."DataHora", upd.read_ts), COALESCE(upd.delivered_ts, upd.read_ts, d."DataHora"), COALESCE(d."EntregueEm", d."DataHora", upd.read_ts))
                          ELSE d."VisualizadoEm"
                        END
                    END,
                    "MessageId" = CASE
                      WHEN d."MessageId" IS NULL OR d."MessageId" = '' THEN upd.message_id
                      ELSE d."MessageId"
                    END,
                    "Status" = CASE
                      WHEN UPPER(COALESCE(d."Status", '')) = 'FALHA' THEN d."Status"
                      WHEN UPPER(COALESCE(d."Status", '')) = 'VISUALIZADO' THEN d."Status"
                      WHEN upd.read_ts IS NOT NULL THEN 'VISUALIZADO'
                      ELSE 'ENTREGUE'
                    END
                FROM upd
                WHERE d."IdTenant" = %s
                  AND d."Canal" = 'WHATSAPP'
                  AND d."Direcao" = 'OUT'
                  {where_campanha}
                  AND (
                    d."MessageId" = upd.message_id
                    OR NULLIF(d."Payload"->>'keyId','') = upd.message_id
                    OR NULLIF(d."Payload"->'key'->>'id','') = upd.message_id
                    OR NULLIF(d."Payload"->'data'->>'keyId','') = upd.message_id
                    OR NULLIF(d."Payload"->'data'->'key'->>'id','') = upd.message_id
                    OR NULLIF(d."Payload"->>'messageId','') = upd.message_id
                    OR NULLIF(d."Payload"->'data'->>'messageId','') = upd.message_id
                    OR NULLIF(d."Payload"->>'id','') = upd.message_id
                    OR NULLIF(d."Payload"->'data'->>'id','') = upd.message_id
                  )
                """,
                tuple(params),
            )
        if delivered_only:
            delivered_times = [delivered_ts.get(x) for x in delivered_only]
            where_campanha = 'AND d."IdCampanha" = %s' if campanha_id is not None else ''
            params2: List[Any] = [delivered_only, delivered_times, int(tid)]
            if campanha_id is not None:
                params2.append(int(campanha_id))
            cursor.execute(
                f"""
                WITH upd AS (
                  SELECT * FROM UNNEST(%s::text[], %s::timestamp[]) AS t(message_id, delivered_ts)
                )
                UPDATE "{DB_SCHEMA}"."Disparos" d
                SET "EntregueEm" = CASE
                      WHEN upd.delivered_ts IS NULL THEN d."EntregueEm"
                      ELSE
                        CASE
                          WHEN d."EntregueEm" IS NULL THEN GREATEST(upd.delivered_ts, COALESCE(d."DataHora", upd.delivered_ts))
                          WHEN d."EntregueEm" < GREATEST(upd.delivered_ts, COALESCE(d."DataHora", upd.delivered_ts)) THEN GREATEST(upd.delivered_ts, COALESCE(d."DataHora", upd.delivered_ts))
                          ELSE d."EntregueEm"
                        END
                    END,
                    "MessageId" = CASE
                      WHEN d."MessageId" IS NULL OR d."MessageId" = '' THEN upd.message_id
                      ELSE d."MessageId"
                    END,
                    "Status" = CASE
                      WHEN UPPER(COALESCE(d."Status", '')) = 'FALHA' THEN d."Status"
                      WHEN UPPER(COALESCE(d."Status", '')) IN ('VISUALIZADO','ENTREGUE') THEN d."Status"
                      ELSE 'ENTREGUE'
                    END
                FROM upd
                WHERE d."IdTenant" = %s
                  AND d."Canal" = 'WHATSAPP'
                  AND d."Direcao" = 'OUT'
                  {where_campanha}
                  AND (
                    d."MessageId" = upd.message_id
                    OR NULLIF(d."Payload"->>'keyId','') = upd.message_id
                    OR NULLIF(d."Payload"->'key'->>'id','') = upd.message_id
                    OR NULLIF(d."Payload"->'data'->>'keyId','') = upd.message_id
                    OR NULLIF(d."Payload"->'data'->'key'->>'id','') = upd.message_id
                    OR NULLIF(d."Payload"->>'messageId','') = upd.message_id
                    OR NULLIF(d."Payload"->'data'->>'messageId','') = upd.message_id
                    OR NULLIF(d."Payload"->>'id','') = upd.message_id
                    OR NULLIF(d."Payload"->'data'->>'id','') = upd.message_id
                  )
                """,
                tuple(params2),
            )

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
            raw_slug = (request.headers.get('X-Tenant') or tenant or 'captar')
            if not isinstance(raw_slug, str):
                raw_slug = 'captar'
            raw_slug = raw_slug.strip() or 'captar'
            slug = (raw_slug.split('/', 1)[0] or 'captar').strip() or 'captar'
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

                try:
                    rc2 = get_redis_client()
                except Exception:
                    rc2 = None

                receipts_updated = 0
                presence_updated = 0
                for ev in events:
                    try:
                        pres = _extract_presence_status(ev)
                        num_pres = _extract_evolution_number(ev)
                        if pres and num_pres and rc2:
                            rc2.setex(f"wa:presence:{tid}:{_digits_only(num_pres)}", 86400, str(pres))
                            presence_updated += 1
                    except Exception:
                        pass

                    try:
                        from_me = _extract_from_me(ev)
                        msg_id = _extract_evolution_message_id(ev)
                        key_id = _extract_evolution_key_id(ev)
                        status_str, ack = _extract_evolution_status(ev)
                        ids: List[str] = []
                        for x in (key_id, msg_id):
                            if isinstance(x, str) and x.strip() and x.strip() not in ids:
                                ids.append(x.strip())
                        if not ids:
                            continue
                        dt_ev = _extract_evolution_datetime(ev) or datetime.utcnow()
                        delivered = False
                        seen = False
                        if ack is not None:
                            delivered = ack >= 2
                            seen = ack >= 3
                        if status_str:
                            ss = str(status_str).upper()
                            if 'DELIVER' in ss or 'RECEIV' in ss:
                                delivered = True
                            if 'READ' in ss or 'SEEN' in ss or 'VISUAL' in ss:
                                delivered = True
                                seen = True
                        if not delivered and not seen:
                            continue
                        delivered_dt = dt_ev if delivered else None
                        seen_dt = dt_ev if seen else None
                        next_status = None
                        if seen:
                            next_status = 'VISUALIZADO'
                        elif delivered:
                            next_status = 'ENTREGUE'
                        cursor.execute(
                            f"""
                            UPDATE "{DB_SCHEMA}"."Disparos"
                            SET "EntregueEm" = CASE
                                  WHEN %s IS NULL THEN "EntregueEm"
                                  WHEN "EntregueEm" IS NULL OR "EntregueEm" < GREATEST(%s, COALESCE("DataHora", %s)) THEN GREATEST(%s, COALESCE("DataHora", %s))
                                  ELSE "EntregueEm"
                                END,
                                "VisualizadoEm" = CASE
                                  WHEN %s IS NULL THEN "VisualizadoEm"
                                  WHEN "VisualizadoEm" IS NULL OR "VisualizadoEm" < GREATEST(%s, COALESCE("DataHora", %s), COALESCE("EntregueEm", "DataHora", %s)) THEN GREATEST(%s, COALESCE("DataHora", %s), COALESCE("EntregueEm", "DataHora", %s))
                                  ELSE "VisualizadoEm"
                                END,
                                "Status" = CASE
                                  WHEN %s IS NULL THEN "Status"
                                  WHEN UPPER(COALESCE("Status", '')) = 'FALHA' THEN "Status"
                                  WHEN UPPER(COALESCE("Status", '')) = 'VISUALIZADO' THEN "Status"
                                  ELSE %s
                                END
                            WHERE "IdTenant" = %s
                              AND "Canal" = 'WHATSAPP'
                              AND "Direcao" = 'OUT'
                              AND (
                                "MessageId" = ANY(%s)
                                OR NULLIF("Payload"->>'keyId','') = ANY(%s)
                                OR NULLIF("Payload"->'key'->>'id','') = ANY(%s)
                                OR NULLIF("Payload"->'data'->>'keyId','') = ANY(%s)
                                OR NULLIF("Payload"->'data'->'key'->>'id','') = ANY(%s)
                                OR NULLIF("Payload"->>'messageId','') = ANY(%s)
                                OR NULLIF("Payload"->'data'->>'messageId','') = ANY(%s)
                                OR NULLIF("Payload"->>'id','') = ANY(%s)
                                OR NULLIF("Payload"->'data'->>'id','') = ANY(%s)
                              )
                            """,
                            (
                                delivered_dt,
                                delivered_dt, delivered_dt, delivered_dt, delivered_dt,
                                seen_dt,
                                seen_dt, seen_dt, seen_dt, seen_dt, seen_dt, seen_dt,
                                next_status,
                                next_status,
                                tid,
                                ids,
                                ids,
                                ids,
                                ids,
                                ids,
                                ids,
                                ids,
                                ids,
                                ids,
                            ),
                        )
                        if cursor.rowcount:
                            receipts_updated += int(cursor.rowcount or 0)
                            conn.commit()
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass

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
                      AND d."Status" IN ('ENVIADO','ENTREGUE','VISUALIZADO')
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
                    "receipts_updated": receipts_updated,
                    "presence_updated": presence_updated,
                    "updated": updated,
                    "ignored": ignored,
                }
        except Exception as e:
            try:
                traceback.print_exc()
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/webhook")
    async def whatsapp_webhook_compat(payload: Dict[str, Any], request: Request, tenant: Optional[str] = None):
        return await whatsapp_webhook(payload, request, tenant=tenant)

    @app.get("/api/integracoes/evolution/key")
    async def integracoes_evolution_key(request: Request):
        try:
            with get_conn_for_request(request) as conn:
                inst = _get_evolution_instance(conn, None)
                val = str(inst.get("token") or "").strip() or str(os.getenv("AUTHENTICATION_API_KEY", "") or "").strip()
                return {"hasKey": bool(val), "keyMasked": mask_key(val), "evolution_api_id": inst["id"]}
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
                headers={"apikey": key, "Accept": "application/json", "Accept-Encoding": "identity", "User-Agent": "CAPTAR/1.0"},
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
                msg: Any = {}
                try:
                    msg = json.loads(raw.decode("utf-8"))
                except Exception:
                    msg = {"text": raw.decode("utf-8", errors="ignore")}
                ok = 200 <= code < 300
                return {
                    "ok": ok,
                    "status_code": code,
                    "message": (msg.get("message") if isinstance(msg, dict) else None) or (msg.get("status") if isinstance(msg, dict) else None) or "",
                    "version": (msg.get("version") if isinstance(msg, dict) else None) or "",
                }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


