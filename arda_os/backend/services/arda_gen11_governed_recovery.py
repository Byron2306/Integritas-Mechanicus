"""Gen11 signed release -> durable recovery-review integration.

This is NOT a boot installer. Verification, evidence binding and
one-use admission do not authorize privileged boot mutation.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from arda_gen11_production_authority import (
    AdmissionLedger,
    Refuse,
    check_envelope,
    sha_file,
)

SCHEMA = "arda-gen11-governed-recovery-review-v1"


def require(condition, reason):
    if not condition:
        raise Refuse(reason)


def durable_receipt(path, payload):
    path = Path(path)
    require(path.is_absolute(), "receipt_must_be_absolute")
    require(path.parent.is_dir(), "receipt_parent_missing")
    require(not path.is_symlink(), "receipt_symlink")
    require(not path.exists(), "receipt_already_exists")

    forbidden = (
        "/boot/", "/etc/", "/usr/", "/sys/",
        "/run/", "/var/lib/arda/",
    )
    require(
        not str(path.resolve()).startswith(forbidden),
        "production_receipt_location_forbidden",
    )

    data = (
        json.dumps(payload, sort_keys=True, indent=2) + "\n"
    ).encode()

    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )

    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())

    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def admit_recovery_review(
    *,
    authorization,
    policy_path,
    independently_expected,
    recovery_evidence_path,
    ledger_path,
    receipt_path,
    now=None,
    enforce_ownership=True,
):
    """Verify signed release and consume one-use review admission.

    The caller MUST independently establish the expected measurements.
    A caller-supplied expected dict is not itself trusted evidence.
    """

    evidence = Path(recovery_evidence_path)

    require(
        evidence.is_file() and not evidence.is_symlink(),
        "recovery_evidence_missing",
    )

    require(
        type(independently_expected) is dict,
        "independent_measurements_required",
    )

    measured_recovery_sha256 = sha_file(evidence)

    require(
        independently_expected.get("recovery_evidence_sha256")
        == measured_recovery_sha256,
        "recovery_evidence_digest_mismatch",
    )

    # Real ARDA Ed25519 production verifier, not a boolean approval.
    decision = check_envelope(
        authorization,
        policy_path=policy_path,
        expected=independently_expected,
        now=now,
        enforce_ownership=enforce_ownership,
    )

    require(
        decision["status"] == "ADMITTED_FOR_HUMAN_REVIEW",
        "unexpected_authority_decision",
    )

    require(
        decision["installation_authorized"] is False
        and decision["first_boot_authorized"] is False,
        "authority_boundary_violation",
    )

    # Reserve BEFORE writing the review receipt.
    # A failed receipt write must not permit authorization reuse.
    ledger = AdmissionLedger(ledger_path)
    try:
        ledger.admit(decision)
    finally:
        ledger.conn.close()

    receipt = {
        "schema": SCHEMA,
        "status": "RECOVERY_EVIDENCE_BOUND_FOR_REVIEW",
        "authorization_id": decision["authorization_id"],
        "authorization_sha256":
            decision["authorization_sha256"],
        "release_key_fingerprint_sha256":
            decision["release_key_fingerprint_sha256"],
        "recovery_evidence_sha256":
            measured_recovery_sha256,
        "production_install_authorized": False,
        "first_boot_authorized": False,
        "fsverity_install_performed": False,
        "boot_configuration_modified": False,
    }

    durable_receipt(receipt_path, receipt)

    return receipt
