#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
VERSION="${ARDA_PACKAGE_VERSION:-0.1.0}"
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
Depends: python3, python3-venv, openssl, rsync, systemd, tpm2-tools, mokutil, fsverity, bpftool
Description: ARDA Valinor hardware-rooted enrollment runtime
 Proof-governed Valinor host enrollment with measured identity,
 TPM attestation, manufacturer-rooted EK verification and signed grading.
EOF

TMP_TREE="$BUILD/tree"
mkdir -p "$TMP_TREE"

git -C "$ROOT" archive HEAD | tar -x -C "$TMP_TREE"

cp -a "$TMP_TREE/arda_os" "$PKG/usr/lib/arda/src/"
cp -a "$TMP_TREE/installer" "$PKG/usr/lib/arda/src/"


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
  "$TMP_TREE/installer/trust/verifier-key.pub.pem" \
  "$PKG/etc/arda/verifier/verifier-key.pub.pem"

install -m 0644 \
  "$TMP_TREE/installer/policy/constitutional-policy.json" \
  "$PKG/etc/arda/policy/constitutional-policy.json"

install -m 0644 \
  "$TMP_TREE/installer/policy/active_projection_plan.json" \
  "$PKG/etc/arda/policy/active_projection_plan.json"

install -m 0644 \
  "$TMP_TREE/installer/systemd/arda-postboot-grade.service" \
  "$PKG/lib/systemd/system/arda-postboot-grade.service"

cat > "$PKG/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e

mkdir -p \
  /etc/arda \
  /etc/arda/policy \
  /etc/arda/trust/intel-ek \
  /etc/arda/verifier \
  /var/lib/arda/enrollment

systemctl daemon-reload >/dev/null 2>&1 || true

cat <<'EOF'

ARDA Valinor installed.

No hardware enrollment has been performed.

Next:

    sudo arda-doctor
    sudo arda-enroll --dry-run

After reviewing the dry-run:

    sudo arda-enroll

EOF

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
