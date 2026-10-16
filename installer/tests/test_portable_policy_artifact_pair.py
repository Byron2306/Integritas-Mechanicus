import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "installer/policy/constitutional-policy.json"
BUNDLE = ROOT / "installer/policy/active_bundle.json"
PLAN = ROOT / "installer/policy/active_projection_plan.json"


def digest(value):
    return "sha256:" + hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def test_portable_policy_artifacts_are_bound():
    policy = json.loads(POLICY.read_text())
    bundle = json.loads(BUNDLE.read_text())
    plan = json.loads(PLAN.read_text())

    source_digest = digest(policy)
    bundle_digest = digest(bundle)

    assert bundle["source_policy_digest"] == source_digest
    assert plan["source_policy_digest"] == source_digest
    assert plan["bundle_digest"] == bundle_digest

    assert policy["policy_id"] == bundle["policy_id"] == plan["policy_id"]
    assert policy["version"] == bundle["policy_version"] == plan["policy_version"]


def test_portable_policy_preserves_seven_reconstructed_redlines():
    bundle = json.loads(BUNDLE.read_text())
    plan = json.loads(PLAN.read_text())

    bundle_redlines = bundle["projections"]["redline_rules"]
    plan_redlines = plan["targets"]["redline_rules"]

    assert len(bundle_redlines) == 7
    assert len(plan_redlines) == 7
    assert bundle_redlines == plan_redlines


def test_portable_bundle_does_not_claim_hmac_authority():
    bundle = json.loads(BUNDLE.read_text())

    assert "signature" not in bundle
    assert bundle["integrity"]["mode"] == "package-measured"
    assert bundle["integrity"]["authenticated_signature"] is False


def test_all_policy_artifacts_are_measured():
    src = (
        ROOT
        / "arda_os/backend/services/measured_policy_profiles.py"
    ).read_text()

    assert '"/etc/arda/policy/constitutional-policy.json"' in src
    assert '"/etc/arda/policy/active_bundle.json"' in src
    assert '"/etc/arda/policy/active_projection_plan.json"' in src
