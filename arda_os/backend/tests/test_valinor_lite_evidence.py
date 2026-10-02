import hashlib

from backend.services.valinor_lite_evidence import (
    REQUIRED_BPF_MAPS,
    collect_lite_evidence,
)


KERNEL_SHA = (
    "875117b4148753e407725a3d3d838d8"
    "f40db95111c88eabd329f9d229414a527"
)
INITRAMFS_SHA = (
    "e1c9cd2c1694b28761d486a3662ec8e3"
    "2803871bd7bd8de11d382824c382c7ec"
)


def _write_file_with_hash(tmp_path, name, wanted_hash):
    path = tmp_path / name

    # Tests use injected expected hashes for arbitrary fixture bytes.
    data = name.encode("utf-8")
    path.write_bytes(data)

    return path, hashlib.sha256(data).hexdigest()


def _make_bpf_root(tmp_path):
    root = tmp_path / "bpf"
    root.mkdir()

    for name in REQUIRED_BPF_MAPS:
        (root / name).touch()

    return root


def test_all_required_evidence_establishes_software_root(tmp_path):
    kernel, kernel_hash = _write_file_with_hash(
        tmp_path, "vmlinuz", KERNEL_SHA
    )
    initramfs, initramfs_hash = _write_file_with_hash(
        tmp_path, "initrd", INITRAMFS_SHA
    )
    bpf_root = _make_bpf_root(tmp_path)

    result = collect_lite_evidence(
        kernel_path=kernel,
        initramfs_path=initramfs,
        expected_kernel_sha256=kernel_hash,
        expected_initramfs_sha256=initramfs_hash,
        bpf_root=bpf_root,
        bpf_lsm_probe=lambda: True,
        native_pqc_probe=lambda: True,
        secure_boot_probe=lambda: "disabled",
    )

    assert result.kernel_identity_verified is True
    assert result.bpf_lsm_available is True
    assert result.measured_maps_available is True
    assert result.pqc_native_verified is True
    assert result.software_rooted is True


def test_wrong_kernel_hash_prevents_software_root(tmp_path):
    kernel, _ = _write_file_with_hash(tmp_path, "vmlinuz", KERNEL_SHA)
    initramfs, initramfs_hash = _write_file_with_hash(
        tmp_path, "initrd", INITRAMFS_SHA
    )

    result = collect_lite_evidence(
        kernel_path=kernel,
        initramfs_path=initramfs,
        expected_kernel_sha256="0" * 64,
        expected_initramfs_sha256=initramfs_hash,
        bpf_root=_make_bpf_root(tmp_path),
        bpf_lsm_probe=lambda: True,
        native_pqc_probe=lambda: True,
        secure_boot_probe=lambda: "enabled",
    )

    assert result.kernel_identity_verified is False
    assert result.software_rooted is False


def test_missing_bpf_lsm_prevents_software_root(tmp_path):
    kernel, kernel_hash = _write_file_with_hash(tmp_path, "vmlinuz", KERNEL_SHA)
    initramfs, initramfs_hash = _write_file_with_hash(
        tmp_path, "initrd", INITRAMFS_SHA
    )

    result = collect_lite_evidence(
        kernel_path=kernel,
        initramfs_path=initramfs,
        expected_kernel_sha256=kernel_hash,
        expected_initramfs_sha256=initramfs_hash,
        bpf_root=_make_bpf_root(tmp_path),
        bpf_lsm_probe=lambda: False,
        native_pqc_probe=lambda: True,
        secure_boot_probe=lambda: "enabled",
    )

    assert result.bpf_lsm_available is False
    assert result.software_rooted is False


def test_missing_required_map_prevents_software_root(tmp_path):
    kernel, kernel_hash = _write_file_with_hash(tmp_path, "vmlinuz", KERNEL_SHA)
    initramfs, initramfs_hash = _write_file_with_hash(
        tmp_path, "initrd", INITRAMFS_SHA
    )
    bpf_root = _make_bpf_root(tmp_path)
    (bpf_root / "measured_exec_map").unlink()

    result = collect_lite_evidence(
        kernel_path=kernel,
        initramfs_path=initramfs,
        expected_kernel_sha256=kernel_hash,
        expected_initramfs_sha256=initramfs_hash,
        bpf_root=bpf_root,
        bpf_lsm_probe=lambda: True,
        native_pqc_probe=lambda: True,
        secure_boot_probe=lambda: "unknown",
    )

    assert result.measured_maps_available is False
    assert result.software_rooted is False


