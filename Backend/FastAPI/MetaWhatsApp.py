from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from pydantic import BaseModel
from typing import Optional, Any, Callable
import os
import json
import hmac
import hashlib
import aiohttp
from datetime import datetime, timedelta
import re
import unicodedata
from urllib.parse import urlencode


class MetaWhatsAppConfigIn(BaseModel):
    perfil: Optional[str] = None
    base_url: Optional[str] = None
    api_version: Optional[str] = None
    access_token: Optional[str] = None
    phone_number_id: Optional[str] = None
    whatsapp_phone: Optional[str] = None
    business_account_id: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    app_secret: Optional[str] = None
    app_id: Optional[str] = None
    configuration_id: Optional[str] = None
    partner_solution_id: Optional[str] = None
    redirect_uri: Optional[str] = None
    validate_signature: Optional[bool] = False
    enabled: Optional[bool] = True


class MetaWhatsAppSendIn(BaseModel):
    to: str
    body: Optional[str] = None
    media_id: Optional[str] = None
    media_url: Optional[str] = None
    media_type: Optional[str] = None
    text_position: Optional[str] = None
    template_name: Optional[str] = None
    template_lang: Optional[str] = None
    template_components: Optional[list[dict[str, Any]]] = None
    campanha_id: Optional[int] = None
    contato_nome: Optional[str] = None


class MetaTemplateCreateIn(BaseModel):
    template_name: str
    language: Optional[str] = None
    category: Optional[str] = None
    body_text: str


class MetaEmbeddedSignupExchangeIn(BaseModel):
    code: str
    redirect_uri: Optional[str] = None
    app_id: Optional[str] = None
    configuration_id: Optional[str] = None
    partner_solution_id: Optional[str] = None
    waba_id: Optional[str] = None
    phone_number_id: Optional[str] = None
    business_id: Optional[str] = None


class MetaWebhookOverrideWabaIn(BaseModel):
    waba_id: Optional[str] = None
    override_callback_uri: Optional[str] = None
    verify_token: Optional[str] = None


class MetaWebhookOverridePhoneIn(BaseModel):
    phone_number_id: Optional[str] = None
    override_callback_uri: Optional[str] = None
    verify_token: Optional[str] = None


class MetaPhoneResolveIn(BaseModel):
    waba_id: Optional[str] = None
    whatsapp_phone: Optional[str] = None
    phone_number_id: Optional[str] = None
    access_token: Optional[str] = None
    base_url: Optional[str] = None
    api_version: Optional[str] = None


