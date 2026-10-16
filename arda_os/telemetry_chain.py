"""
Tamper-Evident Telemetry Service
================================
Signed telemetry envelopes, merkle/hash chains, and OpenTelemetry-style tracing.
Prevents "log rewriting" attacks and provides court-admissible audit trails.
"""

import os
import json
import hashlib
import hmac
import base64
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict, field
from collections import deque
import uuid
import asyncio
import threading
import time
from backend.services.tpm_attestation_service import get_tpm_service
from backend.services.flame_imperishable import get_flame_imperishable_service

try:
    from services.world_events import emit_world_event
except Exception:
    try:
        from backend.services.world_events import emit_world_event
    except Exception:
        emit_world_event = None

logger = logging.getLogger(__name__)


@dataclass
class SignedEvent:
    """Tamper-evident signed event envelope"""
    event_id: str
    event_type: str
    severity: str
    timestamp: str
    agent_id: str
    hostname: Optional[str]
    data: Dict[str, Any]
    
    # Integrity fields
    signature: str              # HMAC signature from agent
    prev_hash: str              # Hash of previous event (chain)
    event_hash: str             # Hash of this event
    
    # Provenance
    source: str                 # "agent" / "server" / "operator"
    trace_id: str               # OpenTelemetry-style trace ID
    span_id: str                # Span ID for action tracing
    parent_span_id: Optional[str] = None


@dataclass 
class AuditRecord:
    """Audit record for actions taken"""
    record_id: str
    timestamp: str
    
    # Who
    principal: str              # agent:{id} / operator:{user} / service:{name}
    principal_trust_state: str
    
    # What
    action: str
    tool_id: Optional[str]
    targets: List[str]
    
    # Why
    case_id: Optional[str]
    evidence_refs: List[str]
    policy_decision_hash: str
    policy_decision_id: str
    governance_decision_id: str
    governance_queue_id: str
    
    # How
    token_id: str               # Capability token used
    execution_id: str
    trace_id: str
    constraints: Dict[str, Any]
    
    # Result
    result: str                 # success / failed / denied
    result_details: Optional[str]
    output_artifact_ids: List[str]
    
    # Chain
    prev_hash: str
    record_hash: str


