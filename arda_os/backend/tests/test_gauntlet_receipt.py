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
