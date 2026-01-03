from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, Any, Callable
import base64
import json
import ssl
import urllib.request
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
import os
from datetime import datetime
import re
import unicodedata
import ipaddress


class TwilioConfigIn(BaseModel):
    account_sid: str
    auth_token: Optional[str] = None
    api_key_sid: Optional[str] = None
    api_key_secret: Optional[str] = None
    messaging_service_sid: Optional[str] = None
    whatsapp_from: Optional[str] = None
    sms_from: Optional[str] = None
    enabled_channels: Optional[list[str]] = None
    status_callback_url: Optional[str] = None
    inbound_webhook_url: Optional[str] = None
    validate_signature: Optional[bool] = False
    enabled: Optional[bool] = True


class TwilioSendIn(BaseModel):
    to: str
    channel: Optional[str] = None
    body: Optional[str] = None
    media_urls: Optional[list[str]] = None
    status_callback_url: Optional[str] = None
    from_override: Optional[str] = None
    campanha_id: Optional[int] = None
    contato_nome: Optional[str] = None
    content_sid: Optional[str] = None
    content_variables: Optional[dict[str, Any] | str] = None


class TwilioOptInUpsertIn(BaseModel):
    numbers: list[str]
    opted_in: Optional[bool] = True
    source: Optional[str] = None


