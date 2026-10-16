from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "arda_os/backend/services/phase4_live_attestation.py"


def test_sovereign_bundle_preserves_manufacturer_ek_proof():
    src = SRC.read_text()

    required = (
        '"ek_certificate": {',
        '"present": tpm_identity.get("ek_certificate", {}).get("present", False)',
        '"source": tpm_identity.get("ek_certificate", {}).get("source")',
        '"certificate_sha256": tpm_identity.get("ek_certificate", {}).get("certificate_sha256")',
        '"tpm_ek_spki_sha256": tpm_identity.get("ek_certificate", {}).get("tpm_ek_spki_sha256")',
        '"certificate_spki_sha256": tpm_identity.get("ek_certificate", {}).get("certificate_spki_sha256")',
        '"spki_match": tpm_identity.get("ek_certificate", {}).get("spki_match", False)',
        '"chain_verified": tpm_identity.get("ek_certificate", {}).get("chain_verified", False)',
    )

    for needle in required:
        assert needle in src, needle


def test_manufacturer_rooted_proof_stays_fail_closed():
    src = SRC.read_text()

    assert '"spki_match": False' in src
    assert '"chain_verified": False' in src
