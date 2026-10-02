"""Deterministic portable Valinor Lite release builder."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile


KERNEL_RELEASE = "6.12.96-valinor"

CANONICAL_KERNEL_ARCHIVE_SHA256 = (
    "cd18653a510cf0e2f67ff00006d22b09e"
    "de74983051c770045f4a2b719e9071d"
)

KERNEL_IMAGE_SHA256 = (
    "875117b4148753e407725a3d3d838d8f"
    "40db95111c88eabd329f9d229414a527"
)

INITRAMFS_SHA256 = (
    "e1c9cd2c1694b28761d486a3662ec8e3"
    "2803871bd7bd8de11d382824c382c7ec"
)

RELEASE_NAME = "valinor-lite-6.12.96"
ARCHIVE_NAME = f"{RELEASE_NAME}.tar.zst"


@dataclass(frozen=True)
class ReleaseBuildResult:
    archive_path: Path
    sha256_path: Path
    archive_sha256: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(65536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _copy_file(
    source: Path,
    destination: Path,
    *,
    executable: bool = False,
) -> None:
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copyfile(
        source,
        destination,
    )

    destination.chmod(
        0o755 if executable else 0o644
    )


def _copy_tree_explicit(
    source: Path,
    destination: Path,
) -> None:
    """Copy files while excluding generated Python debris."""

    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)

        if "__pycache__" in relative.parts:
            continue

        if path.suffix == ".pyc":
            continue

        if path.is_dir():
            continue

        target = destination / relative

        _copy_file(
            path,
            target,
            executable=os.access(path, os.X_OK),
        )


def _stage_python_runtime(
    *,
    repo_root: Path,
    release_root: Path,
) -> None:
    runtime = (
        release_root
        / "profile"
        / "python"
    )

    backend_services = (
        runtime
        / "backend"
        / "services"
    )

    for name in (
        "attestation_profile.py",
        "valinor_lite_evidence.py",
        "valinor_lite_preflight.py",
    ):
        _copy_file(
            repo_root
            / "arda_os"
            / "backend"
            / "services"
            / name,
            backend_services / name,
        )

    installer_runtime = (
        runtime
        / "kernel"
        / "valinor"
        / "lite"
        / "installer"
    )

    for name in (
        "preflight.py",
        "install.py",
        "rollback.py",
        "greeter.py",
    ):
        _copy_file(
            repo_root
            / "arda_os"
            / "kernel"
            / "valinor"
            / "lite"
            / "installer"
            / name,
            installer_runtime / name,
        )

    verifier_runtime = (
        runtime
        / "kernel"
        / "valinor"
        / "lite"
        / "verify"
    )

    _copy_file(
        repo_root
        / "arda_os"
        / "kernel"
        / "valinor"
        / "lite"
        / "verify"
        / "verify_valinor_lite.py",
        verifier_runtime
        / "verify_valinor_lite.py",
    )


def _write_install_launcher(
    destination: Path,
) -> None:
    destination.write_text(
        """#!/usr/bin/env python3
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "profile" / "python"
sys.path.insert(0, str(RUNTIME))

SOURCE = (
    ROOT
    / "profile"
    / "source"
    / "install-valinor-lite"
)

runpy.run_path(
    str(SOURCE),
    run_name="__main__",
)
""",
        encoding="utf-8",
    )
    destination.chmod(0o755)


def _write_verify_launcher(
    destination: Path,
) -> None:
    destination.write_text(
        """#!/usr/bin/env python3
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "profile" / "python"
sys.path.insert(0, str(RUNTIME))

SOURCE = (
    ROOT
    / "profile"
    / "source"
    / "verify-valinor-lite"
)

runpy.run_path(
    str(SOURCE),
    run_name="__main__",
)
""",
        encoding="utf-8",
    )
    destination.chmod(0o755)


def _write_offline_verifier(
    destination: Path,
) -> None:
    destination.write_text(
        """#!/usr/bin/env python3
from pathlib import Path
import hashlib
import json
import sys


