from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

LSMS = [
    ROOT / "arda_os/backend/services/bpf/arda_physical_lsm.c",
    ROOT / "arda_os/backend/services/bpf/proof_host_lsm.c",
    ROOT / "arda_os/backend/services/bpf/proof_digest_lsm.c",
    ROOT / "arda_os/backend/services/bpf/proof_host_integrity_lsm.c",
]


def test_redline_presence_is_distinct_from_triggered_veto():
    for path in LSMS:
        src = path.read_text()

        assert "#define ARDA_POLICY_FLAG_REDLINE_PRESENT 1" in src
        assert "#define ARDA_POLICY_FLAG_REDLINE_TRIGGERED 2" in src

        # Presence of constitutional redline rules must not blanket-veto
        # strict measured execution.
        assert (
            "projection_flags & ARDA_POLICY_FLAG_REDLINE_PRESENT"
            not in src
        )

        # Only an explicitly triggered runtime redline may veto.
        assert (
            "projection_flags & ARDA_POLICY_FLAG_REDLINE_TRIGGERED"
            in src
        )


def test_old_presence_equals_global_veto_contract_is_gone():
    for path in LSMS:
        src = path.read_text()

        assert (
            "redline_rule_count > 0 && "
            "(!state || *state != ARDA_MODE_AUDIT)"
            not in src
        )


def test_userspace_projects_presence_bit_not_triggered_bit():
    path = ROOT / "arda_os/backend/services/os_enforcement_service.py"
    src = path.read_text()

    assert "POLICY_PROJECTION_FLAG_REDLINE_PRESENT = 1 << 0" in src
    assert "POLICY_PROJECTION_FLAG_REDLINE_TRIGGERED = 1 << 1" in src

    assert (
        "self.POLICY_PROJECTION_FLAG_REDLINE_PRESENT "
        "if redline_rule_count > 0 else 0"
    ) in src

    assert (
        "self.POLICY_PROJECTION_FLAG_REDLINE_TRIGGERED "
        "if redline_rule_count > 0 else 0"
    ) not in src
