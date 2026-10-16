import os
import sys
import subprocess
import asyncio
import time

def run_morgoth_gauntlet():
    # Force UTF-8 for terminal output
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("================================================================================")
    print(" [ARDA OS : MORGOTH MEGA GAUNTLET - ADVERSARIAL DENIAL BRIDGE] ")
    print("================================================================================")
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ["PYTHONPATH"] = root_dir
    sys.path.insert(0, root_dir)
    
    print(f"[BRIDGE] Root: {root_dir}")
    print("[BRIDGE] Setting PYTHONPATH for absolute self-contained imports.")
    
    # 1. Identify Adversarial Scripts
    script_dir = os.path.join(root_dir, "backend", "scripts")
    adversarial_scripts = [
        "e2e_morgoth_campaign.py",
        "e2e_adversarial_mega_gauntlet.py"
    ]
    
    print(f"[BRIDGE] Found {len(adversarial_scripts)} adversarial campaigns.")
    
    # 2. Execute
    print("\n--- [ACT] COMMENCING ADVERSARIAL SIEGE ---")
    
    for script_name in adversarial_scripts:
        script_path = os.path.join(script_dir, script_name)
        print(f"\n[GAUNTLET] Launching Attack: {script_name}")
        
        # Run using the current python interpreter to ensure environment consistency
        # We use a subprocess to cleanly isolate the async loops and telemetry instances
        ret = subprocess.run([sys.executable, script_path], 
                             cwd=root_dir, capture_output=False)
        
        if ret.returncode != 0:
             print(f"[ERROR] Campaign {script_name} failed with code {ret.returncode}")

    print("\n================================================================================")
    print("✅ ADVERSARIAL SIEGE CONCLUDED.")
    print("   Abominable Intelligence has been DENIED by Machine Law.")
    print("   Check 'backend/scripts/telemetry_logs/' for the full Denial Reports.")
    print("================================================================================")

if __name__ == "__main__":
    run_morgoth_gauntlet()
