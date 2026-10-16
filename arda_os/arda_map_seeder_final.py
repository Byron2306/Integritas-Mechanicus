import subprocess
import json
import struct
import sys
import argparse

def get_map_id(name):
    try:
        output = subprocess.check_output(['sudo', 'bpftool', 'map', 'show', '-j'], text=True)
        maps = json.loads(output)
        for m in maps:
            m_name = m.get('name', '')
            if m_name.startswith(name):
                return m['id']
    except Exception as e:
        print(f"Error finding map: {e}")
    return None

def seed(json_file, verify_only=False):
    map_id = get_map_id("arda_harmony")
    if not map_id:
        print("ERROR: arda_harmony map not found.")
        sys.exit(1)

    if verify_only:
        output = subprocess.check_output(['sudo', 'bpftool', 'map', 'dump', 'id', str(map_id), '-j'], text=True)
        data = json.loads(output)
        if not data:
            print("VERIFICATION FAILURE: Map empty.")
            sys.exit(1)
        print(f"VERIFICATION SUCCESS: Map has {len(data)} entries.")
        return

    with open(json_file, 'r') as f:
        identities = json.load(f)

    print(f"Seeding {len(identities)} identities into map {map_id}...")
    success_count = 0
    for entry in identities:
        key_bytes = struct.pack('<QLI', entry['inode'], entry['dev'], 0)
        # Use simpler hex string without spaces if possible, or try standard bpftool format
        key_hex = " ".join(f"{b:02x}" for b in key_bytes)
        val_bytes = struct.pack('<I', 1)
        val_hex = " ".join(f"{b:02x}" for b in val_bytes)
        
        cmd = ['sudo', 'bpftool', 'map', 'update', 'id', str(map_id), 'key'] + key_hex.split() + ['value'] + val_hex.split()
        try:
            subprocess.check_call(cmd)
            success_count += 1
        except Exception as e:
            print(f"Failed to seed inode {entry['inode']}: {e}")

    print(f"Successfully seeded {success_count}/{len(identities)} identities.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-file")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    seed(args.json_file, args.verify)
