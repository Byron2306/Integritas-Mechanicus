from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
ARDA_OS = ROOT / "arda_os"

if str(ARDA_OS) not in sys.path:
    sys.path.insert(0, str(ARDA_OS))

from backend.services.measured_policy_profiles import (
    CRITICAL_SYSTEM_FILES,
    DISCOVERY_ALLOWED_PREFIXES,
)


def test_boot_remains_an_allowed_discovery_prefix():
    assert "/boot/" in DISCOVERY_ALLOWED_PREFIXES


def test_efi_system_partition_is_excluded():
    assert not any(
        path.startswith("/boot/efi/")
        for path in CRITICAL_SYSTEM_FILES
    )


def test_non_esp_boot_artifacts_remain_measured():
    assert "/boot/grub/grub.cfg" in CRITICAL_SYSTEM_FILES
    assert any(path.startswith("/boot/vmlinuz-") for path in CRITICAL_SYSTEM_FILES)
    assert any(path.startswith("/boot/initrd") for path in CRITICAL_SYSTEM_FILES)
