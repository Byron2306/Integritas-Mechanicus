from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AttestationProfile:
    name: Literal["full", "lite"]
    require_tpm: bool
    permit_software_root: bool


FULL_PROFILE = AttestationProfile(
    name="full",
    require_tpm=True,
    permit_software_root=False,
)

LITE_PROFILE = AttestationProfile(
    name="lite",
    require_tpm=False,
    permit_software_root=True,
)


def resolve_attestation_profile(
    value: str | None,
) -> AttestationProfile:
    if value is None:
        return FULL_PROFILE

    normalized = value.strip().lower()

    if normalized == "full":
        return FULL_PROFILE

    if normalized == "lite":
        return LITE_PROFILE

    raise ValueError(
        f"unknown attestation profile: {value}"
    )
