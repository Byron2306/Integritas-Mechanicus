from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_enroll_requires_verified_chain_and_spki():
    text = (ROOT / "installer" / "arda-enroll").read_text()
    assert 'cert.get("source") == "tpm_nv"' not in text
    assert 'cert.get("chain_verified") is True' in text
    assert 'cert.get("spki_match") is True' in text

def test_attest_requires_verified_chain_and_spki():
    text = (ROOT / "installer" / "arda-attest").read_text()
    assert 'cert.get("source") == "tpm_nv"' not in text
    assert 'cert.get("chain_verified") is True' in text
    assert 'cert.get("spki_match") is True' in text
