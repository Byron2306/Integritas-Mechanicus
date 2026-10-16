from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_pluton_trust_material_is_present():
    trust = ROOT / "installer" / "trust" / "microsoft-pluton"

    required = {
        "pluton-factory-device.pem",
        "microsoft-pluton-policy-ca-a.pem",
        "microsoft-pluton-root-ca-2021.pem",
    }

    assert required <= {p.name for p in trust.iterdir() if p.is_file()}


def test_live_attestation_has_fail_closed_pluton_adapter():
    text = (
        ROOT
        / "arda_os"
        / "backend"
        / "services"
        / "phase4_live_attestation.py"
    ).read_text()

    assert "_verify_microsoft_pluton_nv_ek_certificate" in text
    assert '"microsoft_pluton_tpm_nv"' in text
    assert '"pluton_ek_certificate_spki_mismatch"' in text
    assert '"pluton_trust_anchor_missing"' in text
    assert '"pluton_ek_chain_verification_failed"' in text
    assert '"0x01c00100"' in text
    assert '"spki_match": True' in text
    assert '"chain_verified": True' in text


def test_package_installs_pluton_trust_material():
    text = (ROOT / "packaging" / "build-arda-valinor-deb.sh").read_text()

    assert "/etc/arda/trust/microsoft-pluton" in text
    assert "pluton-factory-device.pem" in text
    assert "microsoft-pluton-policy-ca-a.pem" in text
    assert "microsoft-pluton-root-ca-2021.pem" in text
