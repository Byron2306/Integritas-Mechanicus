import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

DIRECT_EXEC_ENTRYPOINTS = (
    ROOT / "installer" / "arda-doctor",
    ROOT / "installer" / "arda-preflight",
)


def test_direct_installer_entrypoints_are_executable():
    for path in DIRECT_EXEC_ENTRYPOINTS:
        assert path.is_file(), f"missing installer entrypoint: {path}"

        mode = path.stat().st_mode

        assert mode & stat.S_IXUSR, f"owner execute missing: {path}"
        assert mode & stat.S_IXGRP, f"group execute missing: {path}"
        assert mode & stat.S_IXOTH, f"other execute missing: {path}"


def test_systemd_units_are_non_executable_source_data():
    for name in (
        "arda-valinor-postboot.service",
        "arda-valinor-postboot.timer",
    ):
        path = ROOT / "installer" / "systemd" / name

        assert path.is_file(), f"missing systemd unit: {path}"

        mode = stat.S_IMODE(path.stat().st_mode)

        assert not (mode & 0o111), (
            f"systemd unit must not be executable: "
            f"{path} has {oct(mode)}"
        )
