import hashlib
import json
from pathlib import Path

import pytest

from backend.services.valinor_lite_preflight import (
    PreflightReport,
    run_preflight,
)


KERNEL_SHA256 = (
    "875117b4148753e407725a3d3d838d8"
    "f40db95111c88eabd329f9d229414a527"
)

INITRAMFS_SHA256 = (
    "e1c9cd2c1694b28761d486a3662ec8e3"
    "2803871bd7bd8de11d382824c382c7ec"
)

MIN_BOOT_FREE_BYTES = 512 * 1024 * 1024


def _write(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def _manifest(
    tmp_path,
    *,
    kernel_sha=None,
    initramfs_sha=None,
):
    kernel = tmp_path / "valinor-kernel.tar.zst"
    initramfs = tmp_path / "initramfs.img"
    identity = tmp_path / "identity" / "manifest.json"

    actual_kernel_sha = _write(kernel, b"kernel-release-payload")
    actual_initramfs_sha = _write(initramfs, b"preserved-initramfs")
    identity.parent.mkdir(parents=True, exist_ok=True)
    identity.write_text(
        '{"schema_version":"valinor-lite-identity-v1"}\n',
        encoding="utf-8",
    )

    manifest = tmp_path / "release_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "valinor-lite-release-v1",
                "kernel_release": "6.12.96-valinor",
                "kernel_artifact": str(kernel),
                "kernel_sha256": kernel_sha or actual_kernel_sha,
                "preserved_initramfs": str(initramfs),
                "preserved_initramfs_sha256": (
                    initramfs_sha or actual_initramfs_sha
                ),
                "identity_manifest": str(identity),
                "supported_architecture": "x86_64",
                "minimum_boot_free_bytes": MIN_BOOT_FREE_BYTES,
            }
        ),
        encoding="utf-8",
    )

    return manifest


def _probes(**overrides):
    values = {
        "architecture": lambda: "x86_64",
        "os_release": lambda: {
            "ID": "debian",
            "ID_LIKE": "",
        },
        "boot_mode": lambda: "uefi",
        "tpm_available": lambda: False,
        "secure_boot_state": lambda: "disabled",
        "efi_entries": lambda: (
            "Boot0000* debian",
            "Boot0001* Windows Boot Manager",
        ),
        "efi_loader_paths": lambda: (
            "/boot/efi/EFI/debian/grubx64.efi",
            "/boot/efi/EFI/Microsoft/Boot/bootmgfw.efi",
        ),
        "fallback_kernels": lambda: (
            "6.12.57+deb13-amd64",
        ),
        "boot_free_bytes": lambda: MIN_BOOT_FREE_BYTES * 2,
        "os_prober_enabled": lambda: False,
    }
    values.update(overrides)
    return values


def test_non_x86_64_refuses(tmp_path):
    report = run_preflight(
        release_manifest_path=_manifest(tmp_path),
        probes=_probes(
            architecture=lambda: "aarch64",
        ),
    )

    assert report.ok is False
    assert report.architecture == "aarch64"
    assert "unsupported_architecture" in report.failures


def test_non_debian_refuses(tmp_path):
    report = run_preflight(
        release_manifest_path=_manifest(tmp_path),
        probes=_probes(
            os_release=lambda: {
                "ID": "ubuntu",
                "ID_LIKE": "debian",
            },
        ),
    )

    assert report.ok is False
    assert report.debian is False
    assert "unsupported_distribution" in report.failures


def test_no_tpm_is_allowed_for_valinor_lite(tmp_path):
    report = run_preflight(
        release_manifest_path=_manifest(tmp_path),
        probes=_probes(
            tpm_available=lambda: False,
        ),
    )

    assert report.tpm_available is False
    assert "tpm_required" not in report.failures
    assert report.ok is True


