import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest

from kernel.valinor.lite.installer.control import (
    PortableReleaseError,
    build_live_preflight_probes,
    prepare_portable_source,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _release(tmp_path: Path):
    root = tmp_path / "release"
    kernel_dir = root / "kernel"
    manifest_dir = root / "manifest"
    identity = root / "identity"

    kernel_dir.mkdir(parents=True)
    manifest_dir.mkdir(parents=True)
    identity.mkdir(parents=True)

    kernel_bytes = b"VALINOR-KERNEL"
    initramfs_bytes = b"VALINOR-INITRAMFS"

    archive = (
        kernel_dir
        / "valinor-kernel-6.12.96.tar.zst"
    )

    # Unit-test transport uses a plain tar stream despite the filename.
    # The orchestration layer receives an injectable extractor.
    archive.write_bytes(b"TEST-TRANSPORT")

    (identity / "marker").write_bytes(b"ARDA")

    release = {
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
            "archive_sha256": _sha256(archive),
            "image_sha256": hashlib.sha256(
                kernel_bytes
            ).hexdigest(),
            "initramfs_sha256": hashlib.sha256(
                initramfs_bytes
            ).hexdigest(),
        },
    }

    (
        manifest_dir / "release.json"
    ).write_text(
        json.dumps(release),
        encoding="utf-8",
    )

    def extractor(source: Path, destination: Path):
        assert source == archive

        kernel = (
            destination
            / "boot"
            / "vmlinuz-6.12.96-valinor"
        )
        initramfs = (
            destination
            / "boot"
            / "initrd.img-6.12.96-valinor"
        )
        modules = (
            destination
            / "lib"
            / "modules"
            / "6.12.96-valinor"
        )

        kernel.parent.mkdir(parents=True)
        modules.mkdir(parents=True)

        kernel.write_bytes(kernel_bytes)
        initramfs.write_bytes(initramfs_bytes)
        (modules / "modules.dep").write_bytes(
            b"valinor\n"
        )

    return root, archive, extractor


def test_prepare_portable_source_verifies_and_expands_release(
    tmp_path,
):
    root, _, extractor = _release(tmp_path)

    prepared = prepare_portable_source(
        release_root=root,
        workspace=tmp_path / "workspace",
        extractor=extractor,
    )

    assert prepared.source_root.is_dir()

    assert (
        prepared.source_root
        / "boot"
        / "vmlinuz-6.12.96-valinor"
    ).is_file()

    assert (
        prepared.source_root
        / "boot"
        / "initrd.img-6.12.96-valinor"
    ).is_file()

    assert (
        prepared.source_root
        / "lib"
        / "modules"
        / "6.12.96-valinor"
        / "modules.dep"
    ).is_file()

    assert (
        prepared.source_root
        / "identity"
        / "marker"
    ).read_bytes() == b"ARDA"

    assert prepared.release_hashes_ok is True


def test_prepare_portable_source_refuses_tampered_transport(
    tmp_path,
):
    root, archive, extractor = _release(tmp_path)

    archive.write_bytes(
        archive.read_bytes() + b"TAMPER"
    )

    workspace = tmp_path / "workspace"

    with pytest.raises(
        PortableReleaseError,
        match="archive_hash_mismatch",
    ):
        prepare_portable_source(
            release_root=root,
            workspace=workspace,
            extractor=extractor,
        )

    assert not workspace.exists()


def test_prepare_portable_source_refuses_bad_extracted_kernel(
    tmp_path,
):
    root, _, extractor = _release(tmp_path)

    def corrupt(source: Path, destination: Path):
        extractor(source, destination)

        (
            destination
            / "boot"
            / "vmlinuz-6.12.96-valinor"
        ).write_bytes(b"CORRUPT")

    with pytest.raises(
        PortableReleaseError,
        match="kernel_hash_mismatch",
    ):
        prepare_portable_source(
            release_root=root,
            workspace=tmp_path / "workspace",
            extractor=corrupt,
        )


def test_prepare_portable_source_refuses_bad_initramfs(
    tmp_path,
):
    root, _, extractor = _release(tmp_path)

    def corrupt(source: Path, destination: Path):
        extractor(source, destination)

        (
            destination
            / "boot"
            / "initrd.img-6.12.96-valinor"
        ).write_bytes(b"CORRUPT")

    with pytest.raises(
        PortableReleaseError,
        match="initramfs_hash_mismatch",
    ):
        prepare_portable_source(
            release_root=root,
            workspace=tmp_path / "workspace",
            extractor=corrupt,
        )


