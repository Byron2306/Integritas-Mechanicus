from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping
import hashlib
import json


@dataclass(frozen=True)
class PreflightReport:
    ok: bool
    architecture: str
    debian: bool
    boot_mode: str
    tpm_available: bool
    secure_boot_state: str
    windows_efi_entries: tuple[str, ...]
    fallback_kernels: tuple[str, ...]
    boot_free_bytes: int
    failures: tuple[str, ...]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _windows_entries(
    efi_entries: tuple[str, ...],
    loader_paths: tuple[str, ...],
) -> tuple[str, ...]:
    found = []

    for entry in efi_entries:
        if "windows" in entry.lower():
            found.append(entry)

    for path in loader_paths:
        normalized = path.lower()
        if (
            "/efi/microsoft/" in normalized
            or normalized.endswith("/bootmgfw.efi")
        ):
            if path not in found:
                found.append(path)

    return tuple(found)


def run_preflight(
    *,
    release_manifest_path: str | Path,
    probes: Mapping[str, Callable[[], object]],
) -> PreflightReport:
    manifest_path = Path(release_manifest_path)
    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    architecture = str(probes["architecture"]())
    os_release = dict(probes["os_release"]())
    boot_mode = str(probes["boot_mode"]())
    tpm_available = bool(probes["tpm_available"]())
    secure_boot_state = str(probes["secure_boot_state"]())

    efi_entries = tuple(probes["efi_entries"]())
    loader_paths = tuple(probes["efi_loader_paths"]())
    fallback_kernels = tuple(probes["fallback_kernels"]())
    boot_free_bytes = int(probes["boot_free_bytes"]())

    failures = []

    if architecture != manifest["supported_architecture"]:
        failures.append("unsupported_architecture")

    debian = os_release.get("ID", "").strip().lower() == "debian"

    if not debian:
        failures.append("unsupported_distribution")

    if not fallback_kernels:
        failures.append("fallback_kernel_missing")

    minimum_boot_free_bytes = int(
        manifest["minimum_boot_free_bytes"]
    )

    if boot_free_bytes < minimum_boot_free_bytes:
        failures.append("insufficient_boot_space")

    kernel_path = Path(manifest["kernel_artifact"])
    expected_kernel_sha = str(
        manifest["kernel_sha256"]
    ).lower()

    try:
        kernel_hash_ok = (
            _sha256(kernel_path).lower()
            == expected_kernel_sha
        )
    except OSError:
        kernel_hash_ok = False

    if not kernel_hash_ok:
        failures.append("kernel_artifact_hash_mismatch")

    initramfs_path = Path(
        manifest["preserved_initramfs"]
    )
    expected_initramfs_sha = str(
        manifest["preserved_initramfs_sha256"]
    ).lower()

    try:
        initramfs_hash_ok = (
            _sha256(initramfs_path).lower()
            == expected_initramfs_sha
        )
    except OSError:
        initramfs_hash_ok = False

    if not initramfs_hash_ok:
        failures.append("initramfs_artifact_hash_mismatch")

    windows_efi_entries = _windows_entries(
        efi_entries,
        loader_paths,
    )

    return PreflightReport(
        ok=not failures,
        architecture=architecture,
        debian=debian,
        boot_mode=boot_mode,
        tpm_available=tpm_available,
        secure_boot_state=secure_boot_state,
        windows_efi_entries=windows_efi_entries,
        fallback_kernels=fallback_kernels,
        boot_free_bytes=boot_free_bytes,
        failures=tuple(failures),
    )
