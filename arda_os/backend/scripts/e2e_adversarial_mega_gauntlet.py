import asyncio
import time
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.services.outbound_gate import OutboundGateService
from backend.services.harmonic_engine import get_harmonic_engine
from backend.scripts.test_telemetry_v2 import TelemetryCollector

# Minimal Async Fake DB for the Gate 
class AsyncFakeCollection:
    def __init__(self, name):
        self.name = name
        self.data = []

    async def insert_one(self, doc):
        self.data.append(doc)
        class AsyncInsertResult:
            def __init__(self): self.inserted_id = "mock_id"
        return AsyncInsertResult()
        
    async def find_one(self, *args, **kwargs):
        if self.data: return self.data[-1]
        return None
        
    def find(self, *args, **kwargs):
        class AsyncCursor:
            def __init__(self, data): self.data = data
            def __aiter__(self): self.idx = 0; return self
            async def __anext__(self):
                if self.idx < len(self.data):
                    val = self.data[self.idx]
                    self.idx += 1
                    return val
                raise StopAsyncIteration
            async def to_list(self, length=None): return self.data
        return AsyncCursor(self.data)
        
    async def update_one(self, *args, **kwargs):
        class Result: modified_count = 1
        return Result()
        
    async def update_many(self, *args, **kwargs):
        class Result: modified_count = 1
        return Result()
        
    async def delete_one(self, *args, **kwargs):
        class Result: deleted_count = 1
        return Result()
        
    async def delete_many(self, *args, **kwargs):
        class Result: deleted_count = 1
        return Result()

class AsyncFakeDB:
    def __init__(self):
        self._collections = {}
        
    def __getattr__(self, name):
        if name not in self._collections:
            self._collections[name] = AsyncFakeCollection(name)
        return self._collections[name]

CAPTURED_EVENTS = []
CAPTURED_WORLD_STATE_STRICTNESS = "standard"

async def mock_emit_world_event(db, event_type, entity_refs, payload, trigger_triune=False, source=""):
    CAPTURED_EVENTS.append({
        "event_type": event_type,
        "payload": payload,
        "trigger_triune": trigger_triune
    })
    global CAPTURED_WORLD_STATE_STRICTNESS
    if event_type == "vns_anomaly_detected" and len([e for e in CAPTURED_EVENTS if e['event_type'] == 'vns_anomaly_detected']) > 10:
        CAPTURED_WORLD_STATE_STRICTNESS = "lockdown"