def test_failed_native_pqc_prevents_software_root(tmp_path):
    kernel, kernel_hash = _write_file_with_hash(tmp_path, "vmlinuz", KERNEL_SHA)
    initramfs, initramfs_hash = _write_file_with_hash(
        tmp_path, "initrd", INITRAMFS_SHA
    )

    result = collect_lite_evidence(
        kernel_path=kernel,
        initramfs_path=initramfs,
        expected_kernel_sha256=kernel_hash,
        expected_initramfs_sha256=initramfs_hash,
        bpf_root=_make_bpf_root(tmp_path),
        bpf_lsm_probe=lambda: True,
        native_pqc_probe=lambda: False,
        secure_boot_probe=lambda: "enabled",
    )

    assert result.pqc_native_verified is False
    assert result.software_rooted is False


def test_secure_boot_state_does_not_grant_software_root(tmp_path):
    kernel, kernel_hash = _write_file_with_hash(tmp_path, "vmlinuz", KERNEL_SHA)
    initramfs, initramfs_hash = _write_file_with_hash(
        tmp_path, "initrd", INITRAMFS_SHA
    )

    result = collect_lite_evidence(
        kernel_path=kernel,
        initramfs_path=initramfs,
        expected_kernel_sha256=kernel_hash,
        expected_initramfs_sha256=initramfs_hash,
        bpf_root=_make_bpf_root(tmp_path),
        bpf_lsm_probe=lambda: True,
        native_pqc_probe=lambda: False,
        secure_boot_probe=lambda: "enabled",
    )

    assert result.secure_boot_state == "enabled"
    assert result.software_rooted is False


def test_native_pqc_probe_requires_real_sign_verify_round_trip():
    from backend.services.valinor_lite_evidence import native_pqc_self_test

    class FakeSignature:
        signature = "signed"

    class FakeKeyPair:
        key_id = "test-key"
        public_key = "public"

    class FakeNativeService:
        mode = "liboqs"

        def generate_dilithium_keypair(self, key_id=None, security_level=3):
            assert security_level == 3
            return FakeKeyPair()

        def dilithium_sign(self, key_id, data):
            assert key_id == "test-key"
            assert data == b"valinor-lite-native-pqc-self-test"
            return FakeSignature()

        def dilithium_verify(self, public_key, data, signature):
            assert public_key == "public"
            assert data == b"valinor-lite-native-pqc-self-test"
            assert signature == "signed"
            return True

    assert native_pqc_self_test(FakeNativeService()) is True


def test_native_pqc_probe_refuses_simulation_even_if_round_trip_claims_success():
    from backend.services.valinor_lite_evidence import native_pqc_self_test

    class FakeSimulationService:
        mode = "simulation"

        def generate_dilithium_keypair(self, **kwargs):
            raise AssertionError("simulation must be refused before key generation")

    assert native_pqc_self_test(FakeSimulationService()) is False


def test_native_pqc_probe_refuses_native_mode_when_verification_fails():
    from backend.services.valinor_lite_evidence import native_pqc_self_test

    class FakeSignature:
        signature = "signed"

    class FakeKeyPair:
        key_id = "test-key"
        public_key = "public"

    class FakeBrokenNativeService:
        mode = "liboqs"

        def generate_dilithium_keypair(self, key_id=None, security_level=3):
            return FakeKeyPair()

        def dilithium_sign(self, key_id, data):
            return FakeSignature()

        def dilithium_verify(self, public_key, data, signature):
            return False

    assert native_pqc_self_test(FakeBrokenNativeService()) is False


def test_native_pqc_probe_refuses_pqcrypto_until_native_signature_path_exists():
    from backend.services.valinor_lite_evidence import native_pqc_self_test

    class FakePqcryptoService:
        mode = "pqcrypto"

        def generate_dilithium_keypair(self, **kwargs):
            raise AssertionError(
                "pqcrypto must not be accepted until its native ML-DSA path exists"
            )

    assert native_pqc_self_test(FakePqcryptoService()) is False
