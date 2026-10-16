from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "arda_os/backend/services/measured_policy_profiles.py"
ENROLL = ROOT / "installer/arda-enroll"


def test_critical_profile_measures_installed_enrollment_entrypoints():
    src = PROFILE.read_text()

    for path in (
        "/usr/bin/arda-enroll",
        "/usr/bin/arda-attest",
        "/usr/bin/arda-grade",
    ):
        assert f'"{path}"' in src


def test_post_strict_attestation_uses_installed_entrypoint():
    src = ENROLL.read_text()

    assert '"/usr/bin/arda-attest"' in src
    assert '"$REPO/installer/arda-attest"' not in src


def test_post_strict_grade_uses_installed_entrypoint():
    src = ENROLL.read_text()

    assert '"/usr/bin/arda-grade"' in src
    assert '"$REPO/installer/arda-grade"' not in src
