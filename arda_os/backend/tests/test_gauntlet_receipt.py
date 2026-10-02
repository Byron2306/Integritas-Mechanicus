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
