from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENROLL = ROOT / "installer" / "arda-enroll"


def source() -> str:
    return ENROLL.read_text()


def test_resume_is_first_class_enrollment_mode():
    src = source()

    assert "--resume" in src
    assert "RESUME=1" in src
    assert 'step "RESUME VALIDATION"' in src


def test_resume_consumes_persisted_generation_instead_of_minting_next():
    src = source()
    resume = src.split('step "RESUME VALIDATION"', 1)[1]
    resume = resume.split('step "60 SIGNED VERIFIER VERDICT"', 1)[0]

    assert 'STATE/active_manifest_path' in resume
    assert 'STATE/active_manifest_id' in resume
    assert 'STATE/active_generation' in resume

    assert "current + 1" not in resume
    assert "arda_build_measured_manifest.py" not in resume
    assert "tpm2_pcrextend" not in resume


def test_resume_requires_completed_immutable_frontier():
    src = source()

    for receipt in (
        "00_preflight",
        "10_ring0",
        "20_policy",
        "30_measured_identity",
        "40_hardware_attestation",
        "50_pcr_baseline",
    ):
        assert receipt in src


def test_resume_refuses_completed_or_ambiguous_later_frontier():
    src = source()

    assert "no_unreceipted_current_verdict" in src

    for receipt in (
        "60_verifier",
        "70_grade",
        "75_ring0_handoff",
        "80_continuous_proof",
    ):
        assert f'"{receipt}"' in src

    assert 'checks[f"receipt_{name}_absent"] = not (' in src
    assert 'state / f"{name}.json"' in src
    assert ").exists()" in src


def test_resume_rebinds_to_committed_hardware_truth():
    src = source()

    assert "pcr11_matches_baseline" in src
    assert "baseline_manufacturer_rooted" in src
    assert "bundle_generation" in src
    assert "bundle_manifest" in src


def test_resume_proves_transient_ring0_ownership_before_handoff():
    src = source()

    assert "bootstrap_unit_active" in src
    assert "persistent_ring0_not_active" in src
    assert "bootstrap_loader_identity" in src
    assert "bootstrap_control_group" in src
    assert "bootstrap_cgroup_bound_to_generation" in src

    # Never reconstruct this merely from a historical receipt.
    assert (
        "RING0_BOOTSTRAPPED=1"
        in src
    )


def test_continuous_proof_must_stay_quiescent_before_step80():
    src = source()

    assert "continuous_timer_inactive" in src
    assert "continuous_timer_disabled" in src

    step80 = src.index(
        'step "80 CONTINUOUS HARDWARE-ROOTED PROOF"'
    )
    enable = src.index(
        "systemctl enable --now arda-valinor-postboot.timer"
    )

    assert enable > step80
