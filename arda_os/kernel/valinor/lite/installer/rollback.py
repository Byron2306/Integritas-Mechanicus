"""Deterministic rollback for Valinor Lite installations.

Rollback authority comes exclusively from the recorded install-state and
backup manifest.  The rollback engine does not discover candidate files,
access the network, alter unrelated kernels, repartition storage, or change
enforcement into a stricter mode.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import shutil


@dataclass(frozen=True)
class RollbackResult:
    success: bool
    restored_backup_id: str
    grub_restored: bool
    plymouth_restored: bool
    windows_preserved: bool


def _failure() -> RollbackResult:
    return RollbackResult(
        success=False,
        restored_backup_id="",
        grub_restored=False,
        plymouth_restored=False,
        windows_preserved=False,
    )


def _safe_target(root: Path, relative: str) -> Path:
    rel = Path(relative)

    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(
            f"unsafe rollback path: {relative}"
        )

    candidate = root / rel

    # Resolve the parent, not the possibly nonexistent leaf.
    root_resolved = root.resolve()
    parent_resolved = candidate.parent.resolve()

    if (
        parent_resolved != root_resolved
        and root_resolved not in parent_resolved.parents
    ):
        raise ValueError(
            f"rollback path escapes target root: {relative}"
        )

    return candidate


def _remove(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return

    if path.is_dir():
        shutil.rmtree(path)


def _restore_record(
    *,
    target_root: Path,
    files_root: Path,
    record: dict,
) -> None:
    relative = str(record["path"])
    existed = bool(record["existed"])
    kind = str(record.get("kind", "file"))

    target = _safe_target(
        target_root,
        relative,
    )
    source = _safe_target(
        files_root,
        relative,
    )

    if not existed:
        if target.exists() or target.is_symlink():
            _remove(target)
        return

    if not source.exists():
        raise FileNotFoundError(
            f"backup payload missing: {relative}"
        )

    if target.exists() or target.is_symlink():
        _remove(target)

    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if kind == "directory":
        shutil.copytree(
            source,
            target,
        )
    else:
        shutil.copy2(
            source,
            target,
        )


def _tree_fingerprint(root: Path) -> tuple:
    if not root.exists():
        return ()

    records = []

    for path in sorted(
        root.rglob("*"),
        key=lambda item: item.as_posix(),
    ):
        relative = path.relative_to(root).as_posix()

        if path.is_file():
            digest = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            records.append(
                ("file", relative, digest)
            )
        elif path.is_dir():
            records.append(
                ("dir", relative)
            )

    return tuple(records)


def _prune_originally_missing_parents(
    *,
    target_root: Path,
    relatives: list[str],
) -> None:
    ordered = sorted(
        relatives,
        key=lambda item: (
            len(Path(item).parts),
            item,
        ),
        reverse=True,
    )

    for relative in ordered:
        target = _safe_target(
            target_root,
            relative,
        )

        if not target.exists():
            continue

        if not target.is_dir():
            raise ValueError(
                "rollback parent provenance "
                f"is not a directory: {relative}"
            )

        try:
            target.rmdir()
        except OSError:
            # Never remove a non-empty directory.
            # It may now contain unrelated host state.
            continue


def rollback_valinor_lite(
    *,
    target_root: str | Path,
    backup_root: str | Path,
    state_path: str | Path,
) -> RollbackResult:
    target_root = Path(target_root)
    backup_root = Path(backup_root)
    state_path = Path(state_path)

    if not state_path.is_file():
        return _failure()

    try:
        state = json.loads(
            state_path.read_text(
                encoding="utf-8"
            )
        )
    except (OSError, json.JSONDecodeError):
        return _failure()

    backup_id = str(
        state.get("backup_id", "")
    ).strip()

    if not backup_id:
        return _failure()

    # Never guess another backup.
    backup_dir = backup_root / backup_id
    manifest_path = backup_dir / "backup.json"
    files_root = backup_dir / "files"

    if not manifest_path.is_file():
        return _failure()

    try:
        manifest = json.loads(
            manifest_path.read_text(
                encoding="utf-8"
            )
        )
    except (OSError, json.JSONDecodeError):
        return _failure()

    if manifest.get("backup_id") != backup_id:
        return _failure()

    records = manifest.get("paths")

    if not isinstance(records, list):
        return _failure()

    originally_missing_parent_dirs = manifest.get(
        "originally_missing_parent_dirs",
        [],
    )

    if not isinstance(
        originally_missing_parent_dirs,
        list,
    ):
        return _failure()

    if not all(
        isinstance(item, str)
        for item in originally_missing_parent_dirs
    ):
        return _failure()

    windows_root = (
        target_root
        / "boot"
        / "efi"
        / "EFI"
        / "Microsoft"
    )
    windows_before = _tree_fingerprint(
        windows_root
    )

    grub_seen = False
    plymouth_seen = False

    try:
        for record in records:
            if not isinstance(record, dict):
                raise ValueError(
                    "invalid backup record"
                )

            relative = str(
                record.get("path", "")
            )

            if not relative:
                raise ValueError(
                    "backup record missing path"
                )

            lower = relative.lower()

            if (
                "grub" in lower
                or relative
                == "boot/grub/grub.cfg"
            ):
                grub_seen = True

            if "plymouth" in lower:
                plymouth_seen = True

            _restore_record(
                target_root=target_root,
                files_root=files_root,
                record=record,
            )

        _prune_originally_missing_parents(
            target_root=target_root,
            relatives=originally_missing_parent_dirs,
        )

    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ):
        return RollbackResult(
            success=False,
            restored_backup_id=backup_id,
            grub_restored=False,
            plymouth_restored=False,
            windows_preserved=(
                windows_before
                == _tree_fingerprint(
                    windows_root
                )
            ),
        )

    windows_after = _tree_fingerprint(
        windows_root
    )

    # Preserve the exact backup reference so repeated rollback uses the
    # same evidence rather than discovering or inventing another source.
    state["phase"] = "ROLLBACK_COMPLETE"
    state["rollback_complete"] = True
    state["restored_backup_id"] = backup_id

    # Rollback must never introduce strict enforcement.
    if state.get("enforcement_mode") == (
        "fsverity_strict"
    ):
        state["enforcement_mode"] = "audit"

    state_path.write_text(
        json.dumps(
            state,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return RollbackResult(
        success=True,
        restored_backup_id=backup_id,
        grub_restored=grub_seen,
        plymouth_restored=plymouth_seen,
        windows_preserved=(
            windows_before == windows_after
        ),
    )


__all__ = [
    "RollbackResult",
    "rollback_valinor_lite",
]
