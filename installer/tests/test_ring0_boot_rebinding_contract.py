from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

RESTORE = (
    ROOT
    / "arda_os/kernel/valinor/scripts/restore_ring0_boot_state.py"
)


def test_boot_restore_uses_persisted_generation_not_old_runtime_identity():
    src = RESTORE.read_text()

    assert "generation" in src
    assert "checked_paths" in src
    assert "loader_digest_specs" in src


def test_boot_restore_rebinds_fresh_cgroup_identity():
    src = RESTORE.read_text()

    assert "current_cgroup_kernel_id" in src
    assert "_project_active_generation" in src


def test_boot_restore_recomputes_measured_exec_identity():
    src = RESTORE.read_text()

    # Runtime identity is reconstructed from a held, kernel-measured file,
    # never from the persisted inode/device and never from a fresh path stat
    # after measurement.
    assert "open_measured" in src
    assert "stage_held_measured_exec" in src
    assert "measured.inode" in src
    assert "measured.device" in src
    assert "checked_paths" in src


def test_boot_restore_does_not_project_old_cgroup_pointer():
    src = RESTORE.read_text()

    # The persisted runtime capsule may be evidence, but it must never become
    # the new boot's authoritative cgroup binding.
    assert '_project_active_generation(cgroup_kernel_id=int(payload["cgroup_kernel_id"])' not in src


def test_boot_restore_is_fail_closed_on_missing_active_generation():
    src = RESTORE.read_text()

    assert "active_record_missing" in src
    assert "return 1" in src or "raise RuntimeError" in src


def test_boot_restore_remeasures_content_before_runtime_rebind():
    src = RESTORE.read_text()

    assert "open_measured" in src
    assert "parse_loader_spec" in src
    assert "measured_exec_fsverity_mismatch" in src
    assert "measured.revalidate()" in src


def test_boot_restore_binds_held_measured_inode_not_fresh_path_stat():
    src = RESTORE.read_text()

    assert "stage_held_measured_exec" in src
    assert "measured.inode" in src
    assert "measured.device" in src


def test_boot_restore_requires_one_digest_identity_per_checked_path():
    src = RESTORE.read_text()

    assert (
        "active_record_content_binding_cardinality_mismatch"
        in src
    )
    assert "zip(" in src
    assert "strict=True" in src


def test_boot_restore_cgroup_resolver_is_not_shadowed():
    src = RESTORE.read_text()

    assert "def resolve_current_cgroup_kernel_id()" in src
    assert (
        "current_cgroup_kernel_id = "
        "resolve_current_cgroup_kernel_id()"
        in src
    )
    assert (
        "current_cgroup_kernel_id = current_cgroup_kernel_id()"
        not in src
    )
