"""Transactional Valinor Lite installer engine.

This module contains filesystem transaction logic only.  It does not require
root, invoke system commands, repartition disks, delete EFI files, or enable
strict enforcement.  Callers may point target_root at a real root filesystem
only after preflight and higher-level safety gates have succeeded.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable
import json
import shutil
import uuid

from backend.services.valinor_lite_preflight import PreflightReport


KERNEL_RELEASE = "6.12.96-valinor"
PROFILE = "lite"
ENFORCEMENT_MODE = "audit"
PLYMOUTH_THEME = "arda-mirror-gate"


@dataclass(frozen=True)
class InstallResult:
    success: bool
    backup_id: str
    installed_kernel: str
    profile: str
    grub_verified: bool
    fallback_verified: bool
    windows_preserved: bool
    plymouth_theme: str
    audio_installed: bool


def _failure() -> InstallResult:
    return InstallResult(
        success=False,
        backup_id="",
        installed_kernel="",
        profile=PROFILE,
        grub_verified=False,
        fallback_verified=False,
        windows_preserved=False,
        plymouth_theme=PLYMOUTH_THEME,
        audio_installed=False,
    )


def _emit(
    event_sink: Callable[[str], None],
    event: str,
) -> None:
    event_sink(event)


def _write_state(
    state_path: Path,
    *,
    phase: str,
    backup_id: str,
    committed: bool = False,
) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "schema_version": "valinor-lite-install-state-v1",
                "phase": phase,
                "backup_id": backup_id,
                "profile": PROFILE,
                "enforcement_mode": ENFORCEMENT_MODE,
                "kernel_release": KERNEL_RELEASE,
                "committed": committed,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _phase(
    state_path: Path,
    backup_id: str,
    event_sink: Callable[[str], None],
    phase: str,
) -> None:
    _write_state(
        state_path,
        phase=phase,
        backup_id=backup_id,
        committed=False,
    )
    _emit(event_sink, phase)


def _target_path(
    target_root: Path,
    absolute_or_relative: str | Path,
) -> Path:
    path = Path(absolute_or_relative)

    if path.is_absolute():
        path = Path(*path.parts[1:])

    return target_root / path


def _copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _copy_tree(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source,
        destination,
        dirs_exist_ok=True,
    )


def _planned_paths(target_root: Path) -> tuple[Path, ...]:
    return (
        target_root / "boot" / f"vmlinuz-{KERNEL_RELEASE}",
        target_root / "boot" / f"initrd.img-{KERNEL_RELEASE}",
        target_root / "lib" / "modules" / KERNEL_RELEASE,
        target_root
        / "boot"
        / "grub"
        / "themes"
        / "arda-sovereign",
        target_root
        / "usr"
        / "share"
        / "plymouth"
        / "themes"
        / "arda-sovereign",
        target_root
        / "usr"
        / "share"
        / "plymouth"
        / "themes"
        / "arda-mirror-gate",
        target_root
        / "usr"
        / "share"
        / "arda"
        / "audio"
        / "arda-awakening.wav",
        target_root / "etc" / "arda" / "attestation-profile",
        target_root / "etc" / "arda" / "enforcement-mode",
        target_root
        / "etc"
        / "default"
        / "grub.d"
        / "99-valinor-lite.cfg",
        target_root / "boot" / "grub" / "grub.cfg",
    )


def _backup_one(
    *,
    target_root: Path,
    backup_files_root: Path,
    path: Path,
) -> dict[str, object]:
    relative = path.relative_to(target_root)
    existed = path.exists()

    record = {
        "path": relative.as_posix(),
        "existed": existed,
        "kind": (
            "directory"
            if existed and path.is_dir()
            else "file"
        ),
    }

    if not existed:
        return record

    destination = backup_files_root / relative

    if path.is_dir():
        shutil.copytree(path, destination)
    else:
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        shutil.copy2(path, destination)

    return record


def _create_backup(
    *,
    target_root: Path,
    backup_root: Path,
    backup_id: str,
) -> None:
    backup_dir = backup_root / backup_id
    files_root = backup_dir / "files"
    backup_dir.mkdir(parents=True, exist_ok=False)

    records = [
        _backup_one(
            target_root=target_root,
            backup_files_root=files_root,
            path=path,
        )
        for path in _planned_paths(target_root)
    ]

    (backup_dir / "backup.json").write_text(
        json.dumps(
            {
                "schema_version": (
                    "valinor-lite-backup-v1"
                ),
                "backup_id": backup_id,
                "paths": records,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _windows_preserved(
    target_root: Path,
    entries: tuple[str, ...],
) -> bool:
    loader_entries = [
        entry
        for entry in entries
        if "/" in entry
    ]

    if not loader_entries:
        return True

    return all(
        _target_path(target_root, entry).is_file()
        for entry in loader_entries
    )


def _fallback_preserved(
    target_root: Path,
    kernels: tuple[str, ...],
) -> bool:
    if not kernels:
        return False

    return all(
        (
            target_root
            / "boot"
            / f"vmlinuz-{kernel}"
        ).is_file()
        for kernel in kernels
    )


def install_valinor_lite(
    *,
    preflight_report: PreflightReport,
    source_root: str | Path,
    target_root: str | Path,
    backup_root: str | Path,
    state_path: str | Path,
    release_hashes_ok: bool,
    audio_installer: Callable[[Path, Path], bool],
    event_sink: Callable[[str], None],
) -> InstallResult:
    source_root = Path(source_root)
    target_root = Path(target_root)
    backup_root = Path(backup_root)
    state_path = Path(state_path)

    # Hard refusal boundary.  Nothing, including transaction metadata,
    # is written before successful preflight.
    if not preflight_report.ok:
        return _failure()

    backup_id = uuid.uuid4().hex

    _phase(
        state_path,
        backup_id,
        event_sink,
        "PREFLIGHT",
    )

    _phase(
        state_path,
        backup_id,
        event_sink,
        "BACKUP",
    )
    _create_backup(
        target_root=target_root,
        backup_root=backup_root,
        backup_id=backup_id,
    )

    _phase(
        state_path,
        backup_id,
        event_sink,
        "VERIFY_ARTIFACTS",
    )

    # Artifact failure may leave transaction/backup metadata outside the
    # target root, but must not mutate the target filesystem.
    if not release_hashes_ok:
        return InstallResult(
            success=False,
            backup_id=backup_id,
            installed_kernel="",
            profile=PROFILE,
            grub_verified=False,
            fallback_verified=_fallback_preserved(
                target_root,
                preflight_report.fallback_kernels,
            ),
            windows_preserved=_windows_preserved(
                target_root,
                preflight_report.windows_efi_entries,
            ),
            plymouth_theme=PLYMOUTH_THEME,
            audio_installed=False,
        )

    _phase(
        state_path,
        backup_id,
        event_sink,
        "INSTALL_KERNEL",
    )

    _copy_file(
        source_root
        / "boot"
        / f"vmlinuz-{KERNEL_RELEASE}",
        target_root
        / "boot"
        / f"vmlinuz-{KERNEL_RELEASE}",
    )

    _copy_file(
        source_root
        / "boot"
        / f"initrd.img-{KERNEL_RELEASE}",
        target_root
        / "boot"
        / f"initrd.img-{KERNEL_RELEASE}",
    )

    _copy_tree(
        source_root
        / "lib"
        / "modules"
        / KERNEL_RELEASE,
        target_root
        / "lib"
        / "modules"
        / KERNEL_RELEASE,
    )

    _phase(
        state_path,
        backup_id,
        event_sink,
        "INSTALL_PROFILE",
    )

    profile_path = (
        target_root
        / "etc"
        / "arda"
        / "attestation-profile"
    )
    profile_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    profile_path.write_text(
        PROFILE + "\n",
        encoding="utf-8",
    )

    enforcement_path = (
        target_root
        / "etc"
        / "arda"
        / "enforcement-mode"
    )
    enforcement_path.write_text(
        ENFORCEMENT_MODE + "\n",
        encoding="utf-8",
    )

    _phase(
        state_path,
        backup_id,
        event_sink,
        "INSTALL_IDENTITY",
    )

    identity = source_root / "identity"

    _copy_tree(
        identity / "grub" / "arda-sovereign",
        target_root
        / "boot"
        / "grub"
        / "themes"
        / "arda-sovereign",
    )

    _copy_tree(
        identity
        / "plymouth"
        / "arda-sovereign",
        target_root
        / "usr"
        / "share"
        / "plymouth"
        / "themes"
        / "arda-sovereign",
    )

    _copy_tree(
        identity
        / "plymouth"
        / "arda-mirror-gate",
        target_root
        / "usr"
        / "share"
        / "plymouth"
        / "themes"
        / "arda-mirror-gate",
    )

    audio_source = (
        identity
        / "audio"
        / "arda-awakening.wav"
    )
    audio_destination = (
        target_root
        / "usr"
        / "share"
        / "arda"
        / "audio"
        / "arda-awakening.wav"
    )
    audio_destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    audio_installed = bool(
        audio_installer(
            audio_source,
            audio_destination,
        )
    )

    if audio_installed and not audio_destination.exists():
        _copy_file(
            audio_source,
            audio_destination,
        )

    _phase(
        state_path,
        backup_id,
        event_sink,
        "CONFIGURE_PLYMOUTH",
    )

    plymouth_cfg = (
        target_root
        / "etc"
        / "arda"
        / "plymouth-theme"
    )
    plymouth_cfg.write_text(
        PLYMOUTH_THEME + "\n",
        encoding="utf-8",
    )

    _phase(
        state_path,
        backup_id,
        event_sink,
        "CONFIGURE_GRUB",
    )

    grub_cfg = (
        target_root
        / "etc"
        / "default"
        / "grub.d"
        / "99-valinor-lite.cfg"
    )
    grub_cfg.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    grub_cfg.write_text(
        '# ARDA_VALINOR_LITE\n'
        'GRUB_THEME="/boot/grub/themes/'
        'arda-sovereign/theme.txt"\n',
        encoding="utf-8",
    )

    _phase(
        state_path,
        backup_id,
        event_sink,
        "GENERATE_BOOT_MENU",
    )

    generated = (
        target_root
        / "boot"
        / "grub"
        / "grub.cfg"
    )
    generated.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    generated.write_text(
        "# generated by Valinor Lite transaction\n"
        f"# kernel {KERNEL_RELEASE}\n",
        encoding="utf-8",
    )

    _phase(
        state_path,
        backup_id,
        event_sink,
        "VERIFY",
    )

    grub_verified = (
        target_root
        / "boot"
        / "grub"
        / "themes"
        / "arda-sovereign"
        / "theme.txt"
    ).is_file() and grub_cfg.is_file()

    fallback_verified = _fallback_preserved(
        target_root,
        preflight_report.fallback_kernels,
    )

    windows_preserved = _windows_preserved(
        target_root,
        preflight_report.windows_efi_entries,
    )

    security_ok = (
        (
            target_root
            / "boot"
            / f"vmlinuz-{KERNEL_RELEASE}"
        ).is_file()
        and (
            target_root
            / "boot"
            / f"initrd.img-{KERNEL_RELEASE}"
        ).is_file()
        and grub_verified
        and fallback_verified
        and windows_preserved
        and enforcement_path.read_text(
            encoding="utf-8"
        ).strip()
        == ENFORCEMENT_MODE
    )

    if not security_ok:
        return InstallResult(
            success=False,
            backup_id=backup_id,
            installed_kernel=KERNEL_RELEASE,
            profile=PROFILE,
            grub_verified=grub_verified,
            fallback_verified=fallback_verified,
            windows_preserved=windows_preserved,
            plymouth_theme=PLYMOUTH_THEME,
            audio_installed=audio_installed,
        )

    _phase(
        state_path,
        backup_id,
        event_sink,
        "COMMIT_INSTALL_STATE",
    )

    _write_state(
        state_path,
        phase="COMMIT_INSTALL_STATE",
        backup_id=backup_id,
        committed=True,
    )

    return InstallResult(
        success=True,
        backup_id=backup_id,
        installed_kernel=KERNEL_RELEASE,
        profile=PROFILE,
        grub_verified=grub_verified,
        fallback_verified=fallback_verified,
        windows_preserved=windows_preserved,
        plymouth_theme=PLYMOUTH_THEME,
        audio_installed=audio_installed,
    )


__all__ = [
    "InstallResult",
    "install_valinor_lite",
]
