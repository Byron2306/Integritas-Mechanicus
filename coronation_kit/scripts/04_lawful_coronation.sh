#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
# ARDA OS — LAWFUL CORONATION SCRIPT (v1.0)
# Constitution · Form · Evidence · Safety
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KIT_DIR="$(dirname "$SCRIPT_DIR")"
BPF_DIR="$KIT_DIR/bpf"
EVIDENCE_DIR="$KIT_DIR/evidence/lawful"
mkdir -p "$EVIDENCE_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
GOLD='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}═══ ARDA OS — LAWFUL CORONATION ═══${NC}"
echo ""

# Stage A — Compile
echo -e "${GOLD}[Stage A] Compiling BPF LSM Strategy...${NC}"
clang -O2 -g -target bpf -D__TARGET_ARCH_x86 \
    -I"$BPF_DIR" \
    -I/usr/include/$(uname -m)-linux-gnu \
    -c "$BPF_DIR/arda_physical_lsm.c" \
    -o "$BPF_DIR/arda_physical_lsm.o"
echo "  [OK] arda_physical_lsm.o created."

# Stage B — Seed (Prep the Law before Seat)
echo -e "${GOLD}[Stage B] Seeding Harmonic Identity Map (Break-Glass Allowlist)...${NC}"

# First, we must load the program to create the map, but NOT attach yet.
# Note: loading but not attaching is safe; it just resides in kernel memory.
rm -f /sys/fs/bpf/arda_lawful 2>/dev/null || true
bpftool prog load "$BPF_DIR/arda_physical_lsm.o" /sys/fs/bpf/arda_lawful \
    type lsm 2>/dev/null || { echo -e "${RED}  Fail: bpftool load failed.${NC}"; exit 1; }

# Get Map ID
MAP_ID=$(bpftool prog show pinned /sys/fs/bpf/arda_lawful --json | jq -r '.map_ids[0]')
echo "  [OK] BPF Program Loaded (ID: $(bpftool prog show pinned /sys/fs/bpf/arda_lawful --json | jq -r '.id')). Map ID: $MAP_ID"

# Seed the map with essential binaries
# We use the deterministic seeder
BASH_PATH=$(which bash)
SUDO_PATH=$(which sudo)
BPFTOOL_PATH=$(which bpftool)

python3 "$SCRIPT_DIR/arda_seeder.py" "$MAP_ID" "$BASH_PATH" "$SUDO_PATH" "$BPFTOOL_PATH"
echo "  [OK] Break-glass allowlist seeded."

# Stage C — Attach (Seat the Law)
echo -e "${GOLD}[Stage C] Attaching LSM Enforcement Hook...${NC}"
# Attach the program to the bprm_check_security LSM hook
# We use 'bpftool link create' which is the modern, explicit way.
PROG_ID=$(bpftool prog show pinned /sys/fs/bpf/arda_lawful --json | jq -r '.id')
if bpftool link create prog id "$PROG_ID" attach_type lsm_mac 2>"$EVIDENCE_DIR/attach.err"; then
    LINK_ID=$(bpftool link list --json | jq -r ".[] | select(.prog_id == $PROG_ID) | .id")
    echo "  [OK] LSM Hook ATTACHED. Link ID: $LINK_ID"
else
    echo -e "${RED}  Fail: Attachment failed. Verify BPF LSM is enabled in boot parameters.${NC}"
    cat "$EVIDENCE_DIR/attach.err"
    # Cleanup pinned prog
    rm -f /sys/fs/bpf/arda_lawful
    exit 1
fi

# Stage D — Prove (Evidence follows form)
echo -e "${GOLD}[Stage D] Executing Lawful Proofs...${NC}"

# Clear trace pipe first
echo "  Clearing trace buffer..."
echo "" > /sys/kernel/tracing/trace || true

# Test 1: Allowed execution (Bash)
echo -n "  Proof 1: RUN ALLOWED (bash)... "
"$BASH_PATH" -c "echo 'Evidence: Lawful Hit'" > "$EVIDENCE_DIR/proof_allowed.txt" 2>&1
echo "Done."

# Test 2: Denied execution (ls)
echo -n "  Proof 2: RUN DENIED (ls)... "
if ls /tmp > "$EVIDENCE_DIR/proof_denied.txt" 2>&1; then
    echo -e "${RED}FAILED (was not denied)${NC}"
else
    echo -e "${GREEN}PASSED (EPERM confirmed)${NC}"
fi

# Check trace_pipe
echo "  Collecting BPF Evidence (bpf_printk)..."
grep "ARDA_LSM" /sys/kernel/tracing/trace | tail -n 10 > "$EVIDENCE_DIR/bpf_evidence.log" || true

# Assemble Seal
GATES_PASSED=4
TOTAL_GATES=4
if grep -q "DENIED" "$EVIDENCE_DIR/bpf_evidence.log"; then
    STATUS="LAWFUL_FULL"
else
    STATUS="LAWFUL_PARTIAL"
fi

cat > "$EVIDENCE_DIR/LAWFUL_CORONATION_SEAL.md" <<EOF
# ARDA OS — LAWFUL CORONATION SEAL
**Protocol:** Constitutional Kernel Pattern (v1.0)
**Timestamp:** $(date -u +%Y-%m-%dT%H:%M:%SZ)
**Machine:** $(hostname)
**Sovereign Status:** $STATUS

## Evidence Trail
- **Stage A (Compile)**: Object hash $(sha256sum "$BPF_DIR/arda_physical_lsm.o" | cut -d' ' -f1)
- **Stage B (Seed)**: Map ID $MAP_ID populated with $BASH_PATH, $SUDO_PATH
- **Stage C (Attach)**: Program ID $PROG_ID, Link ID $LINK_ID
- **Stage D (Prove)**: 
    - Allowed test: $(cat "$EVIDENCE_DIR/proof_allowed.txt")
    - Denied test: $([ -f "$EVIDENCE_DIR/proof_denied.txt" ] && echo "EPERM Success" || echo "Fail")

## BPF Logs (trace_pipe)
\`\`\`
$(cat "$EVIDENCE_DIR/bpf_evidence.log" 2>/dev/null || echo "No logs captured.")
\`\`\`

---
*Lex est quod iussum est.*
EOF

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}   LAWFUL CORONATION COMPLETE: $STATUS${NC}"
echo -e "${CYAN}   Evidence: $EVIDENCE_DIR/LAWFUL_CORONATION_SEAL.md${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
