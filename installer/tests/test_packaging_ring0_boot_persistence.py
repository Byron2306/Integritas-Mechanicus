from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "packaging/build-arda-valinor-deb.sh"
POSTBOOT = ROOT / "installer/systemd/arda-valinor-postboot.service"


def test_package_installs_ring0_boot_units():
    src = BUILD.read_text()

    assert (
        '"$TMP_TREE/arda_os/kernel/valinor/systemd/arda-ring0.service"'
        in src
    )
    assert (
        '"$PKG/lib/systemd/system/arda-ring0.service"'
        in src
    )

    assert (
        '"$TMP_TREE/arda_os/kernel/valinor/systemd/arda-ring0-verify.service"'
        in src
    )
    assert (
        '"$PKG/lib/systemd/system/arda-ring0-verify.service"'
        in src
    )


def test_package_enables_ring0_for_next_boot():
    src = BUILD.read_text()

    assert "systemctl enable arda-ring0.service" in src
    assert "systemctl enable arda-ring0-verify.service" in src

    # Installation must not attempt live attachment during recovery/package
    # installation. Activation belongs to the next normal boot.
    assert "systemctl enable --now arda-ring0.service" not in src
    assert "systemctl enable --now arda-ring0-verify.service" not in src


def test_packaged_postboot_requires_verified_ring0():
    src = POSTBOOT.read_text()

    assert "Requires=arda-ring0.service arda-ring0-verify.service" in src
    assert "After=arda-ring0.service arda-ring0-verify.service" in src


def test_ring0_verifier_script_enters_archived_package_source():
    src = BUILD.read_text()

    assert 'git -C "$ROOT" archive HEAD | tar -x -C "$TMP_TREE"' in src
    assert 'cp -a "$TMP_TREE/arda_os" "$PKG/usr/lib/arda/src/"' in src


def test_package_archives_ring0_restore_script():
    src = BUILD.read_text()

    assert "git -C" in src
    assert "archive HEAD" in src
    assert "arda_os" in src

    restore = (
        ROOT
        / "arda_os/kernel/valinor/scripts/"
        "restore_ring0_boot_state.py"
    )

    assert restore.is_file()
    assert "current_cgroup_kernel_id" in restore.read_text()
