#!/usr/bin/env python3

import argparse
import ctypes
import json
import os
import struct
from pathlib import Path

import backend.services.os_enforcement_service as oes
from backend.services.os_enforcement_service import OsEnforcementService
from backend.services.proof_file_measurement import open_measured


DEFAULT_PLAN = Path("/etc/arda/policy/active_projection_plan.json")
DEFAULT_READY = Path("/run/arda/ring0-ready")
DEFAULT_RECEIPT = Path("/run/arda/ring0-restore.json")


class _FileHandle(ctypes.Structure):
    _fields_ = [
        ("handle_bytes", ctypes.c_uint),
        ("handle_type", ctypes.c_int),
        ("f_handle", ctypes.c_ubyte * 128),
    ]


AT_FDCWD = -100


def resolve_current_cgroup_kernel_id() -> int | None:
    try:
        lines = [
            line.strip()
            for line in Path("/proc/self/cgroup").read_text().splitlines()
            if line.strip()
        ]
    except Exception:
        return None

    cgroup_path = lines[-1].split(":", 2)[-1] if lines else "/"
    relative = cgroup_path.lstrip("/")
    target = (
        os.path.join("/sys/fs/cgroup", relative)
        if relative
        else "/sys/fs/cgroup"
    )

    libc = ctypes.CDLL(None, use_errno=True)
    handle = _FileHandle()
    handle.handle_bytes = 128
    mount_id = ctypes.c_int()

    rc = libc.name_to_handle_at(
        ctypes.c_int(AT_FDCWD),
        ctypes.c_char_p(target.encode()),
        ctypes.byref(handle),
        ctypes.byref(mount_id),
        ctypes.c_int(0),
    )

    if rc == 0 and handle.handle_bytes >= 8:
        return int.from_bytes(bytes(handle.f_handle[:8]), "little")

    try:
        return os.stat(target).st_ino
    except OSError:
        return None


def parse_loader_spec(loader_spec: str) -> tuple[int, str]:
    try:
        algorithm_text, digest = loader_spec.split(":", 1)
        algorithm = int(algorithm_text)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"invalid_loader_digest_spec:{loader_spec}"
        ) from exc

    digest = digest.lower()

    if algorithm not in (1, 2):
        raise RuntimeError(
            f"unsupported_fsverity_algorithm:{algorithm}"
        )

    expected_length = 64 if algorithm == 1 else 128
    if len(digest) != expected_length:
        raise RuntimeError(
            f"invalid_fsverity_digest_length:{loader_spec}"
        )

    try:
        bytes.fromhex(digest)
    except ValueError as exc:
        raise RuntimeError(
            f"invalid_fsverity_digest_hex:{loader_spec}"
        ) from exc

    return algorithm, digest


def stage_held_measured_exec(
    service: OsEnforcementService,
    *,
    cgroup_kernel_id: int,
    generation: int,
    measured,
) -> dict:
    pin_path = os.path.join(
        service.CANONICAL_PIN_ROOT,
        service.PHASE3_REQUIRED_MAPS[
            "arda_measured_exec_map"
        ]["pin_name"],
    )

    kernel_dev = service._kernel_device_value(  # noqa: SLF001
        measured.device
    )

    key_bytes = struct.pack(
        "<QQQI4x",
        cgroup_kernel_id,
        generation,
        measured.inode,
        kernel_dev,
    )

    fd = service._open_pinned_map_fd(pin_path)  # noqa: SLF001
    try:
        key_buf = (ctypes.c_uint8 * len(key_bytes))(*key_bytes)
        value_buf = (ctypes.c_uint8 * 4)(*struct.pack("<I", 1))
        attr = (ctypes.c_uint8 * oes._MAP_ELEM_SIZE)()

        struct.pack_into("<I", attr, 0, fd)

        key_addr = ctypes.addressof(key_buf)
        value_addr = ctypes.addressof(value_buf)

        if ctypes.sizeof(ctypes.c_void_p) == 8:
            struct.pack_into("<Q", attr, 8, key_addr)
            struct.pack_into("<Q", attr, 16, value_addr)
        else:
            struct.pack_into("<I", attr, 8, key_addr)
            struct.pack_into("<I", attr, 12, value_addr)

        rc = oes._bpf(
            oes._BPF_MAP_UPDATE_ELEM,
            attr,
            oes._MAP_ELEM_SIZE,
        )

        if rc != 0:
            errno_value = ctypes.get_errno()
            raise OSError(
                errno_value,
                f"failed to stage held measured executable "
                f"{measured.path}",
            )

        return {
            "cgroup_kernel_id": cgroup_kernel_id,
            "generation": generation,
            "path": measured.path,
            "inode": measured.inode,
            "dev": kernel_dev,
            "raw_dev": measured.device,
            "fs_verity_algorithm_id": measured.algorithm,
            "fs_verity_digest": measured.digest,
        }
    finally:
        os.close(fd)


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


