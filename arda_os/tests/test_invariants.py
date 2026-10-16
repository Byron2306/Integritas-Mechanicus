"""
Arda Trusted Core: Property-Based Invariant Tests
===================================================
Uses Hypothesis to verify the three formal invariants
across thousands of random inputs.

Invariant 1: No grant without policy match
Invariant 2: No envelope without valid signature
Invariant 3: No audit pass without chain-verified receipt
"""

import hashlib
import hmac
import json
import os
import sys
import tempfile

import pytest
from hypothesis import given, settings, assume, HealthCheck
from hypothesis import strategies as st

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.services.policy_engine import (
    generate_policy, load_and_verify_policy, evaluate, _canonical_bytes, _sign
)
from backend.services.attestation_service import (
    create_envelope, verify_envelope, _canonical_body, _pae, DSSE_TYPE_URI
)
from backend.services import ledger


# ============================================================================
# Strategies: random but realistic test data
# ============================================================================

command_st = st.sampled_from(["check_health", "deploy", "delete", "escalate", "reboot"])
principal_st = st.sampled_from(["Magos_Indomitus", "Unknown_Agent", "Rogue_Echo", "Admin"])
lane_st = st.sampled_from(["Shire", "Gondor", "The Void", "Rohan"])
token_st = st.text(min_size=3, max_size=20, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")


# ============================================================================
# INVARIANT 1: No grant without policy match
# ============================================================================

class TestInvariant1_NoGrantWithoutPolicy:
    """Only explicitly allowed (command, principal, lane) triples pass policy."""

    @given(command=command_st, principal=principal_st, lane=lane_st)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_only_allowed_triple_passes(self, command, principal, lane, tmp_path):
        """Policy MUST deny any triple not in the declared rules."""
        policy_path = str(tmp_path / "test_policy.json")
        generate_policy(path=policy_path)

        # The only allowed triple
        allowed = (command == "check_health" and principal == "Magos_Indomitus" and lane == "Shire")

        if allowed:
            result = evaluate.__wrapped__(command, principal, lane) if hasattr(evaluate, '__wrapped__') else None
            # Just verify evaluate doesn't raise for the allowed case
            try:
                from backend.services import policy_engine
                old_path = policy_engine.POLICY_PATH
                policy_engine.POLICY_PATH = policy_path
                result = evaluate(command, principal, lane)
                assert result == "ALLOW"
                policy_engine.POLICY_PATH = old_path
            except Exception:
                policy_engine.POLICY_PATH = old_path
                raise
        else:
            try:
                from backend.services import policy_engine
                old_path = policy_engine.POLICY_PATH
                policy_engine.POLICY_PATH = policy_path
                evaluate(command, principal, lane)
                policy_engine.POLICY_PATH = old_path
                # If we get here without RuntimeError, invariant is broken
                assert False, f"Policy should DENY ({command}, {principal}, {lane})"
            except RuntimeError as e:
                policy_engine.POLICY_PATH = old_path
                assert "DENY" in str(e)

    def test_tampered_policy_rejected(self, tmp_path):
        """A policy with a modified signature MUST be rejected."""
        policy_path = str(tmp_path / "tampered_policy.json")
        generate_policy(path=policy_path)

        # Tamper with the policy
        with open(policy_path, "r") as f:
            policy = json.load(f)
        policy["commands"].append({"name": "evil_cmd", "lanes": ["Shire"], "principals": ["Evil"]})
        with open(policy_path, "w") as f:
            json.dump(policy, f)

        with pytest.raises(RuntimeError, match="INVALID"):
            load_and_verify_policy(path=policy_path)


# ============================================================================
# INVARIANT 2: No envelope without valid signature
# ============================================================================

class TestInvariant2_NoUnsignedEnvelope:
    """Every DSSE envelope must have a verifiable signature."""

    def test_envelope_signature_round_trips(self):
        """A freshly created envelope MUST verify."""
        env = create_envelope(
            command="check_health", principal="Magos_Indomitus",
            token_id="TOK-TEST", lane="Shire",
            policy_id="ARDA-POLICY-V1", policy_version="1.0.0",
            verdict="ALLOW", artifact_digest="abc123",
            policy_verdict="ALLOW",
        )
        assert verify_envelope(env), "Freshly signed envelope must verify"

    def test_tampered_envelope_rejected(self):
        """A tampered envelope MUST fail verification."""
        env = create_envelope(
            command="check_health", principal="Magos_Indomitus",
            token_id="TOK-TEST", lane="Shire",
            policy_id="ARDA-POLICY-V1", policy_version="1.0.0",
            verdict="ALLOW", artifact_digest="abc123",
            policy_verdict="ALLOW",
        )
        # Tamper with the payload
        env["payload"]["verdict"] = "DENY"
        assert not verify_envelope(env), "Tampered envelope must NOT verify"

    def test_denied_request_cannot_be_attested(self):
        """Cannot produce an envelope for a denied request."""
        with pytest.raises(RuntimeError, match="DENY"):
            create_envelope(
                command="check_health", principal="Evil",
                token_id="TOK-TEST", lane="Shire",
                policy_id="ARDA-POLICY-V1", policy_version="1.0.0",
                verdict="DENY", artifact_digest="abc123",
                policy_verdict="DENY",  # This should block envelope creation
            )

    @given(principal=principal_st, command=command_st)
    @settings(max_examples=100, deadline=None)
    def test_random_envelopes_always_verify(self, principal, command):
        """Any honestly-created envelope must verify, regardless of content."""
        env = create_envelope(
            command=command, principal=principal,
            token_id="TOK-FUZZ", lane="Shire",
            policy_id="ARDA-POLICY-V1", policy_version="1.0.0",
            verdict="ALLOW", artifact_digest=hashlib.sha3_256(command.encode()).hexdigest(),
            policy_verdict="ALLOW",
        )
        assert verify_envelope(env)


# ============================================================================
# INVARIANT 3: No audit pass without chain-verified receipt
# ============================================================================

class TestInvariant3_NoAuditWithoutReceipt:
    """Ledger chain must be verifiable and tamper-evident."""

    def test_chain_valid_after_append(self, tmp_path):
        """Appending a signed envelope must produce a valid chain."""
        ledger_path = str(tmp_path / "test_ledger.jsonl")
        old_path = ledger.LEDGER_PATH
        ledger.LEDGER_PATH = ledger_path

        env = create_envelope(
            command="check_health", principal="Magos_Indomitus",
            token_id="TOK-TEST", lane="Shire",
            policy_id="ARDA-POLICY-V1", policy_version="1.0.0",
            verdict="ALLOW", artifact_digest="abc123",
            policy_verdict="ALLOW",
        )
        receipt = ledger.append(env)
        assert len(receipt) == 64, "Receipt must be SHA3-256 hex"
        assert ledger.verify_chain(ledger_path)

        ledger.LEDGER_PATH = old_path

    def test_tampered_ledger_detected(self, tmp_path):
        """Modifying a ledger entry must break the chain."""
        ledger_path = str(tmp_path / "test_ledger.jsonl")
        old_path = ledger.LEDGER_PATH
        ledger.LEDGER_PATH = ledger_path

        env = create_envelope(
            command="check_health", principal="Magos_Indomitus",
            token_id="TOK-TEST", lane="Shire",
            policy_id="ARDA-POLICY-V1", policy_version="1.0.0",
            verdict="ALLOW", artifact_digest="abc123",
            policy_verdict="ALLOW",
        )
        ledger.append(env)

        # Tamper
        with open(ledger_path, "r") as f:
            lines = f.readlines()
        entry = json.loads(lines[0])
        entry["envelope"]["payload"]["verdict"] = "TAMPERED"
        lines[0] = json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n"
        with open(ledger_path, "w") as f:
            f.writelines(lines)

        assert not ledger.verify_chain(ledger_path), "Tampered ledger must fail verification"

        ledger.LEDGER_PATH = old_path

    def test_unsigned_envelope_rejected_by_ledger(self):
        """Ledger must refuse an envelope without a signature field."""
        with pytest.raises(ValueError, match="signed"):
            ledger.append({"payload": "test", "no_signature": True})


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