def register_meta_whatsapp_routes(
    app: FastAPI,
    get_db_connection: Callable[..., Any],
    get_conn_for_request: Callable[[Request], Any],
    db_schema: str,
    mask_key: Callable[[str], str],
    tenant_id_from_header: Callable[[Request], int],
):
    safe_schema = str(db_schema or "captar").replace('"', '""')
    table_name = "MetaWhatsappAPI"
    legacy_table_name = "MetaAPI"
    prefix = "meta"

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

    def ensure_table(request: Optional[Request] = None):
        def _conn_factory():
            if request is not None:
                return get_conn_for_request(request)
            return get_db_connection()

        try:
            with _conn_factory() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{safe_schema}"."{table_name}" (
                        "Id" SERIAL PRIMARY KEY,
                        "IdTenant" INTEGER NOT NULL,
                        "TenantSlug" TEXT,
                        "BaseUrl" TEXT,
                        "ApiVersion" TEXT,
                        "PhoneNumberId" TEXT,
                        "WhatsappPhone" TEXT,
                        "BusinessAccountId" TEXT,
                        "Perfil" TEXT,
                        "AccessToken" TEXT,
                        "WebhookVerifyToken" TEXT,
                        "AppSecret" TEXT,
                        "ValidateSignature" BOOLEAN DEFAULT FALSE,
                        "Enabled" BOOLEAN DEFAULT TRUE,
                        "AppId" TEXT,
                        "ConfigurationId" TEXT,
                        "PartnerSolutionId" TEXT,
                        "RedirectUri" TEXT,
                        "CreatedAt" TIMESTAMP DEFAULT NOW(),
                        "UpdatedAt" TIMESTAMP DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    f'CREATE INDEX IF NOT EXISTS "idx_{table_name}_IdTenant" ON "{safe_schema}"."{table_name}"("IdTenant")'
                )
                cur.execute(
                    f'CREATE INDEX IF NOT EXISTS "idx_{table_name}_TenantSlug" ON "{safe_schema}"."{table_name}"("TenantSlug")'
                )
                conn.commit()
        except Exception:
            pass
        try:
            with _conn_factory() as conn:
                cur = conn.cursor()
                cur.execute(f'ALTER TABLE "{safe_schema}"."{table_name}" ADD COLUMN IF NOT EXISTS "AppId" TEXT')
                cur.execute(f'ALTER TABLE "{safe_schema}"."{table_name}" ADD COLUMN IF NOT EXISTS "ConfigurationId" TEXT')
                cur.execute(f'ALTER TABLE "{safe_schema}"."{table_name}" ADD COLUMN IF NOT EXISTS "PartnerSolutionId" TEXT')
                cur.execute(f'ALTER TABLE "{safe_schema}"."{table_name}" ADD COLUMN IF NOT EXISTS "RedirectUri" TEXT')
                cur.execute(f'ALTER TABLE "{safe_schema}"."{table_name}" ADD COLUMN IF NOT EXISTS "Perfil" TEXT')
                cur.execute(f'ALTER TABLE "{safe_schema}"."{table_name}" ADD COLUMN IF NOT EXISTS "WhatsappPhone" TEXT')
                conn.commit()
        except Exception:
            pass

        try:
            with _conn_factory() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{safe_schema}"."{legacy_table_name}" (
                        "Id" SERIAL PRIMARY KEY,
                        "IdTenant" INTEGER NOT NULL,
                        "TenantSlug" TEXT,
                        "BaseUrl" TEXT,
                        "ApiVersion" TEXT,
                        "PhoneNumberId" TEXT,
                        "WhatsappPhone" TEXT,
                        "BusinessAccountId" TEXT,
                        "Perfil" TEXT,
                        "AccessToken" TEXT,
                        "WebhookVerifyToken" TEXT,
                        "AppSecret" TEXT,
                        "ValidateSignature" BOOLEAN DEFAULT FALSE,
                        "Enabled" BOOLEAN DEFAULT TRUE,
                        "AppId" TEXT,
                        "ConfigurationId" TEXT,
                        "PartnerSolutionId" TEXT,
                        "RedirectUri" TEXT,
                        "CreatedAt" TIMESTAMP DEFAULT NOW(),
                        "UpdatedAt" TIMESTAMP DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    f'CREATE INDEX IF NOT EXISTS "idx_{legacy_table_name}_IdTenant" ON "{safe_schema}"."{legacy_table_name}"("IdTenant")'
                )
                cur.execute(
                    f'CREATE INDEX IF NOT EXISTS "idx_{legacy_table_name}_TenantSlug" ON "{safe_schema}"."{legacy_table_name}"("TenantSlug")'
                )
                conn.commit()
        except Exception:
            pass
        try:
            with _conn_factory() as conn:
                cur = conn.cursor()
                cur.execute(f'ALTER TABLE "{safe_schema}"."{legacy_table_name}" ADD COLUMN IF NOT EXISTS "AppId" TEXT')
                cur.execute(f'ALTER TABLE "{safe_schema}"."{legacy_table_name}" ADD COLUMN IF NOT EXISTS "ConfigurationId" TEXT')
                cur.execute(f'ALTER TABLE "{safe_schema}"."{legacy_table_name}" ADD COLUMN IF NOT EXISTS "PartnerSolutionId" TEXT')
                cur.execute(f'ALTER TABLE "{safe_schema}"."{legacy_table_name}" ADD COLUMN IF NOT EXISTS "RedirectUri" TEXT')
                cur.execute(f'ALTER TABLE "{safe_schema}"."{legacy_table_name}" ADD COLUMN IF NOT EXISTS "Perfil" TEXT')
                cur.execute(f'ALTER TABLE "{safe_schema}"."{legacy_table_name}" ADD COLUMN IF NOT EXISTS "WhatsappPhone" TEXT')
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

    def _digits_only(v: Any) -> str:
        try:
            return "".join([c for c in str(v or "") if c.isdigit()])
        except Exception:
            return ""

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
            s = v.strip()
            if not s:
                return None
            try:
                parsed = json.loads(s)
                return parsed if isinstance(parsed, dict) else None
            except Exception:
                return None
        try:
            if hasattr(v, "decode"):
                s = v.decode("utf-8").strip()
                parsed = json.loads(s) if s else None
                return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None
        return None

    def _tenant_id_from_slug(slug: str) -> int:
        s = str(slug or "").strip()
        if not s:
            return 1
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"""
                    SELECT "IdTenant"
                    FROM "{safe_schema}"."Tenant"
                    WHERE LOWER(COALESCE("Slug",'')) = LOWER(%s)
                    LIMIT 1
                    """,
                    (s,),
                )
                row = cur.fetchone()
                if row and row[0] is not None:
                    return int(row[0])
        except Exception:
            pass
        return 1

    def _tenant_id_for_request(request: Request) -> int:
        try:
            tid = int(tenant_id_from_header(request) or 1)
            if tid > 0:
                return tid
        except Exception:
            pass
        try:
            slug = _tenant_slug(request)
            return _tenant_id_from_slug(slug)
        except Exception:
            return 1

    def _default_country_code() -> str:
        cc = _digits_only(os.getenv("DEFAULT_COUNTRY_CODE", "") or "")
        return cc or "55"

    def _normalize_wa_id(to_raw: Any) -> str:
        s = str(to_raw or "").strip()
        if not s:
            return ""
        if s.lower().startswith("whatsapp:"):
            s = s.split(":", 1)[1].strip()
        d = _digits_only(s)
        if not d:
            return ""
        cc = _default_country_code()
        if len(d) <= 11 and not d.startswith(cc):
            d = f"{cc}{d}"
        return d

    def _get_latest_config_from(conn, *, tname: str, slug: Optional[str], tid: Optional[int]):
        cur = conn.cursor()
        if tid is not None:
            cur.execute(
                f"""
                SELECT
                    "Id","IdTenant","TenantSlug","BaseUrl","ApiVersion",
                    "AccessToken","PhoneNumberId","BusinessAccountId","WebhookVerifyToken","AppSecret",
                    "ValidateSignature","Enabled","AppId","ConfigurationId","PartnerSolutionId","RedirectUri"
                    ,"Perfil","WhatsappPhone"
                FROM "{safe_schema}"."{tname}"
                WHERE "IdTenant"=%s
                ORDER BY "Id" DESC
                LIMIT 1
                """,
                (int(tid),),
            )
        else:
            cur.execute(
                f"""
                SELECT
                    "Id","IdTenant","TenantSlug","BaseUrl","ApiVersion",
                    "AccessToken","PhoneNumberId","BusinessAccountId","WebhookVerifyToken","AppSecret",
                    "ValidateSignature","Enabled","AppId","ConfigurationId","PartnerSolutionId","RedirectUri"
                    ,"Perfil","WhatsappPhone"
                FROM "{safe_schema}"."{tname}"
                WHERE LOWER(COALESCE("TenantSlug",'')) = LOWER(%s)
                ORDER BY "Id" DESC
                LIMIT 1
                """,
                (str(slug or "").strip(),),
            )
        return cur.fetchone()

    def _get_latest_config(conn, *, slug: Optional[str], tid: Optional[int]):
        row = None
        try:
            row = _get_latest_config_from(conn, tname=table_name, slug=slug, tid=tid)
        except Exception:
            row = None
        if row:
            return row
        try:
            return _get_latest_config_from(conn, tname=legacy_table_name, slug=slug, tid=tid)
        except Exception:
            return None

    def _get_config_by_id_from(conn, *, tname: str, config_id: int):
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT
                "Id","IdTenant","TenantSlug","BaseUrl","ApiVersion",
                "AccessToken","PhoneNumberId","BusinessAccountId","WebhookVerifyToken","AppSecret",
                "ValidateSignature","Enabled","AppId","ConfigurationId","PartnerSolutionId","RedirectUri"
                ,"Perfil","WhatsappPhone"
            FROM "{safe_schema}"."{tname}"
            WHERE "Id"=%s
            LIMIT 1
            """,
            (int(config_id),),
        )
        return cur.fetchone()

    def _get_config_by_id(conn, config_id: int):
        row = None
        try:
            row = _get_config_by_id_from(conn, tname=table_name, config_id=config_id)
        except Exception:
            row = None
        if row:
            return row
        try:
            return _get_config_by_id_from(conn, tname=legacy_table_name, config_id=config_id)
        except Exception:
            return None

    def _update_config_by_id(
        conn,
        *,
        config_id: int,
        tid: int,
        slug: str,
        base_url: Optional[str],
        api_version: Optional[str],
        phone_number_id: Optional[str],
        whatsapp_phone: Optional[str],
        business_account_id: Optional[str],
        perfil: Optional[str],
        access_token: Optional[str],
        webhook_verify_token: Optional[str],
        app_secret: Optional[str],
        validate_signature: bool,
        enabled: bool,
        app_id: Optional[str],
        configuration_id: Optional[str],
        partner_solution_id: Optional[str],
        redirect_uri: Optional[str],
    ) -> int:
        for tname in (table_name, legacy_table_name):
            try:
                cur = conn.cursor()
                cur.execute(
                    f"""
                    UPDATE "{safe_schema}"."{tname}"
                    SET
                      "IdTenant"=%s,
                      "TenantSlug"=%s,
                      "BaseUrl"=%s,
                      "ApiVersion"=%s,
                      "PhoneNumberId"=%s,
                      "WhatsappPhone"=%s,
                      "BusinessAccountId"=%s,
                      "Perfil"=%s,
                      "AccessToken"=%s,
                      "WebhookVerifyToken"=%s,
                      "AppSecret"=%s,
                      "ValidateSignature"=%s,
                      "Enabled"=%s,
                      "AppId"=%s,
                      "ConfigurationId"=%s,
                      "PartnerSolutionId"=%s,
                      "RedirectUri"=%s,
                      "UpdatedAt"=NOW()
                    WHERE "Id"=%s
                    RETURNING "Id"
                    """,
                    (
                        int(tid),
                        slug,
                        base_url,
                        api_version,
                        phone_number_id,
                        whatsapp_phone,
                        business_account_id,
                        perfil,
                        _encrypt_secret(access_token) if access_token else None,
                        _encrypt_secret(webhook_verify_token) if webhook_verify_token else None,
                        _encrypt_secret(app_secret) if app_secret else None,
                        bool(validate_signature),
                        bool(enabled),
                        app_id,
                        configuration_id,
                        partner_solution_id,
                        redirect_uri,
                        int(config_id),
                    ),
                )
                row = cur.fetchone()
                if row and row[0] is not None:
                    try:
                        conn.commit()
                    except Exception:
                        pass
                    return int(row[0])
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
                continue
        return 0

    def _parse_config_id(request: Request) -> Optional[int]:
        try:
            raw = request.query_params.get("config_id") or request.query_params.get("configId") or ""
            raw = str(raw or "").strip()
            if not raw:
                return None
            v = int(raw)
            return v if v > 0 else None
        except Exception:
            return None

    def _assert_cfg_matches(*, cfg_row: Any, slug: Optional[str], tid: Optional[int]):
        if not cfg_row:
            return
        if tid is not None:
            try:
                if cfg_row[1] is not None and int(cfg_row[1]) != int(tid):
                    raise HTTPException(status_code=404, detail="Config Meta não encontrada.")
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=404, detail="Config Meta não encontrada.")
        try:
            s = str(slug or "").strip().lower()
            rs = str(cfg_row[2] or "").strip().lower()
            if s and rs and s != rs:
                raise HTTPException(status_code=404, detail="Config Meta não encontrada.")
        except HTTPException:
            raise
        except Exception:
            pass

    def _graph_base(cfg_row: Any) -> str:
        raw = ""
        if cfg_row and len(cfg_row) > 3:
            raw = str(cfg_row[3] or "").strip()
        base = raw or "https://graph.facebook.com"
        return base.rstrip("/")

    def _graph_version(cfg_row: Any) -> str:
        raw = ""
        if cfg_row and len(cfg_row) > 4:
            raw = str(cfg_row[4] or "").strip()
        v = raw or str(os.getenv("META_GRAPH_API_VERSION") or "").strip() or "v21.0"
        v = v.strip()
        if not v.startswith("v"):
            v = f"v{v}"
        return v

    def _cfg_enabled(cfg_row: Any) -> bool:
        if cfg_row and len(cfg_row) > 11 and cfg_row[11] is not None:
            return bool(cfg_row[11])
        return True

    def _cfg_access_token(cfg_row: Any) -> str:
        raw = str(cfg_row[5] or "").strip() if cfg_row and len(cfg_row) > 5 else ""
        token = _decrypt_secret(raw)
        if not token:
            token = str(os.getenv("META_WHATSAPP_ACCESS_TOKEN") or "").strip()
        return token

    def _cfg_phone_number_id(cfg_row: Any) -> str:
        raw = str(cfg_row[6] or "").strip() if cfg_row and len(cfg_row) > 6 else ""
        if not raw:
            raw = str(os.getenv("META_WHATSAPP_PHONE_NUMBER_ID") or "").strip()
        return raw

    def _cfg_whatsapp_phone(cfg_row: Any) -> str:
        return str(cfg_row[17] or "").strip() if cfg_row and len(cfg_row) > 17 else ""

    def _cfg_business_account_id(cfg_row: Any) -> str:
        return str(cfg_row[7] or "").strip() if cfg_row and len(cfg_row) > 7 else ""

    def _cfg_perfil(cfg_row: Any) -> str:
        return str(cfg_row[16] or "").strip() if cfg_row and len(cfg_row) > 16 else ""

    def _cfg_verify_token(cfg_row: Any) -> str:
        raw = str(cfg_row[8] or "").strip() if cfg_row and len(cfg_row) > 8 else ""
        token = _decrypt_secret(raw)
        if not token:
            token = str(os.getenv("META_WHATSAPP_WEBHOOK_VERIFY_TOKEN") or "").strip()
        return token

    def _cfg_app_secret(cfg_row: Any) -> str:
        raw = str(cfg_row[9] or "").strip() if cfg_row and len(cfg_row) > 9 else ""
        secret = _decrypt_secret(raw)
        if not secret:
            secret = str(os.getenv("META_APP_SECRET") or "").strip()
        return secret

    def _cfg_validate_signature(cfg_row: Any) -> bool:
        if cfg_row and len(cfg_row) > 10 and cfg_row[10] is not None:
            return bool(cfg_row[10])
        raw = str(os.getenv("META_VALIDATE_WEBHOOK_SIGNATURE", "0") or "0").strip().lower()
        return raw not in ("0", "false", "no", "off")

    def _cfg_app_id(cfg_row: Any) -> str:
        raw = str(cfg_row[12] or "").strip() if cfg_row and len(cfg_row) > 12 else ""
        if not raw:
            raw = str(os.getenv("META_APP_ID") or os.getenv("META_WHATSAPP_APP_ID") or "").strip()
        return raw

    def _cfg_configuration_id(cfg_row: Any) -> str:
        return str(cfg_row[13] or "").strip() if cfg_row and len(cfg_row) > 13 else ""

    def _cfg_partner_solution_id(cfg_row: Any) -> str:
        return str(cfg_row[14] or "").strip() if cfg_row and len(cfg_row) > 14 else ""

    def _cfg_redirect_uri(cfg_row: Any) -> str:
        raw = str(cfg_row[15] or "").strip() if cfg_row and len(cfg_row) > 15 else ""
        if not raw:
            raw = str(os.getenv("META_OAUTH_REDIRECT_URI") or "").strip()
        return raw

    async def _oauth_exchange_code_for_token(
        *,
        base: str,
        ver: str,
        app_id: str,
        app_secret: str,
        code: str,
        redirect_uri: Optional[str],
        timeout: int = 40,
    ) -> dict[str, Any]:
        url = f"{base}/{ver}/oauth/access_token"
        candidates: list[dict[str, str]] = []
        if redirect_uri is not None:
            candidates.append(
                {
                    "client_id": app_id,
                    "client_secret": app_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                }
            )
        candidates.append({"client_id": app_id, "client_secret": app_secret, "code": code})
        if redirect_uri is None:
            candidates.append({"client_id": app_id, "client_secret": app_secret, "code": code, "redirect_uri": ""})
        last_text = ""
        async with aiohttp.ClientSession() as session:
            for params in candidates:
                qs = urlencode({k: v for k, v in params.items() if v is not None})
                try:
                    async with session.get(f"{url}?{qs}", timeout=timeout) as resp:
                        last_text = await resp.text()
                        if resp.status in (200, 201):
                            try:
                                return json.loads(last_text or "{}")
                            except Exception:
                                return {"raw": last_text}
                        try:
                            j = json.loads(last_text or "")
                            msg = ""
                            if isinstance(j, dict) and isinstance(j.get("error"), dict):
                                msg = str(j["error"].get("message") or "").strip()
                            if "redirect_uri" in msg.lower():
                                continue
                        except Exception:
                            pass
                except Exception:
                    continue
        raise HTTPException(status_code=400, detail=f"Falha ao trocar code por token. {last_text}".strip())

    async def _oauth_debug_token(
        *,
        base: str,
        ver: str,
        app_id: str,
        app_secret: str,
        input_token: str,
        timeout: int = 40,
    ) -> dict[str, Any]:
        url = f"{base}/{ver}/debug_token"
        qs = urlencode({"input_token": input_token, "access_token": f"{app_id}|{app_secret}"})
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}?{qs}", timeout=timeout) as resp:
                text = await resp.text()
                if resp.status not in (200, 201):
                    raise HTTPException(status_code=resp.status if resp.status < 500 else 502, detail=text)
                try:
                    return json.loads(text or "{}")
                except Exception:
                    return {"raw": text}

    async def _graph_json(
        *,
        method: str,
        url: str,
        token: str,
        json_payload: Optional[dict[str, Any]] = None,
        timeout: int = 40,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"}
        if json_payload is not None:
            headers["Content-Type"] = "application/json"
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method.upper(),
                url,
                headers=headers,
                json=json_payload,
                timeout=timeout,
            ) as resp:
                text = await resp.text()
                if resp.status not in (200, 201):
                    err_msg = ""
                    try:
                        j = json.loads(text or "")
                        if isinstance(j, dict):
                            err = j.get("error")
                            if isinstance(err, dict):
                                err_msg = str(err.get("message") or "").strip()
                    except Exception:
                        err_msg = ""
                    if resp.status in (401, 403):
                        detail = "Meta Cloud API: access token inválido ou sem permissão."
                        if err_msg:
                            detail = f"{detail} {err_msg}"
                        raise HTTPException(status_code=400, detail=detail)
                    raise HTTPException(status_code=resp.status if resp.status < 500 else 502, detail=text)
                try:
                    return await resp.json()
                except Exception:
                    return {"raw": text}

    async def _graph_upload(
        *,
        url: str,
        token: str,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        timeout: int = 60,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {token}"}
        form = aiohttp.FormData()
        form.add_field("messaging_product", "whatsapp")
        form.add_field("file", file_bytes, filename=filename, content_type=content_type)
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=form, timeout=timeout) as resp:
                text = await resp.text()
                if resp.status not in (200, 201):
                    err_msg = ""
                    try:
                        j = json.loads(text or "")
                        if isinstance(j, dict):
                            err = j.get("error")
                            if isinstance(err, dict):
                                err_msg = str(err.get("message") or "").strip()
                    except Exception:
                        err_msg = ""
                    if resp.status in (401, 403):
                        detail = "Meta Cloud API: access token inválido ou sem permissão."
                        if err_msg:
                            detail = f"{detail} {err_msg}"
                        raise HTTPException(status_code=400, detail=detail)
                    raise HTTPException(status_code=resp.status if resp.status < 500 else 502, detail=text)
                try:
                    return await resp.json()
                except Exception:
                    return {"raw": text}

    def _insert_disparo_log(
        request: Request,
        *,
        campanha_id: Optional[int],
        numero: str,
        nome: str,
        mensagem: str,
        imagem: Optional[str],
        status: str,
        payload: Any,
        message_id: Optional[str],
    ) -> None:
        try:
            with get_conn_for_request(request) as conn:
                cur = conn.cursor()
                tid = int(tenant_id_from_header(request) or 1)
                cur.execute(
                    f"""
                    INSERT INTO "{safe_schema}"."Disparos"
                    ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload","MessageId","EvolutionInstance")
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW() AT TIME ZONE 'UTC',%s::jsonb,%s,%s)
                    """,
                    (
                        tid,
                        campanha_id,
                        "WHATSAPP",
                        "OUT",
                        numero,
                        nome,
                        mensagem,
                        imagem,
                        status,
                        json.dumps(payload, ensure_ascii=False) if payload is not None else None,
                        message_id,
                        "META",
                    ),
                )
                try:
                    conn.commit()
                except Exception:
                    pass
        except Exception:
            pass

    def _verify_webhook_signature(request: Request, raw_body: bytes, secret: str) -> bool:
        sig = str(request.headers.get("X-Hub-Signature-256") or "").strip()
        if not sig or not sig.startswith("sha256="):
            return False
        want = sig.split("=", 1)[1].strip()
        mac = hmac.new(secret.encode("utf-8"), msg=raw_body, digestmod=hashlib.sha256).hexdigest()
        return hmac.compare_digest(mac, want)

    @app.get(f"/api/integracoes/{prefix}/config")
    async def meta_get_config(request: Request):
        ensure_table(request)
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                tid = int(tenant_id_from_header(request) or 1)
                cfg_id = _parse_config_id(request)
                if cfg_id:
                    row = _get_config_by_id(conn, cfg_id)
                    _assert_cfg_matches(cfg_row=row, slug=slug, tid=tid)
                else:
                    row = _get_latest_config(conn, slug=slug, tid=tid)
                    if not row:
                        row = _get_latest_config(conn, slug=slug, tid=None)
            if not row:
                return {
                    "tenant_slug": slug,
                    "perfil": "",
                    "base_url": "https://graph.facebook.com",
                    "api_version": "v21.0",
                    "phone_number_id": "",
                    "whatsapp_phone": "",
                    "business_account_id": "",
                    "has_access_token": False,
                    "access_token_masked": "",
                    "has_webhook_verify_token": False,
                    "webhook_verify_token_masked": "",
                    "has_app_secret": False,
                    "app_secret_masked": "",
                    "validate_signature": False,
                    "enabled": True,
                }
            access_plain = _cfg_access_token(row)
            verify_plain = _cfg_verify_token(row)
            app_secret_plain = _cfg_app_secret(row)
            return {
                "tenant_slug": slug,
                "id": int(row[0]),
                "perfil": _cfg_perfil(row),
                "base_url": _graph_base(row),
                "api_version": _graph_version(row),
                "phone_number_id": _cfg_phone_number_id(row),
                "whatsapp_phone": _cfg_whatsapp_phone(row),
                "business_account_id": _cfg_business_account_id(row),
                "app_id": _cfg_app_id(row),
                "configuration_id": _cfg_configuration_id(row),
                "partner_solution_id": _cfg_partner_solution_id(row),
                "redirect_uri": _cfg_redirect_uri(row),
                "has_access_token": bool(access_plain),
                "access_token_masked": mask_key(access_plain) if access_plain else "",
                "has_webhook_verify_token": bool(verify_plain),
                "webhook_verify_token_masked": mask_key(verify_plain) if verify_plain else "",
                "has_app_secret": bool(app_secret_plain),
                "app_secret_masked": mask_key(app_secret_plain) if app_secret_plain else "",
                "validate_signature": _cfg_validate_signature(row),
                "enabled": _cfg_enabled(row),
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get(f"/api/integracoes/{prefix}/configs")
    async def meta_list_configs(request: Request):
        ensure_table(request)
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                tid = int(tenant_id_from_header(request) or 1)
                cur = conn.cursor()
                cur.execute(
                    f"""
                    SELECT
                      "Id","Perfil","WhatsappPhone","PhoneNumberId","BusinessAccountId",
                      "Enabled","ValidateSignature","BaseUrl","ApiVersion",
                      "AppId","ConfigurationId","PartnerSolutionId","RedirectUri"
                    FROM "{safe_schema}"."{table_name}"
                    WHERE "IdTenant"=%s AND LOWER(COALESCE("TenantSlug",'')) = LOWER(%s)
                    ORDER BY COALESCE("Perfil",'') ASC, "Id" DESC
                    """,
                    (tid, slug),
                )
                rows = cur.fetchall() or []
            out: list[dict[str, Any]] = []
            for r in rows:
                out.append(
                    {
                        "id": int(r[0]),
                        "perfil": str(r[1] or "").strip(),
                        "whatsapp_phone": str(r[2] or "").strip(),
                        "phone_number_id": str(r[3] or "").strip(),
                        "business_account_id": str(r[4] or "").strip(),
                        "enabled": bool(r[5]) if r[5] is not None else True,
                        "validate_signature": bool(r[6]) if r[6] is not None else False,
                        "base_url": str(r[7] or "").strip(),
                        "api_version": str(r[8] or "").strip(),
                        "app_id": str(r[9] or "").strip(),
                        "configuration_id": str(r[10] or "").strip(),
                        "partner_solution_id": str(r[11] or "").strip(),
                        "redirect_uri": str(r[12] or "").strip(),
                    }
                )
            return {"ok": True, "rows": out}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post(f"/api/integracoes/{prefix}/config")
    async def meta_save_config(payload: MetaWhatsAppConfigIn, request: Request):
        ensure_table(request)
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                tid = int(tenant_id_from_header(request) or 1)
                cfg_id = _parse_config_id(request)
                if cfg_id:
                    prev = _get_config_by_id(conn, cfg_id)
                    _assert_cfg_matches(cfg_row=prev, slug=slug, tid=tid)
                else:
                    prev = _get_latest_config(conn, slug=slug, tid=tid)
                base_url = str(payload.base_url or "").strip() or (_graph_base(prev) if prev else "https://graph.facebook.com")
                api_version = str(payload.api_version or "").strip() or (_graph_version(prev) if prev else "v21.0")
                phone_number_id = str(payload.phone_number_id or "").strip() or (_cfg_phone_number_id(prev) if prev else "")
                whatsapp_phone = str(payload.whatsapp_phone or "").strip() or (_cfg_whatsapp_phone(prev) if prev else "")
                business_account_id = str(payload.business_account_id or "").strip() or (_cfg_business_account_id(prev) if prev else "")
                perfil = str(payload.perfil or "").strip() or (_cfg_perfil(prev) if prev else "")

                access_token = str(payload.access_token or "").strip()
                if not access_token and prev:
                    access_token = _cfg_access_token(prev)

                webhook_verify_token = str(payload.webhook_verify_token or "").strip()
                if not webhook_verify_token and prev:
                    webhook_verify_token = _cfg_verify_token(prev)

                app_secret = str(payload.app_secret or "").strip()
                if not app_secret and prev:
                    app_secret = _cfg_app_secret(prev)

                app_id = str(payload.app_id or "").strip()
                if not app_id and prev:
                    app_id = _cfg_app_id(prev)

                configuration_id = str(payload.configuration_id or "").strip()
                if not configuration_id and prev:
                    configuration_id = _cfg_configuration_id(prev)

                partner_solution_id = str(payload.partner_solution_id or "").strip()
                if not partner_solution_id and prev:
                    partner_solution_id = _cfg_partner_solution_id(prev)

                redirect_uri = str(payload.redirect_uri or "").strip()
                if not redirect_uri and prev:
                    redirect_uri = _cfg_redirect_uri(prev)

                validate_signature = (
                    bool(payload.validate_signature)
                    if payload.validate_signature is not None
                    else (_cfg_validate_signature(prev) if prev else False)
                )
                enabled = payload.enabled if payload.enabled is not None else (_cfg_enabled(prev) if prev else True)

                token_for_sync = str(access_token or "").strip()
                if (whatsapp_phone and not phone_number_id) or (phone_number_id and not whatsapp_phone) or (whatsapp_phone and phone_number_id):
                    if not token_for_sync:
                        raise HTTPException(status_code=400, detail="Informe Access Token para resolver/validar WhatsApp Phone e PhoneID.")
                if whatsapp_phone and not phone_number_id:
                    if not business_account_id:
                        raise HTTPException(status_code=400, detail="Informe WABA ID para resolver PhoneID a partir do WhatsApp Phone.")
                    base = str(base_url or "https://graph.facebook.com").rstrip("/")
                    ver = str(api_version or "v21.0").strip()
                    if not ver.startswith("v"):
                        ver = f"v{ver}"
                    url = f"{base}/{ver}/{business_account_id}/phone_numbers?fields=id,display_phone_number"
                    data = await _graph_json(method="GET", url=url, token=token_for_sync, timeout=40)
                    items = (data.get("data") if isinstance(data, dict) else None) or []
                    found_id = ""
                    found_display = ""
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        pid = str(it.get("id") or "").strip()
                        disp = str(it.get("display_phone_number") or "").strip()
                        if pid and disp and _match_phone(disp, whatsapp_phone):
                            found_id = pid
                            found_display = disp
                            break
                    if not found_id:
                        raise HTTPException(status_code=400, detail="Não foi possível resolver PhoneID para esse WhatsApp Phone no WABA informado.")
                    phone_number_id = found_id
                    whatsapp_phone = found_display or whatsapp_phone
                elif phone_number_id and not whatsapp_phone:
                    base = str(base_url or "https://graph.facebook.com").rstrip("/")
                    ver = str(api_version or "v21.0").strip()
                    if not ver.startswith("v"):
                        ver = f"v{ver}"
                    url = f"{base}/{ver}/{phone_number_id}?fields=display_phone_number"
                    data = await _graph_json(method="GET", url=url, token=token_for_sync, timeout=40)
                    disp = str((data.get("display_phone_number") if isinstance(data, dict) else "") or "").strip()
                    if not disp:
                        raise HTTPException(status_code=400, detail="Não foi possível resolver WhatsApp Phone a partir do PhoneID.")
                    whatsapp_phone = disp
                elif phone_number_id and whatsapp_phone:
                    base = str(base_url or "https://graph.facebook.com").rstrip("/")
                    ver = str(api_version or "v21.0").strip()
                    if not ver.startswith("v"):
                        ver = f"v{ver}"
                    url = f"{base}/{ver}/{phone_number_id}?fields=display_phone_number"
                    data = await _graph_json(method="GET", url=url, token=token_for_sync, timeout=40)
                    disp = str((data.get("display_phone_number") if isinstance(data, dict) else "") or "").strip()
                    if disp and not _match_phone(disp, whatsapp_phone):
                        raise HTTPException(status_code=400, detail="WhatsApp Phone não corresponde ao PhoneID informado.")
                    if disp:
                        whatsapp_phone = disp

                if cfg_id:
                    updated_id = _update_config_by_id(
                        conn,
                        config_id=cfg_id,
                        tid=tid,
                        slug=slug,
                        base_url=base_url or None,
                        api_version=api_version or None,
                        phone_number_id=phone_number_id or None,
                        whatsapp_phone=whatsapp_phone or None,
                        business_account_id=business_account_id or None,
                        perfil=perfil or None,
                        access_token=access_token or None,
                        webhook_verify_token=webhook_verify_token or None,
                        app_secret=app_secret or None,
                        validate_signature=bool(validate_signature),
                        enabled=bool(enabled),
                        app_id=app_id or None,
                        configuration_id=configuration_id or None,
                        partner_solution_id=partner_solution_id or None,
                        redirect_uri=redirect_uri or None,
                    )
                    if updated_id:
                        return {"id": updated_id, "saved": True}

                cur = conn.cursor()
                cur.execute(
                    f"""
                    INSERT INTO "{safe_schema}"."{table_name}" (
                        "IdTenant","TenantSlug","BaseUrl","ApiVersion","PhoneNumberId","WhatsappPhone","BusinessAccountId","Perfil",
                        "AccessToken","WebhookVerifyToken","AppSecret","ValidateSignature","Enabled",
                        "AppId","ConfigurationId","PartnerSolutionId","RedirectUri",
                        "CreatedAt","UpdatedAt"
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
                    RETURNING "Id"
                    """,
                    (
                        tid,
                        slug,
                        base_url or None,
                        api_version or None,
                        phone_number_id or None,
                        whatsapp_phone or None,
                        business_account_id or None,
                        perfil or None,
                        _encrypt_secret(access_token) if access_token else None,
                        _encrypt_secret(webhook_verify_token) if webhook_verify_token else None,
                        _encrypt_secret(app_secret) if app_secret else None,
                        bool(validate_signature),
                        bool(enabled),
                        app_id or None,
                        configuration_id or None,
                        partner_solution_id or None,
                        redirect_uri or None,
                    ),
                )
                new_id = int(cur.fetchone()[0])
                try:
                    conn.commit()
                except Exception:
                    pass
                return {"id": new_id, "saved": True}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete(f"/api/integracoes/{prefix}/config")
    async def meta_delete_config(request: Request):
        ensure_table(request)
        slug = _tenant_slug(request)
        try:
            cfg_id = _parse_config_id(request)
            if not cfg_id:
                raise HTTPException(status_code=400, detail="Informe config_id.")
            with get_conn_for_request(request) as conn:
                tid = int(tenant_id_from_header(request) or 1)
                row = _get_config_by_id(conn, cfg_id)
                _assert_cfg_matches(cfg_row=row, slug=slug, tid=tid)
                if not row:
                    raise HTTPException(status_code=404, detail="Config Meta não encontrada.")
                deleted = 0
                for tname in (table_name, legacy_table_name):
                    try:
                        cur = conn.cursor()
                        cur.execute(f'DELETE FROM "{safe_schema}"."{tname}" WHERE "Id"=%s', (int(cfg_id),))
                        if cur.rowcount:
                            deleted += int(cur.rowcount)
                    except Exception:
                        continue
                try:
                    conn.commit()
                except Exception:
                    pass
            return {"ok": True, "deleted": deleted}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post(f"/api/integracoes/{prefix}/phone/resolve")
    async def meta_resolve_phone(payload: MetaPhoneResolveIn, request: Request):
        ensure_table(request)
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                tid = int(tenant_id_from_header(request) or 1)
                cfg_id = _parse_config_id(request)
                if cfg_id:
                    row = _get_config_by_id(conn, cfg_id)
                    _assert_cfg_matches(cfg_row=row, slug=slug, tid=tid)
                    if not row:
                        raise HTTPException(status_code=404, detail="Config Meta não encontrada.")
                else:
                    row = _get_latest_config(conn, slug=slug, tid=tid)
            token = str(payload.access_token or "").strip() or _cfg_access_token(row)
            if not token:
                raise HTTPException(status_code=400, detail="Informe Access Token para resolver PhoneID/WhatsApp Phone.")
            base = str(payload.base_url or "").strip() or _graph_base(row)
            ver = str(payload.api_version or "").strip() or _graph_version(row)
            if not ver.startswith("v"):
                ver = f"v{ver}"
            base = base.rstrip("/")

            waba_id = str(payload.waba_id or "").strip() or _cfg_business_account_id(row)
            in_phone_id = str(payload.phone_number_id or "").strip()
            in_wa = str(payload.whatsapp_phone or "").strip()

            if in_phone_id and in_wa:
                url = f"{base}/{ver}/{in_phone_id}?fields=display_phone_number"
                data = await _graph_json(method="GET", url=url, token=token, timeout=40)
                disp = str((data.get("display_phone_number") if isinstance(data, dict) else "") or "").strip()
                if disp and not _match_phone(disp, in_wa):
                    raise HTTPException(status_code=400, detail="WhatsApp Phone não corresponde ao PhoneID informado.")
                return {"ok": True, "phone_number_id": in_phone_id, "whatsapp_phone": disp or in_wa}

            if in_phone_id:
                url = f"{base}/{ver}/{in_phone_id}?fields=display_phone_number"
                data = await _graph_json(method="GET", url=url, token=token, timeout=40)
                disp = str((data.get("display_phone_number") if isinstance(data, dict) else "") or "").strip()
                if not disp:
                    raise HTTPException(status_code=400, detail="Não foi possível resolver WhatsApp Phone a partir do PhoneID.")
                return {"ok": True, "phone_number_id": in_phone_id, "whatsapp_phone": disp}

            if in_wa:
                if not waba_id:
                    raise HTTPException(status_code=400, detail="Informe WABA ID para resolver PhoneID a partir do WhatsApp Phone.")
                url = f"{base}/{ver}/{waba_id}/phone_numbers?fields=id,display_phone_number"
                data = await _graph_json(method="GET", url=url, token=token, timeout=40)
                items = (data.get("data") if isinstance(data, dict) else None) or []
                found_id = ""
                found_display = ""
                for it in items:
                    if not isinstance(it, dict):
                        continue
                    pid = str(it.get("id") or "").strip()
                    disp = str(it.get("display_phone_number") or "").strip()
                    if pid and disp and _match_phone(disp, in_wa):
                        found_id = pid
                        found_display = disp
                        break
                if not found_id:
                    raise HTTPException(status_code=400, detail="Não foi possível resolver PhoneID para esse WhatsApp Phone no WABA informado.")
                return {"ok": True, "phone_number_id": found_id, "whatsapp_phone": found_display or in_wa}

            raise HTTPException(status_code=400, detail="Informe whatsapp_phone ou phone_number_id.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get(f"/api/integracoes/{prefix}/test")
    async def meta_test(request: Request):
        ensure_table(request)
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                tid = int(tenant_id_from_header(request) or 1)
                cfg_id = _parse_config_id(request)
                if cfg_id:
                    row = _get_config_by_id(conn, cfg_id)
                    _assert_cfg_matches(cfg_row=row, slug=slug, tid=tid)
                else:
                    row = _get_latest_config(conn, slug=slug, tid=tid)
            
            # Prioritize query params for testing credentials without saving
            qp = request.query_params
            token = str(qp.get("access_token") or "").strip() or _cfg_access_token(row)
            phone_number_id = str(qp.get("phone_number_id") or "").strip() or _cfg_phone_number_id(row)
            
            if not token or not phone_number_id:
                raise HTTPException(status_code=400, detail="Informe Access Token e Phone Number ID.")
            
            base = str(qp.get("base_url") or "").strip() or _graph_base(row)
            ver = str(qp.get("api_version") or "").strip() or _graph_version(row)
            if not ver.startswith("v"):
                ver = f"v{ver}"
            base = base.rstrip("/")
            
            url = f"{base}/{ver}/{phone_number_id}?fields=display_phone_number,verified_name,code_verification_status,quality_rating"
            data = await _graph_json(method="GET", url=url, token=token, timeout=30)
            return {"ok": True, "status_code": 200, "phone_number": data}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post(f"/api/integracoes/{prefix}/upload")
    async def meta_upload(request: Request, file: UploadFile = File(...)):
        ensure_table(request)
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                tid = int(tenant_id_from_header(request) or 1)
                cfg_id = _parse_config_id(request)
                if cfg_id:
                    row = _get_config_by_id(conn, cfg_id)
                    _assert_cfg_matches(cfg_row=row, slug=slug, tid=tid)
                else:
                    row = _get_latest_config(conn, slug=slug, tid=tid)
            if not row:
                raise HTTPException(status_code=400, detail="Meta WhatsApp não configurada.")
            if not _cfg_enabled(row):
                raise HTTPException(status_code=400, detail="Meta WhatsApp está desativada.")
            token = _cfg_access_token(row)
            phone_number_id = _cfg_phone_number_id(row)
            if not token or not phone_number_id:
                raise HTTPException(status_code=400, detail="Informe Access Token e Phone Number ID.")
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Arquivo vazio.")
            base = _graph_base(row)
            ver = _graph_version(row)
            url = f"{base}/{ver}/{phone_number_id}/media"
            res = await _graph_upload(
                url=url,
                token=token,
                file_bytes=content,
                filename=str(file.filename or "upload.bin"),
                content_type=str(file.content_type or "application/octet-stream"),
            )
            media_id = str(res.get("id") or "").strip()
            if not media_id:
                raise HTTPException(status_code=502, detail=str(res))
            return {"ok": True, "id": media_id}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post(f"/api/integracoes/{prefix}/send")
    async def meta_send(payload: MetaWhatsAppSendIn, request: Request):
        ensure_table(request)
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                tid = int(tenant_id_from_header(request) or 1)
                cfg_id = _parse_config_id(request)
                if cfg_id:
                    row = _get_config_by_id(conn, cfg_id)
                    _assert_cfg_matches(cfg_row=row, slug=slug, tid=tid)
                else:
                    row = _get_latest_config(conn, slug=slug, tid=tid)
            if not row:
                raise HTTPException(status_code=400, detail="Meta WhatsApp não configurada.")
            if not _cfg_enabled(row):
                raise HTTPException(status_code=400, detail="Meta WhatsApp está desativada.")
            token = _cfg_access_token(row)
            phone_number_id = _cfg_phone_number_id(row)
            if not token or not phone_number_id:
                raise HTTPException(status_code=400, detail="Informe Access Token e Phone Number ID.")

            to_waid = _normalize_wa_id(payload.to)
            if not to_waid:
                raise HTTPException(status_code=400, detail="Destino inválido.")

            base = _graph_base(row)
            ver = _graph_version(row)
            url = f"{base}/{ver}/{phone_number_id}/messages"
            body = str(payload.body or "").strip()
            media_id = str(payload.media_id or "").strip()
            media_url = str(payload.media_url or "").strip()
            media_type = str(payload.media_type or "").strip().lower() or "image"
            text_position = str(payload.text_position or "").strip().lower() or "bottom"

            results: list[dict[str, Any]] = []

            async def send_one(message_payload: dict[str, Any]) -> dict[str, Any]:
                full = {"messaging_product": "whatsapp", "to": to_waid, **message_payload}
                res = await _graph_json(method="POST", url=url, token=token, json_payload=full, timeout=40)
                return res

            if payload.template_name:
                tname = str(payload.template_name or "").strip()
                tlang = str(payload.template_lang or "").strip() or "pt_BR"
                comp = payload.template_components if isinstance(payload.template_components, list) else None
                msg = {
                    "type": "template",
                    "template": {
                        "name": tname,
                        "language": {"code": tlang},
                        **({"components": comp} if comp else {}),
                    },
                }
                res = await send_one(msg)
                results.append(res)
                message_id = None
                try:
                    message_id = str(((res.get("messages") or [])[0] or {}).get("id") or "").strip() or None
                except Exception:
                    message_id = None
                ids = [message_id] if message_id else []
                _insert_disparo_log(
                    request,
                    campanha_id=payload.campanha_id,
                    numero=to_waid,
                    nome=str(payload.contato_nome or "").strip(),
                    mensagem=f"TEMPLATE:{tname}",
                    imagem=None,
                    status="ENVIADO",
                    payload={"provider": "meta", "request": msg, "response": res, "message_ids": ids},
                    message_id=message_id,
                )
                return {"ok": True, "results": results, "message_id": message_id, "message_ids": ids}

            async def send_text() -> Optional[str]:
                if not body:
                    return None
                msg = {"type": "text", "text": {"preview_url": True, "body": body}}
                res = await send_one(msg)
                results.append(res)
                try:
                    return str(((res.get("messages") or [])[0] or {}).get("id") or "").strip() or None
                except Exception:
                    return None

            async def send_media() -> Optional[str]:
                if not (media_id or media_url):
                    return None
                media_obj: dict[str, Any] = {}
                if media_id:
                    media_obj["id"] = media_id
                else:
                    media_obj["link"] = media_url
                msg = {"type": media_type, media_type: media_obj}
                res = await send_one(msg)
                results.append(res)
                try:
                    return str(((res.get("messages") or [])[0] or {}).get("id") or "").strip() or None
                except Exception:
                    return None

            ids: list[str] = []
            if text_position == "top":
                mid1 = await send_text()
                if mid1:
                    ids.append(mid1)
                mid2 = await send_media()
                if mid2:
                    ids.append(mid2)
            else:
                mid2 = await send_media()
                if mid2:
                    ids.append(mid2)
                mid1 = await send_text()
                if mid1:
                    ids.append(mid1)

            _insert_disparo_log(
                request,
                campanha_id=payload.campanha_id,
                numero=to_waid,
                nome=str(payload.contato_nome or "").strip(),
                mensagem=body or "",
                imagem=(media_id or media_url or None),
                status="ENVIADO",
                payload={"provider": "meta", "request": payload.model_dump(), "responses": results, "message_ids": ids},
                message_id=(ids[-1] if ids else None),
            )

            return {"ok": True, "results": results, "message_ids": ids}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post(f"/api/integracoes/{prefix}/embedded-signup/exchange")
    async def meta_embedded_signup_exchange(payload: MetaEmbeddedSignupExchangeIn, request: Request):
        ensure_table(request)
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                tid = int(tenant_id_from_header(request) or 1)
                cfg_id = _parse_config_id(request)
                if cfg_id:
                    row = _get_config_by_id(conn, cfg_id)
                    _assert_cfg_matches(cfg_row=row, slug=slug, tid=tid)
                else:
                    row = _get_latest_config(conn, slug=slug, tid=tid)
            if not row:
                raise HTTPException(status_code=400, detail="Meta WhatsApp não configurada.")
            if not _cfg_enabled(row):
                raise HTTPException(status_code=400, detail="Meta WhatsApp está desativada.")

            code = str(payload.code or "").strip()
            if not code:
                raise HTTPException(status_code=400, detail="Informe o code.")

            base = _graph_base(row)
            ver = _graph_version(row)
            app_id = str(payload.app_id or "").strip() or _cfg_app_id(row)
            if not app_id:
                raise HTTPException(status_code=400, detail="Informe App ID.")
            app_secret = _cfg_app_secret(row)
            if not app_secret:
                raise HTTPException(status_code=400, detail="Informe App Secret.")

            redirect_uri = str(payload.redirect_uri or "").strip() or _cfg_redirect_uri(row) or None
            tok = await _oauth_exchange_code_for_token(
                base=base,
                ver=ver,
                app_id=app_id,
                app_secret=app_secret,
                code=code,
                redirect_uri=redirect_uri,
                timeout=40,
            )
            access_token = str(tok.get("access_token") or "").strip()
            if not access_token:
                raise HTTPException(status_code=400, detail=str(tok))

            debug = await _oauth_debug_token(base=base, ver=ver, app_id=app_id, app_secret=app_secret, input_token=access_token, timeout=40)
            waba_ids: list[str] = []
            try:
                data = debug.get("data") if isinstance(debug, dict) else None
                gs = (data.get("granular_scopes") if isinstance(data, dict) else None) or []
                for item in gs if isinstance(gs, list) else []:
                    if not isinstance(item, dict):
                        continue
                    scope = str(item.get("scope") or "").strip().lower()
                    if scope not in ("whatsapp_business_management", "whatsapp_business_messaging", "business_management"):
                        continue
                    tids = item.get("target_ids")
                    if isinstance(tids, list):
                        for t in tids:
                            v = str(t or "").strip()
                            if v and v not in waba_ids:
                                waba_ids.append(v)
            except Exception:
                waba_ids = []

            phone_numbers: list[dict[str, Any]] = []
            waba_id_in = str(payload.waba_id or "").strip()
            waba_id = waba_id_in or (waba_ids[0] if waba_ids else "")
            if waba_id:
                pn_url = f"{base}/{ver}/{waba_id}/phone_numbers?{urlencode({'fields': 'id,display_phone_number,verified_name,code_verification_status,quality_rating', 'limit': '50'})}"
                pn = await _graph_json(method="GET", url=pn_url, token=access_token, json_payload=None, timeout=60)
                try:
                    arr = pn.get("data") if isinstance(pn, dict) else None
                    if isinstance(arr, list):
                        phone_numbers = [x for x in arr if isinstance(x, dict)]
                except Exception:
                    phone_numbers = []

            phone_number_id_in = str(payload.phone_number_id or "").strip()
            phone_number_id = phone_number_id_in
            if not phone_number_id and phone_numbers:
                phone_number_id = str(phone_numbers[0].get("id") or "").strip()

            configuration_id = str(payload.configuration_id or "").strip()
            partner_solution_id = str(payload.partner_solution_id or "").strip()

            updated_id = 0
            if cfg_id:
                try:
                    with get_conn_for_request(request) as conn2:
                        updated_id = _update_config_by_id(
                            conn2,
                            config_id=cfg_id,
                            tid=tid,
                            slug=slug,
                            base_url=_graph_base(row) or None,
                            api_version=_graph_version(row) or None,
                            phone_number_id=phone_number_id or (_cfg_phone_number_id(row) or None),
                            business_account_id=waba_id or (_cfg_business_account_id(row) or None),
                            access_token=access_token,
                            webhook_verify_token=_cfg_verify_token(row) if _cfg_verify_token(row) else None,
                            app_secret=app_secret if app_secret else None,
                            validate_signature=bool(_cfg_validate_signature(row)),
                            enabled=bool(_cfg_enabled(row)),
                            app_id=app_id or None,
                            configuration_id=configuration_id or (_cfg_configuration_id(row) or None),
                            partner_solution_id=partner_solution_id or (_cfg_partner_solution_id(row) or None),
                            redirect_uri=redirect_uri or (_cfg_redirect_uri(row) or None),
                        )
                except Exception:
                    updated_id = 0

            try:
                if updated_id:
                    new_id = int(updated_id)
                else:
                    with get_conn_for_request(request) as conn2:
                        cur = conn2.cursor()
                        cur.execute(
                            f"""
                            INSERT INTO "{safe_schema}"."{table_name}" (
                                "IdTenant","TenantSlug","BaseUrl","ApiVersion","PhoneNumberId","BusinessAccountId",
                                "AccessToken","WebhookVerifyToken","AppSecret","ValidateSignature","Enabled",
                                "AppId","ConfigurationId","PartnerSolutionId","RedirectUri",
                                "CreatedAt","UpdatedAt"
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),NOW())
                            RETURNING "Id"
                            """,
                            (
                                int(tid),
                                slug,
                                _graph_base(row) or None,
                                _graph_version(row) or None,
                                phone_number_id or (_cfg_phone_number_id(row) or None),
                                waba_id or (_cfg_business_account_id(row) or None),
                                _encrypt_secret(access_token),
                                _encrypt_secret(_cfg_verify_token(row)) if _cfg_verify_token(row) else None,
                                _encrypt_secret(app_secret) if app_secret else None,
                                bool(_cfg_validate_signature(row)),
                                bool(_cfg_enabled(row)),
                                app_id or None,
                                configuration_id or (_cfg_configuration_id(row) or None),
                                partner_solution_id or (_cfg_partner_solution_id(row) or None),
                                redirect_uri or (_cfg_redirect_uri(row) or None),
                            ),
                        )
                        new_id = int(cur.fetchone()[0])
                        try:
                            conn2.commit()
                        except Exception:
                            pass
            except Exception:
                new_id = int(row[0]) if row and row[0] is not None else 0

            return {
                "ok": True,
                "id": new_id,
                "tenant_slug": slug,
                "waba_ids": waba_ids,
                "business_account_id": waba_id or None,
                "phone_number_id": phone_number_id or None,
                "phone_numbers": phone_numbers,
                "debug_token": debug,
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get(f"/api/integracoes/{prefix}/webhook")
    async def meta_webhook_verify(request: Request):
        ensure_table(request)
        slug = _tenant_slug(request)
        try:
            mode = str(request.query_params.get("hub.mode") or "").strip()
            token = str(request.query_params.get("hub.verify_token") or "").strip()
            challenge = str(request.query_params.get("hub.challenge") or "").strip()
            if not mode or not token or not challenge:
                raise HTTPException(status_code=400, detail="Parâmetros de verificação ausentes.")
            with get_conn_for_request(request) as conn:
                cfg_id = _parse_config_id(request)
                if cfg_id:
                    row = _get_config_by_id(conn, cfg_id)
                    _assert_cfg_matches(cfg_row=row, slug=slug, tid=None)
                else:
                    row = _get_latest_config(conn, slug=slug, tid=None)
            verify_expected = _cfg_verify_token(row) if row else str(os.getenv("META_WHATSAPP_WEBHOOK_VERIFY_TOKEN") or "").strip()
            if mode == "subscribe" and verify_expected and token == verify_expected:
                return int(challenge)
            raise HTTPException(status_code=403, detail="Verify token inválido.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post(f"/api/integracoes/{prefix}/webhook")
    async def meta_webhook_event(request: Request):
        ensure_table(request)
        slug = _tenant_slug(request)
        raw = await request.body()
        try:
            with get_conn_for_request(request) as conn:
                cfg_id = _parse_config_id(request)
                if cfg_id:
                    row = _get_config_by_id(conn, cfg_id)
                    _assert_cfg_matches(cfg_row=row, slug=slug, tid=None)
                else:
                    row = _get_latest_config(conn, slug=slug, tid=None)
            if row and _cfg_validate_signature(row):
                secret = _cfg_app_secret(row)
                if not secret:
                    raise HTTPException(status_code=400, detail="App Secret não configurado para validar assinatura.")
                if not _verify_webhook_signature(request, raw, secret):
                    raise HTTPException(status_code=403, detail="Assinatura inválida.")
            payload = None
            try:
                payload = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                payload = {}

            try:
                def _extract_meta_message_text(msg: Any) -> str:
                    try:
                        if not isinstance(msg, dict):
                            return ""
                        t = str(msg.get("type") or "").strip().lower()
                        if t == "text":
                            txt = msg.get("text")
                            if isinstance(txt, dict):
                                return str(txt.get("body") or "").strip()
                            return ""
                        if t == "button":
                            b = msg.get("button")
                            if isinstance(b, dict):
                                return str(b.get("text") or b.get("payload") or "").strip()
                            return ""
                        if t == "interactive":
                            inter = msg.get("interactive")
                            if not isinstance(inter, dict):
                                return ""
                            br = inter.get("button_reply")
                            if isinstance(br, dict):
                                return str(br.get("title") or br.get("id") or "").strip()
                            lr = inter.get("list_reply")
                            if isinstance(lr, dict):
                                return str(lr.get("title") or lr.get("id") or "").strip()
                            return ""
                        if t == "reaction":
                            r = msg.get("reaction")
                            if isinstance(r, dict):
                                return str(r.get("emoji") or "").strip()
                            return ""
                        return ""
                    except Exception:
                        return ""

                def _extract_contact_name(value: Any, waid: str) -> str:
                    try:
                        if not isinstance(value, dict):
                            return ""
                        contacts = value.get("contacts")
                        if not isinstance(contacts, list):
                            return ""
                        for c in contacts:
                            if not isinstance(c, dict):
                                continue
                            w = str(c.get("wa_id") or "").strip()
                            if w and waid and w != waid:
                                continue
                            prof = c.get("profile")
                            if isinstance(prof, dict):
                                n = str(prof.get("name") or "").strip()
                                if n:
                                    return n
                        return ""
                    except Exception:
                        return ""

                def _insert_inbound_disparo(
                    *,
                    tid: int,
                    numero: str,
                    nome: str,
                    mensagem: str,
                    message_id: Optional[str],
                    ts_unix: Optional[int],
                    raw_payload: Any,
                ) -> Optional[int]:
                    try:
                        with get_conn_for_request(request) as conn_in:
                            cur = conn_in.cursor()
                            try:
                                if message_id:
                                    cur.execute(
                                        f"""
                                        SELECT "IdDisparo"
                                        FROM "{safe_schema}"."Disparos"
                                        WHERE "IdTenant" = %s
                                          AND "Direcao" = 'IN'
                                          AND COALESCE("EvolutionInstance",'') = 'META'
                                          AND "MessageId" = %s
                                        ORDER BY "IdDisparo" DESC
                                        LIMIT 1
                                        """,
                                        (int(tid), str(message_id)),
                                    )
                                    row0 = cur.fetchone()
                                    if row0 and row0[0] is not None:
                                        return int(row0[0])
                            except Exception:
                                pass
                            if ts_unix and int(ts_unix) > 0:
                                cur.execute(
                                    f"""
                                    INSERT INTO "{safe_schema}"."Disparos"
                                    ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload","MessageId","EvolutionInstance")
                                    VALUES (%s,NULL,%s,%s,%s,%s,%s,NULL,%s,TO_TIMESTAMP(%s)::timestamp,%s::jsonb,%s,%s)
                                    RETURNING "IdDisparo"
                                    """,
                                    (
                                        int(tid),
                                        "WHATSAPP",
                                        "IN",
                                        str(numero or ""),
                                        str(nome or "") or None,
                                        str(mensagem or ""),
                                        "RECEBIDO",
                                        int(ts_unix),
                                        json.dumps(raw_payload, ensure_ascii=False) if raw_payload is not None else None,
                                        message_id,
                                        "META",
                                    ),
                                )
                            else:
                                cur.execute(
                                    f"""
                                    INSERT INTO "{safe_schema}"."Disparos"
                                    ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload","MessageId","EvolutionInstance")
                                    VALUES (%s,NULL,%s,%s,%s,%s,%s,NULL,%s,NOW() AT TIME ZONE 'UTC',%s::jsonb,%s,%s)
                                    RETURNING "IdDisparo"
                                    """,
                                    (
                                        int(tid),
                                        "WHATSAPP",
                                        "IN",
                                        str(numero or ""),
                                        str(nome or "") or None,
                                        str(mensagem or ""),
                                        "RECEBIDO",
                                        json.dumps(raw_payload, ensure_ascii=False) if raw_payload is not None else None,
                                        message_id,
                                        "META",
                                    ),
                                )
                            rowi = cur.fetchone()
                            try:
                                conn_in.commit()
                            except Exception:
                                pass
                            return int(rowi[0]) if rowi and rowi[0] is not None else None
                    except Exception:
                        return None

                def _insert_webhook_disparo(
                    *,
                    tid: int,
                    field: str,
                    ts_unix: Optional[int],
                    raw_payload: Any,
                ) -> Optional[int]:
                    try:
                        with get_conn_for_request(request) as conn_in:
                            cur = conn_in.cursor()
                            msg = str(field or "").strip().lower()
                            msg = f"FIELD:{msg}" if msg else "FIELD"
                            if ts_unix and int(ts_unix) > 0:
                                cur.execute(
                                    f"""
                                    INSERT INTO "{safe_schema}"."Disparos"
                                    ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload","MessageId","EvolutionInstance")
                                    VALUES (%s,NULL,%s,%s,%s,%s,%s,NULL,%s,TO_TIMESTAMP(%s)::timestamp,%s::jsonb,NULL,%s)
                                    RETURNING "IdDisparo"
                                    """,
                                    (
                                        int(tid),
                                        "WHATSAPP",
                                        "WEBHOOK",
                                        "",
                                        None,
                                        msg,
                                        "WEBHOOK",
                                        int(ts_unix),
                                        json.dumps(raw_payload, ensure_ascii=False) if raw_payload is not None else None,
                                        "META",
                                    ),
                                )
                            else:
                                cur.execute(
                                    f"""
                                    INSERT INTO "{safe_schema}"."Disparos"
                                    ("IdTenant","IdCampanha","Canal","Direcao","Numero","Nome","Mensagem","Imagem","Status","DataHora","Payload","MessageId","EvolutionInstance")
                                    VALUES (%s,NULL,%s,%s,%s,%s,%s,NULL,%s,NOW() AT TIME ZONE 'UTC',%s::jsonb,NULL,%s)
                                    RETURNING "IdDisparo"
                                    """,
                                    (
                                        int(tid),
                                        "WHATSAPP",
                                        "WEBHOOK",
                                        "",
                                        None,
                                        msg,
                                        "WEBHOOK",
                                        json.dumps(raw_payload, ensure_ascii=False) if raw_payload is not None else None,
                                        "META",
                                    ),
                                )
                            rowi = cur.fetchone()
                            try:
                                conn_in.commit()
                            except Exception:
                                pass
                            return int(rowi[0]) if rowi and rowi[0] is not None else None
                    except Exception:
                        return None

                entry = payload.get("entry") if isinstance(payload, dict) else None
                if isinstance(entry, list):
                    for ent in entry:
                        changes = ent.get("changes") if isinstance(ent, dict) else None
                        if not isinstance(changes, list):
                            continue
                        for ch in changes:
                            field = str(ch.get("field") or "").strip().lower() if isinstance(ch, dict) else ""
                            value = ch.get("value") if isinstance(ch, dict) else None
                            if field and field != "messages":
                                tid = int(_tenant_id_for_request(request) or 1)
                                ts_unix = None
                                try:
                                    cand = None
                                    if isinstance(ent, dict):
                                        cand = ent.get("time")
                                    if cand is None and isinstance(value, dict):
                                        cand = value.get("timestamp")
                                    cand_i = int(str(cand or "0").strip() or "0")
                                    ts_unix = cand_i if cand_i > 0 else None
                                except Exception:
                                    ts_unix = None
                                _insert_webhook_disparo(
                                    tid=tid,
                                    field=field,
                                    ts_unix=ts_unix,
                                    raw_payload={"meta": payload, "entry": ent, "change": ch, "field": field},
                                )
                                continue
                            if not isinstance(value, dict):
                                continue
                            statuses = value.get("statuses")
                            if not isinstance(statuses, list):
                                statuses = []
                            for st in statuses:
                                if not isinstance(st, dict):
                                    continue
                                mid = str(st.get("id") or "").strip()
                                status = str(st.get("status") or "").strip().lower()
                                ts = st.get("timestamp")
                                if not mid or not status:
                                    continue
                                mapped = "ENVIADO"
                                if status in ("sent", "queued", "accepted"):
                                    mapped = "ENVIADO"
                                elif status in ("delivered",):
                                    mapped = "ENTREGUE"
                                elif status in ("read",):
                                    mapped = "VISUALIZADO"
                                elif status in ("failed",):
                                    mapped = "FALHA"
                                try:
                                    with get_conn_for_request(request) as conn2:
                                        cur = conn2.cursor()
                                        tid = int(_tenant_id_for_request(request) or 1)
                                        cur.execute(
                                            f"""
                                            UPDATE "{safe_schema}"."Disparos"
                                            SET "Status" = %s,
                                                "EntregueEm" = CASE WHEN %s = 'ENTREGUE' THEN (TO_TIMESTAMP(%s)::timestamp) ELSE "EntregueEm" END,
                                                "VisualizadoEm" = CASE WHEN %s = 'VISUALIZADO' THEN (TO_TIMESTAMP(%s)::timestamp) ELSE "VisualizadoEm" END
                                            WHERE "IdTenant" = %s
                                              AND (
                                                "MessageId" = %s
                                                OR COALESCE("Payload"->'message_ids','[]'::jsonb) ? %s
                                              )
                                            """,
                                            (
                                                mapped,
                                                mapped,
                                                int(ts or 0),
                                                mapped,
                                                int(ts or 0),
                                                tid,
                                                mid,
                                                mid,
                                            ),
                                        )
                                        try:
                                            conn2.commit()
                                        except Exception:
                                            pass
                                except Exception:
                                    pass

                            messages = value.get("messages")
                            if not isinstance(messages, list):
                                continue
                            tid = int(_tenant_id_for_request(request) or 1)
                            out_rows: Optional[list[Any]] = None
                            for m in messages:
                                if not isinstance(m, dict):
                                    continue
                                from_waid = str(m.get("from") or "").strip()
                                incoming_digits = _digits_only(from_waid)
                                incoming_text = _extract_meta_message_text(m).strip()
                                if not incoming_digits or not incoming_text:
                                    continue
                                incoming_ts = None
                                try:
                                    incoming_ts = int(str(m.get("timestamp") or "0").strip() or "0")
                                    if incoming_ts <= 0:
                                        incoming_ts = None
                                except Exception:
                                    incoming_ts = None
                                incoming_mid = str(m.get("id") or "").strip() or None
                                incoming_name = _extract_contact_name(value, incoming_digits)

                                inserted_in_id = _insert_inbound_disparo(
                                    tid=tid,
                                    numero=incoming_digits,
                                    nome=incoming_name,
                                    mensagem=incoming_text,
                                    message_id=incoming_mid,
                                    ts_unix=incoming_ts,
                                    raw_payload={"meta": payload, "entry": ent, "change": ch, "message": m},
                                )

                                resposta = _parse_sim_nao_response(incoming_text)
                                if resposta not in (1, 2) or not inserted_in_id:
                                    continue

                                if out_rows is None:
                                    try:
                                        with get_conn_for_request(request) as conn3:
                                            cur3 = conn3.cursor()
                                            cur3.execute(
                                                f"""
                                                SELECT d."IdDisparo", d."Numero", d."IdCampanha"
                                                FROM "{safe_schema}"."Disparos" d
                                                JOIN "{safe_schema}"."Campanhas" c
                                                  ON c."IdTenant" = d."IdTenant"
                                                 AND c."IdCampanha" = d."IdCampanha"
                                                WHERE d."IdTenant" = %s
                                                  AND d."Canal" = 'WHATSAPP'
                                                  AND d."Direcao" = 'OUT'
                                                  AND COALESCE(d."EvolutionInstance",'') = 'META'
                                                  AND d."Status" IN ('ENVIADO','ENTREGUE','VISUALIZADO')
                                                  AND d."IdCampanha" IS NOT NULL
                                                  AND COALESCE(c."AnexoJSON"->'config'->>'response_mode', '') = 'SIM_NAO'
                                                ORDER BY d."DataHora" DESC, d."IdDisparo" DESC
                                                LIMIT 500
                                                """,
                                                (tid,),
                                            )
                                            out_rows = cur3.fetchall() or []
                                    except Exception:
                                        out_rows = []

                                candidates = [
                                    (out_id_raw, out_num, campanha_id)
                                    for (out_id_raw, out_num, campanha_id) in (out_rows or [])
                                    if _match_phone(out_num, incoming_digits)
                                ]
                                for (out_id_raw, _out_num, campanha_id) in candidates[:5]:
                                    try:
                                        with get_conn_for_request(request) as conn4:
                                            cur4 = conn4.cursor()
                                            cur4.execute(
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
                                            try:
                                                conn4.commit()
                                            except Exception:
                                                pass
                                        break
                                    except Exception:
                                        pass
            except Exception:
                pass

            return {"ok": True}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get(f"/api/integracoes/{prefix}/webhook/echo")
    async def meta_webhook_echo_verify(request: Request):
        try:
            mode = str(request.query_params.get("hub.mode") or "").strip()
            token = str(request.query_params.get("hub.verify_token") or "").strip()
            challenge = str(request.query_params.get("hub.challenge") or "").strip()
            if not mode or not token or not challenge:
                raise HTTPException(status_code=400, detail="Parâmetros de verificação ausentes.")
            verify_expected = str(os.getenv("META_ECHO_VERIFY_TOKEN") or "").strip()
            if not verify_expected:
                verify_expected = str(os.getenv("VERIFY_TOKEN") or "").strip()
            if mode == "subscribe" and verify_expected and token == verify_expected:
                return int(challenge)
            raise HTTPException(status_code=403, detail="Verify token inválido.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post(f"/api/integracoes/{prefix}/webhook/echo")
    async def meta_webhook_echo_event(request: Request):
        raw = await request.body()
        try:
            try:
                payload = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                payload = {}
            try:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            except Exception:
                try:
                    print(str(payload))
                except Exception:
                    pass
            return {"ok": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post(f"/api/integracoes/{prefix}/webhook/override/waba")
    async def meta_webhook_override_waba(payload: MetaWebhookOverrideWabaIn, request: Request):
        ensure_table(request)
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                tid = int(tenant_id_from_header(request) or 1)
                cfg_id = _parse_config_id(request)
                if cfg_id:
                    row = _get_config_by_id(conn, cfg_id)
                    _assert_cfg_matches(cfg_row=row, slug=slug, tid=tid)
                else:
                    row = _get_latest_config(conn, slug=slug, tid=tid)
            if not row:
                raise HTTPException(status_code=400, detail="Meta WhatsApp não configurada.")
            if not _cfg_enabled(row):
                raise HTTPException(status_code=400, detail="Meta WhatsApp está desativada.")
            token = _cfg_access_token(row)
            if not token:
                raise HTTPException(status_code=400, detail="Informe Access Token.")
            waba_id = str(payload.waba_id or "").strip() or _cfg_business_account_id(row)
            if not waba_id:
                raise HTTPException(status_code=400, detail="Informe WABA (Business Account ID).")

            base = _graph_base(row)
            ver = _graph_version(row)
            url = f"{base}/{ver}/{waba_id}/subscribed_apps"
            override_uri = str(payload.override_callback_uri or "").strip()
            verify_token = str(payload.verify_token or "").strip()

            if override_uri:
                if not verify_token:
                    raise HTTPException(status_code=400, detail="Informe verify_token para override do WABA.")
                res = await _graph_json(
                    method="POST",
                    url=url,
                    token=token,
                    json_payload={"override_callback_uri": override_uri, "verify_token": verify_token},
                    timeout=60,
                )
                return {"ok": True, "mode": "override", "response": res}

            res = await _graph_json(method="POST", url=url, token=token, json_payload=None, timeout=60)
            return {"ok": True, "mode": "default", "response": res}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get(f"/api/integracoes/{prefix}/webhook/subscribed_apps")
    async def meta_webhook_subscribed_apps(request: Request, waba_id: Optional[str] = None):
        ensure_table(request)
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                tid = int(tenant_id_from_header(request) or 1)
                cfg_id = _parse_config_id(request)
                if cfg_id:
                    row = _get_config_by_id(conn, cfg_id)
                    _assert_cfg_matches(cfg_row=row, slug=slug, tid=tid)
                else:
                    row = _get_latest_config(conn, slug=slug, tid=tid)

            qp = request.query_params
            token = str(qp.get("access_token") or "").strip() or _cfg_access_token(row)
            if not token:
                raise HTTPException(status_code=400, detail="Informe Access Token.")
            
            waba = str(waba_id or "").strip() or _cfg_business_account_id(row)
            if not waba:
                raise HTTPException(status_code=400, detail="Informe WABA (Business Account ID).")

            base = str(qp.get("base_url") or "").strip() or _graph_base(row)
            ver = str(qp.get("api_version") or "").strip() or _graph_version(row)
            if not ver.startswith("v"):
                ver = f"v{ver}"
            base = base.rstrip("/")

            url = f"{base}/{ver}/{waba}/subscribed_apps"
            res = await _graph_json(method="GET", url=url, token=token, json_payload=None, timeout=60)
            return {"ok": True, "response": res}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post(f"/api/integracoes/{prefix}/webhook/override/phone")
    async def meta_webhook_override_phone(payload: MetaWebhookOverridePhoneIn, request: Request):
        ensure_table(request)
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                tid = int(tenant_id_from_header(request) or 1)
                cfg_id = _parse_config_id(request)
                if cfg_id:
                    row = _get_config_by_id(conn, cfg_id)
                    _assert_cfg_matches(cfg_row=row, slug=slug, tid=tid)
                else:
                    row = _get_latest_config(conn, slug=slug, tid=tid)
            if not row:
                raise HTTPException(status_code=400, detail="Meta WhatsApp não configurada.")
            if not _cfg_enabled(row):
                raise HTTPException(status_code=400, detail="Meta WhatsApp está desativada.")
            token = _cfg_access_token(row)
            if not token:
                raise HTTPException(status_code=400, detail="Informe Access Token.")

            phone_id = str(payload.phone_number_id or "").strip() or _cfg_phone_number_id(row)
            if not phone_id:
                raise HTTPException(status_code=400, detail="Informe Phone Number ID.")
            override_uri = str(payload.override_callback_uri or "").strip()
            verify_token = str(payload.verify_token or "").strip()
            if override_uri and not verify_token:
                raise HTTPException(status_code=400, detail="Informe verify_token para override do Phone Number.")

            base = _graph_base(row)
            ver = _graph_version(row)
            url = f"{base}/{ver}/{phone_id}"
            res = await _graph_json(
                method="POST",
                url=url,
                token=token,
                json_payload={
                    "webhook_configuration": {
                        "override_callback_uri": override_uri,
                        **({"verify_token": verify_token} if verify_token else {}),
                    }
                },
                timeout=60,
            )
            return {"ok": True, "response": res}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get(f"/api/integracoes/{prefix}/webhook/override/status")
    async def meta_webhook_override_status(request: Request, phone_number_id: Optional[str] = None):
        ensure_table(request)
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                tid = int(tenant_id_from_header(request) or 1)
                cfg_id = _parse_config_id(request)
                if cfg_id:
                    row = _get_config_by_id(conn, cfg_id)
                    _assert_cfg_matches(cfg_row=row, slug=slug, tid=tid)
                else:
                    row = _get_latest_config(conn, slug=slug, tid=tid)
            if not row:
                raise HTTPException(status_code=400, detail="Meta WhatsApp não configurada.")
            if not _cfg_enabled(row):
                raise HTTPException(status_code=400, detail="Meta WhatsApp está desativada.")
            token = _cfg_access_token(row)
            if not token:
                raise HTTPException(status_code=400, detail="Informe Access Token.")

            phone_id = str(phone_number_id or "").strip() or _cfg_phone_number_id(row)
            if not phone_id:
                raise HTTPException(status_code=400, detail="Informe Phone Number ID.")

            base = _graph_base(row)
            ver = _graph_version(row)
            url = f"{base}/{ver}/{phone_id}"
            res = await _graph_json(method="GET", url=f"{url}?fields=webhook_configuration", token=token, json_payload=None, timeout=60)
            return {"ok": True, "response": res}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post(f"/api/integracoes/{prefix}/templates/create")
    async def meta_create_template(payload: MetaTemplateCreateIn, request: Request):
        ensure_table(request)
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                tid = int(tenant_id_from_header(request) or 1)
                cfg_id = _parse_config_id(request)
                if cfg_id:
                    row = _get_config_by_id(conn, cfg_id)
                    _assert_cfg_matches(cfg_row=row, slug=slug, tid=tid)
                else:
                    row = _get_latest_config(conn, slug=slug, tid=tid)
            if not row:
                raise HTTPException(status_code=400, detail="Meta WhatsApp não configurada.")
            if not _cfg_enabled(row):
                raise HTTPException(status_code=400, detail="Meta WhatsApp está desativada.")
            token = _cfg_access_token(row)
            waba_id = _cfg_business_account_id(row)
            if not token:
                raise HTTPException(status_code=400, detail="Informe Access Token.")
            if not waba_id:
                raise HTTPException(status_code=400, detail="Informe WABA (Business Account ID).")

            base = _graph_base(row)
            ver = _graph_version(row)
            url = f"{base}/{ver}/{waba_id}/message_templates"

            name = str(payload.template_name or "").strip()
            if not name:
                raise HTTPException(status_code=400, detail="Informe TEMPLATE NAME.")
            language = str(payload.language or "").strip() or "pt_BR"
            category = str(payload.category or "").strip() or "UTILITY"
            body_text = str(payload.body_text or "").strip()
            if not body_text:
                raise HTTPException(status_code=400, detail="Informe BODY TEXT.")

            req_payload = {
                "name": name,
                "language": language,
                "category": category,
                "components": [{"type": "BODY", "text": body_text}],
            }
            res = await _graph_json(method="POST", url=url, token=token, json_payload=req_payload, timeout=60)
            return {"ok": True, "response": res}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get(f"/api/integracoes/{prefix}/templates/list")
    async def meta_list_templates(
        request: Request,
        waba_id: Optional[str] = None,
        name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ):
        ensure_table(request)
        slug = _tenant_slug(request)
        try:
            with get_conn_for_request(request) as conn:
                tid = int(tenant_id_from_header(request) or 1)
                cfg_id = _parse_config_id(request)
                if cfg_id:
                    row = _get_config_by_id(conn, cfg_id)
                    _assert_cfg_matches(cfg_row=row, slug=slug, tid=tid)
                else:
                    row = _get_latest_config(conn, slug=slug, tid=tid)
            if not row:
                raise HTTPException(status_code=400, detail="Meta WhatsApp não configurada.")
            if not _cfg_enabled(row):
                raise HTTPException(status_code=400, detail="Meta WhatsApp está desativada.")
            token = _cfg_access_token(row)
            if not token:
                raise HTTPException(status_code=400, detail="Informe Access Token.")
            waba = str(waba_id or "").strip() or _cfg_business_account_id(row)
            if not waba:
                raise HTTPException(status_code=400, detail="Informe WABA (Business Account ID).")
            base = _graph_base(row)
            ver = _graph_version(row)
            params: dict[str, str] = {"limit": str(max(1, min(int(limit or 50), 250)))}
            if name:
                params["name"] = str(name).strip()
            if status:
                params["status"] = str(status).strip().upper()
            url = f"{base}/{ver}/{waba}/message_templates?{urlencode(params)}"
            res = await _graph_json(method="GET", url=url, token=token, json_payload=None, timeout=60)
            return {"ok": True, "response": res}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get(f"/api/integracoes/{prefix}/stats")
    async def meta_stats(request: Request, days: int = 14):
        ensure_table(request)
        try:
            d = int(days or 14)
            if d < 1:
                d = 1
            if d > 90:
                d = 90
        except Exception:
            d = 14
        try:
            tid = int(tenant_id_from_header(request) or 1)
            start = datetime.utcnow() - timedelta(days=d)
            with get_conn_for_request(request) as conn:
                cur = conn.cursor()
                cur.execute(
                    f"""
                    SELECT
                        TO_CHAR(DATE_TRUNC('day',"DataHora"), 'YYYY-MM-DD') AS dia,
                        COUNT(*) FILTER (WHERE "Status" = 'ENVIADO') AS enviados,
                        COUNT(*) FILTER (WHERE "Status" = 'ENTREGUE') AS entregues,
                        COUNT(*) FILTER (WHERE "Status" = 'VISUALIZADO') AS visualizados,
                        COUNT(*) FILTER (WHERE "Status" = 'FALHA') AS falhas,
                        COUNT(*) AS total
                    FROM "{safe_schema}"."Disparos"
                    WHERE "IdTenant" = %s
                      AND COALESCE("EvolutionInstance",'') = 'META'
                      AND "Direcao" = 'OUT'
                      AND "Canal" = 'WHATSAPP'
                      AND "DataHora" >= %s
                    GROUP BY 1
                    ORDER BY 1
                    """,
                    (tid, start),
                )
                rows = cur.fetchall() or []
            out = []
            for r in rows:
                out.append(
                    {
                        "date": str(r[0] or ""),
                        "sent": int(r[1] or 0),
                        "delivered": int(r[2] or 0),
                        "read": int(r[3] or 0),
                        "failed": int(r[4] or 0),
                        "total": int(r[5] or 0),
                    }
                )
            return {"ok": True, "days": d, "rows": out}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
