from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

LOADER = (
    ROOT
    / "arda_os/backend/services/bpf/arda_lsm_loader.c"
)

RING0 = (
    ROOT
    / "arda_os/kernel/valinor/systemd/arda-ring0.service"
)

VERIFY = (
    ROOT
    / "arda_os/kernel/valinor/systemd/arda-ring0-verify.service"
)

POSTBOOT = (
    ROOT
    / "installer/systemd/arda-valinor-postboot.service"
)


def test_loader_supports_deferred_attachment():
    src = LOADER.read_text()

    assert "--defer-attach-until" in src
    assert "defer_attach_until" in src


def test_ring0_does_not_arm_directly_in_audit_mode():
    src = RING0.read_text()

    assert "--enforcement-mode audit" not in src
    assert "--defer-attach-until" in src


def test_boot_restore_occurs_before_attachment_verification():
    src = RING0.read_text()

    assert "restore_ring0_boot_state.py" in src
    assert "/run/arda/ring0-ready" in src


def test_verifier_requires_restored_strict_state():
    src = VERIFY.read_text()

    assert "verify_ring0_attachment.py" in src
    assert "--require-restored-state" in src


def test_postboot_remains_downstream_of_verified_ring0():
    src = POSTBOOT.read_text()

    assert "Requires=arda-ring0.service arda-ring0-verify.service" in src
    assert "After=arda-ring0.service arda-ring0-verify.service" in src


def test_ring0_restore_has_installed_python_import_root():
    src = RING0.read_text()

    assert "Environment=PYTHONPATH=/usr/lib/arda/src/arda_os" in src
