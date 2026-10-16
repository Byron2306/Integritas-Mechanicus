from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PROFILE = (
    ROOT
    / "arda_os"
    / "backend"
    / "services"
    / "measured_policy_profiles.py"
)


def test_authority_bearing_post_strict_runtime_is_measured():
    src = PROFILE.read_text()

    required = (
        "arda_os/kernel/valinor/scripts/post_boot_valinor_gate.py",
        "arda_os/kernel/valinor/scripts/restore_ring0_boot_state.py",
        "arda_os/kernel/valinor/scripts/verify_ring0_attachment.py",
        "/usr/lib/systemd/system/arda-ring0.service",
        "/usr/lib/systemd/system/arda-ring0-verify.service",
        "/usr/lib/systemd/system/arda-valinor-postboot.service",
        "/usr/lib/systemd/system/arda-valinor-postboot.timer",
    )

    for artifact in required:
        assert artifact in src, (
            f"authority-bearing runtime escaped measured profile: {artifact}"
        )


def test_installed_authority_units_not_trusted_only_by_source_ancestry():
    src = PROFILE.read_text()

    # Measuring a repository copy is insufficient. The exact installed unit
    # consumed by systemd must itself belong to the measured host identity.
    for unit in (
        "arda-ring0.service",
        "arda-ring0-verify.service",
        "arda-valinor-postboot.service",
        "arda-valinor-postboot.timer",
    ):
        assert f"/usr/lib/systemd/system/{unit}" in src
