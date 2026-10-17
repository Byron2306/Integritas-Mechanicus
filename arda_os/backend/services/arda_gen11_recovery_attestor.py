"""Bind an executed sandbox rollback to a signed recovery witness.

LAB ONLY. Never installs, authorizes boot or provisions signing keys.
"""
from __future__ import annotations

import base64
import json
import sqlite3
from pathlib import Path

from arda_gen11_production_authority import Refuse, canonical, sha_file
from arda_gen11_recovery_coordinator import RecoveryCoordinator
from arda_gen11_recovery_supervisor import Supervisor, digest
from arda_gen11_recovery_witness import SCHEMA as WITNESS_SCHEMA


def need(value, reason):
    if not value:
        raise Refuse(reason)


def emit_from_executed_rollback(
    *, sandbox_root, transaction_database, admission_database,
    review_path, recovery_evidence_path, output_dir, sign,
):
    """Produce a witness only for a verified executed sandbox rollback.

    `sign` is an injected laboratory signer callable returning signature bytes.
    A production authority must NEVER be inferred from this callable.
    """
    root = Path(sandbox_root)
    output = Path(output_dir)

    need(output.is_absolute() and output.is_dir(), "output_directory")
    need(not output.is_symlink(), "output_symlink")
    need(not output.stat().st_mode & 0o022, "output_writable_by_others")

    review = json.loads(Path(review_path).read_text())
    need(review.get("status") == "RECOVERY_EVIDENCE_BOUND_FOR_REVIEW",
         "review_not_admitted")
    for field in ("production_install_authorized", "first_boot_authorized"):
        need(review.get(field) is False, "review_claims_install_authority")

    authorization_id = review["authorization_id"]
    review_hash = sha_file(review_path)
    recovery_hash = sha_file(recovery_evidence_path)

    need(review["recovery_evidence_sha256"] == recovery_hash,
         "recovery_evidence_changed")

    with RecoveryCoordinator(transaction_database, admission_database) as coordinator:
        need(coordinator.status(authorization_id) == "REVIEW_RECORDED",
             "review_transaction_missing")
        row = coordinator.conn.execute(
            """SELECT authorization_sha256, review_sha256, recovery_sha256
               FROM transactions WHERE authorization_id=?""",
            (authorization_id,),
        ).fetchone()

    need(row == (
        review["authorization_sha256"], review_hash, recovery_hash,
    ), "review_binding_mismatch")

    supervisor = Supervisor(root)
    try:
        journal = supervisor._state()
        need(journal["state"] == "ROLLED_BACK", "rollback_not_completed")
        need(journal["id"] == authorization_id,
             "rollback_authorization_mismatch")
        need(digest(supervisor.active) == journal["old"],
             "restored_artifact_mismatch")
        need(digest(supervisor.backup) == journal["old"],
             "fallback_identity_mismatch")

        recovery = json.loads(supervisor.receipt.read_text())
        need(recovery.get("schema") == "arda-gen11-recovery-proof-v1",
             "recovery_receipt_schema")
        need(recovery.get("status") == "ROLLED_BACK",
             "recovery_receipt_status")
        need(recovery.get("id") == authorization_id,
             "recovery_receipt_identity")
        need(recovery.get("restored_sha256") == journal["old"],
             "recovery_receipt_digest")
        need(recovery.get("boot_proven") is False,
             "unexpected_boot_proof")

        ledger = supervisor.conn.execute(
            "SELECT state FROM ids WHERE id=?", (authorization_id,)
        ).fetchone()
        need(ledger == ("rolled_back",), "supervisor_ledger_mismatch")
    finally:
        supervisor.conn.close()

    receipt = {
        "schema": "arda-gen11-transaction-recovery-receipt-v1",
        "status": "ROLLED_BACK",
        "authorization_id": authorization_id,
        "authorization_sha256": review["authorization_sha256"],
        "review_sha256": review_hash,
        "recovery_evidence_sha256": recovery_hash,
        "restored_artifact_sha256": journal["old"],
        "laboratory_only": True,
        "production_install_authorized": False,
        "first_boot_authorized": False,
        "boot_proven": False,
    }

    receipt_bytes = (json.dumps(receipt, sort_keys=True) + "\n").encode()
    receipt_path = output / "executed-recovery-receipt.json"
    witness_path = output / "executed-recovery-witness.json"

    need(not receipt_path.exists() and not witness_path.exists(),
         "witness_already_issued")

    # Generate signature in memory, before publishing either artifact.
    import hashlib
    receipt_hash = hashlib.sha256(receipt_bytes).hexdigest()
    payload = {
        "schema": WITNESS_SCHEMA,
        "authorization_id": authorization_id,
        "authorization_sha256": review["authorization_sha256"],
        "review_sha256": review_hash,
        "recovery_evidence_sha256": recovery_hash,
        "recovery_receipt_sha256": receipt_hash,
        "recovery_status": "ROLLED_BACK",
    }

    signature = sign(canonical(payload))
    need(type(signature) is bytes and len(signature) == 64,
         "signer_result_invalid")

    witness = {
        "payload": payload,
        "signature": base64.b64encode(signature).decode("ascii"),
    }
    witness_bytes = (json.dumps(witness, sort_keys=True) + "\n").encode()

    # Exclusive writes prevent replacing a previously issued witness.
    # Both outputs are evidence only; never interpret them as a boot grant.
    for path, data in (
        (receipt_path, receipt_bytes),
        (witness_path, witness_bytes),
    ):
        try:
            with path.open("xb") as stream:
                stream.write(data)
                stream.flush()
                import os
                os.fsync(stream.fileno())
        except FileExistsError as exc:
            raise Refuse("witness_replay") from exc

    import os
    fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

    return receipt_path, witness_path