class TamperEvidentTelemetry:
    """
    Tamper-evident telemetry storage with hash chains.
    
    Features:
    - Signed event envelopes (agent signs, server verifies)
    - Append-only hash chain (merkle-style)
    - OpenTelemetry-style action tracing
    - Court-admissible audit trail
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        
        # Configuration
        self.signing_key = os.environ.get('TELEMETRY_SIGNING_KEY', 'default-key-change-me')
        
        # Event chain (in production, use append-only DB/object store)
        self.event_chain: deque = deque(maxlen=100000)
        self.audit_chain: deque = deque(maxlen=50000)
        
        # Genesis hashes
        self.genesis_event_hash = hashlib.sha256(b"SERAPH_GENESIS_EVENT").hexdigest()
        self.genesis_audit_hash = hashlib.sha256(b"SERAPH_GENESIS_AUDIT").hexdigest()
        
        # Current chain heads
        self.current_event_hash = self.genesis_event_hash
        self.current_audit_hash = self.genesis_audit_hash
        
        # Trace context
        self.active_traces: Dict[str, Dict] = {}
        self.edge_observation_index: Dict[str, Dict[str, Any]] = {}
        
        # Silmaril Crystallization State
        self.last_crystallized_at = time.time()
        self.crystallization_interval = float(os.environ.get('SILMARIL_INTERVAL', 300)) # 5 mins
        self.last_crystallized_hash = self.genesis_event_hash
        self.flame_service = get_flame_imperishable_service()
        self.secrets_ready = threading.Event()
        
        # Start background helper for crystallization
        self._start_crystallizer()
        
        logger.info("Tamper-Evident Telemetry Service initialized with Silmaril Crystallization")

    def _start_crystallizer(self):
        """Starts the background thread for periodic chain crystallization."""
        def _loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 1. Initialize Flame Imperishable (Hardware-sealed secrets)
            loop.run_until_complete(self.initialize_secrets())
            
            # 2. Enter periodic crystallization loop
            loop.run_until_complete(self._background_crystallizer())
            
        threading.Thread(target=_loop, daemon=True).start()

    async def initialize_secrets(self):
        """Initializes the Flame Imperishable (Sealed Signing Key) from TPM."""
        logger.info("PHASE VI: Telemetry Chain: Unsealing Secret Fire...")
        try:
            unsealed_key = await self.flame_service.initialize_flame()
            if unsealed_key:
                self.signing_key = unsealed_key
                logger.info("PHASE VI: Secret Fire unsealed. Hardware-backed signing ACTIVE.")
        except Exception as e:
            logger.error(f"PHASE VI: Secret Fire unsealing FAILED: {e}")
        finally:
            self.secrets_ready.set()

    async def _background_crystallizer(self):
        """Periodically anchors the chain to hardware (Silmaril Crystallization)."""
        while True:
            await asyncio.sleep(self.crystallization_interval)
            try:
                await self.crystallize_chain()
            except Exception as e:
                logger.error(f"TELEMETRY: Crystallization failed: {e}")

    async def crystallize_chain(self) -> str:
        """
        The Silmarils: Captures the current chain state into hardware (TPM PCR 14).
        Crystallization anchors the current hash chain to the physical substrate.
        """
        current_hash = self.current_event_hash
        if current_hash == self.last_crystallized_hash:
            return current_hash
            
        logger.info(f"TELEMETRY: Crystallizing chain head {current_hash[:8]} to hardware Silmaril...")
        
        # 1. Anchor to TPM PCR 14 (one-way hardware extension)
        tpm = get_tpm_service()
        success = await tpm.extend_pcr(14, current_hash)
        
        if success:
            # 2. Record the crystallization event in the chain itself
            self.ingest_event(
                event_type="silmaril_crystallized",
                severity="low",
                data={
                    "crystallized_hash": current_hash,
                    "prev_crystallized_hash": self.last_crystallized_hash,
                    "pcr_index": 14
                }
            )
            self.last_crystallized_hash = current_hash
            self.last_crystallized_at = time.time()
            return current_hash
        else:
            logger.warning("TELEMETRY: Failed to extend PCR 14. Hardware anchoring skipped.")
            return self.last_crystallized_hash

    def set_db(self, db):
        self.db = db

    def _emit_telemetry_event(self, event_type: str, entity_refs: List[str], payload: Dict[str, Any], trigger_triune: bool = False):
        if emit_world_event is None or getattr(self, "db", None) is None:
            return
        coro = emit_world_event(self.db, event_type=event_type, entity_refs=entity_refs, payload=payload, trigger_triune=trigger_triune)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            try:
                asyncio.run(coro)
            except Exception:
                pass
            return

        def _runner():
            try:
                asyncio.run(coro)
            except Exception:
                pass

        threading.Thread(target=_runner, daemon=True).start()
    
    def _compute_hash(self, data: Dict[str, Any]) -> str:
        """Compute SHA256 hash of data"""
        payload = json.dumps(data, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()
    
    def _compute_signature(self, data: Dict[str, Any], key: str = None) -> str:
        """Compute HMAC signature"""
        if key is None:
            # Wait briefly for secrets to unseal if this is the start of boot
            if not self.secrets_ready.is_set():
                self.secrets_ready.wait(timeout=2.0)
            key = self.signing_key
            
        payload = json.dumps(data, sort_keys=True)
        return hmac.new(key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    
    def verify_event_signature(self, event: SignedEvent, agent_key: str) -> bool:
        """Verify event signature from agent"""
        data = {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "timestamp": event.timestamp,
            "agent_id": event.agent_id,
            "data": event.data
        }
        expected = self._compute_signature(data, agent_key)
        return hmac.compare_digest(expected, event.signature)
    
    def verify_chain_integrity(self) -> Tuple[bool, str]:
        """Verify the integrity of the event chain"""
        if not self.event_chain:
            return True, "Empty chain"
        
        prev_hash = self.genesis_event_hash
        
        for event in self.event_chain:
            # Verify link
            if event.prev_hash != prev_hash:
                return False, f"Chain broken at event {event.event_id}"
            
            # Verify self-hash
            computed_hash = self._compute_hash({
                "event_id": event.event_id,
                "event_type": event.event_type,
                "timestamp": event.timestamp,
                "data": event.data,
                "prev_hash": event.prev_hash
            })
            
            if computed_hash != event.event_hash:
                return False, f"Hash mismatch at event {event.event_id}"
            
            prev_hash = event.event_hash
        
        return True, "Chain integrity verified"
    
    # =========================================================================
    # TRACING (OpenTelemetry-style)
    # =========================================================================
    
    def start_trace(self, operation: str, metadata: Dict[str, Any] = None) -> str:
        """Start a new trace for an operation"""
        trace_id = uuid.uuid4().hex
        
        self.active_traces[trace_id] = {
            "trace_id": trace_id,
            "operation": operation,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
            "spans": []
        }
        
        return trace_id
    
    def start_span(self, trace_id: str, operation: str, 
                   parent_span_id: str = None) -> str:
        """Start a new span within a trace"""
        if trace_id not in self.active_traces:
            return None
        
        span_id = uuid.uuid4().hex[:16]
        
        span = {
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "operation": operation,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": None,
            "status": "in_progress",
            "events": []
        }
        
        self.active_traces[trace_id]["spans"].append(span)
        
        return span_id
    
    def end_span(self, trace_id: str, span_id: str, 
                 status: str = "success", result: Dict = None):
        """End a span"""
        if trace_id not in self.active_traces:
            return
        
        for span in self.active_traces[trace_id]["spans"]:
            if span["span_id"] == span_id:
                span["ended_at"] = datetime.now(timezone.utc).isoformat()
                span["status"] = status
                span["result"] = result
                break
    
    def end_trace(self, trace_id: str) -> Dict:
        """End a trace and return the complete trace data"""
        if trace_id not in self.active_traces:
            return None
        
        trace = self.active_traces.pop(trace_id)
        trace["ended_at"] = datetime.now(timezone.utc).isoformat()
        
        return trace
    
    # =========================================================================
    # EVENT INGESTION
    # =========================================================================
    
    def ingest_event(self, event_type: str, severity: str, data: Dict[str, Any],
                     agent_id: str = None, hostname: str = None,
                     signature: str = None, trace_id: str = None,
                     span_id: str = None, parent_span_id: str = None) -> SignedEvent:
        """
        Ingest an event into the tamper-evident chain.
        """
        event_id = f"evt-{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Generate trace/span IDs if not provided
        if not trace_id:
            trace_id = uuid.uuid4().hex
        if not span_id:
            span_id = uuid.uuid4().hex[:16]
        
        # Build event for hashing
        event_data = {
            "event_id": event_id,
            "event_type": event_type,
            "timestamp": timestamp,
            "data": data,
            "prev_hash": self.current_event_hash
        }
        
        event_hash = self._compute_hash(event_data)
        
        # Server signature if agent signature not provided
        if not signature:
            signature = self._compute_signature({
                "event_id": event_id,
                "event_type": event_type,
                "timestamp": timestamp,
                "data": data
            })
        
        event = SignedEvent(
            event_id=event_id,
            event_type=event_type,
            severity=severity,
            timestamp=timestamp,
            agent_id=agent_id,
            hostname=hostname,
            data=data,
            signature=signature,
            prev_hash=self.current_event_hash,
            event_hash=event_hash,
            source="agent" if agent_id else "server",
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id
        )
        
        # Append to chain
        self.event_chain.append(event)
        self.current_event_hash = event_hash
        self._emit_telemetry_event(
            event_type="telemetry_event_ingested",
            entity_refs=[event.event_id, event.agent_id or "server"],
            payload={"event_type": event.event_type, "severity": event.severity, "trace_id": event.trace_id},
            trigger_triune=event.severity in {"critical", "high"},
        )
        
        return event

    def record_harmonic_timeline(
        self,
        *,
        trace_id: str,
        timeline: Dict[str, Any],
        baseline_ref: Optional[Dict[str, Any]] = None,
        harmonic_state: Optional[Dict[str, Any]] = None,
    ) -> Optional[SignedEvent]:
        if not timeline:
            return None
        return self.ingest_event(
            event_type="harmonic_timeline_recorded",
            severity="low",
            data={
                "trace_id": trace_id,
                "timeline": timeline,
                "baseline_ref": baseline_ref or {},
                "harmonic_state": harmonic_state or {},
            },
            trace_id=trace_id or None,
        )

    def store_harmonic_state(
        self,
        *,
        trace_id: str,
        state: Dict[str, Any],
        contributors: Optional[Dict[str, Any]] = None,
    ) -> Optional[SignedEvent]:
        if not state:
            return None
        discord = float(state.get("discord_score") or 0.0)
        severity = "high" if discord >= 0.8 else "medium" if discord >= 0.6 else "low"
        return self.ingest_event(
            event_type="harmonic_state_stored",
            severity=severity,
            data={
                "trace_id": trace_id,
                "harmonic_state": state,
                "contributors": contributors or {},
            },
            trace_id=trace_id or None,
        )

    def record_constitutional_audit(
        self,
        *,
        event_type: str,
        boot_status: str,
        herald_id: str,
        manifold_id: str,
        data: Dict[str, Any]
    ) -> SignedEvent:
        """
        Record a Phase I constitutional foundation event.
        Ensures the Three Trees (Truth, Order, Fabric) are anchored in the chain.
        """
        enriched_data = {
            **data,
            "constitutional_context": {
                "boot_status": boot_status,
                "herald_id": herald_id,
                "manifold_id": manifold_id,
                "phase": "I"
            }
        }
        return self.ingest_event(
            event_type=f"constitutional_{event_type}",
            severity="info" if boot_status == "lawful" else "critical",
            data=enriched_data
        )

    def record_edge_sequence(
        self,
        *,
        action_id: str,
        edge_type: str,
        sequence: List[str],
        timeline: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> Optional[SignedEvent]:
        if not action_id:
            return None
        event = self.ingest_event(
            event_type="edge_sequence_recorded",
            severity="low",
            data={
                "action_id": action_id,
                "edge_type": edge_type,
                "sequence": list(sequence or []),
                "timeline": timeline or {},
            },
            trace_id=trace_id or None,
        )
        entry = self.edge_observation_index.setdefault(action_id, {})
        entry["action_id"] = action_id
        entry["edge_type"] = edge_type
        entry["sequence"] = list(sequence or [])
        entry["timeline"] = dict(timeline or {})
        return event

    def record_participant_appearance(
        self,
        *,
        action_id: str,
        edge_type: str,
        participant: str,
        timestamp_ms: Optional[float] = None,
        trace_id: Optional[str] = None,
    ) -> Optional[SignedEvent]:
        if not action_id or not participant:
            return None
        ts_ms = float(timestamp_ms if timestamp_ms is not None else datetime.now(timezone.utc).timestamp() * 1000.0)
        event = self.ingest_event(
            event_type="edge_participant_appearance",
            severity="low",
            data={
                "action_id": action_id,
                "edge_type": edge_type,
                "participant": participant,
                "timestamp_ms": ts_ms,
            },
            trace_id=trace_id or None,
        )
        entry = self.edge_observation_index.setdefault(action_id, {})
        entry["action_id"] = action_id
        entry["edge_type"] = edge_type
        participants = list(entry.get("participants") or [])
        if participant not in participants:
            participants.append(participant)
        entry["participants"] = participants
        timestamps = dict(entry.get("participant_timestamps_ms") or {})
        timestamps[participant] = ts_ms
        entry["participant_timestamps_ms"] = timestamps
        return event

    def replay_edge_observation(self, action_id: str) -> Dict[str, Any]:
        if not action_id:
            return {}
        return dict(self.edge_observation_index.get(action_id) or {})
    
    # =========================================================================
    # AUDIT RECORDS
    # =========================================================================
    
    def record_action(self, principal: str, principal_trust_state: str,
                      action: str, targets: List[str],
                      case_id: str = None, evidence_refs: List[str] = None,
                      policy_decision_hash: str = None, token_id: str = None,
                      policy_decision_id: str = None,
                      governance_decision_id: str = None,
                      governance_queue_id: str = None,
                      execution_id: str = None,
                      trace_id: str = None,
                      constraints: Dict = None, tool_id: str = None,
                      result: str = "pending", result_details: str = None,
                      output_artifact_ids: List[str] = None) -> AuditRecord:
        """
        Record an action in the audit chain.
        
        This provides "who did what, when, with which inputs" for court-admissible audit.
        """
        record_id = f"aud-{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc).isoformat()
        
        record_data = {
            "record_id": record_id,
            "timestamp": timestamp,
            "principal": principal,
            "action": action,
            "targets": targets,
            "prev_hash": self.current_audit_hash
        }
        
        record_hash = self._compute_hash(record_data)
        
        record = AuditRecord(
            record_id=record_id,
            timestamp=timestamp,
            principal=principal,
            principal_trust_state=principal_trust_state,
            action=action,
            tool_id=tool_id,
            targets=targets,
            case_id=case_id,
            evidence_refs=evidence_refs or [],
            policy_decision_hash=policy_decision_hash or "",
            policy_decision_id=policy_decision_id or "",
            governance_decision_id=governance_decision_id or "",
            governance_queue_id=governance_queue_id or "",
            token_id=token_id or "",
            execution_id=execution_id or "",
            trace_id=trace_id or "",
            constraints=constraints or {},
            result=result,
            result_details=result_details,
            output_artifact_ids=output_artifact_ids or [],
            prev_hash=self.current_audit_hash,
            record_hash=record_hash
        )
        
        self.audit_chain.append(record)
        self.current_audit_hash = record_hash
        
        logger.info(f"AUDIT: {principal} | {action} | {targets} | {result}")
        self._emit_telemetry_event(
            event_type="telemetry_audit_recorded",
            entity_refs=[record.record_id, principal],
            payload={
                "action": action,
                "result": result,
                "target_count": len(targets),
                "policy_decision_id": record.policy_decision_id,
                "governance_decision_id": record.governance_decision_id,
                "governance_queue_id": record.governance_queue_id,
                "token_id": record.token_id,
                "execution_id": record.execution_id,
                "trace_id": record.trace_id,
            },
            trigger_triune=result in {"failed", "denied"},
        )
        
        return record
    
    def record_amendment(self, original_record_id: str, new_result: str,
                         details: str = None, artifact_ids: List[str] = None,
                         governance_decision_id: str = None) -> AuditRecord:
        """
        Amendment Scrolls: Records an outcome change without mutating history.
        The original record remains intact; a new record captures the correction.
        """
        logger.info(f"AUDIT: Recording amendment for {original_record_id} -> {new_result}")
        return self.record_action(
            principal="system:amendment_engine",
            principal_trust_state="lawful",
            action="amend_prior_record",
            targets=[original_record_id],
            governance_decision_id=governance_decision_id or "",
            result=new_result,
            result_details=f"AMENDMENT of {original_record_id}: {details}",
            output_artifact_ids=artifact_ids or []
        )

    def update_action_result(self, record_id: str, result: str, 
                             details: str = None, artifact_ids: List[str] = None):
        """
        [DEPRECATED] Mutates an action result.
        Now redirects to record_amendment to avoid breaking existing code,
        but logs the intent as an amendment scroll.
        """
        logger.warning(f"AUDIT: Deprecated mutation call for {record_id}. Using Amendment Scroll.")
        self.record_amendment(record_id, result, details, artifact_ids)
        return True
    
    # =========================================================================
    # QUERIES
    # =========================================================================
    
    def get_events(self, event_type: str = None, agent_id: str = None,
                   severity: str = None, limit: int = 100) -> List[Dict]:
        """Query events with filters"""
        results = []
        
        for event in reversed(self.event_chain):
            if event_type and event.event_type != event_type:
                continue
            if agent_id and event.agent_id != agent_id:
                continue
            if severity and event.severity != severity:
                continue
            
            results.append(asdict(event))
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_audit_trail(self, principal: str = None, action: str = None,
                        case_id: str = None, limit: int = 100) -> List[Dict]:
        """Query audit records with filters"""
        results = []
        
        for record in reversed(self.audit_chain):
            if principal and record.principal != principal:
                continue
            if action and record.action != action:
                continue
            if case_id and record.case_id != case_id:
                continue
            
            results.append(asdict(record))
            
            if len(results) >= limit:
                break
        
        return results
    
    def get_chain_status(self) -> Dict:
        """Get chain status and integrity check"""
        integrity_ok, integrity_msg = self.verify_chain_integrity()
        
        return {
            "event_chain_length": len(self.event_chain),
            "audit_chain_length": len(self.audit_chain),
            "current_event_hash": self.current_event_hash[:16] + "...",
            "current_audit_hash": self.current_audit_hash[:16] + "...",
            "integrity_verified": integrity_ok,
            "integrity_message": integrity_msg,
            "active_traces": len(self.active_traces)
        }


# Global singleton
tamper_evident_telemetry = TamperEvidentTelemetry()


# Convenience alias
from typing import Tuple
def verify_chain() -> Tuple[bool, str]:
    return tamper_evident_telemetry.verify_chain_integrity()
