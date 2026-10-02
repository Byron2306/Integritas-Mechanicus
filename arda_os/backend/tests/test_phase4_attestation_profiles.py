from backend.services.attestation_profile import resolve_attestation_profile
from backend.services.phase4_live_attestation import (
    Phase4LiveAttestationError,
    Phase4LiveAttestationService,
)


def test_full_profile_refuses_when_tpm_device_is_missing(monkeypatch, tmp_path):
    service = Phase4LiveAttestationService()

    monkeypatch.setattr(
        "backend.services.phase4_live_attestation.shutil.which",
        lambda tool: f"/usr/bin/{tool}",
    )
    monkeypatch.setattr(
        "backend.services.phase4_live_attestation.os.path.exists",
        lambda path: False if path in {"/dev/tpm0", "/dev/tpmrm0"} else True,
    )

    profile = resolve_attestation_profile("full")

    try:
        service.capture(
            str(tmp_path),
            attestation_profile=profile,
        )
    except Phase4LiveAttestationError as exc:
        assert "no TPM device found" in str(exc)
    else:
        raise AssertionError("FULL profile must refuse when TPM is absent")


def test_lite_profile_without_tpm_returns_no_fabricated_tpm_evidence(
    monkeypatch,
    tmp_path,
):
    service = Phase4LiveAttestationService()

    monkeypatch.setattr(
        "backend.services.phase4_live_attestation.os.path.exists",
        lambda path: False if path in {"/dev/tpm0", "/dev/tpmrm0"} else True,
    )
    monkeypatch.setattr(
        "backend.services.phase4_live_attestation.shutil.which",
        lambda tool: None,
    )

    profile = resolve_attestation_profile("lite")

    result = service.capture(
        str(tmp_path),
        attestation_profile=profile,
    )

    assert result["ok"] is True
    assert result["attestation_profile"] == "lite"
    assert result["tpm_available"] is False
    assert result["hardware_rooted"] is False
    assert "tpm_pcr_quote" not in result["bundle"]
    assert "tpm_identity" not in result["bundle"]


def test_lite_gate_carries_truth_without_manufacturing_hardware_authority(
    monkeypatch,
):
    from datetime import datetime, timezone

    from backend.services.phase4_attestation_gate import Phase4AttestationGate

    monkeypatch.setattr(
        "backend.services.phase4_attestation_gate.get_envelope_trust_report",
        lambda envelope: {
            "verified": True,
            "externally_verifiable": True,
        },
    )

    now = datetime.now(timezone.utc)

    manifest = {
        "schema_version": "test",
        "manifest_id": "lite-test",
        "generation": 1,
        "node_id": "test-node",
        "policy_generation": "test-policy",
        "audience": "test",
        "attestation_result_id": None,
        "attestation_evidence_digest": None,
        "issued_at": now.isoformat(),
        "expires_at": now.isoformat(),
        "entries": [],
    }

    envelope = {
        "payload": {
            "timestamp": now.isoformat(),
            "boot_context": {},
        },
        "signing_algorithm": "test",
    }

    lite_evidence = {
        "schema_version": "arda-sovereign-attestation-lite-v1",
        "attestation_profile": "lite",
        "tpm_available": False,
        "hardware_rooted": False,
        "software_rooted": False,
    }

    result = Phase4AttestationGate().evaluate(
        manifest,
        envelope,
        local_evidence=lite_evidence,
        attestation_profile="lite",
        now=now,
    )

    assert result["attestation_profile"] == "lite"
    assert result["tpm_available"] is False
    assert result["hardware_rooted"] is False
    assert result["software_rooted"] is False

    assert result["ok"] is False
    assert "local_evidence_software_root_unverified" in result["failures"]

    assert not any(
        failure.startswith("local_evidence_pcr")
        or failure.startswith("local_evidence_quote")
        or failure == "local_evidence_not_silicon_signed"
        for failure in result["failures"]
    )


def test_lite_capture_promotes_only_verified_software_root(
    tmp_path,
    monkeypatch,
):
    from backend.services.phase4_live_attestation import (
        Phase4LiveAttestationService,
    )
    from backend.services.valinor_lite_evidence import LiteEvidence

    monkeypatch.setattr(
        "backend.services.phase4_live_attestation.os.path.exists",
        lambda path: False if path in ("/dev/tpm0", "/dev/tpmrm0") else True,
    )

    evidence = LiteEvidence(
        kernel_sha256="a" * 64,
        initramfs_sha256="b" * 64,
        kernel_identity_verified=True,
        initramfs_identity_verified=True,
        bpf_lsm_available=True,
        measured_maps_available=True,
        pqc_native_verified=True,
        secure_boot_state="disabled",
        software_rooted=True,
    )

    service = Phase4LiveAttestationService()

    result = service.capture(
        str(tmp_path),
        attestation_profile="lite",
        lite_evidence_collector=lambda: evidence,
    )

    assert result["ok"] is True
    assert result["attestation_profile"] == "lite"
    assert result["tpm_available"] is False
    assert result["hardware_rooted"] is False
    assert result["software_rooted"] is True

    bundle = result["bundle"]

    assert bundle["software_rooted"] is True
    assert bundle["kernel_identity_verified"] is True
    assert bundle["initramfs_identity_verified"] is True
    assert bundle["bpf_lsm_available"] is True
    assert bundle["measured_maps_available"] is True
    assert bundle["pqc_native_verified"] is True
    assert bundle["secure_boot_state"] == "disabled"
    assert "tpm_pcr_quote" not in bundle
    assert "tpm_identity" not in bundle
