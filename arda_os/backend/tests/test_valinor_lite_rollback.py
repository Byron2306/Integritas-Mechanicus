import json
from pathlib import Path

from kernel.valinor.lite.installer.rollback import (
    RollbackResult,
    rollback_valinor_lite,
)


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _make_backup(
    tmp_path: Path,
    *,
    backup_id: str = "backup-123",
):
    target = tmp_path / "target"
    backup_root = tmp_path / "backups"
    backup_dir = backup_root / backup_id
    files = backup_dir / "files"

    target.mkdir()
    backup_dir.mkdir(parents=True)

    records = [
        {
            "path": "etc/default/grub.d/99-valinor-lite.cfg",
            "existed": True,
            "kind": "file",
        },
        {
            "path": "etc/arda/plymouth-theme",
            "existed": True,
            "kind": "file",
        },
        {
            "path": "boot/vmlinuz-6.12.96-valinor",
            "existed": False,
            "kind": "file",
        },
    ]

    _write(
        files / "etc/default/grub.d/99-valinor-lite.cfg",
        b"OLD-GRUB\n",
    )
    _write(
        files / "etc/arda/plymouth-theme",
        b"OLD-PLYMOUTH\n",
    )

    _write(
        target / "etc/default/grub.d/99-valinor-lite.cfg",
        b"NEW-GRUB\n",
    )
    _write(
        target / "etc/arda/plymouth-theme",
        b"arda-mirror-gate\n",
    )
    _write(
        target / "boot/vmlinuz-6.12.96-valinor",
        b"VALINOR\n",
    )

    windows = (
        target
        / "boot"
        / "efi"
        / "EFI"
        / "Microsoft"
        / "Boot"
        / "bootmgfw.efi"
    )
    _write(windows, b"WINDOWS")

    fallback = (
        target
        / "boot"
        / "vmlinuz-6.12.57+deb13-amd64"
    )
    _write(fallback, b"DEBIAN")

    (backup_dir / "backup.json").write_text(
        json.dumps(
            {
                "schema_version": "valinor-lite-backup-v1",
                "backup_id": backup_id,
                "paths": records,
            }
        ),
        encoding="utf-8",
    )

    state = tmp_path / "install-state.json"
    state.write_text(
        json.dumps(
            {
                "schema_version": "valinor-lite-install-state-v1",
                "phase": "INSTALL_KERNEL",
                "backup_id": backup_id,
                "profile": "lite",
                "enforcement_mode": "audit",
                "kernel_release": "6.12.96-valinor",
                "committed": False,
            }
        ),
        encoding="utf-8",
    )

    return target, backup_root, state, windows, fallback


def test_exact_backup_selected_from_install_state(tmp_path):
    target, backups, state, _, _ = _make_backup(tmp_path)

    result = rollback_valinor_lite(
        target_root=target,
        backup_root=backups,
        state_path=state,
    )

    assert result.success is True
    assert result.restored_backup_id == "backup-123"


def test_interrupted_install_can_roll_back(tmp_path):
    target, backups, state, _, _ = _make_backup(tmp_path)

    payload = json.loads(state.read_text())
    payload["phase"] = "INSTALL_IDENTITY"
    payload["committed"] = False
    state.write_text(json.dumps(payload))

    result = rollback_valinor_lite(
        target_root=target,
        backup_root=backups,
        state_path=state,
    )

    assert result.success is True


def test_missing_backup_refuses_rather_than_guessing(tmp_path):
    target = tmp_path / "target"
    target.mkdir()

    state = tmp_path / "install-state.json"
    state.write_text(
        json.dumps(
            {
                "backup_id": "missing-backup",
                "phase": "INSTALL_KERNEL",
                "committed": False,
            }
        )
    )

    result = rollback_valinor_lite(
        target_root=target,
        backup_root=tmp_path / "backups",
        state_path=state,
    )

    assert result.success is False
    assert result.restored_backup_id == ""


