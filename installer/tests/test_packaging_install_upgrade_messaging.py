from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "packaging" / "build-arda-valinor-deb.sh"


def source() -> str:
    return BUILD.read_text()


def test_upgrade_does_not_claim_host_is_unenrolled():
    src = source()

    assert 'if [ -n "${2:-}" ]; then' in src
    assert "ARDA Valinor upgraded." in src
    assert "The package transaction did not re-enroll this host" in src


def test_fresh_install_retains_enrollment_guidance():
    src = source()

    assert "ARDA Valinor installed." in src
    assert "No hardware enrollment has been performed." in src
    assert "sudo arda-enroll --dry-run" in src


def test_upgrade_points_to_grade_not_automatic_reenrollment():
    src = source()

    assert "sudo arda-grade" in src
    assert (
        "Run arda-enroll only for an intentional measured-generation transition."
        in src
    )
