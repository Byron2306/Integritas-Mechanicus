import pytest

from backend.services import quantum_security as qs


def test_native_pqc_refuses_simulation(monkeypatch):
    monkeypatch.setattr(qs.quantum_security, "mode", "simulation")

    with pytest.raises(RuntimeError, match="NATIVE_PQC_REQUIRED"):
        qs.require_native_pqc()


def test_native_pqc_accepts_real_provider(monkeypatch):
    monkeypatch.setattr(qs.quantum_security, "mode", "liboqs")
    assert qs.require_native_pqc() == "liboqs"

    monkeypatch.setattr(qs.quantum_security, "mode", "pqcrypto")
    assert qs.require_native_pqc() == "pqcrypto"


def test_native_pqc_self_test_refuses_simulation(monkeypatch):
    monkeypatch.setattr(qs.quantum_security, "mode", "simulation")

    with pytest.raises(RuntimeError, match="NATIVE_PQC_REQUIRED"):
        qs.native_pqc_self_test()


def test_native_pqc_self_test_requires_ml_dsa_65(monkeypatch):
    monkeypatch.setattr(qs.quantum_security, "mode", "liboqs")

    class FakeOQS:
        @staticmethod
        def get_enabled_sig_mechanisms():
            return []

        @staticmethod
        def get_enabled_kem_mechanisms():
            return ["ML-KEM-768"]

    monkeypatch.setattr(qs, "oqs", FakeOQS)

    with pytest.raises(RuntimeError, match="ML-DSA-65"):
        qs.native_pqc_self_test()

from backend.services.gauntlet_receipt import (
    build_canonical_receipt,
    seal_receipt,
    verify_sealed_receipt,
)
from backend.services.witnessed_authority_gauntlet import GauntletRunContext


def test_canonical_receipt_is_deterministic():
    ctx = GauntletRunContext(
        run_id="arda-test-001",
        started_at="2026-10-02T00:00:00+00:00",
        hostname="valinor",
    )

    a = build_canonical_receipt(ctx)
    b = build_canonical_receipt(ctx)

    assert a == b
    assert b'"run_id":"arda-test-001"' in a


def test_native_sealed_receipt_verifies():
    ctx = GauntletRunContext(
        run_id="arda-test-002",
        started_at="2026-10-02T00:00:00+00:00",
        hostname="valinor",
    )

    sealed = seal_receipt(ctx, "aule-gauntlet-test")

    assert sealed.provider == "liboqs"
    assert sealed.algorithm == "ML-DSA-65"
    assert verify_sealed_receipt(sealed) is True


def test_tampered_receipt_fails_verification():
    ctx = GauntletRunContext(
        run_id="arda-test-003",
        started_at="2026-10-02T00:00:00+00:00",
        hostname="valinor",
    )

    sealed = seal_receipt(ctx, "aule-gauntlet-tamper")
    sealed.payload = sealed.payload + b"tampered"

    assert verify_sealed_receipt(sealed) is False
