import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
GENERATOR = ROOT / "arda_os/bin/arda_generate_pcr_baseline.py"


def _module():
    spec = importlib.util.spec_from_file_location(
        "arda_generate_pcr_baseline",
        GENERATOR,
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _bundle():
    return {
        "mirror_id": "ARDA-CORONATION-TEST",
        "boot_state": "LAWFUL_FULL",
        "chain_hash": "a" * 64,
        "tpm_pcr_quote": {
            "pcr_selection": "sha256:0,1,7,11",
            "pcr_values": {
                "0": "0" * 64,
                "1": "1" * 64,
                "7": "7" * 64,
                "11": "b" * 64,
            },
        },
        "tpm_identity": {
            "manufacturer": "Microsoft (MSFT)",
            "identity_chain_mode": "ek-certificate+createak",
            "ek_certificate_present": True,
            "ak_certified_by_ek": True,
            "ek_certificate": {
                "spki_match": True,
                "chain_verified": True,
            },
        },
        "software_state_binding": {
            "bound": True,
            "generation": 5,
            "manifest_id": "measured-test",
            "node_id": "debian",
            "policy_generation": "ARDA-POLICY-V1@1.1.0",
        },
    }


def test_generator_emits_historical_schema(tmp_path):
    mod = _module()

    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(_bundle()))

    result = mod.build_baseline(
        bundle_path,
        "arda-test-known-good",
    )

    assert result["schema_version"] == "arda.phase4.pcr_baseline.v1"
    assert result["baseline_name"] == "arda-test-known-good"
    assert result["pcr_selection"] == "sha256:0,1,7,11"
    assert set(result["pcrs"]) == {"0", "1", "7", "11"}

    approved = result["approved_boot"]

    assert approved["generation"] == 5
    assert approved["manifest_id"] == "measured-test"
    assert approved["manufacturer"] == "Microsoft (MSFT)"
    assert approved["manufacturer_rooted"] is True
    assert approved["policy_generation"] == "ARDA-POLICY-V1@1.1.0"


def test_generator_refuses_unverified_manufacturer_chain(tmp_path):
    mod = _module()

    bundle = _bundle()
    bundle["tpm_identity"]["ek_certificate"]["chain_verified"] = False

    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle))

    with pytest.raises(
        mod.BaselineError,
        match="manufacturer-rooted",
    ):
        mod.build_baseline(bundle_path, "bad")


def test_generator_refuses_missing_required_pcr(tmp_path):
    mod = _module()

    bundle = _bundle()
    del bundle["tpm_pcr_quote"]["pcr_values"]["11"]

    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle))

    with pytest.raises(
        mod.BaselineError,
        match="required PCRs missing",
    ):
        mod.build_baseline(bundle_path, "bad")


def test_generator_refuses_unbound_software_state(tmp_path):
    mod = _module()

    bundle = _bundle()
    bundle["software_state_binding"]["bound"] = False

    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle))

    with pytest.raises(
        mod.BaselineError,
        match="not bound",
    ):
        mod.build_baseline(bundle_path, "bad")
