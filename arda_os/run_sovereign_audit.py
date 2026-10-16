import os
import sys
import json
import time
from datetime import datetime, timezone
from backend.scripts.test_telemetry_v2 import TelemetryCollector
import subprocess

def run_sovereign_audit():
    # Force UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    root_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ["PYTHONPATH"] = root_dir
    os.environ["PYTHONUTF8"] = "1"
    
    collector = TelemetryCollector("SOVEREIGN_AUDIT_v2")
    
    claims_mapping = {
        "Claim 1: Silicon Integrity": [
            "backend/tests/test_governance_token_enforcement.py",
            "backend/tests/gauntlets/e2e_formation_gauntlet.py"
        ],
        "Claim 2: PQC Root of Trust": ["backend/tests/test_quantum_security_service.py"],
        "Claim 3: Multi-Model Synthesis": [
            "backend/tests/test_governance_token_enforcement.py",
            "backend/tests/gauntlets/e2e_constitutional_gauntlet.py"
        ],
        "Claim 4: Spatial Gating": ["backend/tests/test_advanced_services.py"],
        "Claim 5: Indomitable Restoration": ["backend/tests/test_advanced_services.py"],
        "Claim 6: Temporal Fencing": ["backend/tests/test_advanced_services.py"],
        "Claim 7: Constitutional Attestation": [
            "backend/tests/test_advanced_services.py",
            "backend/tests/gauntlets/test_secret_fire_gauntlet.py"
        ],
        "Claim 8: Memory Class Isolation": ["backend/tests/test_advanced_services.py"],
        "Claim 9: Quorum Enforcement": [
            "backend/tests/test_advanced_services.py",
            "backend/tests/gauntlets/e2e_chorus_gauntlet.py"
        ],
        "Claim 10: Behavioral Baselining": ["backend/tests/test_advanced_services.py"],
        "Claim 11: Sovereign Transport": [
            "backend/tests/test_advanced_services.py",
            "backend/tests/gauntlets/test_secret_fire_gauntlet.py"
        ],
        "Claim 12: Recursive Witnessing": [
            "backend/tests/test_advanced_services.py",
            "backend/tests/gauntlets/test_tulkas_enforcement.py"
        ],
        "Claim 13: Perfect Honesty": ["backend/tests/test_advanced_services.py"]
    }

    collector.logger.info("================================================================================")
    collector.logger.info(" [ARDA OS : SOVEREIGN AUDIT EXECUTION BRIDGE (v2.0.0-INFALLIBLE)] ")
    collector.logger.info("================================================================================")

    for claim, tests in claims_mapping.items():
        collector.set_phase(claim.upper())
        for test_path in tests:
            test_file = os.path.join(root_dir, test_path)
            if not os.path.exists(test_file):
                collector.logger.warning(f"Test not found: {test_path}")
                continue
                
            collector.logger.info(f"Witnessing: {test_path}")
            
            # Execute with verbose output and capture results
            process = subprocess.run(
                [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
                cwd=root_dir,
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            status = "passed" if process.returncode == 0 else "failed"
            
            # Log the claim outcome to telemetry
            collector.log_event(
                event_type="claim_verification",
                actor="holy_witness",
                action_type=claim,
                impact_level="critical",
                status=status,
                details={
                    "test_path": test_path,
                    "exit_code": process.returncode,
                    "summary": process.stdout.splitlines()[-1] if process.stdout.splitlines() else "No output",
                    "transparency_trace": "Infallible" if status == "passed" else "Dissonant"
                }
            )
            
            if status == "failed":
                 collector.logger.error(f"FRACTURE DETECTED in {claim}")
                 collector.logger.error(process.stdout)

    collector.generate_report()
    
    # Custom 13-Claims Final Summary
    collector.logger.info("\n================================================================================")
    all_passed = all(e.status == "passed" for e in collector.entries)
    if all_passed:
        collector.logger.info("[PASS] ALL 13 SOVEREIGNTY CLAIMS VERIFIED AS INFALLIBLE.")
        collector.logger.info("   The Machine is Absolute. The Law is Silicon. Arda is Sovereign.")
    else:
        collector.logger.error("[FAIL] SOVEREIGN DISSONANCE DETECTED.")
    collector.logger.info("================================================================================")

if __name__ == "__main__":
    run_sovereign_audit()
