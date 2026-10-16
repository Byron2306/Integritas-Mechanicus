from pathlib import Path
import importlib.util
import subprocess


ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "arda_os" / "bin" / "arda_build_measured_manifest.py"


def load_builder():
    spec = importlib.util.spec_from_file_location("arda_manifest_builder", BUILDER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_ed25519_sign_and_verify_large_manifest_payload(tmp_path):
    builder = load_builder()

    private_key = tmp_path / "key.pem"
    public_key = tmp_path / "key.pub.pem"

    subprocess.run(
        [
            "/usr/bin/openssl",
            "genpkey",
            "-algorithm",
            "ED25519",
            "-out",
            str(private_key),
        ],
        check=True,
    )

    subprocess.run(
        [
            "/usr/bin/openssl",
            "pkey",
            "-in",
            str(private_key),
            "-pubout",
            "-out",
            str(public_key),
        ],
        check=True,
    )

    # Deliberately larger than a tiny stdin-sized test message.
    payload = b'{"arda":"' + (b"x" * 131072) + b'"}'

    signature = builder.sign_manifest(private_key, payload)

    builder.verify_signature(
        public_key,
        payload,
        signature,
    )
