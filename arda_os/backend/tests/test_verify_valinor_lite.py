import json
import subprocess
from pathlib import Path

from backend.services.attestation_profile import (
    LITE_PROFILE,
)
from backend.services.valinor_lite_evidence import (
    LiteEvidence,
)

from kernel.valinor.lite.verify.verify_valinor_lite import (
    VerificationReport,
    render_text_report,
    verify_valinor_lite,
)


def _evidence(
    *,
    kernel_identity_verified=True,
    initramfs_identity_verified=True,
    bpf_lsm_available=True,
    measured_maps_available=True,
    pqc_native_verified=True,
    secure_boot_state="disabled",
):
    software_rooted = all(
        (
            kernel_identity_verified,
            initramfs_identity_verified,
            bpf_lsm_available,
            measured_maps_available,
            pqc_native_verified,
        )
    )

    return LiteEvidence(
        kernel_sha256="a" * 64,
        initramfs_sha256="b" * 64,
        kernel_identity_verified=kernel_identity_verified,
        initramfs_identity_verified=initramfs_identity_verified,
        bpf_lsm_available=bpf_lsm_available,
        measured_maps_available=measured_maps_available,
        pqc_native_verified=pqc_native_verified,
        secure_boot_state=secure_boot_state,
        software_rooted=software_rooted,
    )


def test_no_tpm_lite_report_is_truthful_and_verified():
    report = verify_valinor_lite(
        profile=LITE_PROFILE,
        evidence=_evidence(),
        tpm_available=False,
        enforcement_mode="audit",
    )

    assert isinstance(report, VerificationReport)

    assert report.trust_profile == "VALINOR_LITE"
    assert report.tpm == "ABSENT"
    assert report.hardware_root == "UNAVAILABLE"
    assert report.software_root == "VERIFIED"
    assert report.kernel_identity == "VERIFIED"
    assert report.bpf_lsm == "VERIFIED"
    assert report.pqc == "VERIFIED"
    assert report.enforcement_mode == "AUDIT"
    assert report.ok is True


def test_human_report_pins_exact_no_tpm_semantics():
    report = verify_valinor_lite(
        profile=LITE_PROFILE,
        evidence=_evidence(),
        tpm_available=False,
        enforcement_mode="audit",
    )

    text = render_text_report(report)

    expected_lines = (
        "TRUST PROFILE .............. VALINOR_LITE",
        "TPM ......................... ABSENT",
        "HARDWARE ROOT ............... UNAVAILABLE",
        "SOFTWARE ROOT ............... VERIFIED",
        "KERNEL IDENTITY ............. VERIFIED",
        "BPF LSM ..................... VERIFIED",
        "PQC ......................... VERIFIED",
        "ENFORCEMENT MODE ............ AUDIT",
    )

    for line in expected_lines:
        assert line in text


def test_json_report_contains_truthful_fields():
    report = verify_valinor_lite(
        profile=LITE_PROFILE,
        evidence=_evidence(),
        tpm_available=False,
        enforcement_mode="audit",
    )

    payload = report.to_dict()

    assert payload["schema_version"] == (
        "valinor-lite-verification-v1"
    )
    assert payload["trust_profile"] == "VALINOR_LITE"
    assert payload["tpm"] == "ABSENT"
    assert payload["hardware_root"] == "UNAVAILABLE"
    assert payload["software_root"] == "VERIFIED"
    assert payload["kernel_identity"] == "VERIFIED"
    assert payload["bpf_lsm"] == "VERIFIED"
    assert payload["pqc"] == "VERIFIED"
    assert payload["enforcement_mode"] == "AUDIT"
    assert payload["ok"] is True


def test_wrong_kernel_fails_kernel_identity_and_software_root():
    report = verify_valinor_lite(
        profile=LITE_PROFILE,
        evidence=_evidence(
            kernel_identity_verified=False,
        ),
        tpm_available=False,
        enforcement_mode="audit",
    )

    assert report.kernel_identity == "FAILED"
    assert report.software_root == "FAILED"
    assert report.ok is False


