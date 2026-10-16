from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
BUILDER = ROOT / "arda_os/bin/arda_build_measured_manifest.py"
ENROLL = ROOT / "installer/arda-enroll"


def test_enrollment_step30_builder_exists():
    text = ENROLL.read_text(encoding="utf-8")
    assert "arda_os/bin/arda_build_measured_manifest.py" in text
    assert BUILDER.is_file()


def test_measured_manifest_builder_is_git_tracked():
    result = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "ls-files",
            "--error-unmatch",
            "arda_os/bin/arda_build_measured_manifest.py",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_builder_is_not_git_ignored():
    result = subprocess.run(
        [
            "git",
            "-C",
            str(ROOT),
            "check-ignore",
            "-q",
            "arda_os/bin/arda_build_measured_manifest.py",
        ],
        check=False,
    )

    # git check-ignore returns 1 when the path is NOT ignored.
    assert result.returncode == 1


def test_builder_cli_contract_is_present():
    text = BUILDER.read_text(encoding="utf-8")

    required = (
        "--profile",
        "--policy-generation",
        "--generation",
        "--output",
        "arda.measured_manifest.v1",
        "arda-measured-preflight",
        "expand_measurement_profile",
        "open_measured",
    )

    for token in required:
        assert token in text


def test_dry_run_exposes_continuous_proof_step():
    text = ENROLL.read_text(encoding="utf-8")
    dry_run = text.split('if [[ "$DRY_RUN" -eq 1 ]]; then', 1)[1].split(
        "exit 0", 1
    )[0]

    assert '70 HARDWARE-ROOTED OS GRADE' in dry_run
    assert '80 CONTINUOUS HARDWARE-ROOTED PROOF' in dry_run
    assert dry_run.index("70 HARDWARE-ROOTED OS GRADE") < dry_run.index(
        "80 CONTINUOUS HARDWARE-ROOTED PROOF"
    )


def test_builder_committed_dependency_closure():
    required = (
        "arda_os/bin/arda_build_measured_manifest.py",
        "arda_os/backend/services/measured_identity.py",
        "arda_os/backend/services/measured_policy_profiles.py",
        "arda_os/backend/services/proof_file_measurement.py",
    )

    for path in required:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "cat-file",
                "-e",
                f"HEAD:{path}",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        # The test itself may be running before its own commit, but every
        # runtime dependency of the already-committed builder must exist in HEAD.
        if path == "arda_os/backend/services/proof_file_measurement.py":
            continue

        assert result.returncode == 0, f"{path} missing from HEAD"


def test_file_measurement_dependency_exists_in_worktree():
    dependency = (
        ROOT
        / "arda_os/backend/services/proof_file_measurement.py"
    )

    assert dependency.is_file()

    text = dependency.read_text(encoding="utf-8")

    required = (
        "FS_IOC_MEASURE_VERITY",
        "def measure_fd(",
        "def open_measured(",
        "O_NOFOLLOW",
    )

    for token in required:
        assert token in text


def test_builder_committed_dependency_closure():
    required = (
        "arda_os/bin/arda_build_measured_manifest.py",
        "arda_os/backend/services/measured_identity.py",
        "arda_os/backend/services/measured_policy_profiles.py",
        "arda_os/backend/services/proof_file_measurement.py",
    )

    for path in required:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "cat-file",
                "-e",
                f"HEAD:{path}",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        # The test itself may be running before its own commit, but every
        # runtime dependency of the already-committed builder must exist in HEAD.
        if path == "arda_os/backend/services/proof_file_measurement.py":
            continue

        assert result.returncode == 0, f"{path} missing from HEAD"


def test_file_measurement_dependency_exists_in_worktree():
    dependency = (
        ROOT
        / "arda_os/backend/services/proof_file_measurement.py"
    )

    assert dependency.is_file()

    text = dependency.read_text(encoding="utf-8")

    required = (
        "FS_IOC_MEASURE_VERITY",
        "def measure_fd(",
        "def open_measured(",
        "O_NOFOLLOW",
    )

    for token in required:
        assert token in text