def restore(
    *,
    ready_file: Path,
    receipt_file: Path,
    projection_plan: Path,
) -> dict:
    ready_file.unlink(missing_ok=True)

    service = OsEnforcementService(arm=False)

    active_records = service._measured_generation_store.list_records(  # noqa: SLF001
        ["active"]
    )
    if not active_records:
        raise RuntimeError("active_record_missing")

    active = max(
        active_records,
        key=lambda record: int(record.get("generation") or 0),
    )

    payload = active.get("payload") or {}
    generation = int(active.get("generation") or 0)

    if generation <= 0:
        raise RuntimeError("active_record_missing_generation")

    if payload.get("enforcement_mode") != "fsverity_strict":
        raise RuntimeError("active_record_not_fsverity_strict")

    policy_generation = str(payload.get("policy_generation") or "")
    if not policy_generation:
        raise RuntimeError("active_record_missing_policy_generation")

    if not projection_plan.is_file():
        raise RuntimeError("projection_plan_missing")

    plan = json.loads(projection_plan.read_text())
    constitutional = (
        (plan.get("targets") or {}).get("constitutional_state") or {}
    )

    plan_generation = str(
        constitutional.get("policy_generation") or ""
    )
    redline_rule_count = int(
        constitutional.get("redline_rule_count") or 0
    )

    if plan_generation != policy_generation:
        raise RuntimeError("policy_generation_mismatch")

    if redline_rule_count <= 0:
        raise RuntimeError("constitutional_redlines_missing")

    current_cgroup_kernel_id = resolve_current_cgroup_kernel_id()
    if not current_cgroup_kernel_id or current_cgroup_kernel_id <= 0:
        raise RuntimeError("current_cgroup_kernel_id_unavailable")

    checked_paths = list(payload.get("checked_paths") or [])
    loader_digest_specs = list(
        payload.get("loader_digest_specs") or []
    )

    if not checked_paths:
        raise RuntimeError("active_record_checked_paths_missing")

    if not loader_digest_specs:
        raise RuntimeError("active_record_loader_digests_missing")

    if len(checked_paths) != len(loader_digest_specs):
        raise RuntimeError(
            "active_record_content_binding_cardinality_mismatch"
        )

    measured_exec = []
    verity_entries = []

    for path, loader_spec in zip(
        checked_paths,
        loader_digest_specs,
        strict=True,
    ):
        expected_algorithm, expected_digest = parse_loader_spec(
            loader_spec
        )

        try:
            measured = open_measured(path)
        except Exception as exc:
            raise RuntimeError(
                f"measured_exec_fsverity_unavailable:{path}"
            ) from exc

        try:
            actual_identity = (
                int(measured.algorithm),
                str(measured.digest).lower(),
            )
            expected_identity = (
                expected_algorithm,
                expected_digest,
            )

            if actual_identity != expected_identity:
                raise RuntimeError(
                    f"measured_exec_fsverity_mismatch:{path}"
                )

            # Revalidate the held descriptor immediately before map
            # projection. Runtime identity may be rebound after reboot;
            # executable content identity may not.
            measured.revalidate()

            measured_exec.append(
                stage_held_measured_exec(
                    service,
                    cgroup_kernel_id=current_cgroup_kernel_id,
                    generation=generation,
                    measured=measured,
                )
            )

            verity_entries.append(
                service._stage_pinned_verity_identity(  # noqa: SLF001
                    cgroup_kernel_id=current_cgroup_kernel_id,
                    generation=generation,
                    loader_spec=loader_spec,
                )
            )

            # Catch pathname replacement during projection before the
            # attachment readiness gate can ever be released.
            measured.revalidate()
        finally:
            measured.close()

    policy_state = service._project_policy_state(  # noqa: SLF001
        policy_generation,
        redline_rule_count,
    )

    active_pointer = service._project_active_generation(  # noqa: SLF001
        cgroup_kernel_id=current_cgroup_kernel_id,
        generation=generation,
    )

    # Boot restoration is deliberately scoped. Global fsverity_strict is
    # not armed before the remaining boot/service cgroups are rebound.
    applied_mode = service._project_state_mode(  # noqa: SLF001
        service.ENFORCEMENT_MODE_SCOPED_STRICT
    )

    state_value = service._read_pinned_u32_scalar(  # noqa: SLF001
        service.REQUIRED_MAPS["arda_state_map"]["pin_name"]
    )
    restored_policy = service._read_policy_state()  # noqa: SLF001
    restored_generation = read_active_generation(
        service,
        current_cgroup_kernel_id,
    )

    if applied_mode != service.ENFORCEMENT_MODE_SCOPED_STRICT:
        raise RuntimeError("boot_mode_restore_failed")

    if state_value != 3:
        raise RuntimeError("boot_mode_readback_mismatch")

    if restored_generation != generation:
        raise RuntimeError("active_generation_readback_mismatch")

    if not restored_policy:
        raise RuntimeError("policy_state_readback_missing")

    if (
        int(restored_policy.get("redline_rule_count") or 0)
        != redline_rule_count
    ):
        raise RuntimeError("policy_redline_readback_mismatch")

    if (
        int(restored_policy.get("projection_flags") or 0) & 1
    ) != 1:
        raise RuntimeError("policy_presence_flag_missing")

    receipt = {
        "ok": True,
        "manifest_id": active.get("manifest_id"),
        "generation": generation,
        "policy_generation": policy_generation,
        "redline_rule_count": redline_rule_count,
        "enforcement_mode": applied_mode,
        "source_cgroup_kernel_id": payload.get(
            "cgroup_kernel_id"
        ),
        "current_cgroup_kernel_id": current_cgroup_kernel_id,
        "active_generation": active_pointer,
        "policy_state": restored_policy,
        "measured_exec_count": len(measured_exec),
        "verity_identity_count": len(verity_entries),
    }

    receipt_file.parent.mkdir(parents=True, exist_ok=True)
    receipt_file.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    )

    # LAST operation. The loader may attach immediately after this exists.
    ready_file.parent.mkdir(parents=True, exist_ok=True)
    ready_file.touch()

    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ready-file",
        default=str(DEFAULT_READY),
    )
    parser.add_argument(
        "--receipt",
        default=str(DEFAULT_RECEIPT),
    )
    parser.add_argument(
        "--projection-plan",
        default=str(DEFAULT_PLAN),
    )
    args = parser.parse_args()

    try:
        result = restore(
            ready_file=Path(args.ready_file),
            receipt_file=Path(args.receipt),
            projection_plan=Path(args.projection_plan),
        )
    except Exception as exc:
        print(json.dumps({
            "ok": False,
            "reason": str(exc),
        }, indent=2, sort_keys=True))
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
