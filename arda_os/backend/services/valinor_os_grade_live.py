"""Live adapter for restored Valinor OS-grade appraisal."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from backend.services.boot_measurement import measure_boot_state
from backend.services.os_enforcement_service import OsEnforcementService
from backend.services.phase4_rollout_control import (
    RolloutControlError,
    TrustedVerifierVerdict,
)
from backend.services.valinor_os_grade import evaluate_valinor_os_grade


DEFAULT_VERDICT = Path("/var/lib/arda/verifier/latest-verdict.json")
DEFAULT_VERIFIER_KEY = Path("/etc/arda/verifier/verifier-key.pub.pem")
DEFAULT_VERIFIER_KEY_ID = "arda-phase4-verifier"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def inspect_live_valinor_os_grade(
    *,
    verdict_path: Path = DEFAULT_VERDICT,
    verifier_public_key: Path = DEFAULT_VERIFIER_KEY,
    verifier_key_id: str = DEFAULT_VERIFIER_KEY_ID,
) -> dict[str, Any]:
    if verdict_path.is_file():
        verifier_result = _load_json(verdict_path)
    else:
        verifier_result = {
            "gate": {},
            "signed_verdict": {},
            "verifier": {},
        }

    signature_verified = False
    signature_error = None

    signed_verdict_present = isinstance(
        verifier_result.get("signed_verdict"),
        dict,
    ) and bool(verifier_result.get("signed_verdict"))

    if signed_verdict_present and verifier_public_key.is_file():
        try:
            verifier = TrustedVerifierVerdict(
                str(verifier_public_key),
                key_id=verifier_key_id,
            )
            verifier.verify(verifier_result)
            signature_verified = True
        except RolloutControlError as exc:
            signature_error = str(exc)
        except Exception as exc:
            signature_error = f"{type(exc).__name__}: {exc}"
    elif signed_verdict_present:
        signature_error = f"verifier public key missing: {verifier_public_key}"
    else:
        signature_error = f"verifier verdict missing: {verdict_path}"

    service = OsEnforcementService(arm=False)
    try:
        status = service.get_status()
    finally:
        service.shutdown()

    local_evidence = (
        (verifier_result.get("gate") or {}).get("local_evidence") or {}
    )
    pcr_values = (
        (local_evidence.get("boot_measurement") or {}).get("pcrs") or {}
    )
    boot_measurement = measure_boot_state(pcrs=pcr_values)

    report = evaluate_valinor_os_grade(
        status=status,
        verifier_result=verifier_result,
        boot_measurement=boot_measurement,
        signature_verified=signature_verified,
    )

    report["verifier_signature_verified"] = signature_verified
    report["verifier_signature_error"] = signature_error
    report["verdict_path"] = str(verdict_path)
    report["verifier_public_key"] = str(verifier_public_key)

    return report