def test_missing_fallback_debian_kernel_refuses(tmp_path):
    report = run_preflight(
        release_manifest_path=_manifest(tmp_path),
        probes=_probes(
            fallback_kernels=lambda: (),
        ),
    )

    assert report.ok is False
    assert report.fallback_kernels == ()
    assert "fallback_kernel_missing" in report.failures


def test_insufficient_boot_space_refuses(tmp_path):
    report = run_preflight(
        release_manifest_path=_manifest(tmp_path),
        probes=_probes(
            boot_free_bytes=lambda: MIN_BOOT_FREE_BYTES - 1,
        ),
    )

    assert report.ok is False
    assert "insufficient_boot_space" in report.failures


def test_windows_efi_entry_is_detected_and_recorded(tmp_path):
    report = run_preflight(
        release_manifest_path=_manifest(tmp_path),
        probes=_probes(),
    )

    assert report.windows_efi_entries
    assert any(
        "Windows Boot Manager" in item
        for item in report.windows_efi_entries
    )


def test_disabled_os_prober_does_not_hide_windows_loader(tmp_path):
    report = run_preflight(
        release_manifest_path=_manifest(tmp_path),
        probes=_probes(
            efi_entries=lambda: (),
            efi_loader_paths=lambda: (
                "/boot/efi/EFI/Microsoft/Boot/bootmgfw.efi",
            ),
            os_prober_enabled=lambda: False,
        ),
    )

    assert report.windows_efi_entries == (
        "/boot/efi/EFI/Microsoft/Boot/bootmgfw.efi",
    )


def test_bad_release_kernel_hash_refuses(tmp_path):
    report = run_preflight(
        release_manifest_path=_manifest(
            tmp_path,
            kernel_sha="0" * 64,
        ),
        probes=_probes(),
    )

    assert report.ok is False
    assert "kernel_artifact_hash_mismatch" in report.failures


def test_bad_preserved_initramfs_hash_refuses(tmp_path):
    report = run_preflight(
        release_manifest_path=_manifest(
            tmp_path,
            initramfs_sha="f" * 64,
        ),
        probes=_probes(),
    )

    assert report.ok is False
    assert "initramfs_artifact_hash_mismatch" in report.failures


def test_successful_no_tpm_debian_host_is_allowed(tmp_path):
    report = run_preflight(
        release_manifest_path=_manifest(tmp_path),
        probes=_probes(),
    )

    assert report.ok is True
    assert report.architecture == "x86_64"
    assert report.debian is True
    assert report.boot_mode == "uefi"
    assert report.tpm_available is False
    assert report.secure_boot_state == "disabled"
    assert report.boot_free_bytes >= MIN_BOOT_FREE_BYTES
    assert report.failures == ()


def test_canonical_release_manifest_pins_valinor_truth():
    repo_root = Path(__file__).resolve().parents[3]
    manifest_path = (
        repo_root
        / "arda_os"
        / "kernel"
        / "valinor"
        / "lite"
        / "installer"
        / "release_manifest.json"
    )

    assert manifest_path.is_file()

    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8")
    )

    assert manifest["schema_version"] == "valinor-lite-release-v1"
    assert manifest["kernel_release"] == "6.12.96-valinor"
    assert manifest["kernel_sha256"] == (
        "875117b4148753e407725a3d3d838d8"
        "f40db95111c88eabd329f9d229414a527"
    )
    assert manifest["preserved_initramfs_sha256"] == (
        "e1c9cd2c1694b28761d486a3662ec8e3"
        "2803871bd7bd8de11d382824c382c7ec"
    )
    assert manifest["supported_architecture"] == "x86_64"
    assert manifest["identity_manifest"] == (
        "../identity/manifest.json"
    )


def test_installer_preflight_adapter_exports_service_contract():
    from kernel.valinor.lite.installer.preflight import (
        PreflightReport as InstallerPreflightReport,
        run_preflight as installer_run_preflight,
    )

    assert InstallerPreflightReport is PreflightReport
    assert installer_run_preflight is run_preflight