def test_live_preflight_probes_collect_debian_uefi_host(
    tmp_path,
):
    root = tmp_path / "host"

    (root / "etc").mkdir(parents=True)
    (root / "etc" / "os-release").write_text(
        'ID=debian\nID_LIKE=""\n',
        encoding="utf-8",
    )

    (root / "sys" / "firmware" / "efi").mkdir(
        parents=True
    )

    (root / "dev").mkdir()
    (root / "dev" / "tpmrm0").write_bytes(b"")

    efi = (
        root
        / "boot"
        / "efi"
        / "EFI"
        / "Microsoft"
        / "Boot"
    )
    efi.mkdir(parents=True)
    (efi / "bootmgfw.efi").write_bytes(b"WINDOWS")

    (root / "boot").mkdir(exist_ok=True)
    (
        root / "boot" / "vmlinuz-6.12.57+deb13-amd64"
    ).write_bytes(b"DEBIAN")

    def runner(argv):
        if argv == ["efibootmgr", "-v"]:
            return (
                "Boot0001* Windows Boot Manager "
                "\\EFI\\Microsoft\\Boot\\bootmgfw.efi\n"
            )
        raise AssertionError(argv)

    probes = build_live_preflight_probes(
        root=root,
        architecture_probe=lambda: "x86_64",
        secure_boot_probe=lambda: "disabled",
        command_runner=runner,
        boot_free_probe=lambda path: 1024 * 1024 * 1024,
    )

    assert probes["architecture"]() == "x86_64"
    assert probes["os_release"]()["ID"] == "debian"
    assert probes["boot_mode"]() == "uefi"
    assert probes["tpm_available"]() is True
    assert probes["secure_boot_state"]() == "disabled"

    assert any(
        "Windows Boot Manager" in item
        for item in probes["efi_entries"]()
    )

    assert probes["efi_loader_paths"]() == (
        "/boot/efi/EFI/Microsoft/Boot/bootmgfw.efi",
    )

    assert probes["fallback_kernels"]() == (
        "6.12.57+deb13-amd64",
    )

    assert probes["boot_free_bytes"]() == (
        1024 * 1024 * 1024
    )


def test_live_preflight_probes_treat_missing_tpm_as_valid_fact(
    tmp_path,
):
    root = tmp_path / "host"

    (root / "etc").mkdir(parents=True)
    (root / "etc" / "os-release").write_text(
        "ID=debian\n",
        encoding="utf-8",
    )
    (root / "boot").mkdir(parents=True)

    probes = build_live_preflight_probes(
        root=root,
        architecture_probe=lambda: "x86_64",
        secure_boot_probe=lambda: "unknown",
        command_runner=lambda argv: "",
        boot_free_probe=lambda path: 999999999,
    )

    assert probes["tpm_available"]() is False
    assert probes["boot_mode"]() == "bios"
    assert probes["efi_entries"]() == ()
    assert probes["efi_loader_paths"]() == ()


def test_run_portable_preflight_uses_prepared_payload_and_host_probes(
    tmp_path,
):
    from kernel.valinor.lite.installer.control import (
        run_portable_preflight,
    )

    root, _, extractor = _release(tmp_path)

    host = tmp_path / "host"
    (host / "etc").mkdir(parents=True)
    (host / "etc" / "os-release").write_text(
        "ID=debian\n",
        encoding="utf-8",
    )
    (host / "sys" / "firmware" / "efi").mkdir(
        parents=True
    )

    boot = host / "boot"
    boot.mkdir(parents=True)
    (
        boot / "vmlinuz-6.12.57+deb13-amd64"
    ).write_bytes(b"DEBIAN")

    probes = build_live_preflight_probes(
        root=host,
        architecture_probe=lambda: "x86_64",
        secure_boot_probe=lambda: "disabled",
        command_runner=lambda argv: "",
        boot_free_probe=lambda path: 1024 * 1024 * 1024,
    )

    report = run_portable_preflight(
        release_root=root,
        workspace=tmp_path / "preflight-work",
        probes=probes,
        extractor=extractor,
    )

    assert report.ok is True
    assert report.architecture == "x86_64"
    assert report.debian is True
    assert report.fallback_kernels == (
        "6.12.57+deb13-amd64",
    )
    assert report.failures == ()
