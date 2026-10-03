import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from kernel.valinor.lite.build_release import (
    CANONICAL_KERNEL_ARCHIVE_SHA256,
    ReleaseBuildResult,
    build_valinor_lite_release,
)


STOCK_THEMES = {
    "ceratopsian",
    "emerald",
    "futureprototype",
    "homeworld",
    "joy",
    "lines",
    "moonlight",
    "softwaves",
    "spacefun",
    "text",
    "tribar",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _fake_kernel_archive(tmp_path: Path) -> Path:
    archive = tmp_path / "valinor-kernel-6.12.96.tar.zst"
    archive.write_bytes(
        b"FAKE-VALINOR-KERNEL-ARCHIVE-FOR-UNIT-TESTS"
    )
    return archive


def _build(tmp_path: Path):
    kernel_archive = _fake_kernel_archive(tmp_path)
    output = tmp_path / "dist"

    result = build_valinor_lite_release(
        repo_root=_repo_root(),
        kernel_archive=kernel_archive,
        output_dir=output,
        expected_kernel_archive_sha256=_sha256(
            kernel_archive
        ),
    )

    return result, kernel_archive


def _extract(
    archive: Path,
    destination: Path,
) -> Path:
    destination.mkdir(parents=True)

    subprocess.run(
        [
            "tar",
            "--zstd",
            "-xf",
            str(archive),
            "-C",
            str(destination),
        ],
        check=True,
    )

    roots = [
        path
        for path in destination.iterdir()
        if path.is_dir()
    ]

    assert len(roots) == 1
    return roots[0]


def test_canonical_kernel_archive_digest_is_pinned():
    assert CANONICAL_KERNEL_ARCHIVE_SHA256 == (
        "cd18653a510cf0e2f67ff00006d22b09e"
        "de74983051c770045f4a2b719e9071d"
    )


def test_build_emits_archive_and_sha256_sidecar(tmp_path):
    result, _ = _build(tmp_path)

    assert isinstance(result, ReleaseBuildResult)
    assert result.archive_path.is_file()
    assert result.sha256_path.is_file()
    assert result.archive_path.name == (
        "valinor-lite-6.12.96.tar.zst"
    )

    digest = _sha256(result.archive_path)

    assert result.archive_sha256 == digest
    assert digest in result.sha256_path.read_text()


def test_release_contains_required_top_level_payloads(
    tmp_path,
):
    result, _ = _build(tmp_path)
    root = _extract(
        result.archive_path,
        tmp_path / "extract",
    )

    required = {
        "install-valinor-lite",
        "manifest",
        "kernel",
        "identity",
        "profile",
        "verify",
    }

    assert required.issubset(
        {path.name for path in root.iterdir()}
    )

    assert (
        root
        / "kernel"
        / "valinor-kernel-6.12.96.tar.zst"
    ).is_file()


def test_release_manifest_pins_transport_and_runtime_truth(
    tmp_path,
):
    result, kernel_archive = _build(tmp_path)
    root = _extract(
        result.archive_path,
        tmp_path / "extract",
    )

    manifest = json.loads(
        (
            root
            / "manifest"
            / "release.json"
        ).read_text()
    )

    assert manifest["schema_version"] == (
        "valinor-lite-portable-release-v1"
    )

    assert manifest["kernel"]["release"] == (
        "6.12.96-valinor"
    )

    assert manifest["kernel"]["archive_sha256"] == (
        _sha256(kernel_archive)
    )

    assert manifest["kernel"]["image_sha256"] == (
        "875117b4148753e407725a3d3d838d8f"
        "40db95111c88eabd329f9d229414a527"
    )

    assert manifest["kernel"]["initramfs_sha256"] == (
        "e1c9cd2c1694b28761d486a3662ec8e3"
        "2803871bd7bd8de11d382824c382c7ec"
    )


def test_every_manifest_file_hash_verifies(tmp_path):
    result, _ = _build(tmp_path)
    root = _extract(
        result.archive_path,
        tmp_path / "extract",
    )

    manifest = json.loads(
        (
            root
            / "manifest"
            / "files.json"
        ).read_text()
    )

    assert manifest["schema_version"] == (
        "valinor-lite-file-manifest-v1"
    )

    for record in manifest["files"]:
        path = root / record["path"]

        assert path.is_file()
        assert _sha256(path) == record["sha256"]


def test_bundled_offline_verifier_accepts_release(
    tmp_path,
):
    result, _ = _build(tmp_path)
    root = _extract(
        result.archive_path,
        tmp_path / "extract",
    )

    verifier = (
        root
        / "manifest"
        / "verify_manifest.py"
    )

    completed = subprocess.run(
        [
            "/usr/bin/python3",
            str(verifier),
            str(root),
        ],
        cwd=tmp_path,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "ALL HASHES PASS" in completed.stdout


def test_bundled_offline_verifier_detects_tamper(
    tmp_path,
):
    result, _ = _build(tmp_path)
    root = _extract(
        result.archive_path,
        tmp_path / "extract",
    )

    target = (
        root
        / "identity"
        / "audio"
        / "arda-awakening.wav"
    )

    target.write_bytes(
        target.read_bytes() + b"TAMPER"
    )

    completed = subprocess.run(
        [
            "/usr/bin/python3",
            str(
                root
                / "manifest"
                / "verify_manifest.py"
            ),
            str(root),
        ],
        cwd=tmp_path,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode != 0
    assert "HASH FAILURE" in completed.stdout


def test_no_stock_theme_clutter_enters_release(tmp_path):
    result, _ = _build(tmp_path)
    root = _extract(
        result.archive_path,
        tmp_path / "extract",
    )

    names = {
        path.name.lower()
        for path in (
            root / "identity"
        ).rglob("*")
    }

    assert names.isdisjoint(STOCK_THEMES)


def test_no_python_bytecode_enters_release(tmp_path):
    result, _ = _build(tmp_path)
    root = _extract(
        result.archive_path,
        tmp_path / "extract",
    )

    bad = [
        path
        for path in root.rglob("*")
        if (
            path.name == "__pycache__"
            or path.suffix == ".pyc"
        )
    ]

    assert bad == []


def test_installer_help_works_without_git_checkout(
    tmp_path,
):
    result, _ = _build(tmp_path)
    root = _extract(
        result.archive_path,
        tmp_path / "extract",
    )

    isolated = tmp_path / "isolated"
    shutil.copytree(root, isolated)

    completed = subprocess.run(
        [
            str(
                isolated
                / "install-valinor-lite"
            )
        ],
        cwd=isolated,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "usage:" in completed.stdout.lower()
    assert "--preflight" in completed.stdout
    assert "--install" in completed.stdout


def test_verify_help_works_without_git_checkout(
    tmp_path,
):
    result, _ = _build(tmp_path)
    root = _extract(
        result.archive_path,
        tmp_path / "extract",
    )

    isolated = tmp_path / "isolated"
    shutil.copytree(root, isolated)

    completed = subprocess.run(
        [
            str(
                isolated
                / "verify"
                / "verify-valinor-lite"
            ),
            "--help",
        ],
        cwd=isolated,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(tmp_path),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "verify valinor lite" in (
        completed.stdout.lower()
    )


def test_wrong_kernel_archive_hash_refuses_build(
    tmp_path,
):
    kernel_archive = _fake_kernel_archive(tmp_path)

    try:
        build_valinor_lite_release(
            repo_root=_repo_root(),
            kernel_archive=kernel_archive,
            output_dir=tmp_path / "dist",
            expected_kernel_archive_sha256="0" * 64,
        )
    except ValueError as exc:
        assert "kernel archive hash mismatch" in str(
            exc
        ).lower()
    else:
        raise AssertionError(
            "builder accepted wrong kernel archive hash"
        )


def test_release_is_deterministic(tmp_path):
    kernel_archive = _fake_kernel_archive(tmp_path)
    digest = _sha256(kernel_archive)

    first = build_valinor_lite_release(
        repo_root=_repo_root(),
        kernel_archive=kernel_archive,
        output_dir=tmp_path / "dist-a",
        expected_kernel_archive_sha256=digest,
    )

    second = build_valinor_lite_release(
        repo_root=_repo_root(),
        kernel_archive=kernel_archive,
        output_dir=tmp_path / "dist-b",
        expected_kernel_archive_sha256=digest,
    )

    assert first.archive_sha256 == second.archive_sha256
    assert (
        first.archive_path.read_bytes()
        == second.archive_path.read_bytes()
    )


def test_preserved_kernel_archive_is_not_normal_git_blob():
    repo = _repo_root()

    tracked = subprocess.run(
        [
            "git",
            "ls-files",
            "--error-unmatch",
            (
                "artifacts/valinor-kernel/"
                "6.12.96-valinor/"
                "valinor-kernel-6.12.96.tar.zst"
            ),
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )

    assert tracked.returncode != 0


def test_release_carries_greeter_identity_and_runtime(tmp_path):
    result, _ = _build(tmp_path)
    root = _extract(
        result.archive_path,
        tmp_path / "extract-greeter",
    )

    assert (
        root
        / "identity"
        / "greeter"
        / "gate-of-becoming.webp"
    ).is_file()

    assert (
        root
        / "identity"
        / "greeter"
        / "arda-mark.png"
    ).is_file()

    config = (
        root
        / "identity"
        / "greeter"
        / "lightdm-gtk-greeter.conf"
    )

    assert config.is_file()
    assert (
        "background=/usr/share/arda/greeter/"
        "gate-of-becoming.webp"
    ) in config.read_text(encoding="utf-8")

    assert (
        root
        / "profile"
        / "python"
        / "kernel"
        / "valinor"
        / "lite"
        / "installer"
        / "greeter.py"
    ).is_file()


def test_release_contains_no_host_lightdm_state(tmp_path):
    result, _ = _build(tmp_path)
    root = _extract(
        result.archive_path,
        tmp_path / "extract-no-host-lightdm",
    )

    assert not (
        root / "etc" / "lightdm"
    ).exists()


def test_release_contains_complete_installer_runtime(
    tmp_path,
):
    result, _ = _build(tmp_path)
    root = _extract(
        result.archive_path,
        tmp_path / "extract-runtime",
    )

    runtime = (
        root
        / "profile"
        / "python"
    )

    required = (
        runtime
        / "backend"
        / "services"
        / "quantum_security.py",
        runtime
        / "kernel"
        / "valinor"
        / "lite"
        / "installer"
        / "control.py",
    )

    assert all(
        path.is_file()
        for path in required
    )
