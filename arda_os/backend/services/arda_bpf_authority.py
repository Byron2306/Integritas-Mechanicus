"""Fail-closed, read-only evidence for Arda's BPF LSM attachment."""

import json
import os
import subprocess

BPFTOOL = "/usr/sbin/bpftool"
PROGRAM = "arda_sovereign_ignition"

PINS = (
    "harmony_map",
    "state_map",
    "deny_count",
    "policy_state_map",
    "lockdown_map",
    "last_deny_event_map",
    "verity_identity_map",
    "active_generation_map",
    "measured_exec_map",
)


# Exact map references observed in the audited BPF program.
# verity_identity_map is pinned but not referenced by this program.
PROGRAM_MAP_PINS = frozenset(
    name for name in PINS if name != "verity_identity_map"
)


def _read_json(*args):
    result = subprocess.run(
        [BPFTOOL, "-j", *args],
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )
    return json.loads(result.stdout)


def verify_attachment(pin_root="/sys/fs/bpf/arda"):
    evidence = {
        "verified": False,
        "reason": "unverified",
        "program_id": None,
        "program_tag": None,
        "link_id": None,
        "map_ids": {},
    }

    try:
        programs = _read_json("prog", "show")
        links = _read_json("link", "show")

        pinned = {}
        for name in PINS:
            path = os.path.join(pin_root, name)
            data = _read_json("map", "show", "pinned", path)
            pinned[name] = int(data["id"])

        evidence["map_ids"] = pinned

        for program in programs:
            if program.get("type") != "lsm":
                continue
            if program.get("name") != PROGRAM:
                continue

            program_id = program.get("id")
            program_tag = program.get("tag")
            associated = set(program.get("map_ids", []))

            expected_map_ids = {
                pinned[name] for name in PROGRAM_MAP_PINS
            }

            # A partial map match cannot establish program identity.
            # Reject missing, additional, or unrelated map associations.
            if len(expected_map_ids) != len(PROGRAM_MAP_PINS):
                continue
            if associated != expected_map_ids:
                continue

            for link in links:
                if (
                    link.get("prog_id") == program_id
                    and link.get("prog_type") == "lsm"
                    and link.get("attach_type") == "lsm_mac"
                ):
                    evidence.update(
                        verified=True,
                        reason="kernel_link_and_map_identity_verified",
                        program_id=program_id,
                        program_tag=program_tag,
                        link_id=link.get("id"),
                    )
                    return evidence

        evidence["reason"] = "no_matching_live_arda_attachment"
        return evidence

    except (
        OSError,
        subprocess.SubprocessError,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        evidence["reason"] = f"kernel_evidence_unavailable:{type(error).__name__}"
        return evidence
