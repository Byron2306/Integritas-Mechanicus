from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

RING0 = ROOT / "arda_os/kernel/valinor/systemd/arda-ring0.service"
VERIFY = ROOT / "arda_os/kernel/valinor/systemd/arda-ring0-verify.service"
POSTBOOT = ROOT / "arda_os/kernel/valinor/systemd/arda-valinor-postboot.service"


def test_ring0_loader_is_persistent_systemd_service():
    src = RING0.read_text()

    assert "Type=simple" in src
    assert "arda_lsm_loader" in src
    assert "arda_physical_lsm.o" in src
    assert "--pin-root /sys/fs/bpf/arda" in src
    # Ring-0 must be recreated even after an unexpected clean loader exit.
    assert "Restart=always" in src
    assert "ConditionKernelCommandLine=!arda.recovery=1" in src


def test_ring0_verifier_checks_kernel_attachment():
    src = VERIFY.read_text()

    assert "Requires=arda-ring0.service" in src
    assert "After=arda-ring0.service" in src
    assert "verify_ring0_attachment.py" in src
    assert "RemainAfterExit=yes" in src


def test_postboot_requires_verified_ring0():
    src = POSTBOOT.read_text()

    assert "Requires=arda-ring0.service arda-ring0-verify.service" in src
    assert "After=arda-ring0.service arda-ring0-verify.service" in src


VERIFY_SCRIPT = ROOT / "arda_os/kernel/valinor/scripts/verify_ring0_attachment.py"
BOOT_INSTALLER = ROOT / "arda_os/kernel/valinor/scripts/install_boot_stability_lane.sh"
INSTALL_PLAN = ROOT / "arda_os/kernel/valinor/scripts/plan_valinor_install.py"
OVERLAY = ROOT / "arda_os/distribution/scripts/prepare_arda_overlay.py"


def test_ring0_verifier_retries_until_live_attachment_is_visible():
    src = VERIFY_SCRIPT.read_text()

    assert "ATTEMPTS = 20" in src
    assert "verify_attachment(PIN_ROOT)" in src
    assert "time.sleep(DELAY_SECONDS)" in src
    # Reboot authority is not proven by attachment alone. The verifier must
    # require both exact live attachment and reconstructed enforcement state.
    assert 'attachment.get("verified") is True' in src
    assert 'restored.get("ok") is True' in src


def test_boot_stability_lane_installs_and_enables_ring0_units():
    src = BOOT_INSTALLER.read_text()

    assert "arda-ring0.service" in src
    assert "arda-ring0-verify.service" in src
    assert "systemctl enable arda-ring0.service" in src
    assert "systemctl enable arda-ring0-verify.service" in src


def test_install_plan_declares_ring0_boot_chain():
    src = INSTALL_PLAN.read_text()

    assert "arda-ring0.service" in src
    assert "arda-ring0-verify.service" in src


def test_distribution_overlay_contains_ring0_units():
    src = OVERLAY.read_text()

    assert "arda-ring0.service" in src
    assert "arda-ring0-verify.service" in src
