import stat
from pathlib import Path


def test_arda_doctor_is_executable_product_source():
    root = Path(__file__).resolve().parents[2]
    doctor = root / "installer" / "arda-doctor"

    assert doctor.is_file(), "installer/arda-doctor is missing"

    mode = doctor.stat().st_mode

    assert mode & stat.S_IXUSR
    assert mode & stat.S_IXGRP
    assert mode & stat.S_IXOTH
