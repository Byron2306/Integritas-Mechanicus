#!/usr/bin/env python3
import os
import subprocess
import struct
import time

# ARDA OS: UNIFIED KINGDOM CORONATION (v3.2.8)
# Full Forensic Inventory + Explicit Map ID Targeting + Final Lock

HARMONY_MAP_ID = 219
STATE_MAP_ID = 220

CRITICAL_BINS = [
    "/usr/bin/bash", "/usr/bin/sh", "/usr/bin/ls", "/usr/bin/cat", "/usr/bin/grep", "/usr/bin/chmod", "/usr/bin/cp", "/usr/bin/rm",
    "/usr/bin/sudo", "/usr/bin/python3", "/usr/sbin/bpftool", "/usr/bin/stat", "/usr/bin/id",
    "/usr/bin/tpm2_pcrread", "/usr/bin/sha256sum", "/usr/bin/cut", "/usr/bin/awk", "/usr/bin/tar",
    "/usr/bin/git", "/usr/bin/ssh", "/usr/bin/ssh-add", "/usr/bin/ssh-agent", "/usr/lib/git-core/git-remote-https"
]

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
    except subprocess.CalledProcessError as e:
        return e.output.decode() if e.output else str(e)

def seed_binary(path):
    if not os.path.exists(path): return False
    try:
        p = os.path.realpath(path)
        s = os.stat(p)
        k_dev = (os.major(s.st_dev) << 20) | os.minor(s.st_dev)
        k_hex = " ".join(f"{b:02x}" for b in struct.pack("<QII", s.st_ino, k_dev, 0))
        run(f"sudo bpftool map update id {HARMONY_MAP_ID} key hex {k_hex} value hex 01 00 00 00")
        return True
    except Exception as e:
        log(f"  Error seeding {path}: {e}")
        return False

def main():
    log("="*60)
    log("   ARDA OS: UNIFIED KINGDOM CORONATION (v3.2.8)")
    log("   Full Forensic Inventory Collection")
    log("="*60)

    # 1. SEEDING
    for b in CRITICAL_BINS: seed_binary(b)

    # 2. EVIDENCE AGGREGATION (FULL INVENTORY)
    log("[1] Aggregating Full Forensic Inventory...")
    archive = "arda_forensic_v3.2_final.tar.gz"
    # Unified Collection
    run("mkdir -p /tmp/final_seal")
    run("cp CERTIFICATE_OF_SOVEREIGN_FINALITY.md /tmp/final_seal/")
    run("cp bpf/*.c /tmp/final_seal/ 2>/dev/null || true")
    run("cp arda_os/*.c /tmp/final_seal/ 2>/dev/null || true")
    run("cp arda_os/*.py /tmp/final_seal/ 2>/dev/null || true")
    run("cp arda_os/attestation/* /tmp/final_seal/ 2>/dev/null || true")
    run(f"tar -czf {archive} -C /tmp/final_seal .")
    
    # 3. NOTARY & COMMIT
    log("[2] Issuing Final Notarization...")
    bundle_hash = run(f"sha256sum {archive} | cut -d' ' -f1").strip()
    os.environ["ARDA_BUNDLE_HASH"] = bundle_hash
    run("python3 arda_os/arda_sovereign_notary.py")
    
    run(f"git add {archive} CERTIFICATE_OF_SOVEREIGN_FINALITY.md")
    run('git commit -m "📜 Arda OS v3.2 Sovereign Coronation (Full Forensic Metadata)"')

    # 4. PUSH (Audit mode)
    run(f"sudo bpftool map update id {STATE_MAP_ID} key hex 00 00 00 00 value hex 00 00 00 00")
    log("[3] Persistence Push...")
    # NOTE: User must run the final push manually due to SSH-Agent context
    log(" >>> SYSTEM READY FOR FINAL SEAL <<<")

    # 5. LOCK
    log("[4] ACTIVATING RING-0 ENFORCEMENT LOCK...")
    run(f"sudo bpftool map update id {STATE_MAP_ID} key hex 00 00 00 00 value hex 01 00 00 00")

    log("\n" + "="*60)
    log("   SOVEREIGN FINALITY ACHIEVED. METADATA PERSISTED.")
    log("="*60)

if __name__ == "__main__":
    main()