def test_bpf_unavailable_fails_bpf_and_software_root():
    report = verify_valinor_lite(
        profile=LITE_PROFILE,
        evidence=_evidence(
            bpf_lsm_available=False,
        ),
        tpm_available=False,
        enforcement_mode="audit",
    )

    assert report.bpf_lsm == "FAILED"
    assert report.software_root == "FAILED"
    assert report.ok is False


def test_missing_measured_maps_fails_software_root():
    report = verify_valinor_lite(
        profile=LITE_PROFILE,
        evidence=_evidence(
            measured_maps_available=False,
        ),
        tpm_available=False,
        enforcement_mode="audit",
    )

    assert report.software_root == "FAILED"
    assert report.ok is False


def test_native_pqc_unavailable_fails_pqc_and_software_root():
    report = verify_valinor_lite(
        profile=LITE_PROFILE,
        evidence=_evidence(
            pqc_native_verified=False,
        ),
        tpm_available=False,
        enforcement_mode="audit",
    )

    assert report.pqc == "FAILED"
    assert report.software_root == "FAILED"
    assert report.ok is False


def test_tpm_present_does_not_make_lite_hardware_rooted():
    report = verify_valinor_lite(
        profile=LITE_PROFILE,
        evidence=_evidence(),
        tpm_available=True,
        enforcement_mode="audit",
    )

    assert report.tpm == "PRESENT"
    assert report.hardware_root == "UNAVAILABLE"
    assert report.software_root == "VERIFIED"
    assert report.ok is True


def test_secure_boot_does_not_make_lite_hardware_rooted():
    report = verify_valinor_lite(
        profile=LITE_PROFILE,
        evidence=_evidence(
            secure_boot_state="enabled",
        ),
        tpm_available=True,
        enforcement_mode="audit",
    )

    assert report.hardware_root == "UNAVAILABLE"
    assert report.software_root == "VERIFIED"


def test_non_lite_profile_is_refused():
    from backend.services.attestation_profile import (
        FULL_PROFILE,
    )

    report = verify_valinor_lite(
        profile=FULL_PROFILE,
        evidence=_evidence(),
        tpm_available=True,
        enforcement_mode="audit",
    )

    assert report.ok is False
    assert "wrong_profile" in report.failures


def test_enforcement_must_begin_in_audit():
    report = verify_valinor_lite(
        profile=LITE_PROFILE,
        evidence=_evidence(),
        tpm_available=False,
        enforcement_mode="fsverity_strict",
    )

    assert report.enforcement_mode == "FSVERITY_STRICT"
    assert report.ok is False
    assert "enforcement_not_audit" in report.failures


def test_verifier_does_not_mutate_enforcement_state(tmp_path):
    mode = tmp_path / "enforcement-mode"
    mode.write_text(
        "audit\n",
        encoding="utf-8",
    )

    before = mode.read_bytes()

    report = verify_valinor_lite(
        profile=LITE_PROFILE,
        evidence=_evidence(),
        tpm_available=False,
        enforcement_mode=mode.read_text().strip(),
    )

    after = mode.read_bytes()

    assert report.ok is True
    assert before == after
    assert b"fsverity_strict" not in after


def test_report_exposes_degraded_reasons_independently():
    report = verify_valinor_lite(
        profile=LITE_PROFILE,
        evidence=_evidence(
            kernel_identity_verified=False,
            bpf_lsm_available=False,
            pqc_native_verified=False,
        ),
        tpm_available=False,
        enforcement_mode="audit",
    )

    assert "kernel_identity_failed" in report.failures
    assert "bpf_lsm_unavailable" in report.failures
    assert "native_pqc_unverified" in report.failures
    assert "software_root_unverified" in report.failures


