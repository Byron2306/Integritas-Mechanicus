"""Restored Valinor sovereign OS-grade appraisal.

This module restores the July 2026 ARDA OS-grade contract without replacing
the October proof subsystem.

Authority remains with the existing ARDA substrate:
- kernel-authoritative BPF enforcement,
- measured identity / fsverity_strict,
- projected constitutional policy,
- Valinor boot state,
- TPM-backed Phase 4 attestation,
- verifier-signed verdicts.

The grader observes those authorities. It does not create a new one.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping


SOFTWARE_BOUNDARY = "software OS-grade production milestone"
HARDWARE_BOUNDARY = "hardware-rooted OS-grade production milestone"

REQUIRED_PCRS = {"0", "1", "7", "11"}
FRESH_VERDICT_SECONDS = 600


def _utc(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _active_records(status: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    phase3 = status.get("phase3_measured_identity") or {}
    required_maps = phase3.get("required_maps") or {}
    records = required_maps.get("active_records") or []
    return [
        record
        for record in records
        if isinstance(record, Mapping) and record.get("state") == "active"
    ]


def _strict_active_records(status: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        record
        for record in _active_records(status)
        if record.get("enforcement_mode") == "fsverity_strict"
    ]


def _signed_verdict(verifier_result: Mapping[str, Any]) -> Mapping[str, Any]:
    verdict = verifier_result.get("signed_verdict")
    return verdict if isinstance(verdict, Mapping) else {}


def _tpm_identity(verifier_result: Mapping[str, Any]) -> Mapping[str, Any]:
    signed = _signed_verdict(verifier_result)
    identity = signed.get("tpm_identity")
    if isinstance(identity, Mapping):
        return identity

    gate = verifier_result.get("gate") or {}
    local = gate.get("local_evidence") or {}
    identity = local.get("tpm_identity")
    return identity if isinstance(identity, Mapping) else {}


def _local_evidence(verifier_result: Mapping[str, Any]) -> Mapping[str, Any]:
    gate = verifier_result.get("gate") or {}
    local = gate.get("local_evidence")
    return local if isinstance(local, Mapping) else {}


def _boot_measurement(
    verifier_result: Mapping[str, Any],
    supplied: Mapping[str, Any] | None,
) -> Mapping[str, Any]:
    if supplied:
        return supplied
    local = _local_evidence(verifier_result)
    value = local.get("boot_measurement")
    return value if isinstance(value, Mapping) else {}


def evaluate_valinor_os_grade(
    *,
    status: Mapping[str, Any],
    verifier_result: Mapping[str, Any],
    boot_measurement: Mapping[str, Any] | None = None,
    signature_verified: bool,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate the frozen July-30 Valinor OS-grade contract.

    `signature_verified` MUST come from verification against the pinned
    verifier public key. Embedded verifier key material alone is not authority.
    """

    instant = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    required_maps = status.get("required_maps") or {}
    policy_state = status.get("policy_projection_state") or {}
    strict_records = _strict_active_records(status)

    software_checks = {
        "bpf_authoritative": bool(
            status.get("is_authoritative") and not status.get("is_simulation")
        ),
        "authoritative_maps_present": bool(
            required_maps.get("all_required_present")
        ),
        "policy_projection_non_empty": bool(
            policy_state.get("generation_hash_prefix")
        ),
        "constitutional_redlines_present": int(
            policy_state.get("redline_rule_count") or 0
        ) > 0,
        "active_measured_identity": bool(strict_records),
        "fsverity_strict": bool(strict_records),
    }

    software_os_grade = all(software_checks.values())

    measurement = _boot_measurement(verifier_result, boot_measurement)
    local = _local_evidence(verifier_result)
    quote = local.get("tpm_quote_verification") or {}
    identity = _tpm_identity(verifier_result)
    binding = local.get("software_state_binding") or {}

    pcr_values = measurement.get("pcrs") or {}
    present_pcrs = {str(key) for key, value in pcr_values.items() if value}

    secure_boot = measurement.get("secure_boot") or {}
    setup_mode = measurement.get("setup_mode") or {}
    lockdown = measurement.get("lockdown") or {}
    kernel_release = measurement.get("kernel_release") or {}

    signed = _signed_verdict(verifier_result)
    issued_at_text = signed.get("issued_at")
    verdict_age_seconds = None
    verdict_fresh = False

    if issued_at_text:
        try:
            issued_at = _utc(str(issued_at_text))
            verdict_age_seconds = (instant - issued_at).total_seconds()
            verdict_fresh = 0 <= verdict_age_seconds <= FRESH_VERDICT_SECONDS
        except Exception:
            verdict_fresh = False

    signed_verdict_present = bool(signed)
    signed_verdict_green = bool(
        signature_verified
        and signed.get("ok") is True
        and signed.get("production_ready") is True
        and not (signed.get("failures") or [])
    )
    remote_verifier_signed_fresh = bool(
        signed_verdict_present
        and signature_verified
        and verdict_fresh
    )

    kernel_value = str(kernel_release.get("value") or "")
    lockdown_value = str(lockdown.get("value") or "").lower()

    hardware_checks = {
        "software_os_grade": software_os_grade,
        "valinor_kernel": "valinor" in kernel_value.lower(),
        "secure_boot_enabled": (
            secure_boot.get("available") is True
            and secure_boot.get("enabled") is True
        ),
        "setup_mode_disabled": (
            setup_mode.get("available") is True
            and setup_mode.get("enabled") is False
        ),
        "efi_lockdown": (
            lockdown.get("available") is True
            and (
                "integrity" in lockdown_value
                or "confidentiality" in lockdown_value
            )
        ),
        "required_pcrs_present": REQUIRED_PCRS.issubset(present_pcrs),
        "tpm_quote_verified": quote.get("ok") is True,
        "manufacturer_rooted_tpm": bool(
            identity.get("present")
            and identity.get("manufacturer_rooted")
            and identity.get("ak_certified_by_ek")
        ),
        "software_state_bound": bool(
            binding.get("available") and binding.get("bound")
        ),
        "signed_verdict_present": signed_verdict_present,
        "remote_verifier_signed_fresh": remote_verifier_signed_fresh,
        "signed_verdict_green": signed_verdict_green,
    }

    hardware_rooted_os_grade = all(hardware_checks.values())

    latest_record = None
    if strict_records:
        latest_record = max(
            strict_records,
            key=lambda record: int(record.get("generation") or 0),
        )

    failures = [
        f"software:{name}"
        for name, ok in software_checks.items()
        if not ok
    ]
    failures.extend(
        f"hardware:{name}"
        for name, ok in hardware_checks.items()
        if not ok
    )

    if hardware_rooted_os_grade:
        boundary = HARDWARE_BOUNDARY
    elif software_os_grade:
        boundary = SOFTWARE_BOUNDARY
    else:
        boundary = "below software OS-grade"

    return {
        "ok": hardware_rooted_os_grade,
        "software_os_grade": software_os_grade,
        "hardware_rooted_os_grade": hardware_rooted_os_grade,
        "boundary": boundary,
        "signed_verdict_present": signed_verdict_present,
        "remote_verifier_signed_fresh": remote_verifier_signed_fresh,
        "signed_verdict_green": signed_verdict_green,
        "verdict_age_seconds": verdict_age_seconds,
        "active_generation": (
            latest_record.get("generation") if latest_record else None
        ),
        "active_manifest_id": (
            latest_record.get("manifest_id") if latest_record else None
        ),
        "software_checks": software_checks,
        "hardware_checks": hardware_checks,
        "failures": failures,
    }
