from pathlib import Path

import pytest

from backend.services.valinor_lite_preflight import PreflightReport
from kernel.valinor.lite.installer.install import (
    InstallResult,
    install_valinor_lite,
)
from kernel.valinor.lite.installer.greeter import GreeterDetection


def _good_preflight() -> PreflightReport:
    return PreflightReport(
        ok=True,
        architecture="x86_64",
        debian=True,
        boot_mode="uefi",
        tpm_available=False,
        secure_boot_state="disabled",
        windows_efi_entries=(
            "/boot/efi/EFI/Microsoft/Boot/bootmgfw.efi",
        ),
        fallback_kernels=("6.12.57+deb13-amd64",),
        boot_free_bytes=1024 * 1024 * 1024,
        failures=(),
    )



def _good_greeter() -> GreeterDetection:
    return GreeterDetection(
        state="ALLOW",
        manager="lightdm",
        greeter="lightdm-gtk-greeter",
        reasons=(),
    )

def _bad_preflight() -> PreflightReport:
    return PreflightReport(
        ok=False,
        architecture="x86_64",
        debian=True,
        boot_mode="uefi",
        tpm_available=False,
        secure_boot_state="disabled",
        windows_efi_entries=(),
        fallback_kernels=(),
        boot_free_bytes=0,
        failures=("fallback_kernel_missing",),
    )


def _source_tree(tmp_path: Path) -> Path:
    source = tmp_path / "release"
    source.mkdir()

    (source / "boot").mkdir()
    (source / "boot" / "vmlinuz-6.12.96-valinor").write_bytes(
        b"VALINOR-KERNEL"
    )
    (source / "boot" / "initrd.img-6.12.96-valinor").write_bytes(
        b"VALINOR-INITRAMFS"
    )

    modules = (
        source
        / "lib"
        / "modules"
        / "6.12.96-valinor"
    )
    modules.mkdir(parents=True)
    (modules / "modules.dep").write_text(
        "valinor\n",
        encoding="utf-8",
    )

    identity = source / "identity"
    (identity / "grub" / "arda-sovereign").mkdir(
        parents=True
    )
    (
        identity
        / "grub"
        / "arda-sovereign"
        / "theme.txt"
    ).write_text(
        "ARDA SOVEREIGN\n",
        encoding="utf-8",
    )

    (
        identity
        / "plymouth"
        / "arda-sovereign"
    ).mkdir(parents=True)
    (
        identity
        / "plymouth"
        / "arda-sovereign"
        / "arda-sovereign.plymouth"
    ).write_text(
        "[Plymouth Theme]\nName=ARDA Sovereign\n",
        encoding="utf-8",
    )

    (
        identity
        / "plymouth"
        / "arda-mirror-gate"
    ).mkdir(parents=True)
    (
        identity
        / "plymouth"
        / "arda-mirror-gate"
        / "arda-mirror-gate.plymouth"
    ).write_text(
        "[Plymouth Theme]\nName=ARDA Mirror Gate\n",
        encoding="utf-8",
    )

    greeter = identity / "greeter"
    greeter.mkdir(parents=True)
    (greeter / "gate-of-becoming.webp").write_bytes(
        b"ARDA-GATE-OF-BECOMING"
    )
    (greeter / "arda-mark.png").write_bytes(
        b"ARDA-MARK"
    )
    (greeter / "lightdm-gtk-greeter.conf").write_text(
        "[greeter]\n"
        "background=/usr/share/arda/greeter/"
        "gate-of-becoming.webp\n"
        "user-background=false\n",
        encoding="utf-8",
    )

    (identity / "audio").mkdir(parents=True)
    (
        identity
        / "audio"
        / "arda-awakening.wav"
    ).write_bytes(b"ARDA-AWAKENING")

    return source


def _target_tree(tmp_path: Path) -> Path:
    target = tmp_path / "target"
    target.mkdir()

    boot = target / "boot"
    boot.mkdir()

    # Existing Debian fallback must survive.
    (boot / "vmlinuz-6.12.57+deb13-amd64").write_bytes(
        b"DEBIAN-FALLBACK"
    )

    # Existing Windows EFI loader must survive.
    windows = (
        boot
        / "efi"
        / "EFI"
        / "Microsoft"
        / "Boot"
    )
    windows.mkdir(parents=True)
    (windows / "bootmgfw.efi").write_bytes(
        b"WINDOWS-EFI"
    )

    return target