def test_cli_default_human_report(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    entry = (
        repo_root
        / "arda_os"
        / "kernel"
        / "valinor"
        / "lite"
        / "verify-valinor-lite"
    )

    fixture = tmp_path / "evidence.json"
    fixture.write_text(
        json.dumps(
            {
                "profile": "lite",
                "tpm_available": False,
                "enforcement_mode": "audit",
                "evidence": {
                    "kernel_sha256": "a" * 64,
                    "initramfs_sha256": "b" * 64,
                    "kernel_identity_verified": True,
                    "initramfs_identity_verified": True,
                    "bpf_lsm_available": True,
                    "measured_maps_available": True,
                    "pqc_native_verified": True,
                    "secure_boot_state": "disabled",
                    "software_rooted": True,
                },
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            str(entry),
            "--evidence-file",
            str(fixture),
        ],
        capture_output=True,
        text=True,
        check=False,
        env={
            **__import__("os").environ,
            "PYTHONPATH": str(repo_root / "arda_os"),
        },
    )

    assert result.returncode == 0
    assert "TRUST PROFILE .............. VALINOR_LITE" in (
        result.stdout
    )
    assert "SOFTWARE ROOT ............... VERIFIED" in (
        result.stdout
    )


def test_cli_json_report(tmp_path):
    repo_root = Path(__file__).resolve().parents[3]
    entry = (
        repo_root
        / "arda_os"
        / "kernel"
        / "valinor"
        / "lite"
        / "verify-valinor-lite"
    )

    fixture = tmp_path / "evidence.json"
    fixture.write_text(
        json.dumps(
            {
                "profile": "lite",
                "tpm_available": False,
                "enforcement_mode": "audit",
                "evidence": {
                    "kernel_sha256": "a" * 64,
                    "initramfs_sha256": "b" * 64,
                    "kernel_identity_verified": True,
                    "initramfs_identity_verified": True,
                    "bpf_lsm_available": True,
                    "measured_maps_available": True,
                    "pqc_native_verified": True,
                    "secure_boot_state": "disabled",
                    "software_rooted": True,
                },
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            str(entry),
            "--json",
            "--evidence-file",
            str(fixture),
        ],
        capture_output=True,
        text=True,
        check=False,
        env={
            **__import__("os").environ,
            "PYTHONPATH": str(repo_root / "arda_os"),
        },
    )

    assert result.returncode == 0

    payload = json.loads(result.stdout)

    assert payload["trust_profile"] == "VALINOR_LITE"
    assert payload["hardware_root"] == "UNAVAILABLE"
    assert payload["software_root"] == "VERIFIED"


def test_cli_exits_nonzero_when_required_evidence_fails(
    tmp_path,
):
    repo_root = Path(__file__).resolve().parents[3]
    entry = (
        repo_root
        / "arda_os"
        / "kernel"
        / "valinor"
        / "lite"
        / "verify-valinor-lite"
    )

    fixture = tmp_path / "evidence.json"
    fixture.write_text(
        json.dumps(
            {
                "profile": "lite",
                "tpm_available": False,
                "enforcement_mode": "audit",
                "evidence": {
                    "kernel_sha256": "bad",
                    "initramfs_sha256": "b" * 64,
                    "kernel_identity_verified": False,
                    "initramfs_identity_verified": True,
                    "bpf_lsm_available": True,
                    "measured_maps_available": True,
                    "pqc_native_verified": True,
                    "secure_boot_state": "disabled",
                    "software_rooted": False,
                },
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            str(entry),
            "--json",
            "--evidence-file",
            str(fixture),
        ],
        capture_output=True,
        text=True,
        check=False,
        env={
            **__import__("os").environ,
            "PYTHONPATH": str(repo_root / "arda_os"),
        },
    )

    assert result.returncode != 0

    payload = json.loads(result.stdout)

    assert payload["kernel_identity"] == "FAILED"
    assert payload["software_root"] == "FAILED"
    assert payload["ok"] is False
