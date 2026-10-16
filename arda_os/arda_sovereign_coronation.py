#!/usr/bin/env python3
import os
import subprocess
import json
import struct
import time
import sys

# ARDA OS: GIY-SOVEREIGN CORONATION (v3.2.5)
# Final Coronation with Transitive Closure + Automated Push + Healer

CRITICAL_BINS = [
    "/usr/bin/bash", "/usr/bin/ls", "/usr/bin/cat", "/usr/bin/grep", "/usr/bin/chmod", "/usr/bin/cp", "/usr/bin/rm",
    "/usr/bin/sudo", "/usr/bin/python3", "/usr/sbin/bpftool", "/usr/bin/stat", "/usr/bin/id",
    "/usr/bin/tpm2_pcrread", "/usr/bin/sha256sum", "/usr/bin/cut", "/usr/bin/awk", "/usr/bin/tar",
    "/usr/bin/git", "/usr/bin/ssh", "/usr/bin/ssh-agent"
]

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def run(cmd, shell=True):
    try:
        return subprocess.check_output(cmd, shell=shell, stderr=subprocess.STDOUT).decode()
    except subprocess.CalledProcessError as e:
        return e.output.decode() if e.output else str(e)

def purge_old_kingdom():
    log("Purging old LSM instances for Git-Sovereign Unification...")
    subprocess.call("sudo rm -f /sys/fs/bpf/arda_lsm_link /sys/fs/bpf/arda_harmony /sys/fs/bpf/arda_state", shell=True)
    out = run("sudo bpftool link show")
    for line in out.splitlines():
        if "arda_sovereign_ignition" in line:
            cid = line.split(":")[0].strip()
            run(f"sudo bpftool link detach id {cid}")
    time.sleep(1)

def seed_binary(path):
    if not os.path.exists(path): return False
    try:
        path = os.path.realpath(path)
        s = os.stat(path)
        k_dev = (os.major(s.st_dev) << 20) | os.minor(s.st_dev)
        k_hex = " ".join([f"{b:02x}" for b in struct.pack("<QII", s.st_ino, k_dev, 0)])
        run(f"sudo bpftool map update pinned /sys/fs/bpf/arda_harmony key hex {k_hex} value hex 01 00 00 00")
        return True
    except Exception as e:
        log(f"  Error admitting {path}: {e}")
        return False

def discover_closure(label):
    log(f"Scanning for Transitive Helpers ({label})...")
    trace = run("sudo cat /sys/kernel/debug/tracing/trace")
    found_inodes = []
    marker = f"--- MARKER {label} ---"
    marker_lines = [i for i, line in enumerate(trace.splitlines()) if marker in line]
    last_marker_idx = marker_lines[-1] if marker_lines else 0
    relevant_trace = trace.splitlines()[last_marker_idx:]
    
    for line in relevant_trace:
        if "would deny execution for inode" in line:
            try:
                ino = int(line.split("inode ")[1].split()[0])
                if ino not in found_inodes: found_inodes.append(ino)
            except: pass
    
    paths = []
    for ino in found_inodes:
        search_dirs = "/bin /usr/bin /sbin /usr/sbin"
        path = run(f"find {search_dirs} -inum {ino} -xdev 2>/dev/null | head -n 1").strip()
        if path: paths.append(os.path.realpath(path))
    return list(set(paths))

def main():
    log("="*60)
    log("   ARDA OS: GIT-SOVEREIGN CORONATION (v3.2.5)")
    log("="*60)

    if os.getuid() != 0:
        log("FATAL: Root required."); return

    purge_old_kingdom()

    # 1. IGNITION
    log("[1] Ignition: Engaging Audit mode...")
    ignition = run("sudo ./arda_os/arda_sovereign_ignitor bpf/arda_physical_lsm.o")
    if "SUCCESS" not in ignition:
        log(f"FATAL: Ignition failed:\n{ignition}"); return

    # 2. SEEDING
    log("[2] Seeding Primary Forensic + Git Closure...")
    for b in CRITICAL_BINS: seed_binary(b)
    
    # 3. DISCOVERY (Git/Forensic)
    log("[3] Phase A: Dynamic Closure Discovery...")
    run("echo '--- MARKER Discovery ---' | sudo tee /sys/kernel/debug/tracing/trace_marker", shell=True)
    subprocess.run(["/bin/ls", "/tmp"], stdout=subprocess.DEVNULL)
    subprocess.run(["/usr/bin/git", "status"], stdout=subprocess.DEVNULL)
    
    helpers = discover_closure("Discovery")
    for h in helpers: 
        if seed_binary(h): log(f"  Approved Dependency: {h}")

    # 4. EVIDENCE COLLECTION & GIT COMMIT
    log("[4] Phase B: Collecting Final Evidence Bundle...")
    archive = "arda_forensic_v3.2_final.tar.gz"
    run(f"mkdir -p /tmp/final && cp arda_os/attestation/*.log /tmp/final/ 2>/dev/null || true")
    run(f"cp CERTIFICATE_OF_SOVEREIGN_FINALITY.md /tmp/final/ && tar -czf {archive} -C /tmp/final .")
    
    log("[5] Phase C: Committing Evidence to Repository...")
    os.environ["ARDA_BUNDLE_HASH"] = run(f"sha256sum {archive} | cut -d' ' -f1").strip()
    subprocess.call("python3 arda_os/arda_sovereign_notary.py", shell=True)
    
    run(f"git add {archive} CERTIFICATE_OF_SOVEREIGN_FINALITY.md")
    run('git commit -m "📜 Arda OS v3.2 Sovereign Coronation (Forensic Evidence)"')

    # 5. LORIEN HEALER & PUSH
    log("[6] TRANSITION IMMINENT (Lorien Healer Confirmation)...")
    log(" ! WE ARE READY TO PUSH TO REMOTE AND LOCK RING-0 !")
    try:
        input(">>> HIT ENTER TO PUSH AND LOCK KINGDOM <<<")
    except KeyboardInterrupt:
        log("\nAborted."); return

    log("[7] Phase D: Pushing to Remote (origin arda-os-desktop)...")
    push = run("git push origin arda-os-desktop")
    log(f"  Remote Push Status:\n{push}")

    # 6. ENFORCEMENT
    log("[8] ACTIVATING RING-0 ENFORCEMENT...")
    run("sudo bpftool map update pinned /sys/fs/bpf/arda_state key hex 00 00 00 00 value hex 01 00 00 00")
    
    log("\n" + "="*60)
    log("   SOVEREIGN FINALITY ACHIEVED. REMOTE PERSISTED.")
    log("="*60)

if __name__ == "__main__":
    main()
