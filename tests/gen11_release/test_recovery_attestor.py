import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

SERVICES = Path(__file__).resolve().parents[2] / "arda_os/backend/services"
sys.path.insert(0, str(SERVICES))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from arda_gen11_production_authority import Refuse, sha_file
from arda_gen11_recovery_attestor import emit_from_executed_rollback
from arda_gen11_recovery_supervisor import Supervisor
from arda_gen11_recovery_witness import verify_witness


class ExecutedRecoveryAttestorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

        self.root = self.base / "sandbox"
        self.root.mkdir(mode=0o700)
        self.output = self.base / "output"
        self.output.mkdir(mode=0o700)

        self.key = Ed25519PrivateKey.generate()
        self.public_key = self.base / "recovery-public.pem"
        self.public_key.write_bytes(
            self.key.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )

        self.auth_id = "arda-gen11-executed-test-0001"
        self.auth_hash = "a" * 64

        self.evidence = self.base / "recovery-evidence.json"
        self.evidence.write_text('{"lab":true}\n')
        self.review = self.base / "review.json"
        review = {
            "status": "RECOVERY_EVIDENCE_BOUND_FOR_REVIEW",
            "authorization_id": self.auth_id,
            "authorization_sha256": self.auth_hash,
            "recovery_evidence_sha256": sha_file(self.evidence),
            "production_install_authorized": False,
            "first_boot_authorized": False,
        }
        self.review.write_text(json.dumps(review))

        self.admissions = self.base / "admissions.sqlite"
        with sqlite3.connect(self.admissions) as db:
            db.execute(
                "CREATE TABLE admissions (id TEXT PRIMARY KEY, digest TEXT, state TEXT)"
            )
            db.execute(
                "INSERT INTO admissions VALUES (?, ?, ?)",
                (self.auth_id, self.auth_hash, "review_required"),
            )

        self.transactions = self.base / "transactions.sqlite"
        with sqlite3.connect(self.transactions) as db:
            db.execute(
                """CREATE TABLE transactions (
                   authorization_id TEXT PRIMARY KEY,
                   authorization_sha256 TEXT,
                   review_sha256 TEXT,
                   recovery_sha256 TEXT,
                   state TEXT)"""
            )
            db.execute(
                "INSERT INTO transactions VALUES (?, ?, ?, ?, ?)",
                (
                    self.auth_id, self.auth_hash,
                    sha_file(self.review), sha_file(self.evidence),
                    "REVIEW_RECORDED",
                ),
            )

        old = b"original-grub\n"
        new = b"candidate-grub\n"
        self.old = hashlib.sha256(old).hexdigest()
        self.new = hashlib.sha256(new).hexdigest()

        (self.root / "grub.cfg").write_bytes(old)
        self.candidate = self.base / "candidate-input.cfg"
        self.candidate.write_bytes(new)

    def stage_and_rollback(self):
        s = Supervisor(self.root)
        try:
            s.begin(
                verified_decision={
                    "status": "DISPOSABLE_GUEST_INSTALL_APPROVED",
                    "destination": str(s.active),
                    "authorization_id": self.auth_id,
                    "candidate_sha256": self.new,
                    "baseline_sha256": self.old,
                },
                candidate=self.candidate,
                old_digest=self.old,
                new_digest=self.new,
            )
            with self.assertRaises(RuntimeError):
                s.install(failpoint="after_replace")
            self.assertEqual(s.watchdog_recover(), "ROLLED_BACK")
        finally:
            s.conn.close()

    def emit(self):
        return emit_from_executed_rollback(
            sandbox_root=self.root,
            transaction_database=self.transactions,
            admission_database=self.admissions,
            review_path=self.review,
            recovery_evidence_path=self.evidence,
            output_dir=self.output,
            sign=self.key.sign,
        )

    def test_executed_rollback_produces_verifiable_witness(self):
        self.stage_and_rollback()
        receipt, witness = self.emit()
        result = verify_witness(
            witness_path=witness,
            recovery_receipt_path=receipt,
            transaction_database=self.transactions,
            recovery_public_key=self.public_key,
            enforce_ownership=False,
        )
        self.assertEqual(
            result["status"], "SIGNED_RECOVERY_WITNESS_VERIFIED"
        )
        self.assertFalse(result["production_install_authorized"])

    def test_no_executed_rollback_refused(self):
        with self.assertRaises(Exception):
            self.emit()

    def test_wrong_restored_artifact_refused(self):
        self.stage_and_rollback()
        (self.root / "grub.cfg").write_bytes(b"tampered")
        with self.assertRaises(Refuse):
            self.emit()

    def test_wrong_authorization_refused(self):
        self.stage_and_rollback()
        journal = self.root / "transaction.json"
        state = json.loads(journal.read_text())
        state["id"] = "unrelated-authorization-0001"
        journal.write_text(json.dumps(state))
        with self.assertRaises(Refuse):
            self.emit()

    def test_issuance_replay_refused(self):
        self.stage_and_rollback()
        self.emit()
        with self.assertRaises(Refuse):
            self.emit()


if __name__ == "__main__":
    unittest.main()
