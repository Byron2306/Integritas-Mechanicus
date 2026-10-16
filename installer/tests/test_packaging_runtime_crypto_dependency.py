from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUILD = (ROOT / "packaging/build-arda-valinor-deb.sh").read_text()


def test_verifier_signature_runtime_dependency_is_packaged():
    assert "python3-cryptography" in BUILD
