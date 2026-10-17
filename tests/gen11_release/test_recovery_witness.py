import base64
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

SERVICES = (
    Path(__file__).resolve().parents[2]
    / "arda_os/backend/services"
)
sys.path.insert(0, str(SERVICES))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from arda_gen11_production_authority import Refuse, canonical
from arda_gen11_recovery_witness import SCHEMA, verify_witness


def sha(data):
    return hashlib.sha256(data).hexdigest()


class RecoveryWitnessTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

        self.key = Ed25519PrivateKey.generate()
        self.public_key = self.root / "recovery-public.pem"
        self.public_key.write_bytes(
            self.key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

        self.authorization_id = "arda-gen11-witness-test-0001"
        self.auth_digest = "a" * 64
        self.review_digest = "b" * 64
        self.evidence_digest = "c" * 64

        self.receipt_path = self.root / "receipt.json"
        self.witness_path = self.root / "witness.json"
        self.database = self.root / "transactions.sqlite"

        self.receipt = {
            "schema": "arda-gen11-transaction-recovery-receipt-v1",
            "status": "ROLLED_BACK",
            "authorization_id": self.authorization_id,
            "authorization_sha256": self.auth_digest,
            "review_sha256": self.review_digest,
            "recovery_evidence_sha256": self.evidence_digest,
        }
        self.save_receipt()

        with sqlite3.connect(self.database) as conn:
            conn.execute("""
                CREATE TABLE transactions (
                    authorization_id TEXT PRIMARY KEY,
                    authorization_sha256 TEXT NOT NULL,
                    review_sha256 TEXT NOT NULL,
                    recovery_sha256 TEXT NOT NULL,
                    state TEXT NOT NULL
                )
            """)
            conn.execute(
                "INSERT INTO transactions VALUES (?, ?, ?, ?, ?)",
                (
                    self.authorization_id,
                    self.auth_digest,
                    self.review_digest,
                    self.evidence_digest,
                    "REVIEW_RECORDED",
                ),
            )

        self.payload = {
            "schema": SCHEMA,
            "authorization_id": self.authorization_id,
            "authorization_sha256": self.auth_digest,
            "review_sha256": self.review_digest,
            "recovery_evidence_sha256": self.evidence_digest,
            "recovery_receipt_sha256": sha(
                self.receipt_path.read_bytes()
            ),
            "recovery_status": "ROLLED_BACK",
        }
        self.sign()

    def save_receipt(self):
        self.receipt_path.write_text(
            json.dumps(self.receipt, sort_keys=True) + "\n"
        )

    def sign(self):
        signature = self.key.sign(canonical(self.payload))
        self.witness_path.write_text(json.dumps({
            "payload": self.payload,
            "signature": base64.b64encode(signature).decode(),
        }))

    def verify(self, **overrides):
        params = {
            "witness_path": self.witness_path,
            "recovery_receipt_path": self.receipt_path,
            "transaction_database": self.database,
            "recovery_public_key": self.public_key,
            "enforce_ownership": False,
        }
        params.update(overrides)
        return verify_witness(**params)

    def test_valid_signed_witness(self):
        result = self.verify()
        self.assertEqual(
            result["status"],
            "SIGNED_RECOVERY_WITNESS_VERIFIED",
        )
        self.assertFalse(result["production_install_authorized"])
        self.assertFalse(result["first_boot_authorized"])

    def test_signature_tampering_refused(self):
        envelope = json.loads(self.witness_path.read_text())
        envelope["payload"]["recovery_status"] = "RECOVERED"
        self.witness_path.write_text(json.dumps(envelope))

        with self.assertRaises(Refuse):
            self.verify()

    def test_modified_receipt_refused(self):
        self.receipt["status"] = "COMMITTED"
        self.save_receipt()

        with self.assertRaises(Refuse):
            self.verify()

    def test_wrong_authorization_id_refused(self):
        self.payload["authorization_id"] = "arda-gen11-unknown-id-0001"
        self.sign()

        with self.assertRaises(Refuse):
            self.verify()

    def test_untrusted_key_refused(self):
        other = Ed25519PrivateKey.generate()
        self.public_key.write_bytes(
            other.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

        with self.assertRaises(Refuse):
            self.verify()

    def test_transaction_state_mismatch_refused(self):
        with sqlite3.connect(self.database) as conn:
            conn.execute(
                "UPDATE transactions SET state='REFUSED'"
            )

        with self.assertRaises(Refuse):
            self.verify()

    def test_receipt_authorization_mismatch_refused(self):
        self.receipt["authorization_id"] = "other-authorization-0001"
        self.save_receipt()
        self.payload["recovery_receipt_sha256"] = sha(
            self.receipt_path.read_bytes()
        )
        self.sign()

        with self.assertRaises(Refuse):
            self.verify()


if __name__ == "__main__":
    unittest.main()