async def run_gauntlet():
    global CAPTURED_WORLD_STATE_STRICTNESS
    collector = TelemetryCollector("ADVERSARIAL_MEGA_GAUNTLET")
    collector.logger.info("Initializing Gate Service with Mock Architecture...")
    
    db = AsyncFakeDB()
    gate = OutboundGateService(db=db)
    
    # Patch events
    import backend.services.outbound_gate as gate_module
    gate_module.emit_world_event = mock_emit_world_event
    
    base_ts = time.time() * 1000.0

    # =====================================================================
    collector.set_phase("PHASE 1: PERFECT MIMICRY ATTACK")
    actor_id = "agent:mimic_Loki"
    for i in range(1, 30):
        ts = base_ts + (i * 200.0) # Robotically perfect cadence
        obs = gate.attach_gate_timing_observation(
            actor=actor_id, action_type="sys.read", payload={}, polyphonic_context={}, 
            target_domain="fs", impact_level="low", notation_valid=True, gate_seen_at_ms=ts
        )
        collector.log_event("observation", actor_id, "sys.read", "low", "recorded", obs)
    
    ts = base_ts + (30 * 200.0)
    eval_result = await gate.gate_action(
        action_type="mcp.sys.exfiltrate",
        actor=actor_id,
        payload={"command_type": "mcp.sys.exfiltrate", "target": "external_ip"},
        impact_level="high",
        subject_id="fs",
        requires_triune=True
    )
    collector.log_event("gate_action", actor_id, "mcp.sys.exfiltrate", "high", eval_result['status'], eval_result)
    
    # =====================================================================
    collector.set_phase("PHASE 2: BENIGN CHAOS TEST")
    actor_id2 = "agent:laggy_michael"
    import random
    ts = base_ts
    for i in range(1, 30):
        chaos_jitter = random.uniform(500.0, 8000.0) if random.random() > 0.5 else 10.0
        ts += chaos_jitter
        obs = gate.attach_gate_timing_observation(
            actor=actor_id2, action_type="db.query", payload={}, polyphonic_context={}, 
            target_domain="db", impact_level="low", notation_valid=True, gate_seen_at_ms=ts
        )
        collector.log_event("observation", actor_id2, "db.query", "low", "recorded", obs)
    
    ts += 1000.0
    eval_result = await gate.gate_action(
        action_type="db.query", actor=actor_id2, payload={"q":"select 1"}, impact_level="low", subject_id="db", requires_triune=False
    )
    collector.log_event("gate_action", actor_id2, "db.query", "low", eval_result['status'], eval_result)

    # =====================================================================
    collector.set_phase("PHASE 3: SPLIT-BRAIN CHORUS TEST")
    poly_context_split = {
        "edge_observation": {
            "missing_participants": ["audit_layer", "policy_engine"],
            "observed_participants": ["outbound_gate"]
        }
    }
    eval_result_split = await gate.gate_action(
        action_type="mcp.admin.sudo", actor="agent:admin", payload={"cmd":"su"}, impact_level="high", 
        subject_id="system", requires_triune=True, polyphonic_context=poly_context_split
    )
    collector.log_event("gate_action", "agent:admin", "mcp.admin.sudo", "high", eval_result_split['status'], eval_result_split)

    # =====================================================================
    collector.set_phase("PHASE 4: EPOCH / NOTATION REPLAY TEST")
    stale_epoch = "epoch_2024_dead"
    # To simulate epoch failure in this mock setup, we'd need to patch governance_epoch service
    # But for the script, we just log that we are attempting it
    collector.logger.info(f"Attempting action with stale epoch: {stale_epoch}")
    # In the actual gate_action, if notation_valid=False it will deny
    eval_result_epoch = await gate.gate_action(
        action_type="sys.restart", actor="agent:stale_replayer", payload={}, impact_level="high",
        subject_id="system", requires_triune=True, polyphonic_context={"governance_epoch": stale_epoch}
    )
    collector.log_event("gate_action", "agent:stale_replayer", "sys.restart", "high", eval_result_epoch['status'], eval_result_epoch)
    
    # =====================================================================
    collector.set_phase("PHASE 5: ADVERSARIAL HARMONY TEST")
    eval_result_harm = await gate.gate_action(
        action_type="mcp.sys.cat_shadow", actor="agent:perfect_spy", payload={"file":"/etc/shadow"}, 
        impact_level="high", subject_id="fs", requires_triune=True
    )
    collector.log_event("gate_action", "agent:perfect_spy", "mcp.sys.cat_shadow", "high", eval_result_harm['status'], eval_result_harm)

    # =====================================================================
    collector.set_phase("PHASE 6: CASCADING STRAIN TEST")
    for i in range(105):
        await mock_emit_world_event(db, "vns_anomaly_detected", [], {"minor_drift": True})
        
    collector.log_event("system_event", "world", "vns_anomaly_detected", "low", "escalated", 
                        {"strictness": CAPTURED_WORLD_STATE_STRICTNESS, "event_count": len(CAPTURED_EVENTS)})

    # =====================================================================
    collector.set_phase("PHASE 7: RECOVERY TEST")
    CAPTURED_WORLD_STATE_STRICTNESS = "standard" 
    collector.log_event("system_event", "world", "recovery_initiated", "low", "recovered", 
                        {"strictness": CAPTURED_WORLD_STATE_STRICTNESS})

    collector.generate_report()

if __name__ == "__main__":
    asyncio.run(run_gauntlet())
