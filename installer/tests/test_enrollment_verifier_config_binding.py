from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ENROLL = ROOT / "installer" / "arda-enroll"


def source() -> str:
    return ENROLL.read_text()


def verifier_section() -> str:
    src = source()
    start = src.index('ATT_HOST_ENV=')
    end = src.index('step "70 HARDWARE-ROOTED OS GRADE"')
    return src[start:end]


def test_enrollment_reads_persisted_verifier_identity():
    src = verifier_section()

    assert "ARDA_ATTESTED_HOST_ENV" in src
    assert "attested_host_value()" in src

    assert (
        'CONFIG_VERIFIER_PUBLIC_KEY="$('
        'attested_host_value ARDA_VERIFIER_PUBLIC_KEY)"'
    ) in src

    assert (
        'CONFIG_VERIFIER_KEY_ID="$('
        'attested_host_value ARDA_VERIFIER_KEY_ID)"'
    ) in src


def test_enrollment_prefers_operator_env_then_persisted_config_then_default():
    src = verifier_section()

    assert "ARDA_VERIFIER_PUBLIC_KEY:-" in src
    assert "CONFIG_VERIFIER_PUBLIC_KEY:-/etc/arda/verifier/verifier-key.pub.pem" in src

    assert "ARDA_VERIFIER_KEY_ID:-" in src
    assert "CONFIG_VERIFIER_KEY_ID:-arda-phase4-verifier" in src


def test_enrollment_does_not_directly_default_verifier_identity_before_config():
    src = verifier_section()

    assert (
        'VERIFIER_KEY_ID="${ARDA_VERIFIER_KEY_ID:-arda-phase4-verifier}"'
        not in src
    )
    assert (
        'VERIFIER_PUBLIC_KEY="${ARDA_VERIFIER_PUBLIC_KEY:-'
        '/etc/arda/verifier/verifier-key.pub.pem}"'
        not in src
    )
