from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, Callable
import ssl
import urllib.request
from urllib.request import urlopen
from urllib.error import URLError, HTTPError
import gzip
import zlib
import json
import pandas as pd


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


def register_tse_routes(app: FastAPI, get_db_connection: Callable[..., Any], db_schema: str):
    DB_SCHEMA = db_schema

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
                    ),
                )
                new_id = cursor.fetchone()[0]
                conn.commit()
                return {"id": new_id, "saved": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/integracoes/testar")
    async def integracoes_testar(payload: TesteIntegracaoRequest):
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
        try:
            uf = uf.upper()
            codigo_uf = {"AM": 13}.get(uf)
            if not codigo_uf:
                raise HTTPException(status_code=400, detail="UF não suportada")
            ctx = ssl.create_default_context()
            req = urllib.request.Request(
                url=f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{codigo_uf}/municipios",
                headers={"Accept-Encoding": "identity", "User-Agent": "CAPTAR/1.0"},
            )
            with urlopen(req, context=ctx, timeout=10) as resp:
                raw = resp.read()
                enc = resp.headers.get("Content-Encoding", "").lower()
                if enc == "gzip" or (len(raw) > 2 and raw[0] == 0x1F and raw[1] == 0x8B):
                    raw = gzip.decompress(raw)
                elif enc == "deflate" or (len(raw) > 2 and raw[0] == 0x78):
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
        try:
            dataset = (payload.dataset or "").strip()
            if not dataset:
                raise HTTPException(status_code=400, detail="Dataset é obrigatório")
            query_url = f"https://dadosabertos.tse.jus.br/api/3/action/package_search?q={dataset}"
            ctx = ssl.create_default_context()
            req = urllib.request.Request(url=query_url, headers={"Accept-Encoding": "identity", "User-Agent": "CAPTAR/1.0"})
            with urlopen(req, context=ctx, timeout=15) as resp:
                raw = resp.read()
                enc = resp.headers.get("Content-Encoding", "").lower()
                if enc == "gzip" or (len(raw) > 2 and raw[0] == 0x1F and raw[1] == 0x8B):
                    raw = gzip.decompress(raw)
                elif enc == "deflate" or (len(raw) > 2 and raw[0] == 0x78):
                    raw = zlib.decompress(raw)
                result = json.loads(raw.decode("utf-8"))
            resources = []
            for pkg in result.get("result", {}).get("results", []):
                for r in pkg.get("resources", []):
                    resources.append(
                        {"id": r.get("id"), "name": r.get("name"), "format": r.get("format"), "url": r.get("url") or r.get("download_url")}
                    )
            uf = (payload.uf or "").upper()
            if uf == "AM":
                resources = [
                    r
                    for r in resources
                    if (r["name"] or "").upper().find("AMAZONAS") != -1 or (r["name"] or "").upper().endswith("AM")
                ]
            return {"resources": resources}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/integracoes/ckan/resources")
    async def integracoes_ckan_resources_get(dataset: str, uf: Optional[str] = None):
        return await integracoes_ckan_resources(CkanResourcesRequest(dataset=dataset, uf=uf))

    @app.post("/api/integracoes/ckan/preview")
    async def integracoes_ckan_preview(payload: dict):
        try:
            url = payload.get("resource_url")
            limit = int(payload.get("limit", 15))
            if not url:
                raise HTTPException(status_code=400, detail="resource_url é obrigatório")
            df = pd.read_csv(url, nrows=limit)
            return {"columns": list(df.columns), "rows": df.head(limit).to_dict(orient="records")}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

