from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "arda_os/backend/services/measured_policy_profiles.py"
ENROLL = ROOT / "installer/arda-enroll"
ATTEST = ROOT / "installer/arda-attest"
GRADE = ROOT / "installer/arda-grade"


def test_post_strict_shell_utilities_are_explicitly_measured():
    src = PROFILE.read_text()

    required = (
        "/usr/bin/mkdir",
        "/usr/bin/sed",
        "/usr/bin/tail",
        "/usr/bin/cat",
        "/usr/bin/hostname",
        "/usr/bin/tee",
        "/usr/bin/install",
        "/usr/bin/mktemp",
        "/usr/bin/rm",
    )

    for path in required:
        assert f'"{path}"' in src, path


def test_installed_arda_lifecycle_entrypoints_are_measured():
    src = PROFILE.read_text()

    for path in (
        "/usr/bin/arda-enroll",
        "/usr/bin/arda-attest",
        "/usr/bin/arda-grade",
    ):
        assert f'"{path}"' in src, path


def test_post_strict_pcr_baseline_builder_is_measured():
    src = PROFILE.read_text()
    assert '"arda_os/bin/arda_generate_pcr_baseline.py"' in src


def test_enrollment_uses_installed_attest_and_grade_entrypoints():
    src = ENROLL.read_text()

    assert '"/usr/bin/arda-attest"' in src
    assert '"/usr/bin/arda-grade"' in src
    assert '"$REPO/installer/arda-attest"' not in src
    assert '"$REPO/installer/arda-grade"' not in src


def test_helper_scripts_retain_expected_runtime_dependencies():
    attest = ATTEST.read_text()
    grade = GRADE.read_text()

    assert 'mkdir -p "$OUT"' in attest
    assert 'sed -n ' in grade
    assert '| tail -n 1' in grade

def test_post_strict_attestation_tpm_tools_are_explicitly_measured():
    src = PROFILE.read_text()

    for path in (
        "/usr/bin/tpm2_nvread",
        "/usr/bin/tpm2_getekcertificate",
        "/usr/bin/tpm2_checkquote",
        "/usr/bin/tpm2_readpublic",
        "/usr/bin/tpm2_pcrextend",
        "/usr/bin/tpm2_loadexternal",
        "/usr/bin/tpm2_verifysignature",
    ):
        assert f'"{path}"' in src, path



def test_pcr_baseline_generator_exists_as_tracked_product_source():
    generator = ROOT / "arda_os/bin/arda_generate_pcr_baseline.py"

    assert generator.is_file()
    assert "arda.phase4.pcr_baseline.v1" in generator.read_text()
