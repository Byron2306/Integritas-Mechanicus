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

from arda_gen11_production_authority import Refuse
from arda_gen11_recovery_coordinator import RecoveryCoordinator


class RecoveryCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

        self.admission = self.root / "admissions.sqlite"
        self.transactions = self.root / "transactions.sqlite"
        self.recovery = self.root / "recovery.json"
        self.review = self.root / "review.json"

        self.auth_id = "arda-gen11-coordinator-test-01"
        self.auth_digest = "a" * 64

        self.recovery.write_text('{"status":"PRIMARY_RESTORED"}\n')
        self.recovery_digest = hashlib.sha256(
            self.recovery.read_bytes()
        ).hexdigest()

        with sqlite3.connect(self.admission) as db:
            db.execute("""
                CREATE TABLE admissions (
                    id TEXT PRIMARY KEY,
                    digest TEXT NOT NULL,
                    state TEXT NOT NULL
                )
            """)
            db.execute(
                "INSERT INTO admissions VALUES (?, ?, ?)",
                (self.auth_id, self.auth_digest, "review_required"),
            )

        self.data = {
            "schema": "arda-gen11-governed-recovery-review-v1",
            "status": "RECOVERY_EVIDENCE_BOUND_FOR_REVIEW",
            "authorization_id": self.auth_id,
            "authorization_sha256": self.auth_digest,
            "recovery_evidence_sha256": self.recovery_digest,
            "production_install_authorized": False,
            "first_boot_authorized": False,
            "fsverity_install_performed": False,
            "boot_configuration_modified": False,
        }
        self.save_review()

    def save_review(self):
        self.review.write_text(json.dumps(self.data))

    def record(self):
        with RecoveryCoordinator(
            self.transactions, self.admission
        ) as coordinator:
            return coordinator.record_review(
                review_path=self.review,
                recovery_path=self.recovery,
            )

    def test_durable_record_survives_reopen(self):
        result = self.record()
        self.assertEqual(result["status"], "REVIEW_RECORDED")
        self.assertFalse(result["production_install_authorized"])

        with RecoveryCoordinator(
            self.transactions, self.admission
        ) as coordinator:
            self.assertEqual(
                coordinator.status(self.auth_id),
                "REVIEW_RECORDED",
            )

    def test_replay_refused(self):
        self.record()
        with self.assertRaises(sqlite3.IntegrityError):
            self.record()

    def test_tampered_recovery_refused(self):
        self.recovery.write_text("tampered")
        with self.assertRaises(Refuse):
            self.record()

    def test_forged_install_permission_refused(self):
        self.data["production_install_authorized"] = True
        self.save_review()
        with self.assertRaises(Refuse):
            self.record()

    def test_missing_admission_refused(self):
        self.data["authorization_id"] = "missing-admission-0001"
        self.save_review()
        with self.assertRaises(Refuse):
            self.record()

    def test_admission_digest_mismatch_refused(self):
        self.data["authorization_sha256"] = "b" * 64
        self.save_review()
        with self.assertRaises(Refuse):
            self.record()


if __name__ == "__main__":
    unittest.main()