def _run(
    tmp_path: Path,
    *,
    preflight=None,
    release_hashes_ok=True,
    audio_ok=True,
):
    source = _source_tree(tmp_path)
    target = _target_tree(tmp_path)
    state = tmp_path / "install-state.json"
    backups = tmp_path / "backups"
    events = []

    result = install_valinor_lite(
        preflight_report=preflight or _good_preflight(),
        source_root=source,
        target_root=target,
        backup_root=backups,
        state_path=state,
        release_hashes_ok=release_hashes_ok,
        greeter_detection=_good_greeter(),
        audio_installer=(
            (lambda src, dst: True)
            if audio_ok
            else (lambda src, dst: False)
        ),
        boot_menu_generator=_test_boot_menu_generator,
        event_sink=events.append,
    )

    return result, source, target, state, backups, events


def test_no_filesystem_mutation_before_successful_preflight(
    tmp_path,
):
    source = _source_tree(tmp_path)
    target = _target_tree(tmp_path)
    before = sorted(
        p.relative_to(target).as_posix()
        for p in target.rglob("*")
    )

    events = []

    result = install_valinor_lite(
        preflight_report=_bad_preflight(),
        source_root=source,
        target_root=target,
        backup_root=tmp_path / "backups",
        state_path=tmp_path / "install-state.json",
        release_hashes_ok=True,
        greeter_detection=_good_greeter(),
        audio_installer=lambda src, dst: True,
        boot_menu_generator=_test_boot_menu_generator,
        event_sink=events.append,
    )

    after = sorted(
        p.relative_to(target).as_posix()
        for p in target.rglob("*")
    )

    assert result.success is False
    assert before == after
    assert events == []


def test_backup_occurs_before_first_boot_file_modification(
    tmp_path,
):
    result, _, _, _, _, events = _run(tmp_path)

    assert result.success is True

    backup_index = events.index("BACKUP")
    kernel_index = events.index("INSTALL_KERNEL")

    assert backup_index < kernel_index


def test_hash_failure_performs_zero_boot_mutations(tmp_path):
    source = _source_tree(tmp_path)
    target = _target_tree(tmp_path)

    before = {
        p.relative_to(target).as_posix(): (
            p.read_bytes() if p.is_file() else None
        )
        for p in target.rglob("*")
    }

    events = []

    result = install_valinor_lite(
        preflight_report=_good_preflight(),
        source_root=source,
        target_root=target,
        backup_root=tmp_path / "backups",
        state_path=tmp_path / "install-state.json",
        release_hashes_ok=False,
        greeter_detection=_good_greeter(),
        audio_installer=lambda src, dst: True,
        boot_menu_generator=_test_boot_menu_generator,
        event_sink=events.append,
    )

    after = {
        p.relative_to(target).as_posix(): (
            p.read_bytes() if p.is_file() else None
        )
        for p in target.rglob("*")
    }

    assert result.success is False
    assert before == after
    assert "INSTALL_KERNEL" not in events
    assert "INSTALL_IDENTITY" not in events


def test_kernel_and_module_payload_installed(
    tmp_path,
):
    result, _, target, _, _, _ = _run(tmp_path)

    assert result.success is True
    assert (
        target
        / "boot"
        / "vmlinuz-6.12.96-valinor"
    ).is_file()
    assert (
        target
        / "boot"
        / "initrd.img-6.12.96-valinor"
    ).is_file()
    assert (
        target
        / "lib"
        / "modules"
        / "6.12.96-valinor"
        / "modules.dep"
    ).is_file()


