#!/usr/bin/env bash
set -euo pipefail

# Package filesystem permissions must not inherit a caller's restrictive
# umask, for example umask 077 used while minting verifier private keys.
umask 022

ROOT="$(git rev-parse --show-toplevel)"
VERSION="${ARDA_PACKAGE_VERSION:-0.1.5}"
ARCH="${ARDA_PACKAGE_ARCH:-amd64}"

BUILD="$ROOT/build/arda-valinor-deb"
PKG="$BUILD/root"
OUT="$ROOT/build/arda-valinor_${VERSION}_${ARCH}.deb"

rm -rf "$BUILD"

mkdir -p \
  "$PKG/DEBIAN" \
  "$PKG/usr/lib/arda/src" \
  "$PKG/usr/bin" \
  "$PKG/etc/arda/trust/intel-ek" \
  "$PKG/etc/arda/trust/microsoft-pluton" \
  "$PKG/etc/arda/verifier" \
  "$PKG/etc/arda/policy" \
  "$PKG/lib/systemd/system" \
  "$PKG/var/lib/arda/enrollment"

cat > "$PKG/DEBIAN/control" <<EOF
Package: arda-valinor
Version: $VERSION
Section: admin
Priority: optional
Architecture: $ARCH
Maintainer: ARDA
Depends: python3, python3-venv, python3-cryptography, openssl, rsync, systemd, tpm2-tools, mokutil, fsverity, bpftool
Description: ARDA Valinor hardware-rooted enrollment runtime
 Proof-governed Valinor host enrollment with measured identity,
 TPM attestation, manufacturer-rooted EK verification and signed grading.
EOF

TMP_TREE="$BUILD/tree"
mkdir -p "$TMP_TREE"

git -C "$ROOT" archive HEAD | tar -x -C "$TMP_TREE"

# ------------------------------------------------------------
# RING-0 BUILD BOUNDARY
# ------------------------------------------------------------
# Compile the executable BPF runtime from the exact archived HEAD
# source that is about to enter the package. Never package a stale .o.
BPF_BUILD="$BUILD/bpf-runtime"

bash "$ROOT/arda_os/bin/build_arda_proof_bpf.sh"   "$TMP_TREE/arda_os/backend/services/bpf"   "$BPF_BUILD"

install -m 0644   "$BPF_BUILD/arda_physical_lsm.o"   "$TMP_TREE/arda_os/backend/services/bpf/arda_physical_lsm.o"

install -m 0755   "$BPF_BUILD/arda_lsm_loader"   "$TMP_TREE/arda_os/backend/services/bpf/arda_lsm_loader"

cp   "$BPF_BUILD/artifacts.sha256"   "$TMP_TREE/arda_os/backend/services/bpf/artifacts.sha256"

cp -a "$TMP_TREE/arda_os" "$PKG/usr/lib/arda/src/"
cp -a "$TMP_TREE/installer" "$PKG/usr/lib/arda/src/"

# Package trust boundary: shipped ARDA source/runtime must never be
# group- or world-writable. Preserve existing execute bits.
chmod -R go-w "$PKG/usr/lib/arda/src"


# ------------------------------------------------------------
# PACKAGE SANITIZATION BOUNDARY
# ------------------------------------------------------------

ARDA_PAYLOAD="$PKG/usr/lib/arda/src/arda_os"

rm -rf \
  "$ARDA_PAYLOAD/attestation" \
  "$ARDA_PAYLOAD/kernel/valinor/checkpoints" \
  "$ARDA_PAYLOAD/backend/scripts/telemetry_logs"

find "$ARDA_PAYLOAD" -type f \
  \( \
    -iname '*.ctx' \
    -o -iname '*.key' \
    -o -iname '*.priv' \
    -o -iname '*private*.pem' \
    -o -iname '*private*.key' \
  \) \
  -print -delete

find "$ARDA_PAYLOAD" -type f \
  \( \
    -name 'latest-verdict.json' \
    -o -name '07_sovereign_attestation.json' \
    -o -name '03_tpm_identity.json' \
    -o -name 'pcr11_binding_state.json' \
    -o -name 'arda_measured_generation.sqlite3' \
    -o -name 'tpm_nonce.bin' \
    -o -name 'tpm_quote_message.dat' \
    -o -name 'tpm_quote_pcrs.dat' \
    -o -name 'tpm_quote_signature.dat' \
  \) \
  -print -delete

echo
echo "=== PACKAGE SECRET / IDENTITY GATE ==="

REFUSE=0

if find "$PKG" -type f \
  \( \
    -iname '*.ctx' \
    -o -iname '*.key' \
    -o -iname '*.priv' \
    -o -name 'latest-verdict.json' \
    -o -name '07_sovereign_attestation.json' \
    -o -name '03_tpm_identity.json' \
    -o -name 'pcr11_binding_state.json' \
    -o -name 'arda_measured_generation.sqlite3' \
  \) \
  -print | grep -q .
