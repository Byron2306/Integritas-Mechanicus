from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "packaging/build-arda-valinor-deb.sh"


def test_package_builds_ring0_from_archived_head():
    src = BUILD.read_text()

    assert 'git -C "$ROOT" archive HEAD | tar -x -C "$TMP_TREE"' in src
    assert 'build_arda_proof_bpf.sh' in src
    assert '"$TMP_TREE/arda_os/backend/services/bpf"' in src

    assert '"$BPF_BUILD/arda_physical_lsm.o"' in src
    assert (
        '"$TMP_TREE/arda_os/backend/services/bpf/arda_physical_lsm.o"'
        in src
    )


def test_package_replaces_loader_from_same_build():
    src = BUILD.read_text()

    assert '"$BPF_BUILD/arda_lsm_loader"' in src
    assert (
        '"$TMP_TREE/arda_os/backend/services/bpf/arda_lsm_loader"'
        in src
    )


def test_package_carries_bpf_build_receipt():
    src = BUILD.read_text()

    assert '"$BPF_BUILD/artifacts.sha256"' in src
    assert (
        '"$TMP_TREE/arda_os/backend/services/bpf/artifacts.sha256"'
        in src
    )


def test_bpf_builder_uses_archivable_colocated_loader_source():
    path = ROOT / "arda_os/bin/build_arda_proof_bpf.sh"
    src = path.read_text()

    assert 'loader_source="$source_dir/arda_lsm_loader.c"' in src
    assert '"$source_dir/../proof_bpf_loader.c"' not in src
