from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENROLL = ROOT / "installer" / "arda-enroll"


def source() -> str:
    return ENROLL.read_text()


def handoff_section() -> str:
    src = source()
    start = src.index('step "75 PERSISTENT RING0 HANDOFF"')
    end = src.index('step "80 CONTINUOUS HARDWARE-ROOTED PROOF"')
    return src[start:end]


def test_handoff_occurs_only_after_hardware_rooted_grade():
    src = source()

    grade = src.index(
        'receipt "70_grade" "PASS" '
        '"hardware-rooted OS-grade production milestone"'
    )
    handoff = src.index('step "75 PERSISTENT RING0 HANDOFF"')
    continuous = src.index(
        'step "80 CONTINUOUS HARDWARE-ROOTED PROOF"'
    )

    assert grade < handoff < continuous


def test_bootstrap_is_stopped_before_persistent_ring0_start():
    src = handoff_section()

    stop = src.index(
        "systemctl stop arda-ring0-enrollment.service"
    )
    start = src.index(
        "systemctl start arda-ring0.service"
    )

    assert stop < start


def test_bpffs_namespace_is_cleared_between_owners():
    src = handoff_section()

    assert 'RING0_PIN_ROOT="/sys/fs/bpf/arda"' in src
    assert 'rm -f "$RING0_PIN_ROOT"/*' in src
    assert "Ring0 bpffs namespace did not clear" in src


def test_persistent_handoff_requires_live_attachment_verification():
    src = handoff_section()

    assert "verify_live_ring0" in src
    assert (
        "persistent Ring0 live attachment failed independent verification"
        in src
    )


def test_persistent_handoff_requires_restored_generation_receipt():
    src = handoff_section()

    assert "verify_restore_receipt" in src
    assert '"generation"' in src
    assert '"manifest_id"' in src
    assert '"scoped_strict"' in src


def test_existing_attachment_must_have_persistent_owner():
    src = handoff_section()

    assert "systemctl is-active --quiet arda-ring0.service" in src
    assert (
        "verified Ring0 attachment is not owned by persistent service"
        in src
    )


def test_handoff_receipt_is_emitted():
    src = handoff_section()

    assert '"75_ring0_handoff"' in src
    assert "persistent Ring0 owns verified generation=" in src
