"""Regression tests for stale BPF pin authority claims."""

from unittest.mock import patch

from backend.services.os_enforcement_service import OsEnforcementService


def test_pinned_maps_alone_cannot_prove_authority():
    with patch.object(
        OsEnforcementService,
        "_find_bpf_source",
        return_value="/tmp/arda_physical_lsm.c",
    ), patch(
        "os.path.exists",
        return_value=True,
    ):
        service = OsEnforcementService.__new__(OsEnforcementService)

        service.CANONICAL_PIN_ROOT = "/sys/fs/bpf/arda"
        service.is_authoritative = False
        service.attach_verified = False
        service.is_simulation = False
        service.arm_mode = "unarmed"
        service.pin_path = None

        service._attach_read_only_status()

        assert service.is_authoritative is False
        assert service.attach_verified is False
