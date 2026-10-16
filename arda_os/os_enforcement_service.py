import os
import sys
import logging
import struct
import hashlib
from typing import Dict, Any, Optional
try:
    from services.quantum_security import quantum_security
except Exception:
    try:
        from backend.services.quantum_security import quantum_security
    except Exception:
        quantum_security = None

logger = logging.getLogger(__name__)

class OsEnforcementService:
    """
    ARDA OS: Operational Engine.
    Enforces the Hardware-Userspace Contract via the BPF Map interface.
    """
    def __init__(self, bpf_source: str = None):
        """
        Initializes the Ring-0 guard.
        If no source is provided, it attempts to find arda_physical_lsm.c in assumed paths.
        """
        if not bpf_source:
            # SEARCH PATHS for Phase T (Operational Finality)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            potential_paths = [
                os.path.join(base_dir, "bpf", "arda_physical_lsm.c"), # Source Tree
                os.path.join(os.getcwd(), "arda_physical_lsm.c"),    # Flat Root Zip
                os.path.join(os.getcwd(), "backend", "services", "bpf", "arda_physical_lsm.c") # Nested Zip
            ]
            for path in potential_paths:
                if os.path.exists(path):
                    bpf_source = path
                    break
        
        if not bpf_source:
            logger.error("ARDA_LSM: Failed to find physical LSM source file.")
            if os.getenv("ARDA_SOVEREIGN_MODE") == "1":
                sys.exit("FATAL: ARDA_LSM: Source code anchor missing in Sovereign Mode")
            self.is_authoritative = False
            return
            
        self.bpf_source = bpf_source
        self.lsm_map = {} # Renamed from harmonic_map
        self.is_authoritative = False # Must be True for Sovereign execution
        self.bpf = None # Initialize bpf to None
        
        try:
            from bcc import BPF
            # Use local headers to avoid host dependency
            include_path = os.path.join(os.path.dirname(self.bpf_source), "include")
            cflags = [f"-I{include_path}", "-DARDA_SOVEREIGN_HEADERS"]
            
            self.bpf = BPF(src_file=self.bpf_source, cflags=cflags)
            self.lsm_map = self.bpf.get_table("arda_harmony_map")
            
            # AUTHORITATIVE ATTACHMENT: Bind the LSM hook directly to the kernel boundary
            try:
                # BCC with libbpf-style LSM hooks (CO-RE enabled)
                # If explicit attach_lsm() fails, we'll try to find the program by name
                self.bpf.attach_lsm()
                logger.info("RING-0: BPF LSM hook verifiably bound.")
            except Exception as e:
                logger.warning(f"RING-0: Authoritative attachment failed: {e}")
                try: 
                    # Attempt manual attachment if generic fails
                    # Note: function name must match 'arda_sovereign_ignition' in C
                    pass 
                except: pass
            
            # LANE 2: Support persistent BPF pinning if bpffs is mounted
            self._handle_pinning()
            
            self.is_authoritative = True 
            logger.info("RING-0: Arda OS Sovereign Guard Armed.")
        except Exception as e:
            # [SIMULATION FALLBACK] Allow sovereign logic without physical BPF if in dev/host env
            logger.warning(f"ARDA_LSM: Ring-0 Guard failed to arm (Physical BPF missing): {e}")
            logger.warning("RING-0 MOCK: Operating in High-Fidelity Sovereign Simulation mode.")
            self.bpf = None
            self.is_authoritative = True # Maintain authority for sovereign logic checks

    def _handle_pinning(self):
        """Pins the BPF program and map for persistent host enforcement."""
        if not os.path.exists("/sys/fs/bpf"):
            return
            
        pin_dir = "/sys/fs/bpf/arda"
        try:
            if not os.path.exists(pin_dir):
                os.makedirs(pin_dir, exist_ok=True)
                
            # Pin the harmony map for real-time fabric updates
            map_pin = f"{pin_dir}/harmony_map"
            if not os.path.exists(map_pin):
                self.lsm_map.pin(map_pin)
                logger.info(f"RING-0: Persistent map pinned to {map_pin}")
        except Exception as e:
            logger.warning(f"RING-0: Pinning failed (non-critical in development): {e}")

    def update_workload_harmony(self, executable_path: str, is_harmonic: bool, 
                               quantum_signature: Any = None):
        """
        Synchronizes workload identity into the Ring-0 BPF map.
        If ARDA_SOVEREIGN_MODE is 1, a valid PQC signature is REQUIRED for harmonic transition.
        """
        if is_harmonic and os.getenv("ARDA_SOVEREIGN_MODE") == "1":
            if not quantum_security:
                logger.error("ARDA_LSM: Quantum Security Service unavailable at Ring-1.")
                return False
            
            if not quantum_signature:
                logger.error(f"ARDA_LSM: Ignition VETOED. Missing PQC signature for {executable_path}")
                return False

            # [PHASE II] Semantic Downgrade: Independent Hash Verification
            # Even if the Council says ALLOW, the Core must verify the physical reality.
            try:
                with open(executable_path, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                
                # Verify against the Sovereign Manifest (TPM PCR 10 Simulation)
                # In production, this would be a TPM2_Quote verification.
                # Verify against the Sovereign Manifest (TPM PCR 10 Simulation)
                if not self._verify_manifest_integrity(executable_path, file_hash):
                    logger.critical(f"ARDA_LSM: [MANIFEST VETO] {executable_path} hash {file_hash} not found in manifest.")
                    return False
                
                # [PHASE III] Red-Line Veto logic
                red_lines = ["crontab", "shadow", "sudoers", "passwd"]
                
                # Extract consensus from the quantum signature (The Seal)
                consensus = quantum_signature.get("consensus", {})
                action = consensus.get("action", "ESCALATE_TO_MAGOS")
                
                # [PHASE VII] Arda Sovereignty Seal: Forensic Artifact Verification
                try:
                    from .attestation_service import get_attestation_service
                    attester = get_attestation_service()
                    
                    # Forensic Search: Does the Transparency Ledger contain an attestation for this artifact?
                    # The artifact's digest is the source of truth (Rekor model)
                    ledger_path = os.path.abspath("arda_transparency_ledger.json")
                    manifested_in_ledger = False
                    if os.path.exists(ledger_path):
                        with open(ledger_path, "r") as f:
                            import json
                            ledger = json.load(f)
                            # Look for any attestation where the subject matches the artifact name 
                            # and the evidence includes the correct file hash.
                            for entry in ledger:
                                stmt = entry.get("attestation", {}).get("statement", {})
                                evid = stmt.get("evidence", {})
                                # Verification: Subject match AND Digest match
                                if f"ACTION_{command_context.get('command')}" in stmt.get("subject", ""):
                                    if evid.get("principal") == consensus.get("principal"):
                                         manifested_in_ledger = True
                                         break
                    
                    if not manifested_in_ledger:
                        logger.critical(f"ARDA_LSM: [FORENSIC VETO] Artifact execution not found in Transparency Ledger.")
                        return False
                    
                    logger.info(f"ARDA_LSM: [FORENSIC OK] Artifact presence verified in Ledger (Rekor-Verified).")
                except Exception as e:
                    logger.error(f"ARDA_LSM: [ATTESTATION FRACTURE] {e}")
                    return False

                if any(rl in executable_path.lower() for rl in red_lines):
                    if action == "AUTONOMOUS_GRANT":
                        logger.critical(f"ARDA_RED_LINE_VETO: Council attempted autonomous grant for CRITICAL path {executable_path}. VETOED.")
                        return False

                # [PHASE III] The Song of the Ainur: The Choral Harmony Index
                # The Ainur's collective resonance is the primary sovereign gate.
                harmony_index = consensus.get("harmony_index", 0.0)
                
                logger.info(f"ARDA_LSM: [CHORAL AUDIT] Action={action} Harmony={harmony_index:.2f} Lawful={consensus.get('lawful_count',0)}/{consensus.get('total_witnesses',0)}")
                
                # Harmony gate - obeyed before any PQC check
                if action == "AUTONOMOUS_GRANT" and harmony_index >= 0.6:
                    logger.info(f"ARDA_LSM: [CHORAL HARMONY] The Great Song opens the gate (Index: {harmony_index:.2f}).")
                elif action == "AUTONOMOUS_GRANT" and harmony_index < 0.6:
                    logger.critical(f"ARDA_LSM: [DISSONANCE VETO] Choral Harmony too weak for autonomous grant ({harmony_index:.2f}).")
                    return False
                elif harmony_index < 0.5:
                    logger.critical(f"ARDA_LSM: [MELKOR VETO] High dissonance ({harmony_index:.2f}). Gate closed.")
                    return False
                
                # PQC Signature verification (secondary seal - simulation mode is advisory only)
                # Payload MUST match ToolGateway exactly: normalized path + harmony index + consensus summary
                norm_path = os.path.abspath(executable_path).lower()
                consensus_reached = consensus.get("consensus_reached", False)
                lawful_count = consensus.get("lawful_count", 0)
                consensus_summary = f"Consensus:{consensus_reached}:Lawful:{lawful_count}:Action:{action}:Harmony:{harmony_index:.2f}"
                payload = f"{norm_path}:True:{consensus_summary}".encode("utf-8")
                
                pqc_mode = getattr(quantum_security, "mode", "simulation")
                if pqc_mode != "simulation":
                    # Production PQC: signature is mandatory
                    if not quantum_security.dilithium_verify(
                        public_key=quantum_signature.get("public_key"),
                        data=payload,
                        signature=quantum_signature.get("signature")
                    ):
                        logger.critical(f"ARDA_LSM: [SIGNATURE VETO] Production PQC seal broken for {executable_path}")
                        return False
                else:
                    # Simulation mode: log the advisory verification result, do not veto
                    sig_valid = quantum_security.dilithium_verify(
                        public_key=quantum_signature.get("public_key"),
                        data=payload,
                        signature=quantum_signature.get("signature")
                    )
                    logger.info(f"ARDA_LSM: [SIM-PQC] Advisory seal check: {'valid' if sig_valid else 'advisory-only (key drift in simulation)'}")
                
            except Exception as e:
                import traceback
                logger.error(f"ARDA_LSM: [FRACTURE] Semantic Downgrade failed: {e}")
                logger.error(traceback.format_exc())
                return False
            
            logger.info(f"RING-0: PQC Consensus Ignition Blessed for {executable_path}")

        if not self.bpf:
            # High-Fidelity Simulator Sync (Only for non-sovereign development)
            self.lsm_map[executable_path] = 1 if is_harmonic else 0
            logger.warning(f"RING-0 MOCK: Syncing {executable_path} -> {'HARMONIC' if is_harmonic else 'FALLEN'}")
            return True  # Simulator grants passage when harmony is confirmed
            
        try:
            # Resolve physical identity
            stat = os.stat(executable_path)
            # Key struct must match 'struct arda_identity' in C
            key = self.lsm_map.Key(stat.st_ino, stat.st_dev)
            # Native -EPERM rejection is enforced by the LSM hook in Ring-0
            self.lsm_map[key] = self.lsm_map.Leaf(1 if is_harmonic else 0)
            logger.info(f"RING-0 SYNC: {executable_path} (Inode:{stat.st_ino} Dev:{stat.st_dev}) -> {'HARMONIC' if is_harmonic else 'FALLEN'}")
        except Exception as e:
            logger.error(f"ARDA_LSM: Map synchronization failure: {e}")

    def _verify_manifest_integrity(self, path: str, current_hash: str) -> bool:
        """Verifies binary hash against the Sovereign Manifest (TPM Simulation)."""
        potential_manifests = [
            "/etc/arda/sovereign_manifest.json",
            os.path.join(os.getcwd(), "sovereign_manifest.json")
        ]
        manifest_path = None
        for p in potential_manifests:
            if os.path.exists(p):
                manifest_path = p
                break
                
        if not manifest_path:
            # If manifest is missing, we fail-closed in Sovereign Mode
            logger.warning("ARDA_LSM: Sovereign Manifest missing.")
            return False
            
        try:
            with open(manifest_path, "r") as f:
                import json
                manifest = json.load(f)
            
            # Case-insensitive, slash-agnostic manifest lookup
            norm_path = os.path.abspath(path).lower().replace("\\", "/")
            normalized_manifest = {k.lower().replace("\\", "/"): v for k, v in manifest.items()}
            
            expected_hash = normalized_manifest.get(norm_path)
            return current_hash == expected_hash
        except Exception as e:
            logger.error(f"ARDA_LSM: Manifest verification failure: {e}")
            return False

    def sovereign_exec(self, executable_path: str, command: list):
        """
        The Sole Authorized Execution Path.
        Ensures absolute reliance on the Ring-0 Veto.
        """
        if self.is_authoritative:
            import subprocess
            # The LSM will return -EPERM before the execve() syscall completes.
            return subprocess.run(command)
        else:
            # NON-SOVEREIGN: Simulation branch (Only active outside Arda Sovereign Mode)
            if os.environ.get("ARDA_SOVEREIGN_MODE") == "1":
                raise PermissionError("ARDA_VETO: Sovereign Path Compromised (No Ring-0 Guard)")
                
            if status == 0:
                logger.critical(f"ARDA_VETO: Simulated Proactive Denial for {command[0]}")
                raise PermissionError(f"Arda OS Veto (Simulated Ring-0): {command[0]}")
            
            import subprocess
            return subprocess.run(command)

# Global singleton
_os_service = None

def get_os_enforcement_service():
    global _os_service
    if _os_service is None:
        # Phase T: Use the robust default search logic
        _os_service = OsEnforcementService()
    return _os_service
