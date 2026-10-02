import pytest

from backend.services.attestation_profile import resolve_attestation_profile


def test_full_profile_requires_tpm():
    profile = resolve_attestation_profile("full")

    assert profile.name == "full"
    assert profile.require_tpm is True
    assert profile.permit_software_root is False


def test_lite_profile_does_not_require_tpm():
    profile = resolve_attestation_profile("lite")

    assert profile.name == "lite"
    assert profile.require_tpm is False
    assert profile.permit_software_root is True


def test_omitted_profile_defaults_to_full():
    profile = resolve_attestation_profile(None)

    assert profile.name == "full"
    assert profile.require_tpm is True
    assert profile.permit_software_root is False


def test_unknown_profile_refuses():
    with pytest.raises(ValueError, match="unknown attestation profile"):
        resolve_attestation_profile("banana")