then
  echo "REFUSE: forbidden identity/secret filename survived sanitization"
  REFUSE=1
fi

if grep -RIl \
  --exclude='*.pyc' \
  --exclude='*.so' \
  --exclude='*.o' \
  --exclude='*.bin' \
  -- \
  '-----BEGIN .*PRIVATE KEY-----' \
  "$PKG" 2>/dev/null | grep -q .
then
  echo "REFUSE: PEM private key material survived sanitization"
  REFUSE=1
fi

if [[ "$REFUSE" -ne 0 ]]; then
  echo "PACKAGE_SANITIZATION: REFUSE"
  exit 1
fi

echo "PACKAGE_SANITIZATION: PASS"

for tool in \
  arda-install \
  arda-preflight \
  arda-doctor \
  arda-enroll \
  arda-attest \
  arda-grade
do
  install -m 0755 \
    "$TMP_TREE/installer/$tool" \
    "$PKG/usr/bin/$tool"
done

install -m 0644 \
  "$TMP_TREE/installer/trust/intel-ek-root.pem" \
  "$PKG/etc/arda/trust/intel-ek/intel-ek-root.pem"

install -m 0644 \
  "$TMP_TREE/installer/trust/intel-ek-intermediate.pem" \
  "$PKG/etc/arda/trust/intel-ek/intel-ek-intermediate.pem"


install -m 0644 \
  "$TMP_TREE/installer/trust/microsoft-pluton/pluton-factory-device.pem" \
  "$PKG/etc/arda/trust/microsoft-pluton/pluton-factory-device.pem"

install -m 0644 \
  "$TMP_TREE/installer/trust/microsoft-pluton/microsoft-pluton-policy-ca-a.pem" \
  "$PKG/etc/arda/trust/microsoft-pluton/microsoft-pluton-policy-ca-a.pem"

install -m 0644 \
  "$TMP_TREE/installer/trust/microsoft-pluton/microsoft-pluton-root-ca-2021.pem" \
  "$PKG/etc/arda/trust/microsoft-pluton/microsoft-pluton-root-ca-2021.pem"

install -m 0644 \
  "$TMP_TREE/installer/policy/constitutional-policy.json" \
  "$PKG/etc/arda/policy/constitutional-policy.json"

install -m 0644 \
  "$TMP_TREE/installer/policy/active_bundle.json" \
  "$PKG/etc/arda/policy/active_bundle.json"

install -m 0644 \
  "$TMP_TREE/installer/policy/active_projection_plan.json" \
  "$PKG/etc/arda/policy/active_projection_plan.json"

install -m 0644 \
  "$TMP_TREE/installer/systemd/arda-postboot-grade.service" \
  "$PKG/lib/systemd/system/arda-postboot-grade.service"

install -m 0644 \
  "$TMP_TREE/arda_os/kernel/valinor/systemd/arda-ring0.service" \
  "$PKG/lib/systemd/system/arda-ring0.service"

install -m 0644 \
  "$TMP_TREE/arda_os/kernel/valinor/systemd/arda-ring0-verify.service" \
  "$PKG/lib/systemd/system/arda-ring0-verify.service"

install -m 0644 \
  "$TMP_TREE/installer/systemd/arda-valinor-postboot.service" \
  "$PKG/lib/systemd/system/arda-valinor-postboot.service"

install -m 0644 \
  "$TMP_TREE/installer/systemd/arda-valinor-postboot.timer" \
  "$PKG/lib/systemd/system/arda-valinor-postboot.timer"

install -m 0644 \
  "$TMP_TREE/installer/attested-host.env.example" \
  "$PKG/etc/arda/attested-host.env.example"

cat > "$PKG/DEBIAN/preinst" <<'PREINST'
#!/bin/sh
set -e

KEY=/etc/arda/verifier/verifier-key.pub.pem
STASH_DIR=/var/lib/arda/upgrade/verifier-key-transition
STASH_KEY="$STASH_DIR/verifier-key.pub.pem"
STASH_SHA="$STASH_DIR/verifier-key.pub.pem.sha256"
STASH_META="$STASH_DIR/verifier-key.pub.pem.meta"

