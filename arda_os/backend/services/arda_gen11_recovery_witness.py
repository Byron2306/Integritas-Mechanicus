"""Signed Gen11 transaction-to-recovery witness verifier.

Review and evidence recording only. Never grants install or boot authority.
"""
from __future__ import annotations

import base64
import hashlib
import json
import sqlite3
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from arda_gen11_production_authority import (
    Refuse, canonical, safe_public_file, sha_file,
)

SCHEMA = "arda-gen11-transaction-recovery-witness-v1"
FIELDS = {
    "schema", "authorization_id", "authorization_sha256",
    "review_sha256", "recovery_evidence_sha256",
    "recovery_receipt_sha256", "recovery_status",
}


def require(ok, why):
    if not ok:
        raise Refuse(why)


def verify_witness(
    *, witness_path, recovery_receipt_path,
    transaction_database, recovery_public_key,
    enforce_ownership=True,
):
    """Authenticate a recovery witness against an existing review transaction."""

    wp = Path(witness_path)
    rp = Path(recovery_receipt_path)
    dbp = Path(transaction_database)
    kp = Path(recovery_public_key)

    for p in (wp, rp, dbp, kp):
        require(p.is_absolute() and p.is_file() and not p.is_symlink(),
                "missing_or_unsafe_input")

    if enforce_ownership:
        safe_public_file(kp)

    envelope = json.loads(wp.read_text())
    require(type(envelope) is dict and
            set(envelope) == {"payload", "signature"},
            "witness_envelope")

    payload = envelope["payload"]
    require(type(payload) is dict and set(payload) == FIELDS,
            "witness_fields")
    require(payload["schema"] == SCHEMA, "witness_schema")
    require(payload["recovery_status"] == "ROLLED_BACK",
            "unrecognized_recovery_status")

    for name in (
        "authorization_sha256", "review_sha256",
        "recovery_evidence_sha256", "recovery_receipt_sha256",
    ):
        value = payload[name]
        require(type(value) is str and len(value) == 64
                and all(c in "0123456789abcdef" for c in value),
                "invalid_digest:" + name)

    require(type(payload["authorization_id"]) is str
            and 16 <= len(payload["authorization_id"]) <= 100,
            "authorization_id")

    key = serialization.load_pem_public_key(kp.read_bytes())
    require(isinstance(key, Ed25519PublicKey), "wrong_key_type")

    try:
        sig = base64.b64decode(envelope["signature"], validate=True)
        require(len(sig) == 64, "signature_length")
        key.verify(sig, canonical(payload))
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise Refuse("invalid_recovery_signature") from exc

    receipt = json.loads(rp.read_text())
    require(type(receipt) is dict, "receipt_not_object")
    require(receipt.get("schema") ==
            "arda-gen11-transaction-recovery-receipt-v1",
            "receipt_schema")
    require(receipt.get("status") == "ROLLED_BACK",
            "receipt_status")
    require(receipt.get("authorization_id") ==
            payload["authorization_id"],
            "receipt_authorization_mismatch")
    require(receipt.get("authorization_sha256") ==
            payload["authorization_sha256"],
            "receipt_authorization_digest_mismatch")
    require(receipt.get("review_sha256") ==
            payload["review_sha256"],
            "receipt_review_mismatch")
    require(receipt.get("recovery_evidence_sha256") ==
            payload["recovery_evidence_sha256"],
            "receipt_evidence_mismatch")
    require(sha_file(rp) == payload["recovery_receipt_sha256"],
            "receipt_digest_mismatch")

    uri = dbp.as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        row = conn.execute(
            """SELECT authorization_sha256, review_sha256,
                      recovery_sha256, state
               FROM transactions WHERE authorization_id=?""",
            (payload["authorization_id"],),
        ).fetchone()

    require(row == (
        payload["authorization_sha256"],
        payload["review_sha256"],
        payload["recovery_evidence_sha256"],
        "REVIEW_RECORDED",
    ), "transaction_binding_mismatch")

    return {
        "schema": "arda-gen11-recovery-witness-verdict-v1",
        "status": "SIGNED_RECOVERY_WITNESS_VERIFIED",
        "authorization_id": payload["authorization_id"],
        "witness_sha256": sha_file(wp),
        "recovery_receipt_sha256": sha_file(rp),
        "production_install_authorized": False,
        "first_boot_authorized": False,
        "boot_configuration_modified": False,
    }
