"""Durable Gen11 release/recovery evidence coordinator.

Review-only. Never authorizes installation, boot selection, or
modification of protected boot artifacts.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from arda_gen11_production_authority import Refuse, sha_file

SCHEMA = "arda-gen11-governed-recovery-review-v1"
RECEIPT_SCHEMA = "arda-gen11-recovery-transaction-receipt-v1"


def require(ok, reason):
    if not ok:
        raise Refuse(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


class RecoveryCoordinator:
    def __init__(self, database, admission_database):
        self.path = Path(database)
        self.admission_path = Path(admission_database)

        for p in (self.path, self.admission_path):
            require(p.is_absolute(), "database_path_not_absolute")
            require(p.parent.is_dir(), "database_parent_missing")
            require(not p.is_symlink(), "database_symlink")

        require(self.path != self.admission_path, "database_alias")
        require(self.admission_path.is_file(), "admission_ledger_missing")

        self.conn = sqlite3.connect(
            str(self.path), isolation_level=None, timeout=10
        )
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                authorization_id TEXT PRIMARY KEY,
                authorization_sha256 TEXT NOT NULL,
                review_sha256 TEXT NOT NULL,
                recovery_sha256 TEXT NOT NULL,
                state TEXT NOT NULL CHECK(
                    state IN ('REVIEW_RECORDED', 'REFUSED')
                )
            )
        """)

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _check_admission(self, authorization_id, authorization_sha256):
        uri = "file:" + str(self.admission_path) + "?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=10) as db:
            row = db.execute(
                "SELECT digest, state FROM admissions WHERE id=?",
                (authorization_id,),
            ).fetchone()

        require(row is not None, "admission_not_found")
        require(row == (authorization_sha256, "review_required"),
                "admission_ledger_mismatch")

    def record_review(self, *, review_path, recovery_path):
        review_path = Path(review_path)
        recovery_path = Path(recovery_path)

        for p in (review_path, recovery_path):
            require(p.is_file() and not p.is_symlink(),
                    "evidence_missing_or_symlink")

        review_bytes = review_path.read_bytes()
        review = json.loads(review_bytes)

        require(type(review) is dict, "review_not_object")
        require(review.get("schema") == SCHEMA, "review_schema")
        require(
            review.get("status") == "RECOVERY_EVIDENCE_BOUND_FOR_REVIEW",
            "review_status",
        )

        for name in (
            "production_install_authorized",
            "first_boot_authorized",
            "fsverity_install_performed",
            "boot_configuration_modified",
        ):
            require(review.get(name) is False,
                    "review_claims_privilege:" + name)

        authorization_id = review.get("authorization_id")
        authorization_hash = review.get("authorization_sha256")
        recovery_hash = review.get("recovery_evidence_sha256")

        require(type(authorization_id) is str and
                16 <= len(authorization_id) <= 100,
                "authorization_id")
        for value in (authorization_hash, recovery_hash):
            require(
                type(value) is str
                and len(value) == 64
                and all(c in "0123456789abcdef" for c in value),
                "invalid_digest",
            )

        require(sha_file(recovery_path) == recovery_hash,
                "recovery_evidence_changed")

        self._check_admission(authorization_id, authorization_hash)

        self.conn.execute("BEGIN IMMEDIATE")
        try:
            self.conn.execute(
                """INSERT INTO transactions
                   (authorization_id, authorization_sha256,
                    review_sha256, recovery_sha256, state)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    authorization_id,
                    authorization_hash,
                    digest(review_bytes),
                    recovery_hash,
                    "REVIEW_RECORDED",
                ),
            )
            self.conn.execute("COMMIT")
        except BaseException:
            if self.conn.in_transaction:
                self.conn.execute("ROLLBACK")
            raise

        return {
            "schema": RECEIPT_SCHEMA,
            "status": "REVIEW_RECORDED",
            "authorization_id": authorization_id,
            "review_sha256": digest(review_bytes),
            "recovery_sha256": recovery_hash,
            "production_install_authorized": False,
            "first_boot_authorized": False,
            "transaction_committed": False,
        }

    def status(self, authorization_id):
        row = self.conn.execute(
            "SELECT state FROM transactions WHERE authorization_id=?",
            (authorization_id,),
        ).fetchone()
        require(row is not None, "transaction_not_found")
        return row[0]