# Migration only. The package does not mint, select, or own verifier identity.
# Preserve an operator-provisioned key across the legacy 0.1.5 -> 0.1.6
# package transition, where dpkg may remove the old package-owned pathname.
if [ "$1" = "upgrade" ] && [ -e "$KEY" ]; then
    if [ -L "$KEY" ] || [ ! -f "$KEY" ]; then
        echo "REFUSE: verifier public key is not a regular file" >&2
        exit 1
    fi

    rm -rf "$STASH_DIR"
    umask 077
    mkdir -p "$STASH_DIR"
    chmod 0700 "$STASH_DIR"

    cp -p "$KEY" "$STASH_KEY"

    sha256sum "$KEY" | awk '{print $1}' > "$STASH_SHA"
    stat -c '%a %u %g' "$KEY" > "$STASH_META"

    expected="$(cat "$STASH_SHA")"
    actual="$(sha256sum "$STASH_KEY" | awk '{print $1}')"

    if [ "$actual" != "$expected" ]; then
        echo "REFUSE: verifier public key transition stash digest mismatch" >&2
        exit 1
    fi

    echo "PRESERVE: verifier public key staged for package transition"
fi

exit 0
PREINST

chmod 0755 "$PKG/DEBIAN/preinst"

cat > "$PKG/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e

mkdir -p \
  /etc/arda \
  /etc/arda/policy \
  /etc/arda/trust/intel-ek \
  /etc/arda/verifier \
  /var/lib/arda/enrollment

KEY=/etc/arda/verifier/verifier-key.pub.pem
STASH_DIR=/var/lib/arda/upgrade/verifier-key-transition
STASH_KEY="$STASH_DIR/verifier-key.pub.pem"
STASH_SHA="$STASH_DIR/verifier-key.pub.pem.sha256"
STASH_META="$STASH_DIR/verifier-key.pub.pem.meta"

if [ -d "$STASH_DIR" ]; then
    if [ ! -f "$STASH_KEY" ] || [ ! -f "$STASH_SHA" ] || [ ! -f "$STASH_META" ]; then
        echo "REFUSE: incomplete verifier public key transition stash" >&2
        exit 1
    fi

    expected="$(cat "$STASH_SHA")"
    stash_actual="$(sha256sum "$STASH_KEY" | awk '{print $1}')"

    if [ "$stash_actual" != "$expected" ]; then
        echo "REFUSE: verifier public key transition stash corrupted" >&2
        exit 1
    fi

    if [ -e "$KEY" ]; then
        if [ -L "$KEY" ] || [ ! -f "$KEY" ]; then
            echo "REFUSE: live verifier public key is not a regular file" >&2
            exit 1
        fi

        live_actual="$(sha256sum "$KEY" | awk '{print $1}')"

        if [ "$live_actual" != "$expected" ]; then
            echo "REFUSE: live verifier identity changed during package transition" >&2
            exit 1
        fi

        echo "PRESERVE: existing verifier public key survived package transition"
    else
        read mode uid gid < "$STASH_META"

        cp "$STASH_KEY" "$KEY"
        chmod "$mode" "$KEY"
        chown "$uid:$gid" "$KEY"

        restored_actual="$(sha256sum "$KEY" | awk '{print $1}')"

        if [ "$restored_actual" != "$expected" ]; then
            echo "REFUSE: restored verifier public key digest mismatch" >&2
            exit 1
        fi

        echo "RESTORE: verifier public key preserved across package transition"
    fi

    rm -rf "$STASH_DIR"
fi

systemctl daemon-reload >/dev/null 2>&1 || true
systemctl enable arda-ring0.service >/dev/null 2>&1 || true
systemctl enable arda-ring0-verify.service >/dev/null 2>&1 || true

if [ -n "${2:-}" ]; then
cat <<'EOF'

ARDA Valinor upgraded.

The package transaction did not re-enroll this host, mint a new measured
generation, extend PCR11, or replace the provisioned verifier identity.

Existing enrolled hosts may verify current state with:

    sudo arda-grade

Run arda-enroll only for an intentional measured-generation transition.

EOF
else
cat <<'EOF'

ARDA Valinor installed.

No hardware enrollment has been performed.

Next:

    sudo arda-doctor
    sudo arda-enroll --dry-run

After reviewing the dry-run:

    sudo arda-enroll

EOF
fi

exit 0
POSTINST

chmod 0755 "$PKG/DEBIAN/postinst"

for script in \
  "$PKG/usr/bin/arda-enroll" \
  "$PKG/usr/bin/arda-attest" \
  "$PKG/usr/bin/arda-grade"
do
  sed -i \
    's|PY="${ARDA_PYTHON:-$REPO/.venv/bin/python}"|PY="${ARDA_PYTHON:-$(command -v python3)}"|' \
    "$script"
done

dpkg-deb --build --root-owner-group "$PKG" "$OUT"

echo
echo "=== BUILT ==="
echo "$OUT"

echo
echo "=== PACKAGE INFO ==="
dpkg-deb --info "$OUT"

echo
echo "=== PACKAGE CONTENTS ==="
dpkg-deb --contents "$OUT"
