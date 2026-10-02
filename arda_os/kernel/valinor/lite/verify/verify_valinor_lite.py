"""Truthful first-boot verifier for Valinor Lite."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from backend.services.attestation_profile import (
    AttestationProfile,
)
from backend.services.valinor_lite_evidence import (
    LiteEvidence,
)


SCHEMA_VERSION = "valinor-lite-verification-v1"


@dataclass(frozen=True)
class VerificationReport:
    schema_version: str
    trust_profile: str
    tpm: str
    hardware_root: str
    software_root: str
    kernel_identity: str
    bpf_lsm: str
    pqc: str
    enforcement_mode: str
    secure_boot_state: str
    measured_maps: str
    initramfs_identity: str
    ok: bool
    failures: tuple[str, ...]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["failures"] = list(self.failures)
        return payload


def verify_valinor_lite(
    *,
    profile: AttestationProfile,
    evidence: LiteEvidence,
    tpm_available: bool,
    enforcement_mode: str,
) -> VerificationReport:
    failures: list[str] = []

    trust_profile = (
        "VALINOR_LITE"
        if profile.name == "lite"
        else profile.name.upper()
    )

    if profile.name != "lite":
        failures.append("wrong_profile")

    kernel_identity = (
        "VERIFIED"
        if evidence.kernel_identity_verified
        else "FAILED"
    )

    if not evidence.kernel_identity_verified:
        failures.append("kernel_identity_failed")

    initramfs_identity = (
        "VERIFIED"
        if evidence.initramfs_identity_verified
        else "FAILED"
    )

    if not evidence.initramfs_identity_verified:
        failures.append("initramfs_identity_failed")

    bpf_lsm = (
        "VERIFIED"
        if evidence.bpf_lsm_available
        else "FAILED"
    )

    if not evidence.bpf_lsm_available:
        failures.append("bpf_lsm_unavailable")

    measured_maps = (
        "VERIFIED"
        if evidence.measured_maps_available
        else "FAILED"
    )

    if not evidence.measured_maps_available:
        failures.append("measured_maps_unavailable")

    pqc = (
        "VERIFIED"
        if evidence.pqc_native_verified
        else "FAILED"
    )

    if not evidence.pqc_native_verified:
        failures.append("native_pqc_unverified")

    software_root = (
        "VERIFIED"
        if evidence.software_rooted
        else "FAILED"
    )

    if not evidence.software_rooted:
        failures.append("software_root_unverified")

    normalized_enforcement = (
        str(enforcement_mode).strip().upper()
    )

    if normalized_enforcement != "AUDIT":
        failures.append("enforcement_not_audit")

    tpm = "PRESENT" if tpm_available else "ABSENT"

    # Lite never claims hardware-rooted trust merely because TPM or
    # Secure Boot happen to be present. That belongs to the Full profile.
    hardware_root = "UNAVAILABLE"

    ok = len(failures) == 0

    return VerificationReport(
        schema_version=SCHEMA_VERSION,
        trust_profile=trust_profile,
        tpm=tpm,
        hardware_root=hardware_root,
        software_root=software_root,
        kernel_identity=kernel_identity,
        bpf_lsm=bpf_lsm,
        pqc=pqc,
        enforcement_mode=normalized_enforcement,
        secure_boot_state=str(
            evidence.secure_boot_state
        ).upper(),
        measured_maps=measured_maps,
        initramfs_identity=initramfs_identity,
        ok=ok,
        failures=tuple(failures),
    )


def render_text_report(
    report: VerificationReport,
) -> str:
    lines = [
        (
            "TRUST PROFILE .............. "
            f"{report.trust_profile}"
        ),
        (
            "TPM ......................... "
            f"{report.tpm}"
        ),
        (
            "HARDWARE ROOT ............... "
            f"{report.hardware_root}"
        ),
        (
            "SOFTWARE ROOT ............... "
            f"{report.software_root}"
        ),
        (
            "KERNEL IDENTITY ............. "
            f"{report.kernel_identity}"
        ),
        (
            "BPF LSM ..................... "
            f"{report.bpf_lsm}"
        ),
        (
            "PQC ......................... "
            f"{report.pqc}"
        ),
        (
            "ENFORCEMENT MODE ............ "
            f"{report.enforcement_mode}"
        ),
    ]

    return "\n".join(lines) + "\n"


__all__ = [
    "VerificationReport",
    "render_text_report",
    "verify_valinor_lite",
]
