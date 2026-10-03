"""Portable Valinor Lite installer orchestration.

This layer prepares a verified release payload for the existing
transactional installer. It does not grant authority by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import hashlib
import json
import shutil

from backend.services.valinor_lite_preflight import (
    run_preflight,
)


KERNEL_RELEASE = "6.12.96-valinor"


class PortableReleaseError(RuntimeError):
    """Portable release failed a deterministic trust boundary."""


@dataclass(frozen=True)
class PreparedPortableSource:
    source_root: Path
    release_hashes_ok: bool


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def prepare_portable_source(
    *,
    release_root: str | Path,
    workspace: str | Path,
    extractor: Callable[[Path, Path], None],
) -> PreparedPortableSource:
    release_root = Path(release_root)
    workspace = Path(workspace)

    manifest_path = (
        release_root
        / "manifest"
        / "release.json"
    )

    try:
        manifest = json.loads(
            manifest_path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
    ) as exc:
        raise PortableReleaseError(
            f"release_manifest_invalid: {exc}"
        ) from exc

    kernel = manifest.get("kernel")

    if not isinstance(kernel, dict):
        raise PortableReleaseError(
            "release_manifest_invalid"
        )

    archive_relative = Path(
        str(kernel.get("archive", ""))
    )

    if (
        not archive_relative.parts
        or archive_relative.is_absolute()
        or ".." in archive_relative.parts
    ):
        raise PortableReleaseError(
            "archive_path_invalid"
        )

    archive = release_root / archive_relative

    expected_archive = str(
        kernel.get("archive_sha256", "")
    ).strip().lower()

    try:
        actual_archive = _sha256(archive).lower()
    except OSError as exc:
        raise PortableReleaseError(
            "archive_missing"
        ) from exc

    # Do not create the workspace before transport custody passes.
    if actual_archive != expected_archive:
        raise PortableReleaseError(
            "archive_hash_mismatch"
        )

    source_root = workspace / "source"
    source_root.mkdir(
        parents=True,
        exist_ok=False,
    )

    try:
        extractor(
            archive,
            source_root,
        )
    except Exception as exc:
        raise PortableReleaseError(
            f"archive_extraction_failed: {exc}"
        ) from exc

    kernel_path = (
        source_root
        / "boot"
        / f"vmlinuz-{KERNEL_RELEASE}"
    )
    initramfs_path = (
        source_root
        / "boot"
        / f"initrd.img-{KERNEL_RELEASE}"
    )

    expected_kernel = str(
        kernel.get("image_sha256", "")
    ).strip().lower()

    expected_initramfs = str(
        kernel.get("initramfs_sha256", "")
    ).strip().lower()

    try:
        actual_kernel = _sha256(
            kernel_path
        ).lower()
    except OSError as exc:
        raise PortableReleaseError(
            "kernel_missing"
        ) from exc

    if actual_kernel != expected_kernel:
        raise PortableReleaseError(
            "kernel_hash_mismatch"
        )

    try:
        actual_initramfs = _sha256(
            initramfs_path
        ).lower()
    except OSError as exc:
        raise PortableReleaseError(
            "initramfs_missing"
        ) from exc

    if actual_initramfs != expected_initramfs:
        raise PortableReleaseError(
            "initramfs_hash_mismatch"
        )

    modules = (
        source_root
        / "lib"
        / "modules"
        / KERNEL_RELEASE
    )

    if not modules.is_dir():
        raise PortableReleaseError(
            "kernel_modules_missing"
        )

    identity_source = (
        release_root / "identity"
    )

    if not identity_source.is_dir():
        raise PortableReleaseError(
            "identity_missing"
        )

    shutil.copytree(
        identity_source,
        source_root / "identity",
    )

    return PreparedPortableSource(
        source_root=source_root,
        release_hashes_ok=True,
    )


__all__ = [
    "PortableReleaseError",
    "build_live_preflight_probes",
    "PreparedPortableSource",
    "prepare_portable_source",
    "run_portable_preflight",
]


def _parse_os_release(path: Path) -> dict[str, str]:
    values = {}

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return values

    for raw in text.splitlines():
        line = raw.strip()

        if (
            not line
            or line.startswith("#")
            or "=" not in line
        ):
            continue

        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"').strip("'")

    return values


def build_live_preflight_probes(
    *,
    root: str | Path = "/",
    architecture_probe,
    secure_boot_probe,
    command_runner,
    boot_free_probe,
):
    root = Path(root)

    def architecture():
        return str(architecture_probe())

    def os_release():
        return _parse_os_release(
            root / "etc" / "os-release"
        )

    def boot_mode():
        return (
            "uefi"
            if (
                root
                / "sys"
                / "firmware"
                / "efi"
            ).exists()
            else "bios"
        )

    def tpm_available():
        return any(
            (
                root / "dev" / name
            ).exists()
            for name in (
                "tpmrm0",
                "tpm0",
            )
        )

    def secure_boot_state():
        return str(secure_boot_probe())

    def efi_entries():
        try:
            output = command_runner(
                ["efibootmgr", "-v"]
            )
        except Exception:
            return ()

        return tuple(
            line.strip()
            for line in str(output).splitlines()
            if line.strip()
        )

    def efi_loader_paths():
        efi_root = (
            root
            / "boot"
            / "efi"
            / "EFI"
        )

        if not efi_root.is_dir():
            return ()

        found = []

        for path in sorted(
            efi_root.rglob("*")
        ):
            if not path.is_file():
                continue

            relative = path.relative_to(root)

            found.append(
                "/" + relative.as_posix()
            )

        return tuple(found)

    def fallback_kernels():
        boot = root / "boot"

        if not boot.is_dir():
            return ()

        kernels = []

        for path in sorted(
            boot.glob("vmlinuz-*")
        ):
            if not path.is_file():
                continue

            release = path.name.removeprefix(
                "vmlinuz-"
            )

            if release != KERNEL_RELEASE:
                kernels.append(release)

        return tuple(kernels)

    def boot_free_bytes():
        return int(
            boot_free_probe(
                root / "boot"
            )
        )

    return {
        "architecture": architecture,
        "os_release": os_release,
        "boot_mode": boot_mode,
        "tpm_available": tpm_available,
        "secure_boot_state": secure_boot_state,
        "efi_entries": efi_entries,
        "efi_loader_paths": efi_loader_paths,
        "fallback_kernels": fallback_kernels,
        "boot_free_bytes": boot_free_bytes,
    }


def run_portable_preflight(
    *,
    release_root: str | Path,
    workspace: str | Path,
    probes,
    extractor,
):
    release_root = Path(release_root)
    workspace = Path(workspace)

    prepared = prepare_portable_source(
        release_root=release_root,
        workspace=workspace,
        extractor=extractor,
    )

    portable_manifest = json.loads(
        (
            release_root
            / "manifest"
            / "release.json"
        ).read_text(encoding="utf-8")
    )

    kernel = portable_manifest["kernel"]

    derived_manifest = (
        workspace / "preflight-manifest.json"
    )

    derived_manifest.write_text(
        json.dumps(
            {
                "schema_version": (
                    "valinor-lite-release-v1"
                ),
                "kernel_release": (
                    kernel["release"]
                ),
                "kernel_artifact": str(
                    prepared.source_root
                    / "boot"
                    / f"vmlinuz-{KERNEL_RELEASE}"
                ),
                "kernel_sha256": (
                    kernel["image_sha256"]
                ),
                "preserved_initramfs": str(
                    prepared.source_root
                    / "boot"
                    / f"initrd.img-{KERNEL_RELEASE}"
                ),
                "preserved_initramfs_sha256": (
                    kernel["initramfs_sha256"]
                ),
                "identity_manifest": str(
                    release_root
                    / "identity"
                    / "manifest.json"
                ),
                "supported_architecture": (
                    portable_manifest["architecture"]
                ),
                "minimum_boot_free_bytes": (
                    512 * 1024 * 1024
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    return run_preflight(
        release_manifest_path=derived_manifest,
        probes=probes,
    )
