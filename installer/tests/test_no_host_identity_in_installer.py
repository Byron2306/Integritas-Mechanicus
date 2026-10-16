from pathlib import Path


FORBIDDEN_NAMES = {
    "arda_measured_generation.sqlite3",
    "pcr11_binding_state.json",
    "latest-verdict.json",
    "07_sovereign_attestation.json",
    "03_tpm_identity.json",
    "verifier-key.pem",
}

FORBIDDEN_PARTS = {
    "machine-id",
    "boot-id",
    "private",
    "ak.ctx",
    "ek.ctx",
}


def test_installer_does_not_ship_host_identity():
    root = Path(__file__).resolve().parents[1]

    files = [
        p for p in root.rglob("*")
        if p.is_file()
    ]

    names = {p.name for p in files}

    assert not (FORBIDDEN_NAMES & names)

    for path in files:
        lowered = str(path.relative_to(root)).lower()

        for forbidden in FORBIDDEN_PARTS:
            assert forbidden not in lowered


def test_verifier_key_is_public_only():
    root = Path(__file__).resolve().parents[1]
    key = root / "trust" / "verifier-key.pub.pem"

    assert key.exists()

    text = key.read_text(errors="ignore")

    assert "PUBLIC KEY" in text
    assert "PRIVATE KEY" not in text


def test_no_restoration_verifier_identity_in_portable_installer():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]

    portable_files = [
        root / "systemd" / "arda-valinor-postboot.service",
        root / "systemd" / "arda-valinor-postboot.timer",
        root / "attested-host.env.example",
    ]

    forbidden = (
        "arda-gen1-restoration-verifier",
        "arda-phase4-loopback-restoration",
        "ARDA_VERIFIER_PRIVATE_KEY",
    )

    for path in portable_files:
        text = path.read_text()
        for token in forbidden:
            assert token not in text, f"{path} leaks restoration identity: {token}"


def test_portable_refresh_units_are_shipped_without_private_signer():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]

    service = (
        root / "systemd" / "arda-valinor-postboot.service"
    ).read_text()

    timer = (
        root / "systemd" / "arda-valinor-postboot.timer"
    ).read_text()

    env = (
        root / "attested-host.env.example"
    ).read_text()

    combined = service + timer + env

    assert "ARDA_VERIFIER_PRIVATE_KEY" not in combined
    assert "arda-gen1-restoration-verifier" not in combined
    assert "arda-phase4-loopback-restoration" not in combined

    assert "OnUnitActiveSec=5min" in timer
    assert "arda-valinor-postboot.service" in timer


def test_enrollment_arms_refresh_only_after_grade():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    enroll = (root / "arda-enroll").read_text()

    grade = enroll.index(
        'receipt "70_grade" "PASS"'
    )

    continuous = enroll.index(
        'step "80 CONTINUOUS HARDWARE-ROOTED PROOF"'
    )

    enable_timer = enroll.index(
        "systemctl enable --now arda-valinor-postboot.timer"
    )

    assert grade < continuous < enable_timer
