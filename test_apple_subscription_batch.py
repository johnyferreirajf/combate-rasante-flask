"""Combate Rasante: testes integrados, locais e SEM conexao com Apple/Firebase/Railway.

Executar da raiz do backend:
    python test_apple_subscription_batch.py

Nao usa create_app(), nao le DATABASE_URL e nao altera bancos existentes.
"""
import hashlib
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask
from app import db
from app.models.app_subscription import AppSubscription
from app.routes.apple_subscription_api import apple_subscription_bp, _account_token

APPLE_MODULE = "app.routes.apple_subscription_api"
OWNER = {"localId": "firebase-A", "email": "a@example.test", "emailVerified": True}
OTHER = {"localId": "firebase-B", "email": "b@example.test", "emailVerified": True}
SAME_EMAIL_OTHER_UID = {"localId": "firebase-B", "email": "a@example.test", "emailVerified": True}
ORIGINAL = "12345678987654321"
ENDPOINT = "/api/app/subscription/apple"


class AppleSubscriptionBatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="combate_apple_test_")
        cls.app = Flask("apple_subscription_batch")
        cls.app.config.update(
            TESTING=True,
            SECRET_KEY="SEGREDO-DE-TESTE-ISOLADO-NAO-USAR-EM-PRODUCAO-2026",
            SQLALCHEMY_DATABASE_URI="sqlite:///" +
                (Path(cls.temp.name) / "apple_tests.sqlite3").as_posix(),
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(cls.app)
        cls.app.register_blueprint(apple_subscription_bp)
        with cls.app.app_context():
            db.create_all()
        cls.client = cls.app.test_client()

    @classmethod
    def tearDownClass(cls):
        with cls.app.app_context():
            db.session.remove()
            db.engine.dispose()
        cls.temp.cleanup()

    def setUp(self):
        with self.app.app_context():
            db.session.remove()
            for record in AppSubscription.query.all():
                db.session.delete(record)
            db.session.commit()

    def make_transaction(self, identity=OWNER, *, original=ORIGINAL,
                         days=30, revoked=False, product="combate_rasante_premium_mensal"):
        with self.app.app_context():
            token = _account_token(identity)
        return SimpleNamespace(
            originalTransactionId=original,
            appAccountToken=token,
            productId=product,
            expiresDate=int((datetime.now(timezone.utc) + timedelta(days=days)).timestamp() * 1000),
            revocationDate=(int(datetime.now(timezone.utc).timestamp() * 1000) if revoked else None),
            isUpgraded=False,
        )

    def call(self, method="POST", path="/verify", *, identity=OWNER,
             transaction=None, status=1, retrieve_error=None, data=None):
        if data is None:
            data = {"transactionId": ORIGINAL}
        if transaction is None:
            transaction = self.make_transaction(identity)
        with patch(f"{APPLE_MODULE}._firebase_identity", return_value=(identity, None)), \
             patch(f"{APPLE_MODULE}._retrieve") as retrieve:
            if retrieve_error is not None:
                retrieve.side_effect = retrieve_error
            else:
                retrieve.return_value = ((transaction, [(status, transaction, None)]), True)
            response = self.client.open(
                ENDPOINT + path, method=method, json=data if method == "POST" else None,
                headers={"Authorization": "Bearer token-de-teste"},
            )
        return response.status_code, response.get_json(), retrieve.call_count

    def count(self):
        with self.app.app_context():
            return AppSubscription.query.count()

    def test_01_unauthenticated_all_routes(self):
        for method, path in [("GET", "/account-token"), ("POST", "/verify"), ("GET", "/status")]:
            with self.subTest(path=path):
                resp = self.client.open(ENDPOINT + path, method=method)
                self.assertEqual(resp.status_code, 401)
                self.assertEqual(resp.get_json()["error"], "missing_token")

    def test_02_app_account_token_stability_and_isolation(self):
        with self.app.app_context():
            self.assertEqual(_account_token(OWNER), _account_token(OWNER))
            self.assertNotEqual(_account_token(OWNER), _account_token(OTHER))
            import uuid
            uuid.UUID(_account_token(OWNER))
        status, body, _ = self.call("GET", "/account-token")
        self.assertEqual(status, 200, body)
        self.assertEqual(body["ok"], True)
        self.assertIn("appAccountToken", body)

    def test_03_missing_transaction_id_rejected(self):
        status, body, calls = self.call(data={})
        self.assertEqual((status, body.get("error"), calls), (400, "transaction_id_invalid", 0))
        self.assertEqual(self.count(), 0)

    def test_04_apple_lookup_failure_does_not_create_record(self):
        status, body, calls = self.call(retrieve_error=ValueError("transaction_not_found"))
        self.assertEqual((status, body.get("error"), calls), (422, "apple_invalid_transaction", 1))
        self.assertEqual(self.count(), 0)

    def test_05_valid_purchase_persisted_and_status_rechecked(self):
        tx = self.make_transaction()
        status, body, calls = self.call(transaction=tx)
        self.assertEqual(status, 200, body)
        self.assertTrue(body["premium"])
        self.assertEqual(calls, 1)
        with self.app.app_context():
            record = AppSubscription.query.one()
            self.assertEqual(record.original_transaction_id, ORIGINAL)
            self.assertEqual(record.provider, "app_store")
            self.assertEqual(record.purchase_token_hash,
                             hashlib.sha256(f"apple:{ORIGINAL}".encode()).hexdigest())
        status2, body2, calls2 = self.call("GET", "/status", transaction=tx)
        self.assertEqual(status2, 200, body2)
        self.assertTrue(body2["premium"])
        self.assertEqual(calls2, 1)
        self.assertEqual(self.count(), 1)

    def test_06_same_purchase_other_firebase_uid_blocked(self):
        tx = self.make_transaction()
        status, body, _ = self.call(transaction=tx)
        self.assertEqual(status, 200, body)
        for identity in (OTHER, SAME_EMAIL_OTHER_UID):
            with self.subTest(identity=identity):
                status2, body2, _ = self.call(identity=identity, transaction=tx)
                self.assertEqual(status2, 409, body2)
                self.assertEqual(body2["error"], "transaction_account_mismatch")
        self.assertEqual(self.count(), 1)

    def test_07_expired_revoked_grace_not_premium(self):
        for name, params, status in [
            ("expired", {"days": -1}, 2),
            ("revoked", {"revoked": True}, 1),
            ("grace", {"days": 2}, 4),
        ]:
            with self.subTest(case=name):
                tx = self.make_transaction(**params)
                http, body, _ = self.call(transaction=tx, status=status)
                self.assertEqual(http, 200, body)
                self.assertFalse(body["premium"], body)
                self.assertEqual(self.count(), 1)
                with self.app.app_context():
                    AppSubscription.query.delete()
                    db.session.commit()

    def test_08_unavailable_apple_must_fail_closed(self):
        http, body, _ = self.call(retrieve_error=ConnectionError("offline"))
        self.assertEqual(http, 503, body)
        self.assertEqual(body["error"], "apple_unavailable")
        self.assertEqual(self.count(), 0)

    def test_09_status_without_purchases(self):
        http, body, calls = self.call("GET", "/status")
        self.assertEqual(http, 200, body)
        self.assertFalse(body["premium"])
        self.assertEqual(body["subscriptionState"], "NONE")
        self.assertEqual(calls, 0)

    def test_10_existing_active_purchase_revoked_on_recheck(self):
        tx = self.make_transaction()
        http, body, _ = self.call(transaction=tx)
        self.assertEqual(http, 200, body)
        revoked = self.make_transaction(revoked=True)
        http2, body2, _ = self.call("GET", "/status", transaction=revoked)
        self.assertEqual(http2, 200, body2)
        self.assertFalse(body2["premium"])
        with self.app.app_context():
            self.assertEqual(AppSubscription.query.one().subscription_state, "REVOKED")


if __name__ == "__main__":
    print("TESTES APPLE COMBATE RASANTE - AMBIENTE ISOLADO", flush=True)
    unittest.main(verbosity=2)
