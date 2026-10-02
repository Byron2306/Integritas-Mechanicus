from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class GreeterDetection:
    state: Literal["ALLOW", "NEEDS_YOU"]
    manager: str
    greeter: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class GreeterVerification:
    ok: bool
    background_verified: bool
    logo_verified: bool
    config_verified: bool
    truthful_lite_copy: bool
    failures: tuple[str, ...]


def detect_greeter(
    *,
    display_manager_target: str,
    xgreeter_entries: tuple[str, ...],
) -> GreeterDetection:
    if not display_manager_target.endswith("lightdm.service"):
        return GreeterDetection(
            state="NEEDS_YOU",
            manager="unsupported",
            greeter="unknown",
            reasons=("unsupported_display_manager",),
        )

    if "lightdm-gtk-greeter.desktop" not in xgreeter_entries:
        return GreeterDetection(
            state="NEEDS_YOU",
            manager="lightdm",
            greeter="unknown",
            reasons=("lightdm_gtk_greeter_unavailable",),
        )

    return GreeterDetection(
        state="ALLOW",
        manager="lightdm",
        greeter="lightdm-gtk-greeter",
        reasons=(),
    )


def render_lightdm_gtk_config(
    *,
    background_path: str,
    user_background: bool = False,
) -> str:
    value = "true" if user_background else "false"

    return (
        "[greeter]\n"
        f"background={background_path}\n"
        f"user-background={value}\n"
    )


def validate_lite_trust_copy(
    *,
    profile: str,
    software_rooted: bool,
    enforcement_mode: str,
    hardware_rooted: bool,
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []

    if profile != "lite":
        reasons.append("profile_is_not_lite")

    if not software_rooted:
        reasons.append("software_root_unverified")

    if enforcement_mode != "audit":
        reasons.append("enforcement_mode_not_audit")

    if hardware_rooted:
        reasons.append("lite_cannot_claim_hardware_root")

    return (not reasons, tuple(reasons))


def verify_greeter(
    *,
    config_text: str,
    background_sha256: str,
    expected_background_sha256: str,
    logo_sha256: str,
    expected_logo_sha256: str,
    trust_copy_ok: bool,
) -> GreeterVerification:
    background_verified = (
        background_sha256 == expected_background_sha256
    )
    logo_verified = logo_sha256 == expected_logo_sha256

    config_verified = (
        "[greeter]" in config_text
        and (
            "background=/usr/share/arda/greeter/"
            "gate-of-becoming.webp"
        )
        in config_text
        and "user-background=false" in config_text
    )

    failures: list[str] = []

    if not background_verified:
        failures.append("background_hash_mismatch")

    if not logo_verified:
        failures.append("logo_hash_mismatch")

    if not config_verified:
        failures.append("greeter_config_invalid")

    if not trust_copy_ok:
        failures.append("lite_trust_copy_invalid")

    return GreeterVerification(
        ok=not failures,
        background_verified=background_verified,
        logo_verified=logo_verified,
        config_verified=config_verified,
        truthful_lite_copy=trust_copy_ok,
        failures=tuple(failures),
    )
