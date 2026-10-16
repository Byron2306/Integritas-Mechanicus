#!/usr/bin/env python3
"""
ARDA PCR baseline generator.

This is a new thin front end implementing the documented
arda.phase4.pcr_baseline.v1 contract.

It is not claimed to be the unrecovered historical implementation.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "arda.phase4.pcr_baseline.v1"


class BaselineError(RuntimeError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise BaselineError(f"cannot read evidence bundle {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise BaselineError("evidence bundle must be a JSON object")

    return payload


def _normalize_pcrs(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise BaselineError("tpm_pcr_quote.pcr_values must be an object")

    result: dict[str, str] = {}

    for key, digest in value.items():
        pcr = str(key).strip()
        digest_text = str(digest).strip().lower()

        if pcr not in {"0", "1", "7", "11"}:
            continue

        if digest_text.startswith("0x"):
            digest_text = digest_text[2:]

        if len(digest_text) != 64:
            raise BaselineError(f"PCR {pcr} is not a SHA-256 digest")

        try:
            int(digest_text, 16)
        except ValueError as exc:
            raise BaselineError(f"PCR {pcr} is not hexadecimal") from exc

        result[pcr] = digest_text

    required = {"0", "1", "7", "11"}
    missing = sorted(required - result.keys())

    if missing:
        raise BaselineError(
            "required PCRs missing from evidence bundle: "
            + ",".join(missing)
        )

    return result


def _manufacturer_rooted(identity: dict[str, Any]) -> bool:
    cert = identity.get("ek_certificate") or {}

    return all(
        (
            identity.get("ek_certificate_present") is True,
            identity.get("ak_certified_by_ek") is True,
            cert.get("spki_match") is True,
            cert.get("chain_verified") is True,
        )
    )


def build_baseline(
    evidence_bundle_path: Path,
    baseline_name: str,
) -> dict[str, Any]:
    bundle = _load_json(evidence_bundle_path)

    quote = bundle.get("tpm_pcr_quote") or {}
    identity = bundle.get("tpm_identity") or {}
    binding = bundle.get("software_state_binding") or {}

    if not isinstance(quote, dict):
        raise BaselineError("tpm_pcr_quote missing or invalid")

    if not isinstance(identity, dict):
        raise BaselineError("tpm_identity missing or invalid")

    if not isinstance(binding, dict):
        raise BaselineError("software_state_binding missing or invalid")

    pcrs = _normalize_pcrs(quote.get("pcr_values"))

    selection = str(
        quote.get("pcr_selection") or "sha256:0,1,7,11"
    ).strip()

    manifest_id = binding.get("manifest_id")
    generation = binding.get("generation")
    policy_generation = binding.get("policy_generation")

    if not manifest_id:
        raise BaselineError(
            "software_state_binding.manifest_id is required"
        )

    if generation is None:
        raise BaselineError(
            "software_state_binding.generation is required"
        )

    if not policy_generation:
        raise BaselineError(
            "software_state_binding.policy_generation is required"
        )

    if binding.get("bound") is not True:
        raise BaselineError(
            "software_state_binding is not bound"
        )

    manufacturer_rooted = _manufacturer_rooted(identity)

    if not manufacturer_rooted:
        raise BaselineError(
            "manufacturer-rooted TPM identity is not verified"
        )

    return {
        "approved_boot": {
            "generation": generation,
            "identity_chain_mode": identity.get(
                "identity_chain_mode"
            ),
            "manifest_id": manifest_id,
            "manufacturer": identity.get("manufacturer"),
            "manufacturer_rooted": True,
            "policy_generation": policy_generation,
        },
        "baseline_name": baseline_name,
        "boot_state": bundle.get("boot_state"),
        "chain_hash": bundle.get("chain_hash"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mirror_id": bundle.get("mirror_id"),
        "node_id": binding.get("node_id"),
        "pcr_selection": selection,
        "pcrs": pcrs,
        "schema_version": SCHEMA_VERSION,
        "source_evidence_bundle": str(evidence_bundle_path),
    }


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=str(path.parent),
        text=True,
    )

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(tmp_name, path)

    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate an ARDA approved PCR baseline"
    )
    parser.add_argument(
        "--evidence-bundle",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--baseline-name",
        required=True,
    )

    args = parser.parse_args()

    try:
        baseline = build_baseline(
            args.evidence_bundle,
            args.baseline_name,
        )
        _atomic_write_json(args.output, baseline)

    except BaselineError as exc:
        print(f"REFUSE: {exc}")
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "schema_version": baseline["schema_version"],
                "baseline_name": baseline["baseline_name"],
                "output": str(args.output),
                "pcr_selection": baseline["pcr_selection"],
                "pcrs": sorted(baseline["pcrs"]),
                "generation": baseline["approved_boot"]["generation"],
                "manifest_id": baseline["approved_boot"]["manifest_id"],
                "manufacturer_rooted": baseline["approved_boot"][
                    "manufacturer_rooted"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
