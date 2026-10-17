"""Fail-closed validation of the frozen Gen11 QEMU recovery evidence.

Historical laboratory qualification only. Never authorizes installation.
"""
import hashlib
import json
import tarfile
from pathlib import Path

EXPECTED_BUNDLE = (
    "22e5fe67daaa411e15822a29ed625dc442b60cc97d59ebc1c1ac90361ac08834"
)
EXPECTED_GRUB = (
    "b0b9c688d7bf5dc3c94eccf1f94eaac312955b8016029b6873d6edc8ad5bc483"
)

REQUIRED = {
    "usr/local/sbin/arda-lab-auto-recover",
    "usr/local/sbin/arda-preboot-repair",
    "etc/systemd/system/arda-lab-auto-recover.service",
    "etc/systemd/system/arda-preboot-repair.service",
    "root/arda-recovery-lab/transaction-state",
    "root/arda-recovery-lab/grub.gen10-known-good.cfg",
    "root/arda-recovery-lab/grub.candidate.cfg",
    "root/arda-recovery-lab/receipts/preboot-recovery.json",
    "root/arda-preboot-recovery/recovery.cfg",
}


class EvidenceRefused(RuntimeError):
    pass


def require(condition, reason):
    if not condition:
        raise EvidenceRefused(reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def inspect(bundle):
    bundle = Path(bundle)
    require(bundle.is_file() and not bundle.is_symlink(),
            "bundle_missing_or_symlink")
    require(bundle.stat().st_size <= 10_000_000,
            "oversized_compressed_bundle")
    require(sha(bundle.read_bytes()) == EXPECTED_BUNDLE,
            "bundle_digest_mismatch")

    with tarfile.open(bundle, "r:gz") as archive:
        members = archive.getmembers()
        names = [m.name for m in members]

        require(len(names) == len(set(names)), "duplicate_members")
        require(set(names) == REQUIRED, "unexpected_bundle_members")
        require(all(
            m.name == m.name.lstrip("/")
            and ".." not in Path(m.name).parts
            for m in members
        ), "unsafe_member_path")
        require(all(m.isfile() for m in members),
                "non_regular_bundle_member")
        require(all(0 <= m.size <= 2_000_000 for m in members),
                "oversized_bundle_member")
        require(sum(m.size for m in members) <= 10_000_000,
                "excessive_uncompressed_size")

        def read(name):
            return archive.extractfile(name).read()

        good = read(
            "root/arda-recovery-lab/grub.gen10-known-good.cfg"
        )
        require(sha(good) == EXPECTED_GRUB,
                "known_good_grub_mismatch")

        receipt = json.loads(read(
            "root/arda-recovery-lab/receipts/preboot-recovery.json"
        ))

        require(receipt.get("schema") == "arda-preboot-lab-v1",
                "receipt_schema")
        require(receipt.get("status") == "PRIMARY_RESTORED",
                "receipt_status")
        require(receipt.get("primary_grub_sha256") == EXPECTED_GRUB,
                "receipt_grub_mismatch")
        require(receipt.get("recovery_boot") is True,
                "recovery_boot_not_recorded")
        require(receipt.get("laboratory_only") is True,
                "laboratory_boundary_missing")

        recovery_cfg = read(
            "root/arda-preboot-recovery/recovery.cfg"
        ).decode()
        require("arda.recovery=1" in recovery_cfg,
                "recovery_marker_missing")

        preboot_unit = read(
            "etc/systemd/system/arda-preboot-repair.service"
        ).decode()
        require(
            "ConditionKernelCommandLine=arda.recovery=1"
            in preboot_unit,
            "recovery_service_not_gated",
        )

        repair_script = read(
            "usr/local/sbin/arda-preboot-repair"
        ).decode()
        require("not_independent_recovery_boot" in repair_script,
                "repair_identity_guard_missing")
        require("unknown_primary_grub_content" in repair_script,
                "unknown_content_refusal_missing")

    return {
        "schema": "arda-gen11-qemu-recovery-evidence-v1",
        "status": "HISTORICAL_LAB_EVIDENCE_VALIDATED",
        "bundle_sha256": EXPECTED_BUNDLE,
        "known_good_grub_sha256": EXPECTED_GRUB,
        "required_members_verified": len(REQUIRED),
        "cryptographic_recovery_authority_proven": False,
        "automatic_primary_failure_detection_proven": False,
        "actual_power_loss_proven": False,
        "production_install_authorized": False,
        "first_boot_authorized": False,
    }


if __name__ == "__main__":
    import sys

    try:
        print(json.dumps(inspect(sys.argv[1]), indent=2))
    except (EvidenceRefused, ValueError, KeyError, IndexError,
            tarfile.TarError, OSError) as exc:
        print("RECOVERY_EVIDENCE=REFUSE:", exc)
        sys.exit(1)
