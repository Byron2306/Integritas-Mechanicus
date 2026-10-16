from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "packaging/build-arda-valinor-deb.sh"
INSTALL = ROOT / "installer/arda-install"


def test_deb_does_not_own_live_verifier_public_key():
    src = BUILD.read_text()

    assert (
        '"$PKG/etc/arda/verifier/verifier-key.pub.pem"'
        not in src
    )


def test_arda_install_never_writes_live_verifier_public_key():
    src = INSTALL.read_text()

    assert (
        'install -m 0644     "$SRC/installer/trust/verifier-key.pub.pem"'
        not in src
    )
    assert "PRESERVE: existing verifier public key" in src
    assert "NOTICE: verifier public key not provisioned" in src


def test_runtime_still_consumes_operator_provisioned_key():
    grade = (ROOT / "installer/arda-grade").read_text()
    enroll = (ROOT / "installer/arda-enroll").read_text()

    assert "/etc/arda/verifier/verifier-key.pub.pem" in grade
    assert "/etc/arda/verifier/verifier-key.pub.pem" in enroll


def test_deb_has_transition_only_verifier_key_preservation():
    src = BUILD.read_text()

    assert '"$PKG/DEBIAN/preinst"' in src
    assert 'if [ "$1" = "upgrade" ]' in src
    assert "verifier-key-transition" in src
    assert 'sha256sum "$KEY"' in src
    assert "stat -c '%a %u %g'" in src

    # Upgrade transport is not package ownership.
    assert (
        '"$PKG/etc/arda/verifier/verifier-key.pub.pem"'
        not in src
    )


def test_transition_refuses_changed_verifier_identity():
    src = BUILD.read_text()

    assert (
        "REFUSE: live verifier identity changed during package transition"
        in src
    )
    assert (
        "REFUSE: verifier public key transition stash corrupted"
        in src
    )
    assert (
        "REFUSE: incomplete verifier public key transition stash"
        in src
    )


def test_transition_restores_only_preserved_verifier_identity():
    src = BUILD.read_text()

    assert 'cp "$STASH_KEY" "$KEY"' in src
    assert 'chmod "$mode" "$KEY"' in src
    assert 'chown "$uid:$gid" "$KEY"' in src
    assert (
        "RESTORE: verifier public key preserved across package transition"
        in src
    )