def register_twilio_routes(
    app: FastAPI,
    get_db_connection: Callable[..., Any],
    get_conn_for_request: Callable[[Request], Any],
    db_schema: str,
    mask_key: Callable[[str], str],
):
    safe_schema = str(db_schema or "captar").replace('"', '""')

    def _get_fernet():
        try:
            from cryptography.fernet import Fernet  # type: ignore

            key = str(os.getenv("DSN_SECRET_KEY", "") or "").strip()
            if not key:
                return None
            return Fernet(key.encode("utf-8"))
        except Exception:
            return None

    def _encrypt_secret(val: str) -> str:
        s = str(val or "").strip()
        if not s:
            return ""
        f = _get_fernet()
        if not f:
            return s
        try:
            return "enc:" + f.encrypt(s.encode("utf-8")).decode("utf-8")
        except Exception:
            return s

    def _decrypt_secret(val: str) -> str:
        s = str(val or "").strip()
        if not s:
            return ""
        if s.startswith("enc:"):
            f = _get_fernet()
            if not f:
                return ""
            try:
                raw = s[len("enc:") :]
                return f.decrypt(raw.encode("utf-8")).decode("utf-8")
            except Exception:
                return ""
        return s

    def ensure_twilio_table():
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{safe_schema}"."twilio_config" (
                        id SERIAL PRIMARY KEY,
                        tenant_slug TEXT NOT NULL,
                        account_sid TEXT NOT NULL,
                        auth_token TEXT,
                        api_key_sid TEXT,
                        api_key_secret TEXT,
                        messaging_service_sid TEXT,
                        whatsapp_from TEXT,
                        sms_from TEXT,
                        status_callback_url TEXT,
                        inbound_webhook_url TEXT,
                        validate_signature BOOLEAN DEFAULT FALSE,
                        enabled BOOLEAN DEFAULT TRUE,
                        enabled_channels TEXT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                    """
                )
                cur.execute(f'ALTER TABLE "{safe_schema}"."twilio_config" ADD COLUMN IF NOT EXISTS auth_token TEXT')
                cur.execute(f'ALTER TABLE "{safe_schema}"."twilio_config" ADD COLUMN IF NOT EXISTS api_key_sid TEXT')
                cur.execute(f'ALTER TABLE "{safe_schema}"."twilio_config" ADD COLUMN IF NOT EXISTS api_key_secret TEXT')
                cur.execute(f'ALTER TABLE "{safe_schema}"."twilio_config" ADD COLUMN IF NOT EXISTS status_callback_url TEXT')
                cur.execute(f'ALTER TABLE "{safe_schema}"."twilio_config" ADD COLUMN IF NOT EXISTS inbound_webhook_url TEXT')
                cur.execute(f'ALTER TABLE "{safe_schema}"."twilio_config" ADD COLUMN IF NOT EXISTS validate_signature BOOLEAN DEFAULT FALSE')
                cur.execute(f'ALTER TABLE "{safe_schema}"."twilio_config" ADD COLUMN IF NOT EXISTS enabled_channels TEXT')
                cur.execute(
                    f'CREATE INDEX IF NOT EXISTS "idx_twilio_config_tenant" ON "{safe_schema}"."twilio_config"(tenant_slug)'
                )
                conn.commit()
        except Exception:
            pass

    def ensure_twilio_optin_table():
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{safe_schema}"."whatsapp_optin" (
                        id SERIAL PRIMARY KEY,
                        "IdTenant" INT NOT NULL,
                        "Numero" TEXT NOT NULL,
                        "Provider" TEXT NOT NULL DEFAULT 'twilio',
                        "Status" TEXT NOT NULL DEFAULT 'OPT_IN',
                        "Source" TEXT,
                        "DataHora" TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'UTC'),
                        UNIQUE("IdTenant","Numero","Provider")
                    )
                    """
                )
                cur.execute(
                    f'CREATE INDEX IF NOT EXISTS "idx_whatsapp_optin_tenant_num" ON "{safe_schema}"."whatsapp_optin"("IdTenant","Numero")'
                )
                conn.commit()
        except Exception:
            pass

    def _tenant_slug(request: Request) -> str:
        try:
            q = getattr(request, "query_params", None)
            qp_tenant = None
            if q is not None:
                qp_tenant = q.get("tenant") or q.get("slug") or None
            return (
                str(qp_tenant or request.headers.get("X-Tenant") or "captar")
                .strip()
                .lower()
                or "captar"
            )
        except Exception:
            return "captar"

    def _digits_only(s: Any) -> str:
        try:
            return "".join([c for c in str(s or "") if c.isdigit()])
        except Exception:
            return ""

    def _default_country_code() -> str:
        cc = _digits_only(os.getenv("DEFAULT_COUNTRY_CODE", "") or "")
        return cc or "55"

    def _normalize_twilio_to(to_raw: str) -> str:
        s = str(to_raw or "").strip()
        if not s:
            return s
        if s.lower().startswith("whatsapp:"):
            rest = s.split(":", 1)[1].strip()
            digits = _digits_only(rest)
            if not digits:
                return s
            cc = _default_country_code()
            if len(digits) <= 11 and not digits.startswith(cc):
                digits = f"{cc}{digits}"
            return f"whatsapp:+{digits}"
        if s.startswith("+"):
            return s
        digits2 = _digits_only(s)
        if digits2:
            cc2 = _default_country_code()
            if len(digits2) <= 11 and not digits2.startswith(cc2):
                digits2 = f"{cc2}{digits2}"
            return f"+{digits2}"
        return s

    def _normalize_optin_digits(raw: Any) -> str:
        d = _digits_only(raw)
        if not d:
            return ""
        cc = _default_country_code()
        if len(d) <= 11 and not d.startswith(cc):
            d = f"{cc}{d}"
        return d

    def _tenant_id_from_request(conn, request: Request) -> int:
        slug = _tenant_slug(request)
        try:
            cur = conn.cursor()
            cur.execute(f'SELECT "IdTenant" FROM "{safe_schema}"."Tenant" WHERE "Slug" = %s LIMIT 1', (slug,))
            row = cur.fetchone()
            if row and row[0] is not None:
                return int(row[0])
        except Exception:
            pass
        return 1

    def _optin_status(conn, *, tid: int, numero_digits: str, provider: str = "twilio") -> str:
        try:
            ensure_twilio_optin_table()
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT "Status"
                FROM "{safe_schema}"."whatsapp_optin"
                WHERE "IdTenant" = %s AND "Numero" = %s AND "Provider" = %s
                LIMIT 1
                """,
                (int(tid), str(numero_digits), str(provider)),
            )
            row = cur.fetchone()
            return str(row[0] or "").strip().upper() if row and row[0] is not None else ""
        except Exception:
            return ""

    def _has_optin(conn, *, tid: int, numero_digits: str, provider: str = "twilio") -> bool:
        st = _optin_status(conn, tid=tid, numero_digits=str(numero_digits or ""), provider=provider)
        return st == "OPT_IN"

    def _map_twilio_status(status_raw: Any) -> str:
        s = str(status_raw or "").strip().lower()
        if s in ("queued", "accepted", "sending", "sent"):
            return "ENVIADO"
        if s in ("delivered",):
            return "ENTREGUE"
        if s in ("read", "seen"):
            return "VISUALIZADO"
        if s in ("undelivered", "failed"):
            return "FALHA"
        return (s.upper() if s else "ENVIADO")

    def _strip_accents(s: str) -> str:
        try:
            nfkd = unicodedata.normalize("NFKD", str(s or ""))
            return "".join([c for c in nfkd if not unicodedata.combining(c)])
        except Exception:
            return str(s or "")

    def _parse_sim_nao_response(text: Any) -> Optional[int]:
        try:
            raw = str(text or "").strip()
            if not raw:
                return None
            t = _strip_accents(raw).strip().lower()
            t = re.sub(r"\s+", " ", t)
            if re.match(r"^\(?\s*1\b", t) or t.startswith("1-") or t.startswith("1 ") or t == "1":
                return 1
            if re.match(r"^\(?\s*2\b", t) or t.startswith("2-") or t.startswith("2 ") or t == "2":
                return 2
            if re.search(r"\bsim\b", t) or t in ("s", "ok", "yes", "y"):
                return 1
            if re.search(r"\bnao\b", t) or t in ("n", "no"):
                return 2
            return None
        except Exception:
            return None

    def _match_phone(stored: Any, incoming_digits: str) -> bool:
        def norm_br(d: str) -> str:
            if not d:
                return d
            dd = "".join([c for c in str(d) if c.isdigit()])
            if len(dd) == 13 and dd.startswith("55") and dd[4] == "9":
                return dd[:4] + dd[5:]
            if len(dd) == 11 and dd[2] == "9":
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

    def _safe_json_obj(v: Any) -> Optional[dict]:
        if v is None:
            return None
        if isinstance(v, dict):
            return v
        if isinstance(v, str):
            try:
                obj = json.loads(v)
                return obj if isinstance(obj, dict) else None
            except Exception:
                return None
        return None

    def _get_latest_config(conn, slug: str):
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT id, tenant_slug, account_sid, auth_token, api_key_sid, api_key_secret, messaging_service_sid, whatsapp_from, sms_from, status_callback_url, inbound_webhook_url, validate_signature, enabled, enabled_channels
            FROM "{safe_schema}"."twilio_config"
            WHERE tenant_slug=%s
            ORDER BY id DESC
            LIMIT 1
            """,
            (slug,),
        )
        return cur.fetchone()

    def _parse_enabled_channels(raw: Any) -> list[str]:
        try:
            if isinstance(raw, list):
                cleaned: list[str] = []
                for item in raw:
                    v = str(item or "").strip().lower()
                    if v and v not in cleaned:
                        cleaned.append(v)
                return cleaned or ["sms", "whatsapp", "mms"]
            if raw is None:
                return ["sms", "whatsapp", "mms"]
            s = str(raw or "").strip()
            if not s:
                return ["sms", "whatsapp", "mms"]
            data = json.loads(s)
            if not isinstance(data, list):
                return ["sms", "whatsapp", "mms"]
            cleaned: list[str] = []
            for item in data:
                v = str(item or "").strip().lower()
                if v and v not in cleaned:
                    cleaned.append(v)
            return cleaned or ["sms", "whatsapp", "mms"]
        except Exception:
            return ["sms", "whatsapp", "mms"]

    def _public_url(request: Request) -> str:
        proto = str(request.headers.get("x-forwarded-proto") or request.url.scheme or "http")
        host = str(request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc)
        q = str(getattr(request.url, "query", "") or "").strip()
        qs = f"?{q}" if q else ""
        return f"{proto}://{host}{request.url.path}{qs}"

    def _public_base(request: Request) -> str:
        override = str(os.getenv("PUBLIC_BASE_URL") or os.getenv("CAPTAR_PUBLIC_BASE_URL") or "").strip().rstrip("/")
        if override and (override.startswith("http://") or override.startswith("https://")) and not _is_localhost_url(override):
            return override
        proto = str(request.headers.get("x-forwarded-proto") or request.url.scheme or "http")
        host = str(request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc)
        return f"{proto}://{host}"

    def _is_localhost_url(url: str) -> bool:
        try:
            u = urlparse(str(url or "").strip())
            host = str(u.hostname or "").strip().lower()
            if host in ("localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal"):
                return True
            try:
                ip = ipaddress.ip_address(host)
                return bool(ip.is_private or ip.is_loopback or ip.is_link_local)
            except Exception:
                return False
        except Exception:
            return False

    def _origin_from_url(url: Any) -> str:
        try:
            u = urlparse(str(url or "").strip())
            if not u.scheme or not u.netloc:
                return ""
            return f"{u.scheme}://{u.netloc}"
        except Exception:
            return ""

    def _public_media_base(request: Request, cfg_row: Any) -> str:
        try:
            inbound_url = ""
            status_url = ""
            if cfg_row:
                inbound_url = str(cfg_row[10] or "").strip()
                status_url = str(cfg_row[9] or "").strip()
            cand = inbound_url or status_url
            origin = _origin_from_url(cand)
            if origin and not _is_localhost_url(origin):
                return origin
        except Exception:
            pass
        override = str(os.getenv("PUBLIC_BASE_URL") or os.getenv("CAPTAR_PUBLIC_BASE_URL") or "").strip().rstrip("/")
        if override and (override.startswith("http://") or override.startswith("https://")) and not _is_localhost_url(override):
            return override
        return _public_base(request)

    def _normalize_public_media_url(request: Request, cfg_row: Any, raw_url: Any, *, is_whatsapp: bool) -> str:
        s = str(raw_url or "").strip()
        if not s:
            return ""
        if s.lower().startswith("data:"):
            raise HTTPException(status_code=400, detail="Mídia inválida: envie uma URL pública ou faça upload pela Twilio.")
        if s.lower().startswith("http://") or s.lower().startswith("https://"):
            if _is_localhost_url(s):
                raise HTTPException(status_code=400, detail=f"URL de mídia não pública '{s}' não é permitida para Twilio.")
            if is_whatsapp and s.lower().startswith("http://"):
                raise HTTPException(status_code=400, detail="Para WhatsApp, a Twilio exige mídia em URL pública HTTPS.")
            return s
        base = _public_media_base(request, cfg_row)
        if _is_localhost_url(base):
            raise HTTPException(status_code=400, detail="Base pública de mídia não configurada para Twilio. Ajuste o 'Status Callback URL' ou 'Inbound Webhook URL' para um domínio público.")
        if is_whatsapp and base.lower().startswith("http://"):
            raise HTTPException(status_code=400, detail="Para WhatsApp, a Twilio exige mídia em URL pública HTTPS.")
        if s.startswith("/"):
            return f"{base}{s}"
        return f"{base}/{s}"

    def _validate_twilio_request(request: Request, params: dict[str, str], token: str) -> bool:
        try:
            from twilio.request_validator import RequestValidator  # type: ignore

            sig = str(request.headers.get("X-Twilio-Signature") or "").strip()
            if not sig:
                return False
            validator = RequestValidator(token)
            url = _public_url(request)
            return bool(validator.validate(url, params, sig))
        except Exception:
            return False

    @app.get("/api/integracoes/twilio/config")
    async def twilio_get_config(request: Request):
        ensure_twilio_table()
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                row = _get_latest_config(conn, slug)
                if not row:
                    base = _public_base(request)
                    return {
                        "tenant_slug": slug,
                        "enabled": True,
                        "enabled_channels": ["sms", "whatsapp", "mms"],
                        "has_auth_token": False,
                        "auth_token_masked": "",
                        "api_key_sid": "",
                        "has_api_key_secret": False,
                        "api_key_secret_masked": "",
                        "messaging_service_sid": "",
                        "whatsapp_from": "",
                        "sms_from": "",
                        "status_callback_url": "" if _is_localhost_url(base) else f"{base}/api/integracoes/twilio/webhook/status?tenant={slug}",
                        "inbound_webhook_url": "" if _is_localhost_url(base) else f"{base}/api/integracoes/twilio/webhook/inbound?tenant={slug}",
                        "validate_signature": False,
                    }
                auth_token_plain = _decrypt_secret(str(row[3] or "").strip())
                api_key_secret_plain = _decrypt_secret(str(row[5] or "").strip())
                enabled_channels = _parse_enabled_channels(row[13] if len(row) > 13 else None)
                base = _public_base(request)
                return {
                    "tenant_slug": slug,
                    "id": int(row[0]),
                    "account_sid": str(row[2] or "").strip(),
                    "enabled_channels": enabled_channels,
                    "has_auth_token": bool(auth_token_plain),
                    "auth_token_masked": mask_key(auth_token_plain),
                    "api_key_sid": str(row[4] or "").strip(),
                    "has_api_key_secret": bool(api_key_secret_plain),
                    "api_key_secret_masked": mask_key(api_key_secret_plain),
                    "messaging_service_sid": str(row[6] or "").strip(),
                    "whatsapp_from": str(row[7] or "").strip(),
                    "sms_from": str(row[8] or "").strip(),
                    "status_callback_url": str(row[9] or "").strip() or ("" if _is_localhost_url(base) else f"{base}/api/integracoes/twilio/webhook/status?tenant={slug}"),
                    "inbound_webhook_url": str(row[10] or "").strip() or ("" if _is_localhost_url(base) else f"{base}/api/integracoes/twilio/webhook/inbound?tenant={slug}"),
                    "validate_signature": bool(row[11]) if row[11] is not None else False,
                    "enabled": bool(row[12]) if row[12] is not None else True,
                }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/integracoes/twilio/config")
    async def twilio_save_config(payload: TwilioConfigIn, request: Request):
        ensure_twilio_table()
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                prev = _get_latest_config(conn, slug)
                account_sid = str(payload.account_sid or "").strip()
                if not account_sid:
                    raise HTTPException(status_code=400, detail="Account SID é obrigatório.")
                auth_token = str(payload.auth_token or "").strip()
                if not auth_token and prev:
                    auth_token = _decrypt_secret(str(prev[3] or "").strip())
                api_key_sid = str(payload.api_key_sid or "").strip()
                api_key_secret = str(payload.api_key_secret or "").strip()
                if not api_key_secret and prev:
                    api_key_secret = _decrypt_secret(str(prev[5] or "").strip())
                if not auth_token and not (api_key_sid and api_key_secret):
                    raise HTTPException(status_code=400, detail="Informe Auth Token ou API Key (SID + Secret).")
                enabled_channels = payload.enabled_channels
                if enabled_channels is None and prev:
                    enabled_channels = _parse_enabled_channels(prev[13] if len(prev) > 13 else None)
                enabled_channels_json = json.dumps(_parse_enabled_channels(enabled_channels))
                cur = conn.cursor()
                cur.execute(
                    f"""
                    INSERT INTO "{safe_schema}"."twilio_config"
                    (tenant_slug, account_sid, auth_token, api_key_sid, api_key_secret, messaging_service_sid, whatsapp_from, sms_from, enabled_channels, status_callback_url, inbound_webhook_url, validate_signature, enabled, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
                    RETURNING id
                    """,
                    (
                        slug,
                        account_sid,
                        (_encrypt_secret(auth_token) if auth_token else None),
                        (api_key_sid or None),
                        (_encrypt_secret(api_key_secret) if api_key_secret else None),
                        (str(payload.messaging_service_sid or "").strip() or None),
                        (str(payload.whatsapp_from or "").strip() or None),
                        (str(payload.sms_from or "").strip() or None),
                        (enabled_channels_json or None),
                        (str(payload.status_callback_url or "").strip() or None),
                        (str(payload.inbound_webhook_url or "").strip() or None),
                        bool(payload.validate_signature) if payload.validate_signature is not None else False,
                        bool(payload.enabled) if payload.enabled is not None else True,
                    ),
                )
                new_id = int(cur.fetchone()[0])
                conn.commit()
                return {"id": new_id, "saved": True}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/integracoes/twilio/test")
    async def twilio_test(request: Request):
        ensure_twilio_table()
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                row = _get_latest_config(conn, slug)
            if not row:
                raise HTTPException(status_code=400, detail="Twilio não configurada.")
            account_sid = str(row[2] or "").strip()
            auth_token = _decrypt_secret(str(row[3] or "").strip())
            api_key_sid = str(row[4] or "").strip()
            api_key_secret = _decrypt_secret(str(row[5] or "").strip())
            if not account_sid:
                raise HTTPException(status_code=400, detail="Twilio não configurada.")
            try:
                from twilio.rest import Client  # type: ignore
            except Exception:
                raise HTTPException(status_code=500, detail="Dependência 'twilio' não instalada no backend.")
            if api_key_sid and api_key_secret:
                client = Client(api_key_sid, api_key_secret, account_sid)
            else:
                if not auth_token:
                    raise HTTPException(status_code=400, detail="Twilio não configurada.")
                client = Client(account_sid, auth_token)
            acc = client.api.accounts(account_sid).fetch()
            return {
                "ok": True,
                "status_code": 200,
                "account": {
                    "sid": getattr(acc, "sid", None),
                    "friendly_name": getattr(acc, "friendly_name", None),
                    "status": getattr(acc, "status", None),
                    "type": getattr(acc, "type", None),
                },
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/integracoes/twilio/optin")
    async def twilio_optin_upsert(payload: TwilioOptInUpsertIn, request: Request):
        ensure_twilio_optin_table()
        try:
            numbers_in = payload.numbers if isinstance(payload.numbers, list) else []
            cleaned: list[str] = []
            for n in numbers_in:
                nd = _normalize_optin_digits(n)
                if nd and nd not in cleaned:
                    cleaned.append(nd)
            if not cleaned:
                raise HTTPException(status_code=400, detail="Informe ao menos um número.")
            source = str(payload.source or "").strip() or None
            status = "OPT_IN" if bool(payload.opted_in is None or payload.opted_in) else "OPT_OUT"
            with get_conn_for_request(request) as conn:
                tid = _tenant_id_from_request(conn, request)
                cur = conn.cursor()
                for nd in cleaned:
                    cur.execute(
                        f"""
                        INSERT INTO "{safe_schema}"."whatsapp_optin" ("IdTenant","Numero","Provider","Status","Source","DataHora")
                        VALUES (%s,%s,'twilio',%s,%s,(NOW() AT TIME ZONE 'UTC'))
                        ON CONFLICT ("IdTenant","Numero","Provider")
                        DO UPDATE SET "Status" = EXCLUDED."Status", "Source" = EXCLUDED."Source", "DataHora" = EXCLUDED."DataHora"
                        """,
                        (int(tid), str(nd), status, source),
                    )
                conn.commit()
            return {"ok": True, "updated": len(cleaned), "status": status, "numbers": cleaned}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/integracoes/twilio/optin/status")
    async def twilio_optin_status(payload: TwilioOptInUpsertIn, request: Request):
        ensure_twilio_optin_table()
        try:
            numbers_in = payload.numbers if isinstance(payload.numbers, list) else []
            cleaned: list[str] = []
            for n in numbers_in:
                nd = _normalize_optin_digits(n)
                if nd and nd not in cleaned:
                    cleaned.append(nd)
            if not cleaned:
                return {"items": []}
            with get_conn_for_request(request) as conn:
                tid = _tenant_id_from_request(conn, request)
                cur = conn.cursor()
                cur.execute(
                    f"""
                    SELECT "Numero", "Status"
                    FROM "{safe_schema}"."whatsapp_optin"
                    WHERE "IdTenant" = %s AND "Provider" = 'twilio' AND "Numero" = ANY(%s)
                    """,
                    (int(tid), cleaned),
                )
                rows = cur.fetchall() or []
            by_num = {str(n): str(st or "").strip().upper() for (n, st) in rows}
            items = [{"number": n, "status": (by_num.get(n) or ""), "opted_in": (by_num.get(n) == "OPT_IN")} for n in cleaned]
            return {"items": items}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/integracoes/twilio/send")
    async def twilio_send(payload: TwilioSendIn, request: Request):
        ensure_twilio_table()
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                row = _get_latest_config(conn, slug)
            if not row:
                raise HTTPException(status_code=400, detail="Twilio não configurada.")
            enabled = bool(row[12]) if row[12] is not None else True
            if not enabled:
                raise HTTPException(status_code=400, detail="Twilio está desativada.")
            account_sid = str(row[2] or "").strip()
            auth_token = _decrypt_secret(str(row[3] or "").strip())
            api_key_sid = str(row[4] or "").strip()
            api_key_secret = _decrypt_secret(str(row[5] or "").strip())
            messaging_service_sid = str(row[6] or "").strip()
            whatsapp_from = str(row[7] or "").strip()
            sms_from = str(row[8] or "").strip()
            status_callback_default = str(row[9] or "").strip()
            enabled_channels = _parse_enabled_channels(row[13] if len(row) > 13 else None)

            to_raw = str(payload.to or "").strip()
            channel_hint = str(payload.channel or "").strip().lower()
            if channel_hint in ("whatsapp", "wa"):
                if to_raw and not to_raw.lower().startswith("whatsapp:"):
                    to_raw = f"whatsapp:{to_raw}"
            elif channel_hint in ("sms", "mms"):
                if to_raw.lower().startswith("whatsapp:"):
                    to_raw = to_raw.split(":", 1)[1].strip()
            to = _normalize_twilio_to(to_raw)
            body = str(payload.body or "").strip() if payload.body is not None else ""
            content_sid = str(payload.content_sid or "").strip()
            content_variables_json: Optional[str] = None
            if payload.content_variables is not None:
                if isinstance(payload.content_variables, dict):
                    content_variables_json = json.dumps(payload.content_variables, ensure_ascii=False)
                elif isinstance(payload.content_variables, str):
                    raw_cv = str(payload.content_variables or "").strip()
                    if raw_cv:
                        try:
                            cv_obj = json.loads(raw_cv)
                        except Exception:
                            raise HTTPException(status_code=400, detail="content_variables inválido: envie um JSON válido.")
                        if not isinstance(cv_obj, dict):
                            raise HTTPException(status_code=400, detail="content_variables inválido: esperado um objeto JSON.")
                        content_variables_json = json.dumps(cv_obj, ensure_ascii=False)

            if not to:
                raise HTTPException(status_code=400, detail="Destino (to) é obrigatório.")
            if not body and not content_sid:
                raise HTTPException(status_code=400, detail="Informe 'body' ou 'content_sid'.")

            try:
                from twilio.rest import Client  # type: ignore
            except Exception:
                raise HTTPException(status_code=500, detail="Dependência 'twilio' não instalada no backend.")

            if api_key_sid and api_key_secret:
                client = Client(api_key_sid, api_key_secret, account_sid)
            else:
                if not auth_token:
                    raise HTTPException(status_code=400, detail="Twilio não configurada.")
                client = Client(account_sid, auth_token)

            is_whatsapp = to.lower().startswith("whatsapp:")
            msg_kwargs: dict[str, Any] = {"to": to}
            if content_sid:
                msg_kwargs["content_sid"] = content_sid
                if content_variables_json is not None:
                    msg_kwargs["content_variables"] = content_variables_json
            else:
                msg_kwargs["body"] = body
            cleaned_media: list[str] = []
            if payload.media_urls:
                raw_media = [str(x or "").strip() for x in payload.media_urls if str(x or "").strip()]
                for m in raw_media:
                    normalized = _normalize_public_media_url(request, row, m, is_whatsapp=is_whatsapp)
                    if normalized:
                        cleaned_media.append(normalized)
                if cleaned_media:
                    msg_kwargs["media_url"] = cleaned_media

            channel = "whatsapp" if is_whatsapp else ("mms" if cleaned_media else "sms")
            if channel not in enabled_channels:
                raise HTTPException(status_code=400, detail=f"Canal '{channel}' não está habilitado na integração Twilio.")

            require_optin = str(os.getenv("TWILIO_REQUIRE_OPTIN", "0") or "0").strip().lower()
            require_optin = require_optin not in ("0", "false", "no", "off")
            if is_whatsapp and require_optin:
                ensure_twilio_optin_table()
                numero_digits = _normalize_optin_digits(_digits_only(to))
                try:
                    with get_conn_for_request(request) as conn_chk:
                        tid_chk = _tenant_id_from_request(conn_chk, request)
                        if not _has_optin(conn_chk, tid=tid_chk, numero_digits=numero_digits, provider="twilio"):
                            try:
                                cur = conn_chk.cursor()
                                cur.execute(
                                    f"""
                                    INSERT INTO "{safe_schema}"."Disparos"
                                    ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload","MessageId")
                                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW() AT TIME ZONE 'UTC',%s::jsonb,%s)
                                    """,
                                    (
                                        int(tid_chk),
                                        payload.campanha_id,
                                        "WHATSAPP",
                                        "OUT",
                                        numero_digits,
                                        (payload.contato_nome or None),
                                        (body if body else None),
                                        (cleaned_media[0] if cleaned_media else None),
                                        "FALHA",
                                        json.dumps({"provider": "twilio", "error": "SEM_OPTIN", "to": to}, ensure_ascii=False),
                                        None,
                                    ),
                                )
                                conn_chk.commit()
                            except Exception:
                                try:
                                    conn_chk.rollback()
                                except Exception:
                                    pass
                            raise HTTPException(status_code=400, detail=f"Número sem opt-in cadastrado: {to}")
                except HTTPException:
                    raise
                except Exception:
                    raise HTTPException(status_code=500, detail="Falha ao validar opt-in para Twilio.")

            if str(payload.status_callback_url or "").strip():
                msg_kwargs["status_callback"] = str(payload.status_callback_url or "").strip()
            elif status_callback_default and not _is_localhost_url(status_callback_default):
                msg_kwargs["status_callback"] = status_callback_default

            if messaging_service_sid and not is_whatsapp:
                msg_kwargs["messaging_service_sid"] = messaging_service_sid
            else:
                from_val = str(payload.from_override or "").strip() or (whatsapp_from if is_whatsapp else sms_from)
                if is_whatsapp and from_val and not from_val.lower().startswith("whatsapp:"):
                    from_val = f"whatsapp:{from_val}"
                if not from_val:
                    raise HTTPException(status_code=400, detail="Remetente (From) não configurado.")
                msg_kwargs["from_"] = from_val

            try:
                msg = client.messages.create(**msg_kwargs)
                sid = getattr(msg, "sid", None)
                status = getattr(msg, "status", None)
                try:
                    with get_conn_for_request(request) as conn_log:
                        cur = conn_log.cursor()
                        tid = _tenant_id_from_request(conn_log, request)
                        canal = "WHATSAPP" if is_whatsapp else ("MMS" if cleaned_media else "SMS")
                        numero = _digits_only(to)
                        imagem = cleaned_media[0] if cleaned_media else None
                        cur.execute(
                            f"""
                            INSERT INTO "{safe_schema}"."Disparos"
                            ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload","MessageId")
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW() AT TIME ZONE 'UTC',%s::jsonb,%s)
                            """,
                            (
                                tid,
                                payload.campanha_id,
                                canal,
                                "OUT",
                                numero,
                                (payload.contato_nome or None),
                                (body if body else None),
                                imagem,
                                _map_twilio_status(status),
                                json.dumps(
                                    {
                                        "provider": "twilio",
                                        "sid": sid,
                                        "status": status,
                                        "to": to,
                                        "from": msg_kwargs.get("from_") or msg_kwargs.get("messaging_service_sid"),
                                        "content_sid": (content_sid or None),
                                    },
                                    ensure_ascii=False,
                                ),
                                sid,
                            ),
                        )
                        conn_log.commit()
                except Exception:
                    pass
                return {"ok": True, "sid": sid, "status": status}
            except Exception as tw_err:
                try:
                    from twilio.base.exceptions import TwilioRestException  # type: ignore

                    if isinstance(tw_err, TwilioRestException):
                        status = int(getattr(tw_err, "status", 400) or 400)
                        code = getattr(tw_err, "code", None)
                        msg = getattr(tw_err, "msg", None) or str(tw_err)
                        detail = f"{msg}{f' (code {code})' if code else ''}"
                        raise HTTPException(status_code=status if status >= 400 else 400, detail=detail)
                except HTTPException:
                    raise
                except Exception:
                    pass
                raise
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/integracoes/twilio/upload")
    async def twilio_upload_media(request: Request, file: UploadFile = File(...)):
        ensure_twilio_table()
        slug = _tenant_slug(request)
        try:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Arquivo vazio.")

            cfg_row = None
            try:
                with get_conn_for_request(request) as conn:
                    cfg_row = _get_latest_config(conn, slug)
            except Exception:
                cfg_row = None
            base_for_media = _public_media_base(request, cfg_row)

            _, ext = os.path.splitext(str(file.filename or "").strip())
            ext_clean = str(ext or "").lower()
            if ext_clean and not ext_clean.startswith("."):
                ext_clean = "." + ext_clean
            if not ext_clean:
                ext_clean = ".bin"

            safe_slug = "".join(ch for ch in slug if ch.isalnum() or ch in ("-", "_")).strip() or "captar"
            out_dir = os.path.join(os.getcwd(), "static", "twilio", safe_slug)
            os.makedirs(out_dir, exist_ok=True)
            out_name = f"{os.urandom(8).hex()}{ext_clean}"
            out_path = os.path.join(out_dir, out_name)
            with open(out_path, "wb") as f:
                f.write(content)

            rel = f"/static/twilio/{safe_slug}/{out_name}"
            return {"ok": True, "url": f"{base_for_media}{rel}", "path": rel}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/integracoes/twilio/messaging-services")
    async def twilio_list_messaging_services(request: Request):
        ensure_twilio_table()
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                row = _get_latest_config(conn, slug)
            if not row:
                raise HTTPException(status_code=400, detail="Twilio não configurada.")
            enabled = bool(row[12]) if row[12] is not None else True
            if not enabled:
                raise HTTPException(status_code=400, detail="Twilio está desativada.")

            account_sid = str(row[2] or "").strip()
            auth_token = _decrypt_secret(str(row[3] or "").strip())
            api_key_sid = str(row[4] or "").strip()
            api_key_secret = _decrypt_secret(str(row[5] or "").strip())
            if not account_sid:
                raise HTTPException(status_code=400, detail="Twilio não configurada.")

            try:
                from twilio.rest import Client  # type: ignore
            except Exception:
                raise HTTPException(status_code=500, detail="Dependência 'twilio' não instalada no backend.")

            if api_key_sid and api_key_secret:
                client = Client(api_key_sid, api_key_secret, account_sid)
            else:
                if not auth_token:
                    raise HTTPException(status_code=400, detail="Twilio não configurada.")
                client = Client(account_sid, auth_token)

            services = client.messaging.services.list(limit=200)
            rows_out: list[dict[str, Any]] = []
            for s in services or []:
                rows_out.append(
                    {
                        "sid": getattr(s, "sid", None),
                        "friendly_name": getattr(s, "friendly_name", None),
                        "inbound_request_url": getattr(s, "inbound_request_url", None),
                        "status_callback": getattr(s, "status_callback", None),
                    }
                )
            return {"services": rows_out}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/integracoes/twilio/webhook/inbound")
    async def twilio_webhook_inbound(request: Request):
        ensure_twilio_table()
        slug = _tenant_slug(request)
        try:
            form = await request.form()
            params: dict[str, str] = {str(k): str(v) for k, v in dict(form).items()}
            with get_conn_for_request(request) as conn:
                row = _get_latest_config(conn, slug)
                if row:
                    validate_signature = bool(row[11]) if row[11] is not None else False
                    auth_token = _decrypt_secret(str(row[3] or "").strip())
                    if validate_signature and auth_token:
                        if not _validate_twilio_request(request, params, auth_token):
                            raise HTTPException(status_code=403, detail="Assinatura Twilio inválida.")

                tid = _tenant_id_from_request(conn, request)
                from_raw = str(params.get("From") or params.get("WaId") or "").strip()
                is_whatsapp = from_raw.lower().startswith("whatsapp:")
                incoming_digits = _digits_only(from_raw)
                incoming_text = str(params.get("Body") or "").strip()
                profile_name = str(params.get("ProfileName") or "").strip() or None
                received_dt = datetime.utcnow()
                inserted_in_id = None
                if not incoming_digits and not incoming_text:
                    return Response(content="<Response></Response>", media_type="text/xml")
                try:
                    cur = conn.cursor()
                    cur.execute(
                        f"""
                        INSERT INTO "{safe_schema}"."Disparos"
                        ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload","MessageId")
                        VALUES (%s,NULL,%s,%s,%s,%s,%s,NULL,%s,%s,%s::jsonb,%s)
                        RETURNING "IdDisparo"
                        """,
                        (
                            tid,
                            ("WHATSAPP" if is_whatsapp else "SMS"),
                            "IN",
                            incoming_digits,
                            profile_name,
                            incoming_text,
                            "RECEBIDO",
                            received_dt,
                            json.dumps({"provider": "twilio", "form": params}, ensure_ascii=False),
                            str(params.get("MessageSid") or params.get("SmsMessageSid") or params.get("SmsSid") or "").strip()
                            or None,
                        ),
                    )
                    row_in = cur.fetchone()
                    inserted_in_id = int(row_in[0]) if row_in else None
                    conn.commit()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

                resposta = _parse_sim_nao_response(incoming_text) if is_whatsapp else None
                if resposta in (1, 2):
                    try:
                        cur2 = conn.cursor()
                        cur2.execute(
                            f"""
                            SELECT d."IdDisparo", d."Numero", d."IdCampanha"
                            FROM "{safe_schema}"."Disparos" d
                            JOIN "{safe_schema}"."Campanhas" c
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
                        out_rows = cur2.fetchall() or []
                    except Exception:
                        out_rows = []

                    candidates = [
                        (out_id_raw, out_num, campanha_id)
                        for (out_id_raw, out_num, campanha_id) in out_rows
                        if _match_phone(out_num, incoming_digits)
                    ]

                    applied = False
                    for out_id_raw, out_num, campanha_id in candidates:
                        try:
                            cur3 = conn.cursor()
                            cur3.execute(
                                f"""
                                SELECT "AnexoJSON", "Positivos", "Negativos", "Enviados"
                                FROM "{safe_schema}"."Campanhas"
                                WHERE "IdCampanha" = %s AND "IdTenant" = %s
                                FOR UPDATE
                                """,
                                (int(campanha_id), int(tid)),
                            )
                            locked = cur3.fetchone()
                            if not locked:
                                try:
                                    conn.rollback()
                                except Exception:
                                    pass
                                continue

                            anexo_obj = _safe_json_obj(locked[0]) or {}
                            positivos = int(locked[1] or 0)
                            negativos = int(locked[2] or 0)
                            enviados = int(locked[3] or 0)
                            contacts = anexo_obj.get("contacts") if isinstance(anexo_obj, dict) else None
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
                                phone = c.get("whatsapp") or c.get("celular") or c.get("telefone") or c.get("phone")
                                if _match_phone(phone, incoming_digits):
                                    idx_match = i
                                    break

                            if idx_match < 0:
                                try:
                                    conn.rollback()
                                except Exception:
                                    pass
                                continue

                            cur_ct = contacts[idx_match]
                            existing = cur_ct.get("resposta") if isinstance(cur_ct, dict) else None
                            if existing in (1, 2, "1", "2"):
                                try:
                                    conn.rollback()
                                except Exception:
                                    pass
                                continue

                            cur_ct["resposta"] = resposta
                            cur_ct["respondido_em"] = (received_dt or datetime.utcnow()).isoformat()
                            contacts[idx_match] = cur_ct
                            anexo_obj["contacts"] = contacts

                            if resposta == 1:
                                positivos += 1
                            else:
                                negativos += 1

                            aguardando = max(0, enviados - (positivos + negativos))
                            cur3.execute(
                                f"""
                                UPDATE "{safe_schema}"."Campanhas"
                                SET "AnexoJSON" = %s::jsonb,
                                    "Positivos" = %s,
                                    "Negativos" = %s,
                                    "Aguardando" = %s,
                                    "Atualizacao" = NOW()
                                WHERE "IdCampanha" = %s AND "IdTenant" = %s
                                """,
                                (
                                    json.dumps(anexo_obj, ensure_ascii=False),
                                    positivos,
                                    negativos,
                                    aguardando,
                                    int(campanha_id),
                                    int(tid),
                                ),
                            )

                            if inserted_in_id:
                                cur3.execute(
                                    f"""
                                    UPDATE "{safe_schema}"."Disparos"
                                    SET "IdCampanha" = %s,
                                        "RespostaClassificacao" = %s,
                                        "IdDisparoRef" = %s
                                    WHERE "IdDisparo" = %s AND "IdTenant" = %s
                                    """,
                                    (
                                        int(campanha_id),
                                        ("SIM" if resposta == 1 else "NAO"),
                                        int(out_id_raw) if out_id_raw is not None else None,
                                        int(inserted_in_id),
                                        int(tid),
                                    ),
                                )
                            conn.commit()
                            applied = True
                            break
                        except Exception:
                            try:
                                conn.rollback()
                            except Exception:
                                pass
                    if not applied:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
            return Response(content="<Response></Response>", media_type="text/xml")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/integracoes/twilio/webhook/status")
    async def twilio_webhook_status(request: Request):
        ensure_twilio_table()
        slug = _tenant_slug(request)
        try:
            form = await request.form()
            params: dict[str, str] = {str(k): str(v) for k, v in dict(form).items()}
            with get_conn_for_request(request) as conn:
                row = _get_latest_config(conn, slug)
            if row:
                validate_signature = bool(row[11]) if row[11] is not None else False
                auth_token = _decrypt_secret(str(row[3] or "").strip())
                if validate_signature and auth_token:
                    if not _validate_twilio_request(request, params, auth_token):
                        raise HTTPException(status_code=403, detail="Assinatura Twilio inválida.")
            try:
                message_sid = str(params.get("MessageSid") or params.get("SmsSid") or "").strip()
                message_status = str(params.get("MessageStatus") or params.get("SmsStatus") or "").strip()
                if message_sid:
                    with get_conn_for_request(request) as conn_log:
                        cur = conn_log.cursor()
                        tid = _tenant_id_from_request(conn_log, request)
                        new_status = _map_twilio_status(message_status)
                        entregue_em = None
                        visualizado_em = None
                        if new_status == "ENTREGUE":
                            entregue_em = "NOW() AT TIME ZONE 'UTC'"
                        elif new_status == "VISUALIZADO":
                            entregue_em = "NOW() AT TIME ZONE 'UTC'"
                            visualizado_em = "NOW() AT TIME ZONE 'UTC'"
                        set_ent = f', "EntregueEm" = {entregue_em}' if entregue_em else ""
                        set_vis = f', "VisualizadoEm" = {visualizado_em}' if visualizado_em else ""
                        cur.execute(
                            f"""
                            UPDATE "{safe_schema}"."Disparos"
                            SET "Status" = %s
                                {set_ent}
                                {set_vis}
                                , "Payload" = COALESCE("Payload",'{{}}'::jsonb) || %s::jsonb
                            WHERE "IdTenant" = %s
                              AND "Direcao" = 'OUT'
                              AND COALESCE(NULLIF("MessageId",''), NULLIF("Payload"->>'sid','')) = %s
                            """,
                            (
                                new_status,
                                json.dumps({"twilio_status_callback": params}, ensure_ascii=False),
                                tid,
                                message_sid,
                            ),
                        )
                        conn_log.commit()
            except Exception:
                pass
            return {"ok": True}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