def test_arda_identity_installs_to_deterministic_destinations(
    tmp_path,
):
    result, _, target, _, _, _ = _run(tmp_path)

    assert result.success is True

    assert (
        target
        / "boot"
        / "grub"
        / "themes"
        / "arda-sovereign"
        / "theme.txt"
    ).is_file()

    assert (
        target
        / "usr"
        / "share"
        / "plymouth"
        / "themes"
        / "arda-sovereign"
        / "arda-sovereign.plymouth"
    ).is_file()

    assert (
        target
        / "usr"
        / "share"
        / "plymouth"
        / "themes"
        / "arda-mirror-gate"
        / "arda-mirror-gate.plymouth"
    ).is_file()


def test_existing_windows_efi_files_are_never_deleted(
    tmp_path,
):
    result, _, target, _, _, _ = _run(tmp_path)

    windows = (
        target
        / "boot"
        / "efi"
        / "EFI"
        / "Microsoft"
        / "Boot"
        / "bootmgfw.efi"
    )

    assert result.success is True
    assert windows.read_bytes() == b"WINDOWS-EFI"
    assert result.windows_preserved is True


def test_fallback_debian_kernel_remains(tmp_path):
    result, _, target, _, _, _ = _run(tmp_path)

    fallback = (
        target
        / "boot"
        / "vmlinuz-6.12.57+deb13-amd64"
    )

    assert result.success is True
    assert fallback.read_bytes() == b"DEBIAN-FALLBACK"
    assert result.fallback_verified is True


def test_initial_enforcement_profile_is_audit(
    tmp_path,
):
    result, _, target, _, _, _ = _run(tmp_path)

    profile = (
        target
        / "etc"
        / "arda"
        / "attestation-profile"
    )

    enforcement = (
        target
        / "etc"
        / "arda"
        / "enforcement-mode"
    )

    assert result.success is True
    assert profile.read_text().strip() == "lite"
    assert enforcement.read_text().strip() == "audit"
    assert "fsverity_strict" not in enforcement.read_text()


def test_running_installer_twice_does_not_duplicate_configuration(
    tmp_path,
):
    source = _source_tree(tmp_path)
    target = _target_tree(tmp_path)

    kwargs = dict(
        preflight_report=_good_preflight(),
        source_root=source,
        target_root=target,
        backup_root=tmp_path / "backups",
        state_path=tmp_path / "install-state.json",
        release_hashes_ok=True,
        greeter_detection=_good_greeter(),
        audio_installer=lambda src, dst: True,
        boot_menu_generator=_test_boot_menu_generator,
        event_sink=lambda event: None,
    )

    first = install_valinor_lite(**kwargs)
    second = install_valinor_lite(**kwargs)

    grub_cfg = (
        target
        / "etc"
        / "default"
        / "grub.d"
        / "99-valinor-lite.cfg"
    )

    text = grub_cfg.read_text(encoding="utf-8")

    assert first.success is True
    assert second.success is True
    assert text.count("ARDA_VALINOR_LITE") == 1


def test_audio_failure_is_reported_without_failing_security_install(
    tmp_path,
):
    result, _, target, _, _, _ = _run(
        tmp_path,
        audio_ok=False,
    )

    assert result.success is True
    assert result.audio_installed is False

    assert (
        target
        / "boot"
        / "vmlinuz-6.12.96-valinor"
    ).is_file()


def test_transaction_phases_are_recorded_in_order(
    tmp_path,
):
    result, _, _, state, _, events = _run(tmp_path)

    assert result.success is True
    assert state.is_file()

    expected = [
        "PREFLIGHT",
        "BACKUP",
        "VERIFY_ARTIFACTS",
        "INSTALL_KERNEL",
        "INSTALL_PROFILE",
        "INSTALL_IDENTITY",
        "CONFIGURE_PLYMOUTH",
        "CONFIGURE_GRUB",
        "GENERATE_BOOT_MENU",
        "VERIFY",
        "COMMIT_INSTALL_STATE",
    ]

    positions = [events.index(item) for item in expected]

    assert positions == sorted(positions)


def test_result_contract(tmp_path):
    result, _, _, _, _, _ = _run(tmp_path)

    assert isinstance(result, InstallResult)
    assert result.success is True
    assert result.backup_id
    assert result.installed_kernel == "6.12.96-valinor"
    assert result.profile == "lite"
    assert result.grub_verified is True
    assert result.fallback_verified is True
    assert result.windows_preserved is True
    assert result.plymouth_theme == "arda-mirror-gate"


