from pathlib import Path

from backend.services.valinor_lite_preflight import (
    PreflightReport,
)
from kernel.valinor.lite.installer.install import (
    install_valinor_lite,
)
from kernel.valinor.lite.installer.rollback import (
    rollback_valinor_lite,
)


def _preflight() -> PreflightReport:
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
        fallback_kernels=(
            "6.12.57+deb13-amd64",
        ),
        boot_free_bytes=1024 * 1024 * 1024,
        failures=(),
    )


def _write(
    path: Path,
    data: bytes,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_bytes(data)


def _source_tree(tmp_path: Path) -> Path:
    source = tmp_path / "release"

    _write(
        source
        / "boot"
        / "vmlinuz-6.12.96-valinor",
        b"VALINOR-KERNEL",
    )

    _write(
        source
        / "boot"
        / "initrd.img-6.12.96-valinor",
        b"VALINOR-INITRAMFS",
    )

    _write(
        source
        / "lib"
        / "modules"
        / "6.12.96-valinor"
        / "modules.dep",
        b"valinor\n",
    )

    _write(
        source
        / "identity"
        / "grub"
        / "arda-sovereign"
        / "theme.txt",
        b"ARDA SOVEREIGN\n",
    )

    _write(
        source
        / "identity"
        / "plymouth"
        / "arda-sovereign"
        / "arda-sovereign.plymouth",
        (
            b"[Plymouth Theme]\n"
            b"Name=ARDA Sovereign\n"
        ),
    )

    _write(
        source
        / "identity"
        / "plymouth"
        / "arda-mirror-gate"
        / "arda-mirror-gate.plymouth",
        (
            b"[Plymouth Theme]\n"
            b"Name=ARDA Mirror Gate\n"
        ),
    )

    _write(
        source
        / "identity"
        / "audio"
        / "arda-awakening.wav",
        b"ARDA-AWAKENING",
    )

    return source


def _target_tree(tmp_path: Path) -> Path:
    target = tmp_path / "target"
    target.mkdir()

    _write(
        target
        / "boot"
        / "vmlinuz-6.12.57+deb13-amd64",
        b"DEBIAN-FALLBACK",
    )

    _write(
        target
        / "boot"
        / "efi"
        / "EFI"
        / "Microsoft"
        / "Boot"
        / "bootmgfw.efi",
        b"WINDOWS-EFI",
    )

    _write(
        target
        / "etc"
        / "arda"
        / "plymouth-theme",
        b"OLD-PLYMOUTH\n",
    )

    return target


def test_real_install_backup_restores_existing_plymouth_config(
    tmp_path,
):
    source = _source_tree(tmp_path)
    target = _target_tree(tmp_path)
    state = tmp_path / "install-state.json"
    backups = tmp_path / "backups"

    original = (
        target
        / "etc"
        / "arda"
        / "plymouth-theme"
    ).read_bytes()

    install = install_valinor_lite(
        preflight_report=_preflight(),
        source_root=source,
        target_root=target,
        backup_root=backups,
        state_path=state,
        release_hashes_ok=True,
        audio_installer=lambda src, dst: True,
        event_sink=lambda event: None,
    )

    assert install.success is True

    plymouth = (
        target
        / "etc"
        / "arda"
        / "plymouth-theme"
    )

    assert plymouth.read_bytes() != original

    rollback = rollback_valinor_lite(
        target_root=target,
        backup_root=backups,
        state_path=state,
    )

    assert rollback.success is True

    assert plymouth.read_bytes() == original

import hashlib
import json
import shutil

import pytest

from backend.services.attestation_profile import (
    resolve_attestation_profile,
)
from backend.services.phase4_live_attestation import (
    Phase4LiveAttestationError,
    Phase4LiveAttestationService,
)
from backend.services.valinor_lite_evidence import (
    REQUIRED_BPF_MAPS,
    collect_lite_evidence,
)
from kernel.valinor.lite.verify.verify_valinor_lite import (
    verify_valinor_lite,
)


AWAKENING_SHA256 = (
    "90f0e19a8b9318ac6472caa28f85894a"
    "ebaaae69113cc69a45b9e88cfa0bbc0a"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(65536),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _canonical_source_tree(
    tmp_path: Path,
) -> Path:
    source = tmp_path / "canonical-release"

    _write(
        source
        / "boot"
        / "vmlinuz-6.12.96-valinor",
        b"VALINOR-GAUNTLET-KERNEL",
    )

    _write(
        source
        / "boot"
        / "initrd.img-6.12.96-valinor",
        b"VALINOR-GAUNTLET-INITRAMFS",
    )

    _write(
        source
        / "lib"
        / "modules"
        / "6.12.96-valinor"
        / "modules.dep",
        b"gauntlet\n",
    )

    repo_root = Path(__file__).resolve().parents[3]

    canonical_identity = (
        repo_root
        / "arda_os"
        / "kernel"
        / "valinor"
        / "lite"
        / "identity"
    )

    shutil.copytree(
        canonical_identity,
        source / "identity",
    )

    return source


def _filesystem_snapshot(
    root: Path,
):
    result = {}

    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()

        if path.is_file():
            result[relative] = path.read_bytes()
        else:
            result[relative] = None

    return result


def test_complete_no_tpm_valinor_lite_simulated_host_gauntlet(
    tmp_path,
    monkeypatch,
):
    source = _canonical_source_tree(tmp_path)
    target = _target_tree(tmp_path)

    state = tmp_path / "install-state.json"
    backups = tmp_path / "backups"

    windows = (
        target
        / "boot"
        / "efi"
        / "EFI"
        / "Microsoft"
        / "Boot"
        / "bootmgfw.efi"
    )

    fallback = (
        target
        / "boot"
        / "vmlinuz-6.12.57+deb13-amd64"
    )

    windows_before = windows.read_bytes()
    fallback_before = fallback.read_bytes()

    original_boot_snapshot = _filesystem_snapshot(
        target / "boot"
    )

    # FULL must refuse a host with no TPM.
    monkeypatch.setattr(
        "backend.services.phase4_live_attestation."
        "os.path.exists",
        lambda path: (
            False
            if path in {
                "/dev/tpm0",
                "/dev/tpmrm0",
            }
            else True
        ),
    )

    monkeypatch.setattr(
        "backend.services.phase4_live_attestation."
        "shutil.which",
        lambda tool: f"/usr/bin/{tool}",
    )

    full_service = Phase4LiveAttestationService()

    with pytest.raises(
        Phase4LiveAttestationError,
        match="no TPM device found",
    ):
        full_service.capture(
            str(tmp_path / "full-attestation"),
            attestation_profile=(
                resolve_attestation_profile("full")
            ),
        )

    # LITE installs on the same truthful no-TPM host.
    first = install_valinor_lite(
        preflight_report=_preflight(),
        source_root=source,
        target_root=target,
        backup_root=backups,
        state_path=state,
        release_hashes_ok=True,
        audio_installer=lambda src, dst: True,
        event_sink=lambda event: None,
    )

    assert first.success is True
    assert first.profile == "lite"

    assert windows.read_bytes() == windows_before
    assert fallback.read_bytes() == fallback_before

    assert (
        target
        / "boot"
        / "vmlinuz-6.12.96-valinor"
    ).is_file()

    assert (
        target
        / "etc"
        / "default"
        / "grub.d"
        / "99-valinor-lite.cfg"
    ).is_file()

    assert (
        target
        / "etc"
        / "arda"
        / "attestation-profile"
    ).read_text(
        encoding="utf-8"
    ).strip() == "lite"

    assert (
        target
        / "etc"
        / "arda"
        / "enforcement-mode"
    ).read_text(
        encoding="utf-8"
    ).strip() == "audit"

    # ARDA identity, including the awakening WAV, must retain
    # its canonical identity.
    installed_audio = (
        target
        / "usr"
        / "share"
        / "arda"
        / "audio"
        / "arda-awakening.wav"
    )

    canonical_audio = (
        source
        / "identity"
        / "audio"
        / "arda-awakening.wav"
    )

    assert _sha256(canonical_audio) == (
        AWAKENING_SHA256
    )
    assert _sha256(installed_audio) == (
        AWAKENING_SHA256
    )

    assert (
        target
        / "boot"
        / "grub"
        / "themes"
        / "arda-sovereign"
        / "theme.txt"
    ).read_bytes() == (
        source
        / "identity"
        / "grub"
        / "arda-sovereign"
        / "theme.txt"
    ).read_bytes()

    # Create the measured BPF surface expected by Task 2.
    bpf_root = tmp_path / "bpffs"

    for name in REQUIRED_BPF_MAPS:
        _write(
            bpf_root / name,
            b"",
        )

    installed_kernel = (
        target
        / "boot"
        / "vmlinuz-6.12.96-valinor"
    )

    installed_initramfs = (
        target
        / "boot"
        / "initrd.img-6.12.96-valinor"
    )

    evidence = collect_lite_evidence(
        kernel_path=installed_kernel,
        initramfs_path=installed_initramfs,
        expected_kernel_sha256=_sha256(
            source
            / "boot"
            / "vmlinuz-6.12.96-valinor"
        ),
        expected_initramfs_sha256=_sha256(
            source
            / "boot"
            / "initrd.img-6.12.96-valinor"
        ),
        bpf_root=bpf_root,
        bpf_lsm_probe=lambda: True,
        native_pqc_probe=lambda: True,
        secure_boot_probe=lambda: "disabled",
    )

    assert evidence.software_rooted is True

    verification = verify_valinor_lite(
        profile=resolve_attestation_profile("lite"),
        evidence=evidence,
        tpm_available=False,
        enforcement_mode=(
            target
            / "etc"
            / "arda"
            / "enforcement-mode"
        ).read_text(
            encoding="utf-8"
        ).strip(),
    )

    assert verification.ok is True
    assert verification.tpm == "ABSENT"
    assert verification.hardware_root == "UNAVAILABLE"
    assert verification.software_root == "VERIFIED"
    assert verification.enforcement_mode == "AUDIT"

    # Preserve the first install state because it identifies
    # the backup representing the original host.
    first_state = tmp_path / "first-install-state.json"
    shutil.copy2(state, first_state)

    after_first = _filesystem_snapshot(target)

    # A repeated install must converge to the same target state.
    second = install_valinor_lite(
        preflight_report=_preflight(),
        source_root=source,
        target_root=target,
        backup_root=backups,
        state_path=state,
        release_hashes_ok=True,
        audio_installer=lambda src, dst: True,
        event_sink=lambda event: None,
    )

    assert second.success is True

    after_second = _filesystem_snapshot(target)

    assert after_second == after_first
    assert windows.read_bytes() == windows_before
    assert fallback.read_bytes() == fallback_before

    # Roll back the original installation using the exact
    # backup ID recorded by the real first Task 5 transaction.
    rollback = rollback_valinor_lite(
        target_root=target,
        backup_root=backups,
        state_path=first_state,
    )

    assert rollback.success is True
    assert rollback.windows_preserved is True

    assert windows.read_bytes() == windows_before
    assert fallback.read_bytes() == fallback_before

    assert not (
        target
        / "boot"
        / "vmlinuz-6.12.96-valinor"
    ).exists()

    assert _filesystem_snapshot(
        target / "boot"
    ) == original_boot_snapshot
