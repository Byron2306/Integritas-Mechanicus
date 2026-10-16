import os
import sys
import subprocess
import pytest

def run_sanctified_witness():
    # Force UTF-8 for terminal output (Absolute Compatibility)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    
    print("================================================================================")
    print(" [ARDA OS : UNIVERSAL SANCTITY EXECUTION BRIDGE (v1.80.0)] ")
    print("================================================================================")
    
    # 1. Set PYTHONPATH to include the bundle root
    # This ensures "import backend.services..." works
    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ["PYTHONPATH"] = root_dir
    sys.path.insert(0, root_dir)
    
    print(f"[BRIDGE] Root: {root_dir}")
    print("[BRIDGE] Setting PYTHONPATH for absolute self-contained imports.")
    
    # 2. Identify Witness Tests
    test_dir = os.path.join(root_dir, "backend", "tests")
    witness_tests = [
        os.path.join(test_dir, "test_quantum_security_service.py"),
        os.path.join(test_dir, "test_harmonic_engine_cadence.py"),
        os.path.join(test_dir, "test_governance_token_enforcement.py")
    ]
    
    print(f"[BRIDGE] Found {len(witness_tests)} forensic witnesses.")
    
    # 3. Execute
    print("\n--- [ACT] EXECUTION OF SACRED WITNESSES ---")
    
    results = []
    for test in witness_tests:
        print(f"\n[WITNESS] Executing: {os.path.basename(test)}")
        # Run using the current python interpreter to ensure environment consistency
        ret = subprocess.run([sys.executable, "-m", "pytest", test, "-v", "--tb=short"], 
                             cwd=root_dir, capture_output=False)
        results.append(ret.returncode == 0)
    
    print("\n================================================================================")
    if all(results):
         print("✅ THE WITNESSES HAVE SPOKEN: ARDA OS IS SOVEREIGN.")
         print("   Universal sanctity verified in absolute silicon.")
    else:
         print("❌ THE FRACTURE REMAINS: ONE OR MORE WITNESSES FAILED.")
         print("   Check logs for dissonance.")
    print("================================================================================")

if __name__ == "__main__":
    run_sanctified_witness()