def sha256(path):
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(65536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def main():
    if len(sys.argv) != 2:
        print(
            "usage: verify_manifest.py RELEASE_ROOT"
        )
        return 2

    root = Path(sys.argv[1]).resolve()
    manifest_path = (
        root
        / "manifest"
        / "files.json"
    )

    try:
        manifest = json.loads(
            manifest_path.read_text(
                encoding="utf-8"
            )
        )
    except Exception as exc:
        print(f"HASH FAILURE: {exc}")
        return 1

    for record in manifest.get("files", []):
        relative = Path(record["path"])

        if (
            relative.is_absolute()
            or ".." in relative.parts
        ):
            print(
                "HASH FAILURE: unsafe path "
                f"{record['path']}"
            )
            return 1

        path = root / relative

        if not path.is_file():
            print(
                "HASH FAILURE: missing "
                f"{record['path']}"
            )
            return 1

        actual = sha256(path)

        if actual != record["sha256"]:
            print(
                "HASH FAILURE: "
                f"{record['path']}"
            )
            return 1

    print("ALL HASHES PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
""",
        encoding="utf-8",
    )
    destination.chmod(0o755)


def _write_release_metadata(
    *,
    release_root: Path,
    kernel_archive_sha256: str,
) -> None:
    manifest_dir = release_root / "manifest"
    manifest_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    release = {
        "schema_version": (
            "valinor-lite-portable-release-v1"
        ),
        "architecture": "x86_64",
        "profile": "lite",
        "kernel": {
            "release": KERNEL_RELEASE,
            "archive": (
                "kernel/"
                "valinor-kernel-6.12.96.tar.zst"
            ),
            "archive_sha256": (
                kernel_archive_sha256
            ),
            "image_sha256": (
                KERNEL_IMAGE_SHA256
            ),
            "initramfs_sha256": (
                INITRAMFS_SHA256
            ),
        },
    }

    (
        manifest_dir
        / "release.json"
    ).write_text(
        json.dumps(
            release,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    _write_offline_verifier(
        manifest_dir / "verify_manifest.py"
    )


def _write_file_manifest(
    release_root: Path,
) -> None:
    manifest_path = (
        release_root
        / "manifest"
        / "files.json"
    )

    records = []

    for path in sorted(
        release_root.rglob("*"),
        key=lambda p: p.as_posix(),
    ):
        if not path.is_file():
            continue

        if path == manifest_path:
            continue

        records.append(
            {
                "path": (
                    path
                    .relative_to(release_root)
                    .as_posix()
                ),
                "sha256": _sha256(path),
            }
        )

    manifest = {
        "schema_version": (
            "valinor-lite-file-manifest-v1"
        ),
        "files": records,
    }

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _stage_release(
    *,
    repo_root: Path,
    kernel_archive: Path,
    release_root: Path,
    kernel_archive_sha256: str,
) -> None:
    lite = (
        repo_root
        / "arda_os"
        / "kernel"
        / "valinor"
        / "lite"
    )

    release_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    # Opaque kernel transport artifact.
    _copy_file(
        kernel_archive,
        release_root
        / "kernel"
        / "valinor-kernel-6.12.96.tar.zst",
    )

    # Canonical identity only. No historical theme tree.
    _copy_tree_explicit(
        lite / "identity",
        release_root / "identity",
    )

    # Self-contained runtime.
    _stage_python_runtime(
        repo_root=repo_root,
        release_root=release_root,
    )

    source_root = (
        release_root
        / "profile"
        / "source"
    )

    _copy_file(
        lite / "install-valinor-lite",
        source_root / "install-valinor-lite",
        executable=True,
    )

    _copy_file(
        lite / "verify-valinor-lite",
        source_root / "verify-valinor-lite",
        executable=True,
    )

    _copy_file(
        lite
        / "installer"
        / "release_manifest.json",
        release_root
        / "profile"
        / "release_manifest.json",
    )

    # Public launchers intentionally bootstrap their own runtime.
    _write_install_launcher(
        release_root / "install-valinor-lite"
    )

    verify_dir = release_root / "verify"
    verify_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    _write_verify_launcher(
        verify_dir / "verify-valinor-lite"
    )

    _write_release_metadata(
        release_root=release_root,
        kernel_archive_sha256=(
            kernel_archive_sha256
        ),
    )

    _write_file_manifest(release_root)


def _build_archive(
    *,
    staging_parent: Path,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    subprocess.run(
        [
            "tar",
            "--zstd",
            "--sort=name",
            "--mtime=@0",
            "--owner=0",
            "--group=0",
            "--numeric-owner",
            "--format=gnu",
            "-cf",
            str(output_path),
            RELEASE_NAME,
        ],
        cwd=staging_parent,
        check=True,
        env={
            **os.environ,
            "TZ": "UTC",
        },
    )


def build_valinor_lite_release(
    *,
    repo_root: str | Path,
    kernel_archive: str | Path,
    output_dir: str | Path,
    expected_kernel_archive_sha256: str = (
        CANONICAL_KERNEL_ARCHIVE_SHA256
    ),
) -> ReleaseBuildResult:
    repo_root = Path(repo_root).resolve()
    kernel_archive = Path(
        kernel_archive
    ).resolve()
    output_dir = Path(output_dir).resolve()

    actual_kernel_archive_sha256 = _sha256(
        kernel_archive
    )

    if (
        actual_kernel_archive_sha256
        != expected_kernel_archive_sha256
    ):
        raise ValueError(
            "kernel archive hash mismatch: "
            f"expected "
            f"{expected_kernel_archive_sha256}, "
            f"got "
            f"{actual_kernel_archive_sha256}"
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    archive_path = (
        output_dir / ARCHIVE_NAME
    )

    sha256_path = Path(
        str(archive_path) + ".sha256"
    )

    with tempfile.TemporaryDirectory(
        prefix="valinor-lite-release-"
    ) as temporary:
        staging_parent = Path(temporary)

        release_root = (
            staging_parent / RELEASE_NAME
        )

        _stage_release(
            repo_root=repo_root,
            kernel_archive=kernel_archive,
            release_root=release_root,
            kernel_archive_sha256=(
                actual_kernel_archive_sha256
            ),
        )

        _build_archive(
            staging_parent=staging_parent,
            output_path=archive_path,
        )

    archive_sha256 = _sha256(
        archive_path
    )

    sha256_path.write_text(
        f"{archive_sha256}  "
        f"{archive_path.name}\n",
        encoding="utf-8",
    )

    return ReleaseBuildResult(
        archive_path=archive_path,
        sha256_path=sha256_path,
        archive_sha256=archive_sha256,
    )


__all__ = [
    "CANONICAL_KERNEL_ARCHIVE_SHA256",
    "ReleaseBuildResult",
    "build_valinor_lite_release",
]
