from kernel.valinor.lite.installer.greeter import (
    detect_greeter,
    render_lightdm_gtk_config,
    validate_lite_trust_copy,
    verify_greeter,
)


def test_lightdm_gtk_is_allowed():
    result = detect_greeter(
        display_manager_target=(
            "/usr/lib/systemd/system/lightdm.service"
        ),
        xgreeter_entries=(
            "lightdm-greeter.desktop",
            "lightdm-gtk-greeter.desktop",
        ),
    )

    assert result.state == "ALLOW"
    assert result.manager == "lightdm"
    assert result.greeter == "lightdm-gtk-greeter"
    assert result.reasons == ()


def test_lightdm_without_gtk_greeter_needs_operator():
    result = detect_greeter(
        display_manager_target=(
            "/usr/lib/systemd/system/lightdm.service"
        ),
        xgreeter_entries=("example-greeter.desktop",),
    )

    assert result.state == "NEEDS_YOU"
    assert result.manager == "lightdm"
    assert result.greeter == "unknown"
    assert "lightdm_gtk_greeter_unavailable" in result.reasons


def test_non_lightdm_manager_needs_operator():
    result = detect_greeter(
        display_manager_target=(
            "/usr/lib/systemd/system/gdm3.service"
        ),
        xgreeter_entries=("lightdm-gtk-greeter.desktop",),
    )

    assert result.state == "NEEDS_YOU"
    assert result.manager == "unsupported"
    assert result.greeter == "unknown"
    assert "unsupported_display_manager" in result.reasons


def test_rendered_lightdm_config_is_canonical():
    rendered = render_lightdm_gtk_config(
        background_path=(
            "/usr/share/arda/greeter/gate-of-becoming.webp"
        ),
        user_background=False,
    )

    assert rendered.startswith("[greeter]\n")
    assert (
        "background=/usr/share/arda/greeter/"
        "gate-of-becoming.webp"
    ) in rendered
    assert "user-background=false" in rendered


def test_lite_rejects_hardware_root_claim():
    ok, reasons = validate_lite_trust_copy(
        profile="lite",
        software_rooted=True,
        enforcement_mode="audit",
        hardware_rooted=True,
    )

    assert ok is False
    assert "lite_cannot_claim_hardware_root" in reasons


def test_lite_accepts_verified_software_root_audit():
    ok, reasons = validate_lite_trust_copy(
        profile="lite",
        software_rooted=True,
        enforcement_mode="audit",
        hardware_rooted=False,
    )

    assert ok is True
    assert reasons == ()


def test_greeter_verification_accepts_matching_assets():
    result = verify_greeter(
        config_text=(
            "[greeter]\n"
            "background=/usr/share/arda/greeter/"
            "gate-of-becoming.webp\n"
            "user-background=false\n"
        ),
        background_sha256="a" * 64,
        expected_background_sha256="a" * 64,
        logo_sha256="b" * 64,
        expected_logo_sha256="b" * 64,
        trust_copy_ok=True,
    )

    assert result.ok is True
    assert result.background_verified is True
    assert result.logo_verified is True
    assert result.config_verified is True
    assert result.truthful_lite_copy is True
    assert result.failures == ()


def test_greeter_verification_refuses_tampered_background():
    result = verify_greeter(
        config_text=(
            "[greeter]\n"
            "background=/usr/share/arda/greeter/"
            "gate-of-becoming.webp\n"
            "user-background=false\n"
        ),
        background_sha256="0" * 64,
        expected_background_sha256="a" * 64,
        logo_sha256="b" * 64,
        expected_logo_sha256="b" * 64,
        trust_copy_ok=True,
    )

    assert result.ok is False
    assert result.background_verified is False
    assert "background_hash_mismatch" in result.failures
