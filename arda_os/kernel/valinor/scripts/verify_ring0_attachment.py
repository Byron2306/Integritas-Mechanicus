#!/usr/bin/env python3

import argparse
import ctypes
import json
import os
import struct
import sys
import time
from pathlib import Path

import backend.services.os_enforcement_service as oes
from backend.services.arda_bpf_authority import verify_attachment
from backend.services.os_enforcement_service import OsEnforcementService


ATTEMPTS = 20
DELAY_SECONDS = 0.25
PIN_ROOT = "/sys/fs/bpf/arda"
RESTORE_RECEIPT = Path("/run/arda/ring0-restore.json")


def read_active_generation(
    service: OsEnforcementService,
    cgroup_kernel_id: int,
) -> int | None:
    pin = os.path.join(
        service.CANONICAL_PIN_ROOT,
        service.PHASE3_REQUIRED_MAPS["arda_active_generation_map"]["pin_name"],
    )
    fd = service._open_pinned_map_fd(pin)  # noqa: SLF001

    try:
        key = (ctypes.c_uint8 * 8)(
            *struct.pack("<Q", cgroup_kernel_id)
        )
        value = (ctypes.c_uint8 * 8)()
        attr = (ctypes.c_uint8 * oes._MAP_ELEM_SIZE)()

        struct.pack_into("<I", attr, 0, fd)

        if ctypes.sizeof(ctypes.c_void_p) == 8:
            struct.pack_into("<Q", attr, 8, ctypes.addressof(key))
            struct.pack_into("<Q", attr, 16, ctypes.addressof(value))
        else:
            struct.pack_into("<I", attr, 8, ctypes.addressof(key))
            struct.pack_into("<I", attr, 12, ctypes.addressof(value))

        rc = oes._bpf(
            oes._BPF_MAP_LOOKUP_ELEM,
            attr,
            oes._MAP_ELEM_SIZE,
        )
        if rc != 0:
            return None

        return struct.unpack("<Q", bytes(value))[0]
    finally:
        os.close(fd)


def restored_state_evidence() -> dict:
    if not RESTORE_RECEIPT.is_file():
        return {
            "ok": False,
            "reason": "restore_receipt_missing",
        }

    receipt = json.loads(RESTORE_RECEIPT.read_text())
    if receipt.get("ok") is not True:
        return {
            "ok": False,
            "reason": "restore_receipt_not_ok",
            "receipt": receipt,
        }

    service = OsEnforcementService(arm=False)

    state_value = service._read_pinned_u32_scalar(  # noqa: SLF001
        service.REQUIRED_MAPS["arda_state_map"]["pin_name"]
    )
    policy_state = service._read_policy_state()  # noqa: SLF001

    cgroup_id = int(
        receipt.get("current_cgroup_kernel_id") or 0
    )
    expected_generation = int(
        receipt.get("generation") or 0
    )

    active_generation = (
        read_active_generation(service, cgroup_id)
        if cgroup_id > 0
        else None
    )

    expected_policy = receipt.get("policy_state") or {}

    checks = {
        "scoped_strict_mode": state_value == 3,
        "active_generation_bound":
            active_generation == expected_generation,
        "policy_state_present": bool(policy_state),
        "policy_generation_bound":
            bool(policy_state)
            and int(policy_state.get("generation_hash_prefix") or 0)
            == int(expected_policy.get("generation_hash_prefix") or 0),
        "redline_count_bound":
            bool(policy_state)
            and int(policy_state.get("redline_rule_count") or 0)
            == int(receipt.get("redline_rule_count") or 0),
        "redline_presence_flag":
            bool(policy_state)
            and (
                int(policy_state.get("projection_flags") or 0) & 1
            ) == 1,
    }

    return {
        "ok": all(checks.values()),
        "checks": checks,
        "state_value": state_value,
        "policy_state": policy_state,
        "active_generation": active_generation,
        "receipt": receipt,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-restored-state",
        action="store_true",
    )
    args = parser.parse_args()

    last = None

    for attempt in range(1, ATTEMPTS + 1):
        attachment = verify_attachment(PIN_ROOT)

        restored = (
            restored_state_evidence()
            if args.require_restored_state
            else {"ok": True}
        )

        last = {
            "attachment": attachment,
            "restored_state": restored,
        }

        if (
            attachment.get("verified") is True
            and restored.get("ok") is True
        ):
            print(json.dumps({
                "ok": True,
                "attempt": attempt,
                "evidence": last,
            }, indent=2, sort_keys=True))
            return 0

        if attempt < ATTEMPTS:
            time.sleep(DELAY_SECONDS)

    print(json.dumps({
        "ok": False,
        "attempts": ATTEMPTS,
        "evidence": last,
    }, indent=2, sort_keys=True))

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
