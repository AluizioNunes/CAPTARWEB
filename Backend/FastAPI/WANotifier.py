from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Any, Callable
import os


class WabaProviderConfigIn(BaseModel):
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    phone_number_id: Optional[str] = None
    business_account_id: Optional[str] = None
    webhook_verify_token: Optional[str] = None
    enabled: Optional[bool] = True


def register_wanotifier_routes(
    app: FastAPI,
    get_db_connection: Callable[..., Any],
    get_conn_for_request: Callable[[Request], Any],
    db_schema: str,
    mask_key: Callable[[str], str],
):
    safe_schema = str(db_schema or "captar").replace('"', '""')
    table_name = "wanotifier_config"
    prefix = "wanotifier"

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

    def ensure_table():
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS "{safe_schema}"."{table_name}" (
                        id SERIAL PRIMARY KEY,
                        tenant_slug TEXT NOT NULL,
                        base_url TEXT,
                        api_key TEXT,
                        phone_number_id TEXT,
                        business_account_id TEXT,
                        webhook_verify_token TEXT,
                        enabled BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    )
                    """
                )
                cur.execute(
                    f'CREATE INDEX IF NOT EXISTS "idx_{table_name}_tenant" ON "{safe_schema}"."{table_name}"(tenant_slug)'
                )
                conn.commit()
        except Exception:
            pass

    def _tenant_slug_from_request(request: Request) -> str:
        try:
            return str(request.headers.get("X-Tenant") or "captar").strip().lower() or "captar"
        except Exception:
            return "captar"

    def _get_latest_config(conn, slug: str):
        cur = conn.cursor()
        cur.execute(
            f"""
            SELECT id, tenant_slug, base_url, api_key, phone_number_id, business_account_id, webhook_verify_token, enabled
            FROM "{safe_schema}"."{table_name}"
            WHERE tenant_slug=%s
            ORDER BY id DESC
            LIMIT 1
            """,
            (slug,),
        )
        return cur.fetchone()

    @app.get(f"/api/integracoes/{prefix}/config")
    async def waba_get_config(request: Request):
        ensure_table()
        slug = _tenant_slug_from_request(request)
        try:
            with get_conn_for_request(request) as conn:
                row = _get_latest_config(conn, slug)
            if not row:
                return {
                    "tenant_slug": slug,
                    "base_url": "",
                    "phone_number_id": "",
                    "business_account_id": "",
                    "has_api_key": False,
                    "api_key_masked": "",
                    "has_webhook_verify_token": False,
                    "webhook_verify_token_masked": "",
                    "enabled": True,
                }
            api_key_plain = _decrypt_secret(str(row[3] or "").strip())
            verify_plain = _decrypt_secret(str(row[6] or "").strip())
            return {
                "tenant_slug": slug,
                "id": int(row[0]),
                "base_url": str(row[2] or "").strip(),
                "phone_number_id": str(row[4] or "").strip(),
                "business_account_id": str(row[5] or "").strip(),
                "has_api_key": bool(api_key_plain),
                "api_key_masked": mask_key(api_key_plain) if api_key_plain else "",
                "has_webhook_verify_token": bool(verify_plain),
                "webhook_verify_token_masked": mask_key(verify_plain) if verify_plain else "",
                "enabled": bool(row[7]) if row[7] is not None else True,
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post(f"/api/integracoes/{prefix}/config")
    async def waba_save_config(payload: WabaProviderConfigIn, request: Request):
        ensure_table()
        slug = _tenant_slug_from_request(request)
        try:
            with get_conn_for_request(request) as conn:
                prev = _get_latest_config(conn, slug)
                base_url = str(payload.base_url or "").strip() or (str(prev[2] or "").strip() if prev else "")
                phone_number_id = str(payload.phone_number_id or "").strip() or (str(prev[4] or "").strip() if prev else "")
                business_account_id = str(payload.business_account_id or "").strip() or (str(prev[5] or "").strip() if prev else "")

                api_key = str(payload.api_key or "").strip()
                if not api_key and prev:
                    api_key = _decrypt_secret(str(prev[3] or "").strip())

                webhook_verify_token = str(payload.webhook_verify_token or "").strip()
                if not webhook_verify_token and prev:
                    webhook_verify_token = _decrypt_secret(str(prev[6] or "").strip())

                enabled = payload.enabled if payload.enabled is not None else (bool(prev[7]) if prev and prev[7] is not None else True)

                cur = conn.cursor()
                cur.execute(
                    f"""
                    INSERT INTO "{safe_schema}"."{table_name}" (
                        tenant_slug, base_url, api_key, phone_number_id, business_account_id, webhook_verify_token, enabled, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
                    """,
                    (
                        slug,
                        base_url or None,
                        _encrypt_secret(api_key) if api_key else None,
                        phone_number_id or None,
                        business_account_id or None,
                        _encrypt_secret(webhook_verify_token) if webhook_verify_token else None,
                        bool(enabled),
                    ),
                )
                new_id = cur.fetchone()[0]
                try:
                    conn.commit()
                except Exception:
                    pass
                return {"id": int(new_id), "saved": True}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

