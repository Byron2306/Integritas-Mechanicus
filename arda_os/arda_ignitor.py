import subprocess
import os
import struct
import json
import sys

BPF_OBJ = "bpf/arda_physical_lsm.o"
BPF_PIN = "/sys/fs/bpf/arda_lsm"
MAP_PIN_DIR = "/sys/fs/bpf/arda_maps"

def run(cmd):
    return subprocess.check_output(cmd, text=True)

def setup():
    print("--- Arda OS: Consolidated Ignition ---")
    run(["clang", "-O2", "-g", "-target", "bpf", "-D__TARGET_ARCH_x86", "-c", "bpf/arda_physical_lsm.c", "-o", BPF_OBJ])
    subprocess.call(["sudo", "rm", "-rf", BPF_PIN])
    subprocess.call(["sudo", "rm", "-rf", MAP_PIN_DIR])
    os.makedirs(MAP_PIN_DIR, exist_ok=True)
    try:
        subprocess.call(["sudo", "mount", "-t", "bpf", "bpf", MAP_PIN_DIR])
    except:
        pass
    run(["sudo", "bpftool", "prog", "load", BPF_OBJ, BPF_PIN, "type", "lsm"])
    output = run(["sudo", "bpftool", "prog", "show", "pinned", BPF_PIN, "-j"])
    prog_info = json.loads(output)
    map_ids = prog_info.get("map_ids", [])
    for mid in map_ids:
        m_info = json.loads(run(["sudo", "bpftool", "map", "show", "id", str(mid), "-j"]))
        m_name = m_info.get("name")
        if m_name and ("arda_harmony" in m_name or "arda_state" in m_name):
            clean_name = "arda_harmony" if "harmony" in m_name else "arda_state"
            pin_path = os.path.join(MAP_PIN_DIR, clean_name)
            run(["sudo", "bpftool", "map", "pin", "id", str(mid), pin_path])

def seed():
    print("[Seeding Harmony (Decimal)...]")
    identities_json = run(["python3", "arda_os/backend/services/arda_seeder.py", "--tier", "critical"])
    identities = json.loads(identities_json)
    harmony_path = os.path.join(MAP_PIN_DIR, "arda_harmony")
    for entry in identities:
        key_bytes = struct.pack('<QLI', entry['inode'], entry['dev'], 0)
        # CONVERT TO DECIMAL STRINGS
        key_dec = [str(b) for b in key_bytes]
        val_bytes = struct.pack('<I', 1)
        val_dec = [str(b) for b in val_bytes]
        try:
            subprocess.check_call(["sudo", "bpftool", "map", "update", "pinned", harmony_path, "key"] + key_dec + ["value"] + val_dec)
        except Exception as e:
            print(f"Failed to seed {entry['path']}: {e}")

def enforce(active=True):
    val = "1" if active else "0"
    print(f"[Setting Enforcement to {val}...]")
    state_path = os.path.join(MAP_PIN_DIR, "arda_state")
    if os.path.exists(state_path):
        subprocess.check_call(["sudo", "bpftool", "map", "update", "pinned", state_path, "key", "0", "0", "0", "0", "value", val, "0", "0", "0"])
        print("Done.")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--disable":
        enforce(False)
    else:
        setup()
        seed()
        enforce(True)
