import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENROLL = ROOT / "installer" / "arda-enroll"


def test_arda_enroll_is_valid_bash():
    result = subprocess.run(
        ["/usr/bin/bash", "-n", str(ENROLL)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_verifier_fallback_expansions_are_valid_single_parameter_expansions():
    src = ENROLL.read_text()

    assert (
        'VERIFIER_PUBLIC_KEY="${ARDA_VERIFIER_PUBLIC_KEY:-'
        '${CONFIG_VERIFIER_PUBLIC_KEY:-/etc/arda/verifier/verifier-key.pub.pem}}"'
        in src
    )

    assert (
        'VERIFIER_KEY_ID="${ARDA_VERIFIER_KEY_ID:-'
        '${CONFIG_VERIFIER_KEY_ID:-arda-phase4-verifier}}"'
        in src
    )
