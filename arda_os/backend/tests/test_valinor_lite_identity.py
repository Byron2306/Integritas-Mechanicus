import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
IDENTITY_ROOT = (
    REPO_ROOT
    / "arda_os"
    / "kernel"
    / "valinor"
    / "lite"
    / "identity"
)

EXPECTED_AUDIO_SHA256 = (
    "90f0e19a8b9318ac6472caa28f85894"
    "aebaaae69113cc69a45b9e88cfa0bbc0a"
)

FORBIDDEN_STOCK_NAMES = {
    "ceratopsian",
    "moonlight",
    "emerald",
    "homeworld",
    "spacefun",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _load_manifest():
    path = IDENTITY_ROOT / "manifest.json"
    assert path.is_file(), "portable identity manifest is missing"

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"]
    assert isinstance(payload["assets"], list)
    assert payload["assets"]

    return payload


def test_canonical_arda_identity_tree_exists():
    assert (
        IDENTITY_ROOT
        / "grub"
        / "arda-sovereign"
    ).is_dir()

    assert (
        IDENTITY_ROOT
        / "plymouth"
        / "arda-sovereign"
    ).is_dir()

    assert (
        IDENTITY_ROOT
        / "plymouth"
        / "arda-mirror-gate"
    ).is_dir()

    assert (
        IDENTITY_ROOT
        / "audio"
        / "arda-awakening.wav"
    ).is_file()


def test_awakening_audio_is_exact_historical_asset():
    audio = (
        IDENTITY_ROOT
        / "audio"
        / "arda-awakening.wav"
    )

    assert audio.is_file()
    assert _sha256(audio) == EXPECTED_AUDIO_SHA256


def test_manifest_contains_only_arda_identity_payload():
    manifest = _load_manifest()

    paths = [
        str(entry["path"]).lower()
        for entry in manifest["assets"]
    ]

    for forbidden in FORBIDDEN_STOCK_NAMES:
        assert not any(
            forbidden in path
            for path in paths
        ), f"stock theme leaked into identity payload: {forbidden}"


def test_manifest_records_required_identity_metadata():
    manifest = _load_manifest()

    for entry in manifest["assets"]:
        assert entry["role"]
        assert entry["path"]
        assert len(entry["sha256"]) == 64
        assert entry["status"] in {"required", "optional"}


def test_every_manifest_hash_matches_payload():
    manifest = _load_manifest()

    for entry in manifest["assets"]:
        relative = Path(entry["path"])

        assert not relative.is_absolute()
        assert ".." not in relative.parts

        asset = IDENTITY_ROOT / relative

        assert asset.is_file(), (
            f"manifest asset is missing: {relative}"
        )

        assert _sha256(asset) == entry["sha256"], (
            f"manifest hash mismatch: {relative}"
        )
