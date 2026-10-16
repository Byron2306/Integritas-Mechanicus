from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

AUTH = ROOT / "arda_os/backend/services/arda_bpf_authority.py"
ENROLL = ROOT / "installer/arda-enroll"


def test_authority_does_not_depend_on_stale_static_program_tag():
    src = AUTH.read_text()

    assert "EXPECTED_TAG" not in src
    assert 'program.get("tag") !=' not in src


def test_authority_records_live_program_tag_as_evidence():
    src = AUTH.read_text()

    assert '"program_tag": None' in src
    assert 'program_tag = program.get("tag")' in src
    assert "program_tag=program_tag" in src


def test_authority_requires_exact_program_map_and_live_lsm_link():
    src = AUTH.read_text()

    assert 'program.get("type") != "lsm"' in src
    assert 'program.get("name") != PROGRAM' in src
    assert "associated != expected_map_ids" in src
    assert 'link.get("prog_id") == program_id' in src
    assert 'link.get("prog_type") == "lsm"' in src
    assert 'link.get("attach_type") == "lsm_mac"' in src


def test_step10_requires_same_live_authority_verifier_as_step20():
    src = ENROLL.read_text()

    assert 'from backend.services.arda_bpf_authority import verify_attachment' in src
    assert 'verify_attachment("/sys/fs/bpf/arda")' in src
    assert 'evidence.get("verified") is not True' in src
    assert 'live Ring0 attachment could not be independently verified' in src


def test_enrollment_bootstraps_from_attachment_truth_not_map_presence():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    src = (root / "installer/arda-enroll").read_text()

    step10 = (
        src.split('step "10 RING0"', 1)[1]
        .split('step "20 POLICY"', 1)[0]
    )

    assert "verify_live_ring0()" in step10
    assert "if ! verify_live_ring0; then" in step10
    assert "starting bounded enrollment bootstrap" in step10
    assert "--enforcement-mode audit" in step10

    assert 'verify_live_ring0 ||' in step10
    assert (
        'refuse "10_ring0" '
        '"live Ring0 attachment could not be independently verified"'
    ) in step10

    assert (
        "if ! bpftool map show pinned "
        "/sys/fs/bpf/arda/policy_state_map"
    ) not in step10
