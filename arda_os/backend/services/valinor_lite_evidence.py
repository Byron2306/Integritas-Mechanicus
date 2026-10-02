from dataclasses import dataclass
from pathlib import Path
from typing import Callable


REQUIRED_BPF_MAPS = (
    "harmony_map",
    "state_map",
    "deny_count",
    "verity_identity_map",
    "active_generation_map",
    "measured_exec_map",
    "policy_state_map",
    "lockdown_map",
    "last_deny_event_map",
)


@dataclass(frozen=True)
class LiteEvidence:
    kernel_sha256: str
    initramfs_sha256: str
    kernel_identity_verified: bool
    initramfs_identity_verified: bool
    bpf_lsm_available: bool
    measured_maps_available: bool
    pqc_native_verified: bool
    secure_boot_state: str
    software_rooted: bool


def _sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def collect_lite_evidence(
    *,
    kernel_path: str | Path,
    initramfs_path: str | Path,
    expected_kernel_sha256: str,
    expected_initramfs_sha256: str,
    bpf_root: str | Path,
    bpf_lsm_probe: Callable[[], bool],
    native_pqc_probe: Callable[[], bool],
    secure_boot_probe: Callable[[], str],
) -> LiteEvidence:
    kernel_path = Path(kernel_path)
    initramfs_path = Path(initramfs_path)
    bpf_root = Path(bpf_root)

    kernel_sha256 = _sha256_file(kernel_path)
    initramfs_sha256 = _sha256_file(initramfs_path)

    kernel_identity_verified = (
        kernel_sha256.lower()
        == expected_kernel_sha256.strip().lower()
    )
    initramfs_identity_verified = (
        initramfs_sha256.lower()
        == expected_initramfs_sha256.strip().lower()
    )

    bpf_lsm_available = bool(bpf_lsm_probe())

    measured_maps_available = all(
        (bpf_root / name).exists()
        for name in REQUIRED_BPF_MAPS
    )

    pqc_native_verified = bool(native_pqc_probe())
    secure_boot_state = str(secure_boot_probe())

    software_rooted = all(
        (
            kernel_identity_verified,
            initramfs_identity_verified,
            bpf_lsm_available,
            measured_maps_available,
            pqc_native_verified,
        )
    )

    return LiteEvidence(
        kernel_sha256=kernel_sha256,
        initramfs_sha256=initramfs_sha256,
        kernel_identity_verified=kernel_identity_verified,
        initramfs_identity_verified=initramfs_identity_verified,
        bpf_lsm_available=bpf_lsm_available,
        measured_maps_available=measured_maps_available,
        pqc_native_verified=pqc_native_verified,
        secure_boot_state=secure_boot_state,
        software_rooted=software_rooted,
    )


def native_pqc_self_test(service) -> bool:
    """
    Prove a real native ML-DSA-65 sign/verify path.

    Current repository truth:
    only liboqs has a native Dilithium/ML-DSA implementation.
    Simulation and pqcrypto must not satisfy this gate.
    """
    if getattr(service, "mode", None) != "liboqs":
        return False

    payload = b"valinor-lite-native-pqc-self-test"

    try:
        keypair = service.generate_dilithium_keypair(
            key_id="test-key",
            security_level=3,
        )

        signature = service.dilithium_sign(
            keypair.key_id,
            payload,
        )

        if signature is None:
            return False

        return bool(
            service.dilithium_verify(
                keypair.public_key,
                payload,
                signature.signature,
            )
        )
    except Exception:
        return False
