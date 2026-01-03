import os
import sys
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(__file__))

from MetaWhatsApp import register_meta_whatsapp_routes


class _FakeCursor:
    def __init__(self, queries):
        self._queries = queries
        self._fetchone = None
        self._fetchall = None

    def execute(self, sql, params=None):
        self._queries.append((str(sql), params))
        s = str(sql)
        if "RETURNING" in s and '"IdDisparo"' in s:
            self._fetchone = (1,)
            return
        self._fetchone = None
        self._fetchall = []

    def fetchone(self):
        return self._fetchone

    def fetchall(self):
        return self._fetchall


class _FakeConn:
    def __init__(self, queries):
        self._queries = queries

    def cursor(self):
        return _FakeCursor(self._queries)

    def commit(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class MetaWebhookTests(unittest.TestCase):
    def _build_app_and_queries(self):
        queries = []

        def get_db_connection():
            return _FakeConn(queries)

        def get_conn_for_request(_request):
            return _FakeConn(queries)

        app = FastAPI()
        register_meta_whatsapp_routes(
            app,
            get_db_connection=get_db_connection,
            get_conn_for_request=get_conn_for_request,
            db_schema="captar",
            mask_key=lambda s: s,
            tenant_id_from_header=lambda _r: 1,
        )
        return app, queries

    def test_non_message_field_is_logged(self):
        app, queries = self._build_app_and_queries()
        client = TestClient(app)
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WABA",
                    "time": 1700000000,
                    "changes": [
                        {
                            "field": "template_status_update",
                            "value": {"timestamp": "1700000000", "event": "APPROVED"},
                        }
                    ],
                }
            ],
        }
        res = client.post("/api/integracoes/meta/webhook", json=payload)
        self.assertEqual(res.status_code, 200)
        inserts = [q for q in queries if "INSERT INTO" in q[0] and '"Disparos"' in q[0]]
        self.assertTrue(inserts)
        sql, params = inserts[-1]
        self.assertIn('"Direcao"', sql)
        self.assertIn('"Status"', sql)
        self.assertIn("WEBHOOK", params)
        self.assertIn("FIELD:template_status_update", params)

    def test_phone_resolve_without_config_requires_token(self):
        prev = os.environ.pop("META_WHATSAPP_ACCESS_TOKEN", None)
        try:
            app, _queries = self._build_app_and_queries()
            client = TestClient(app)
            res = client.post("/api/integracoes/meta/phone/resolve", json={"phone_number_id": "123"})
            self.assertEqual(res.status_code, 400)
            self.assertEqual(
                (res.json() or {}).get("detail"),
                "Informe Access Token para resolver PhoneID/WhatsApp Phone.",
            )
        finally:
            if prev is not None:
                os.environ["META_WHATSAPP_ACCESS_TOKEN"] = prev


if __name__ == "__main__":
    unittest.main()