def test_grub_config_restored(tmp_path):
    target, backups, state, _, _ = _make_backup(tmp_path)

    result = rollback_valinor_lite(
        target_root=target,
        backup_root=backups,
        state_path=state,
    )

    assert result.success is True
    assert (
        target
        / "etc/default/grub.d/99-valinor-lite.cfg"
    ).read_bytes() == b"OLD-GRUB\n"
    assert result.grub_restored is True


def test_plymouth_config_restored(tmp_path):
    target, backups, state, _, _ = _make_backup(tmp_path)

    result = rollback_valinor_lite(
        target_root=target,
        backup_root=backups,
        state_path=state,
    )

    assert result.success is True
    assert (
        target
        / "etc/arda/plymouth-theme"
    ).read_bytes() == b"OLD-PLYMOUTH\n"
    assert result.plymouth_restored is True


def test_windows_efi_files_are_untouched(tmp_path):
    target, backups, state, windows, _ = _make_backup(tmp_path)

    before = windows.read_bytes()

    result = rollback_valinor_lite(
        target_root=target,
        backup_root=backups,
        state_path=state,
    )

    assert result.success is True
    assert windows.read_bytes() == before
    assert result.windows_preserved is True


def test_unrelated_fallback_kernel_is_untouched(tmp_path):
    target, backups, state, _, fallback = _make_backup(tmp_path)

    before = fallback.read_bytes()

    result = rollback_valinor_lite(
        target_root=target,
        backup_root=backups,
        state_path=state,
    )

    assert result.success is True
    assert fallback.read_bytes() == before


def test_created_valinor_file_is_removed(tmp_path):
    target, backups, state, _, _ = _make_backup(tmp_path)

    valinor = target / "boot/vmlinuz-6.12.96-valinor"
    assert valinor.is_file()

    result = rollback_valinor_lite(
        target_root=target,
        backup_root=backups,
        state_path=state,
    )

    assert result.success is True
    assert not valinor.exists()


def test_rollback_requires_no_network(tmp_path, monkeypatch):
    target, backups, state, _, _ = _make_backup(tmp_path)

    def explode(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(
        "socket.create_connection",
        explode,
    )

    result = rollback_valinor_lite(
        target_root=target,
        backup_root=backups,
        state_path=state,
    )

    assert result.success is True


def test_rollback_never_activates_strict_mode(tmp_path):
    target, backups, state, _, _ = _make_backup(tmp_path)

    result = rollback_valinor_lite(
        target_root=target,
        backup_root=backups,
        state_path=state,
    )

    assert result.success is True

    strict_markers = list(
        target.rglob("*fsverity_strict*")
    )
    assert strict_markers == []


def test_repeated_rollback_is_safe_and_idempotent(tmp_path):
    target, backups, state, _, _ = _make_backup(tmp_path)

    first = rollback_valinor_lite(
        target_root=target,
        backup_root=backups,
        state_path=state,
    )
    second = rollback_valinor_lite(
        target_root=target,
        backup_root=backups,
        state_path=state,
    )

    assert first.success is True
    assert second.success is True
    assert second.restored_backup_id == first.restored_backup_id


def test_result_contract(tmp_path):
    target, backups, state, _, _ = _make_backup(tmp_path)

    result = rollback_valinor_lite(
        target_root=target,
        backup_root=backups,
        state_path=state,
    )

    assert isinstance(result, RollbackResult)
    assert result.success is True
    assert result.grub_restored is True
    assert result.plymouth_restored is True
    assert result.windows_preserved is True


def test_cli_rollback_requires_explicit_paths(tmp_path):
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
        [str(entry), "--rollback"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "rollback requires" in result.stderr.lower()


def test_cli_rollback_uses_recorded_backup(tmp_path):
    import subprocess

    target, backups, state, _, _ = _make_backup(tmp_path)

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
            "--rollback",
            "--target-root",
            str(target),
            "--backup-root",
            str(backups),
            "--state-path",
            str(state),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "ROLLBACK_COMPLETE" in result.stdout

    assert (
        target
        / "etc/default/grub.d/99-valinor-lite.cfg"
    ).read_bytes() == b"OLD-GRUB\n"
