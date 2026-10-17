import base64
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

SERVICES = Path(__file__).resolve().parents[2] / (
    "arda_os/backend/services"
)
sys.path.insert(0, str(SERVICES))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from arda_gen11_production_authority import (
    ACTION, DESTINATION, DIGEST_FIELDS, PROFILE,
    SCHEMA, POLICY_SCHEMA, EXPECTED_GEN10_VERITY,
    Refuse, canonical, sha_file,
)
from arda_gen11_governed_recovery import admit_recovery_review


class GovernedRecoveryTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

        self.evidence = self.root / "recovery.json"
        self.evidence.write_text('{"recovered":true}\n')

        self.policy = self.root / "policy.json"
        self.ledger = self.root / "admissions.sqlite"
        self.receipt = self.root / "review.json"

        self.key = Ed25519PrivateKey.generate()
        pub = self.key.public_key()

        raw = pub.public_bytes(
            serialization.Encoding.Raw,
            serialization.PublicFormat.Raw,
        )
        pem = pub.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        self.policy.write_text(json.dumps({
            "schema": POLICY_SCHEMA,
            "status": "APPROVED",
            "release_key_pem": pem,
            "key_fingerprint_sha256":
                hashlib.sha256(raw).hexdigest(),
            "attestation_key_fingerprints_sha256": ["a" * 64],
            "scope": "GEN11_PROTECTED_BOOT_ADMISSION_ONLY",
        }))

        self.expected = {
            field: hashlib.sha256(field.encode()).hexdigest()
            for field in DIGEST_FIELDS
        }
        self.expected["baseline_grub_fsverity"] = (
            EXPECTED_GEN10_VERITY
        )
        self.expected["recovery_evidence_sha256"] = (
            sha_file(self.evidence)
        )

        now = datetime.now(timezone.utc)
        self.now = now

        self.payload = {
            "schema": SCHEMA,
            "action": ACTION,
            "authorization_id": "arda-gen11-test-000001",
            "generation": 11,
            "boot_profile": PROFILE,
            "destination": DESTINATION,
            **self.expected,
            "issued_at":
                (now - timedelta(seconds=5)).isoformat(),
            "expires_at":
                (now + timedelta(minutes=5)).isoformat(),
        }
        self.authorization = self.root / "authorization.json"
        self.sign()

    def sign(self):
        signature = self.key.sign(canonical(self.payload))
        self.authorization.write_text(json.dumps({
            "payload": self.payload,
            "signature": base64.b64encode(signature).decode(),
        }))

    def admit(self):
        return admit_recovery_review(
            authorization=self.authorization,
            policy_path=self.policy,
            independently_expected=self.expected,
            recovery_evidence_path=self.evidence,
            ledger_path=self.ledger,
            receipt_path=self.receipt,
            now=self.now,
            enforce_ownership=False,  # Temporary test fixture only.
        )

    def test_valid_signature_creates_bound_receipt(self):
        result = self.admit()
        self.assertEqual(
            result["status"],
            "RECOVERY_EVIDENCE_BOUND_FOR_REVIEW",
        )
        self.assertEqual(
            result["recovery_evidence_sha256"],
            sha_file(self.evidence),
        )
        self.assertFalse(result["production_install_authorized"])
        self.assertFalse(result["first_boot_authorized"])
        self.assertFalse(result["boot_configuration_modified"])
        self.assertTrue(self.receipt.is_file())

    def test_authorization_replay_refused(self):
        self.admit()
        self.receipt.unlink()
        with self.assertRaises(Refuse):
            self.admit()

    def test_tampered_recovery_evidence_refused(self):
        self.evidence.write_text('{"recovered":false}\n')
        with self.assertRaises(Refuse):
            self.admit()
        self.assertFalse(self.receipt.exists())

    def test_tampered_signed_payload_refused(self):
        self.payload["gen11_kernel_sha256"] = "f" * 64
        # Do not re-sign.
        doc = json.loads(self.authorization.read_text())
        doc["payload"] = self.payload
        self.authorization.write_text(json.dumps(doc))
        with self.assertRaises(Refuse):
            self.admit()

    def test_expired_authorization_refused(self):
        self.payload["expires_at"] = (
            self.now - timedelta(seconds=1)
        ).isoformat()
        self.sign()
        with self.assertRaises(Refuse):
            self.admit()


if __name__ == "__main__":
    unittest.main()
