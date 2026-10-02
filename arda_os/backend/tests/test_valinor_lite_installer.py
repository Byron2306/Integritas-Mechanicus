from pathlib import Path

import pytest

from backend.services.valinor_lite_preflight import PreflightReport
from kernel.valinor.lite.installer.install import (
    InstallResult,
    install_valinor_lite,
)


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
        audio_installer=(
            (lambda src, dst: True)
            if audio_ok
            else (lambda src, dst: False)
        ),
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
        audio_installer=lambda src, dst: True,
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
        audio_installer=lambda src, dst: True,
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
        audio_installer=lambda src, dst: True,
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
