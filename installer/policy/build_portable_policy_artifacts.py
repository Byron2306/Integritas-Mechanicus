#!/usr/bin/env python3
"""
Build the portable ARDA policy artifact pair.

The portable bundle deliberately does not claim an authenticated policy
signature. Its integrity is supplied by package provenance, the measured
manifest, fs-verity, and the bundle_digest binding carried by the projection
plan.

This is current product machinery, not recovered July source.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARDA_OS = ROOT / "arda_os"

if str(ARDA_OS) not in sys.path:
    sys.path.insert(0, str(ARDA_OS))

from backend.services.policy_compiler import (  # noqa: E402
    compile_policy_bundle,
    compile_projection_plan,
)


EXECUTABLE_PATHS = [
    "/usr/bin/bash",
    "/usr/bin/cat",
    "/usr/bin/env",
    "/usr/bin/ls",
    "/usr/bin/python3",
    "/usr/bin/sudo",
    "/usr/bin/systemctl",
]


def canonical_digest(value: dict) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return "sha256:" + hashlib.sha256(raw).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--policy",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--plan",
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    policy = json.loads(args.policy.read_text(encoding="utf-8"))

    bundle = compile_policy_bundle(policy)

    # The historical compiler emits an HMAC made with ARDA_POLICY_SECRET.
    # Portable policy authority does not depend on that mechanism.
    bundle.pop("signature", None)
    bundle.pop("compiled_at", None)

    bundle["integrity"] = {
        "mode": "package-measured",
        "authenticated_signature": False,
        "bundle_digest_bound_by_projection_plan": True,
        "note": (
            "Portable artifact integrity is provided by package provenance, "
            "measured identity, fs-verity, and projection-plan digest binding."
        ),
    }

    plan = compile_projection_plan(
        bundle,
        executable_paths=EXECUTABLE_PATHS,
        enforcement_mode="audit",
    )

    source_digest = canonical_digest(policy)

    if bundle.get("source_policy_digest") != source_digest:
        raise RuntimeError("bundle/source policy digest mismatch")

    if plan.get("source_policy_digest") != source_digest:
        raise RuntimeError("plan/source policy digest mismatch")

    expected_bundle_digest = canonical_digest(bundle)

    if plan.get("bundle_digest") != expected_bundle_digest:
        raise RuntimeError("plan/bundle digest mismatch")

    bundle_redlines = (
        bundle.get("projections", {}).get("redline_rules", [])
    )
    plan_redlines = (
        plan.get("targets", {}).get("redline_rules", [])
    )

    if len(bundle_redlines) != 7 or len(plan_redlines) != 7:
        raise RuntimeError(
            "portable policy artifacts require exactly seven reconstructed "
            "constitutional redline records"
        )

    write_json(args.bundle, bundle)
    write_json(args.plan, plan)

    print(
        json.dumps(
            {
                "ok": True,
                "policy_id": bundle["policy_id"],
                "policy_version": bundle["policy_version"],
                "source_policy_digest": source_digest,
                "bundle_digest": expected_bundle_digest,
                "redline_rule_count": len(bundle_redlines),
                "bundle": str(args.bundle),
                "plan": str(args.plan),
                "integrity_mode": bundle["integrity"]["mode"],
                "authenticated_signature": False,
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