def test_shell_entrypoint_default_prints_help_without_mutation():
    import subprocess

    repo_root = Path(__file__).resolve().parents[3]
    entry = (
        repo_root
        / "arda_os"
        / "kernel"
        / "valinor"
        / "lite"
        / "install-valinor-lite"
    )

    result = subprocess.run(
        [str(entry)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()
    assert "--preflight" in result.stdout
    assert "--install" in result.stdout


def test_shell_entrypoint_modes_are_mutually_exclusive():
    import subprocess

    repo_root = Path(__file__).resolve().parents[3]
    entry = (
        repo_root
        / "arda_os"
        / "kernel"
        / "valinor"
        / "lite"
        / "install-valinor-lite"
    )

    result = subprocess.run(
        [
            str(entry),
            "--preflight",
            "--install",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0



def test_greeter_identity_installs_to_deterministic_destinations(
    tmp_path,
):
    result, source, target, _, _, events = _run(tmp_path)

    assert result.success is True

    installed_background = (
        target
        / "usr"
        / "share"
        / "arda"
        / "greeter"
        / "gate-of-becoming.webp"
    )
    installed_logo = (
        target
        / "usr"
        / "share"
        / "arda"
        / "greeter"
        / "arda-mark.png"
    )
    installed_config = (
        target
        / "etc"
        / "lightdm"
        / "lightdm-gtk-greeter.conf"
    )

    assert installed_background.read_bytes() == (
        source
        / "identity"
        / "greeter"
        / "gate-of-becoming.webp"
    ).read_bytes()

    assert installed_logo.read_bytes() == (
        source
        / "identity"
        / "greeter"
        / "arda-mark.png"
    ).read_bytes()

    assert (
        "background=/usr/share/arda/greeter/"
        "gate-of-becoming.webp"
    ) in installed_config.read_text(encoding="utf-8")

    assert "user-background=false" in installed_config.read_text(
        encoding="utf-8"
    )

    assert "INSTALL_GREETER_IDENTITY" in events
    assert "CONFIGURE_GREETER" in events
    assert "VERIFY_GREETER" in events


def test_greeter_phases_run_after_identity_before_plymouth(
    tmp_path,
):
    result, _, _, _, _, events = _run(tmp_path)

    assert result.success is True

    expected = [
        "INSTALL_IDENTITY",
        "INSTALL_GREETER_IDENTITY",
        "CONFIGURE_GREETER",
        "VERIFY_GREETER",
        "CONFIGURE_PLYMOUTH",
    ]

    positions = [events.index(item) for item in expected]

    assert positions == sorted(positions)


def test_unsupported_greeter_refuses_before_target_mutation(
    tmp_path,
):
    source = _source_tree(tmp_path)
    target = _target_tree(tmp_path)

    before = {
        p.relative_to(target).as_posix(): (
            p.read_bytes() if p.is_file() else None
        )
        for p in target.rglob("*")
    }

    result = install_valinor_lite(
        preflight_report=_good_preflight(),
        source_root=source,
        target_root=target,
        backup_root=tmp_path / "backups",
        state_path=tmp_path / "install-state.json",
        release_hashes_ok=True,
        greeter_detection=GreeterDetection(
            state="NEEDS_YOU",
            manager="unsupported",
            greeter="unknown",
            reasons=("unsupported_display_manager",),
        ),
        audio_installer=lambda src, dst: True,
        boot_menu_generator=_test_boot_menu_generator,
        event_sink=lambda event: None,
    )

    after = {
        p.relative_to(target).as_posix(): (
            p.read_bytes() if p.is_file() else None
        )
        for p in target.rglob("*")
    }

    assert result.success is False
    assert before == after


def _portable_cli_release(tmp_path: Path) -> Path:
    import hashlib
    import json
    import subprocess

    release = tmp_path / "portable-release"
    payload = tmp_path / "kernel-payload"

    kernel = (
        payload
        / "boot"
        / "vmlinuz-6.12.96-valinor"
    )
    initramfs = (
        payload
        / "boot"
        / "initrd.img-6.12.96-valinor"
    )
    modules = (
        payload
        / "lib"
        / "modules"
        / "6.12.96-valinor"
    )

    kernel.parent.mkdir(parents=True)
    modules.mkdir(parents=True)

    kernel.write_bytes(b"CLI-VALINOR-KERNEL")
    initramfs.write_bytes(b"CLI-VALINOR-INITRAMFS")
    (modules / "modules.dep").write_bytes(b"valinor\n")

    archive = (
        release
        / "kernel"
        / "valinor-kernel-6.12.96.tar.zst"
    )
    archive.parent.mkdir(parents=True)

    subprocess.run(
        [
            "tar",
            "--zstd",
            "-cf",
            str(archive),
            "-C",
            str(payload),
            ".",
        ],
        check=True,
    )

    identity = release / "identity"
    identity.mkdir(parents=True)
    (identity / "marker").write_bytes(b"ARDA")

    grub = (
        identity
        / "grub"
        / "arda-sovereign"
    )
    grub.mkdir(parents=True)
    (grub / "theme.txt").write_bytes(
        b"ARDA SOVEREIGN\n"
    )

    sovereign = (
        identity
        / "plymouth"
        / "arda-sovereign"
    )
    sovereign.mkdir(parents=True)
    (
        sovereign / "arda-sovereign.plymouth"
    ).write_bytes(
        b"[Plymouth Theme]\n"
        b"Name=ARDA Sovereign\n"
    )

    mirror = (
        identity
        / "plymouth"
        / "arda-mirror-gate"
    )
    mirror.mkdir(parents=True)
    (
        mirror / "arda-mirror-gate.plymouth"
    ).write_bytes(
        b"[Plymouth Theme]\n"
        b"Name=ARDA Mirror Gate\n"
    )

    audio = identity / "audio"
    audio.mkdir()
    (
        audio / "arda-awakening.wav"
    ).write_bytes(b"ARDA-AWAKENING")

    greeter = identity / "greeter"
    greeter.mkdir()
    (
        greeter / "gate-of-becoming.webp"
    ).write_bytes(b"ARDA-GATE")
    (
        greeter / "arda-mark.png"
    ).write_bytes(b"ARDA-MARK")
    (
        greeter / "lightdm-gtk-greeter.conf"
    ).write_text(
        "[greeter]\n"
        "background=/usr/share/arda/greeter/"
        "gate-of-becoming.webp\n"
        "user-background=false\n",
        encoding="utf-8",
    )

    manifest_dir = release / "manifest"
    manifest_dir.mkdir(parents=True)

    def sha(path):
        return hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

    (
        manifest_dir / "release.json"
    ).write_text(
        json.dumps(
            {
                "schema_version": (
                    "valinor-lite-portable-release-v1"
                ),
                "architecture": "x86_64",
                "profile": "lite",
                "kernel": {
                    "release": "6.12.96-valinor",
                    "archive": (
                        "kernel/"
                        "valinor-kernel-6.12.96.tar.zst"
                    ),
                    "archive_sha256": sha(archive),
                    "image_sha256": sha(kernel),
                    "initramfs_sha256": sha(initramfs),
                },
            }
        ),
        encoding="utf-8",
    )

    return release


def test_cli_preflight_runs_real_portable_readiness_check(
    tmp_path,
):
    import subprocess

    repo_root = Path(__file__).resolve().parents[3]

    entry = (
        repo_root
        / "arda_os"
        / "kernel"
        / "valinor"
        / "lite"
        / "install-valinor-lite"
    )

    release = _portable_cli_release(tmp_path)

    host = tmp_path / "host"
    (host / "etc").mkdir(parents=True)
    (host / "etc" / "os-release").write_text(
        "ID=debian\n",
        encoding="utf-8",
    )

    (
        host
        / "sys"
        / "firmware"
        / "efi"
    ).mkdir(parents=True)

    (host / "boot").mkdir(parents=True)
    (
        host
        / "boot"
        / "vmlinuz-6.12.57+deb13-amd64"
    ).write_bytes(b"DEBIAN-FALLBACK")

    result = subprocess.run(
        [
            str(entry),
            "--preflight",
            "--release-root",
            str(release),
            "--target-root",
            str(host),
        ],
        cwd=repo_root,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
            "PYTHONPATH": str(repo_root / "arda_os"),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "PREFLIGHT_ALLOW" in result.stdout
    assert "architecture=x86_64" in result.stdout
    assert "profile=lite" in result.stdout
    assert "PREFLIGHT\n" != result.stdout


def test_cli_dry_run_proves_readiness_without_target_mutation(
    tmp_path,
):
    import subprocess

    repo_root = Path(__file__).resolve().parents[3]

    entry = (
        repo_root
        / "arda_os"
        / "kernel"
        / "valinor"
        / "lite"
        / "install-valinor-lite"
    )

    release = _portable_cli_release(tmp_path)

    host = tmp_path / "host"
    (host / "etc").mkdir(parents=True)
    (host / "etc" / "os-release").write_text(
        "ID=debian\n",
        encoding="utf-8",
    )

    (
        host
        / "sys"
        / "firmware"
        / "efi"
    ).mkdir(parents=True)

    (host / "boot").mkdir(parents=True)
    (
        host
        / "boot"
        / "vmlinuz-6.12.57+deb13-amd64"
    ).write_bytes(b"DEBIAN-FALLBACK")

    before = {
        p.relative_to(host).as_posix(): (
            p.read_bytes() if p.is_file() else None
        )
        for p in host.rglob("*")
    }

    result = subprocess.run(
        [
            str(entry),
            "--dry-run",
            "--release-root",
            str(release),
            "--target-root",
            str(host),
        ],
        cwd=repo_root,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
            "PYTHONPATH": str(repo_root / "arda_os"),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    after = {
        p.relative_to(host).as_posix(): (
            p.read_bytes() if p.is_file() else None
        )
        for p in host.rglob("*")
    }

    assert result.returncode == 0
    assert before == after
    assert "DRY_RUN_ALLOW" in result.stdout
    assert "install_kernel=6.12.96-valinor" in result.stdout
    assert "profile=lite" in result.stdout
    assert "enforcement=audit" in result.stdout
    assert "DRY_RUN\n" != result.stdout


def test_cli_install_runs_real_transaction(
    tmp_path,
):
    import subprocess

    repo_root = Path(__file__).resolve().parents[3]

    entry = (
        repo_root
        / "arda_os"
        / "kernel"
        / "valinor"
        / "lite"
        / "install-valinor-lite"
    )

    release = _portable_cli_release(tmp_path)

    host = tmp_path / "host"

    (host / "etc").mkdir(parents=True)
    (host / "etc" / "os-release").write_text(
        "ID=debian\n",
        encoding="utf-8",
    )

    (
        host
        / "sys"
        / "firmware"
        / "efi"
    ).mkdir(parents=True)

    (host / "boot").mkdir(parents=True)
    (
        host
        / "boot"
        / "vmlinuz-6.12.57+deb13-amd64"
    ).write_bytes(b"DEBIAN-FALLBACK")

    windows = (
        host
        / "boot"
        / "efi"
        / "EFI"
        / "Microsoft"
        / "Boot"
    )
    windows.mkdir(parents=True)
    (
        windows / "bootmgfw.efi"
    ).write_bytes(b"WINDOWS-EFI")

    # Supported LightDM GTK host.
    display_manager = (
        host
        / "etc"
        / "systemd"
        / "system"
        / "display-manager.service"
    )
    display_manager.parent.mkdir(parents=True)

    display_manager.symlink_to(
        "/usr/lib/systemd/system/lightdm.service"
    )

    xgreeters = (
        host
        / "usr"
        / "share"
        / "xgreeters"
    )
    xgreeters.mkdir(parents=True)
    (
        xgreeters / "lightdm-gtk-greeter.desktop"
    ).write_text(
        "[Desktop Entry]\nName=LightDM GTK Greeter\n",
        encoding="utf-8",
    )

    backup_root = tmp_path / "backups"
    state_path = tmp_path / "install-state.json"

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    fake_update_grub = fake_bin / "update-grub"
    fake_update_grub.write_text(
        "#!/bin/sh\n"
        "mkdir -p \"$VALINOR_TARGET_ROOT/boot/grub\"\n"
        "printf 'REAL-GENERATED-GRUB\\n' "
        "> \"$VALINOR_TARGET_ROOT/boot/grub/grub.cfg\"\n"
        "exit 0\n",
        encoding="utf-8",
    )
    fake_update_grub.chmod(0o755)

    result = subprocess.run(
        [
            str(entry),
            "--install",
            "--release-root",
            str(release),
            "--target-root",
            str(host),
            "--backup-root",
            str(backup_root),
            "--state-path",
            str(state_path),
        ],
        cwd=repo_root,
        env={
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "HOME": str(tmp_path),
            "PYTHONPATH": str(repo_root / "arda_os"),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "INSTALL_COMPLETE" in result.stdout
    assert "profile=lite" in result.stdout

    assert (
        host
        / "boot"
        / "vmlinuz-6.12.96-valinor"
    ).is_file()

    assert (
        host
        / "etc"
        / "arda"
        / "enforcement-mode"
    ).read_text(
        encoding="utf-8"
    ).strip() == "audit"

    assert (
        host
        / "usr"
        / "share"
        / "arda"
        / "greeter"
        / "gate-of-becoming.webp"
    ).is_file()

    assert (
        host
        / "etc"
        / "lightdm"
        / "lightdm-gtk-greeter.conf"
    ).is_file()

    assert state_path.is_file()
    assert backup_root.is_dir()

    assert (
        windows / "bootmgfw.efi"
    ).read_bytes() == b"WINDOWS-EFI"


def test_installer_delegates_boot_menu_generation(
    tmp_path,
):
    source = _source_tree(tmp_path)
    target = _target_tree(tmp_path)

    grub_cfg = (
        target / "boot" / "grub" / "grub.cfg"
    )
    grub_cfg.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    grub_cfg.write_text(
        "ORIGINAL-GRUB-CONFIG\n",
        encoding="utf-8",
    )

    calls = []

    def generate(root):
        calls.append(root)

        # Test double for the real bootloader generator.
        grub_cfg.write_text(
            "REAL-GENERATED-GRUB\n",
            encoding="utf-8",
        )
        return True

    result = install_valinor_lite(
        preflight_report=_good_preflight(),
        source_root=source,
        target_root=target,
        backup_root=tmp_path / "backups",
        state_path=tmp_path / "state.json",
        release_hashes_ok=True,
        greeter_detection=_good_greeter(),
        audio_installer=lambda src, dst: True,
        boot_menu_generator=generate,
        event_sink=lambda event: None,
    )

    assert result.success is True
    assert calls == [target]

    assert grub_cfg.read_text(
        encoding="utf-8"
    ) == "REAL-GENERATED-GRUB\n"

    assert (
        "# generated by Valinor Lite transaction"
        not in grub_cfg.read_text(
            encoding="utf-8"
        )
    )


def _test_boot_menu_generator(root):
    grub_cfg = root / "boot" / "grub" / "grub.cfg"
    grub_cfg.parent.mkdir(parents=True, exist_ok=True)
    grub_cfg.write_text(
        "REAL-GENERATED-GRUB\n",
        encoding="utf-8",
    )
    return True


def test_cli_verify_is_not_placeholder(
    tmp_path,
):
    import subprocess

    repo_root = Path(__file__).resolve().parents[3]

    entry = (
        repo_root
        / "arda_os"
        / "kernel"
        / "valinor"
        / "lite"
        / "install-valinor-lite"
    )

    result = subprocess.run(
        [
            str(entry),
            "--verify",
            "--target-root",
            str(tmp_path),
        ],
        cwd=repo_root,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
            "PYTHONPATH": str(repo_root / "arda_os"),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.stdout != "VERIFY\n"
    assert "VERIFY_" in (
        result.stdout + result.stderr
    )
