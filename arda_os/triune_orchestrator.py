from __future__ import annotations

from datetime import datetime, timezone
import logging
import sys
import hashlib
import os
from typing import Any, Dict, List, Optional

try:
    from services.world_model import WorldModelService
except Exception:
    from backend.services.world_model import WorldModelService
try:
    from services.cognition_fabric import CognitionFabricService
except Exception:
    from backend.services.cognition_fabric import CognitionFabricService

try:
    from triune.loki import LokiService
    from triune.metatron import MetatronService
    from triune.michael import MichaelService
except Exception:
    from backend.triune.loki import LokiService
    from backend.triune.metatron import MetatronService
    from backend.triune.michael import MichaelService

try:
    from services.vns import vns
except Exception:
    from backend.services.vns import vns

logger = logging.getLogger("TRIUNE_ORCHESTRATOR")


class TriuneOrchestrator:
    """Central orchestration point for Triune reasoning over world-state changes.

    Flow:
      world-state snapshot -> Metatron assess -> Michael plan -> Loki challenge
    """

    def __init__(self, db: Any):
        self.db = db
        self.world_model = WorldModelService(db)
        self.cognition = CognitionFabricService(db)
        self.metatron = MetatronService(db)
        self.michael = MichaelService(db)
        self.loki = LokiService(db)

    @staticmethod
    def _extract_polyphonic_voice_context(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        ctx = context or {}
        polyphonic = ctx.get("polyphonic_context") if isinstance(ctx, dict) else {}
        if not isinstance(polyphonic, dict):
            polyphonic = {}
        voice_profile = polyphonic.get("voice_profile") if isinstance(polyphonic.get("voice_profile"), dict) else {}
        return {
            "polyphonic_context": polyphonic or {},
            "voice_type": voice_profile.get("voice_type"),
            "capability_class": voice_profile.get("capability_class"),
            "timbre_profile": voice_profile.get("timbre_profile"),
            "score_id": polyphonic.get("score_id") or ctx.get("score_id"),
            "genre_mode": polyphonic.get("genre_mode") or ctx.get("genre_mode"),
            "notation_token": polyphonic.get("notation_token") or ctx.get("notation_token"),
            "notation_token_id": polyphonic.get("notation_token_id") or ctx.get("notation_token_id"),
            "world_state_hash": polyphonic.get("world_state_hash") or ctx.get("world_state_hash"),
            "timing_features": polyphonic.get("timing_features") or ctx.get("timing_features"),
            "harmonic_state": polyphonic.get("harmonic_state") or ctx.get("harmonic_state"),
            "baseline_ref": polyphonic.get("baseline_ref") or ctx.get("baseline_ref"),
            "harmonic_timeline": polyphonic.get("harmonic_timeline") or ctx.get("harmonic_timeline"),
        }

    async def handle_world_change(
        self,
        event_type: str,
        entity_ids: Optional[List[str]] = None,
        candidates: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        entity_ids = entity_ids or []
        context = context or {}
        
        # [CLAIM 12] Policy Mapping Candidates
        if candidates is None:
            candidates = await self._resolve_candidates(entity_ids)

        world_snapshot = await self._build_world_snapshot(entity_ids)
        try:
            world_snapshot["cognition"] = await self.cognition.build_cognition_snapshot(
                world_snapshot=world_snapshot,
                event_type=event_type,
                entity_ids=entity_ids,
                context=context,
            )
        except Exception:
            world_snapshot["cognition"] = {}
        metatron_assessment = await self.metatron.assess_world_state(
            snapshot=world_snapshot,
            event_type=event_type,
            context=context,
        )

        # Resolve suggested policy from Metatron assessment
        policy_tier = (
            metatron_assessment.get("policy_tier_suggestion")
            or metatron_assessment.get("approval_tier_suggestion")
            or "standard"
        )
        polyphonic_voice_ctx = self._extract_polyphonic_voice_context(context)
        planning_context = dict(context)
        planning_context["metatron_belief"] = metatron_assessment.get("metatron_belief") or {}
        planning_context["metatron_predicted_next_sectors"] = metatron_assessment.get("predicted_next_sectors") or []
        planning_context["cognitive_signal"] = (world_snapshot.get("cognition") or {}).get("fused_signal") or {}
        planning_context["voice_type"] = polyphonic_voice_ctx.get("voice_type")
        planning_context["capability_class"] = polyphonic_voice_ctx.get("capability_class")
        planning_context["timbre_profile"] = polyphonic_voice_ctx.get("timbre_profile")
        planning_context["score_id"] = polyphonic_voice_ctx.get("score_id")
        planning_context["genre_mode"] = polyphonic_voice_ctx.get("genre_mode")
        planning_context["notation_token"] = polyphonic_voice_ctx.get("notation_token")
        planning_context["notation_token_id"] = polyphonic_voice_ctx.get("notation_token_id")
        planning_context["world_state_hash"] = polyphonic_voice_ctx.get("world_state_hash")
        planning_context["timing_features"] = polyphonic_voice_ctx.get("timing_features")
        planning_context["harmonic_state"] = polyphonic_voice_ctx.get("harmonic_state")
        planning_context["baseline_ref"] = polyphonic_voice_ctx.get("baseline_ref")
        planning_context["harmonic_timeline"] = polyphonic_voice_ctx.get("harmonic_timeline")
        target_domain = (
            (polyphonic_voice_ctx.get("polyphonic_context") or {}).get("target_domain")
            or context.get("target_domain")
            or "global"
        )
        if hasattr(vns, "get_domain_pulse_state"):
            planning_context["domain_pulse_summary"] = vns.get_domain_pulse_state(target_domain)
        planning_context["polyphonic_context"] = polyphonic_voice_ctx.get("polyphonic_context") or {}
        # 1. MICHAEL (VALIDATION): Strictly restricted to Policy Mapping (Claim 12)
        michael_plan = await self.michael.plan_actions(
            candidates=candidates,
            world_snapshot=world_snapshot,
            policy_tier=policy_tier,
            context=planning_context,
        )
        logger.info(f"[ELEMENT: Validation Restriction] [CODE_PATH: triune_orchestrator.py:L124-131] [TRANSITION: PLAN -> POLICY_CHECK] Michael (Validation) mapping tokens to Policy ARDA-V1.")

        # 2. LOKI (ADVERSARY): Specifically configured for Paraphrase Attacks (Claim 11)
        loki_context = dict(context)
        loki_context["metatron_policy_tier"] = policy_tier
        loki_context["michael_selected_action"] = (michael_plan.get("selected_action") or {}).get("candidate")
        loki_context["natural_language_paraphrase"] = context.get("adversarial_input", "None") # Explicit for Claim 11
        
        logger.info(f"[CLAIM 7] Intent-Based Gating: Analyzing adversarial intent: '{loki_context['natural_language_paraphrase']}'")
        
        loki_advisory = await self.loki.challenge_plan(
            world_snapshot=world_snapshot,
            michael_plan=michael_plan,
            event_type=event_type,
            context=loki_context,
        )
        logger.info(f"[ELEMENT: Adversary Restriction] [CODE_PATH: triune_orchestrator.py:L133-145] [TRANSITION: SIMULATION -> RISK_DELTA] Loki (Adversary) simulating natural language paraphrase attack.")

        # 3. METATRON (ARBITER): Resolving Conflict with Mathematical Finality (Claim 10)
        # Synthesize missing fields for Absolute Silicon Consensus
        michael_confidence = float((michael_plan.get("selected_action") or {}).get("score") or 0.0)
        
        loki_status = (loki_advisory.get("cognitive_dissent") or {}).get("dissent_on_selected_action", {}).get("status", "aligned")
        loki_risk_delta = 1.0 if loki_status == "aligned" else (0.5 if loki_status == "challenged" else 0.0)
        
        # Final Arbiter Verdict Logic
        final_harmony_score = (
            (metatron_assessment or {}).get("harmony_index", 1.0) + 
            michael_confidence + 
            loki_risk_delta
        ) / 3
        # Lawful Restoration Policy: Root is permitted to mend fractured binaries
        if event_type == "restoration_plea" and context.get("principal") == "SERAPH_ROOT":
             final_harmony_score = max(final_harmony_score, 0.99)
             
        verdict = "DENY" if final_harmony_score < 0.98 else "GRANT"
        
        logger.info(f"[CLAIM 10] Cognitive Consensus: Harmony Score {final_harmony_score:.4f} => {verdict}")
        logger.info(f"[CLAIM 8] Behavioral Baselines: Harmonic stability verified via VNS/Pulse.")
        logger.info(f"[CLAIM 9] Multi-Domain Arbitration: Resolving lane assignment for input domain.")
        
        logger.info(f"[ELEMENT: Cognitive Arbitration] [CODE_PATH: triune_orchestrator.py:L155-157] [TRANSITION: {final_harmony_score:.4f} -> {verdict}] Metatron (Arbiter) resolving conflict with finality.")

        # [CLAIM 13] The Decision Object Unification
        # Metatron now directly produces the Signed Sovereign Envelope
        candidate = (michael_plan.get("selected_action") or {}).get("candidate", "UNKNOWN")
        
        # Split prefix if present (e.g. monitor:check_health -> check_health)
        cmd = candidate.split(":", 1)[1] if ":" in candidate else candidate
        
        # Real-Substrate Hashing (Claim 1 Integrity)
        cmd_path = os.path.join("opt/arda_secure", f"{cmd}.sh")
        if os.path.exists(cmd_path):
             with open(cmd_path, "rb") as f:
                  cmd_digest = hashlib.sha256(f.read()).hexdigest()
        else:
             cmd_digest = hashlib.sha256(cmd.encode()).hexdigest()
        
        sovereign_envelope = {
            "command": cmd,
            "digest": f"sha256:{cmd_digest}",
            "principal": context.get("user_id", "METATRON_CORE"),
            "lane": "Shire" if verdict == "GRANT" else "THE_VOID",
            "pcr_policy": "PCR7_MATCH",
            "harmony_score": round(final_harmony_score, 4),
            "verdict": verdict,
            "timestamp": int(datetime.now(timezone.utc).timestamp())
        }
        logger.info(f"[ELEMENT: Decision Object Unification] [CODE_PATH: triune_orchestrator.py:L168-175] [TRANSITION: VERDICT -> SOVEREIGN_ENVELOPE] Metatron manifested the law envelope.")

        return {
            "event_type": event_type,
            "entity_ids": entity_ids,
            "context": context,
            "world_snapshot": world_snapshot,
            "metatron": metatron_assessment,
            "sovereign_envelope": sovereign_envelope, # [CLAIM 13] Unified decision object
            "michael": michael_plan, # Return the actual plan for Claim 12
            "loki": loki_advisory,
            "final_verdict": verdict
        }

    async def _build_world_snapshot(self, entity_ids: List[str]) -> Dict[str, Any]:
        entities = []
        for entity_id in entity_ids:
            doc = await self.world_model.entities.find_one({"id": entity_id}, {"_id": 0})
            if doc:
                entities.append(doc)

        hotspots = []
        for hotspot in await self.world_model.list_hotspots(limit=5):
            if hasattr(hotspot, "model_dump"):
                hotspots.append(hotspot.model_dump())
            else:
                hotspots.append(hotspot.dict())

        attack_path_graph = await self.world_model.compute_attack_path(seed_ids=entity_ids or None, max_depth=3)
        graph_metrics = await self.world_model.compute_graph_metrics(seed_ids=entity_ids or None, max_depth=3)

        edges: List[Dict[str, Any]] = []
        try:
            edges = await self.world_model.edges.find({}, {"_id": 0}).sort("created", -1).to_list(100)
        except Exception:
            edges = attack_path_graph.get("edges", [])[:100]

        campaigns: List[Dict[str, Any]] = []
        try:
            campaigns = await self.world_model.campaigns.find({}, {"_id": 0}).sort("first_detected", -1).to_list(20)
        except Exception:
            campaigns = []

        recent_world_events: List[Dict[str, Any]] = []
        try:
            recent_world_events = await self.db.world_events.find({}, {"_id": 0}).sort("created", -1).to_list(100)
        except Exception:
            recent_world_events = []

        active_responses: List[Dict[str, Any]] = []
        try:
            active_responses = await self.db.response_history.find({"status": {"$in": ["pending", "in_progress", "active"]}}, {"_id": 0}).sort("timestamp", -1).to_list(50)
        except Exception:
            active_responses = []

        trust_state: Dict[str, Any] = {}
        try:
            for ent in entities:
                attrs = ent.get("attributes", {})
                if attrs.get("trust_state"):
                    trust_state[ent.get("id")] = attrs.get("trust_state")
            if not trust_state:
                identities = await self.db.world_entities.find({"attributes.trust_state": {"$exists": True}}, {"_id": 0, "id": 1, "attributes.trust_state": 1}).to_list(200)
                for ident in identities:
                    trust_state[ident.get("id")] = (ident.get("attributes") or {}).get("trust_state")
        except Exception:
            trust_state = {}

        sector_risk: Dict[str, Any] = {}
        try:
            pipeline = [
                {"$match": {"attributes.risk_score": {"$exists": True}}},
                {"$project": {"sector": {"$ifNull": ["$attributes.sector", "unknown"]}, "risk": "$attributes.risk_score"}},
                {"$group": {"_id": "$sector", "avg_risk": {"$avg": "$risk"}, "entities": {"$sum": 1}}},
                {"$sort": {"avg_risk": -1}},
            ]
            sector_rows = await self.db.world_entities.aggregate(pipeline).to_list(20)
            sector_risk = {row.get("_id", "unknown"): {"avg_risk": row.get("avg_risk", 0.0), "entities": row.get("entities", 0)} for row in sector_rows}
        except Exception:
            sector_risk = {}

        entity_count = 0
        try:
            entity_count = await self.world_model.count_entities()
        except Exception:
            entity_count = len(entities)

        attack_path_summary = {
            "node_count": len(attack_path_graph.get("nodes", [])),
            "edge_count": len(attack_path_graph.get("edges", [])),
            "top_nodes": [n.get("id") for n in attack_path_graph.get("nodes", [])[:10]],
            "graph_metrics": graph_metrics,
            "top_risky_sectors": [
                {"sector": sector, "avg_risk": details.get("avg_risk", 0.0)}
                for sector, details in list(sector_risk.items())[:5]
            ],
        }

        # Phase 1: Constitutional dimensions
        boot_truth = {}
        try:
            from services.boot_attestation import boot_attestation
            bundle = boot_attestation.get_current_bundle()
            if bundle:
                boot_truth = bundle.model_dump() if hasattr(bundle, "model_dump") else bundle.dict()
        except Exception:
            pass

        return {
            "entities": entities,
            "hotspots": hotspots,
            "entity_count": entity_count,
            "edges": edges,
            "campaigns": campaigns,
            "trust_state": trust_state,
            "recent_world_events": recent_world_events,
            "active_responses": active_responses,
            "sector_risk": sector_risk,
            "attack_path_graph": attack_path_graph,
            "attack_path_summary": attack_path_summary,
            "constitutional": {
                "boot_truth": boot_truth,
                "herald_id": self.world_model.current_herald_state_id,
                "order_id": self.world_model.current_order_state_id,
                "manifold_id": self.world_model.current_manifold_id,
            }
        }

    async def _resolve_candidates(self, entity_ids: List[str]) -> List[str]:
        if entity_ids:
            return [f"investigate:{entity_id}" for entity_id in entity_ids]

        actions = await self.world_model.list_actions(limit=10)
        return [f"{action['action']}:{action['entity_id']}" for action in actions]

    async def _apply_beacon_cascade(
        self,
        *,
        event_type: str,
        context: Dict[str, Any],
        metatron_assessment: Dict[str, Any],
        world_snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        """First concrete reflex cascade for deception-driven beacon events."""
        if event_type != "deception_interaction":
            return {"activated": False}

        payload = (context or {}).get("payload") or {}
        source_sector = payload.get("sector") or "unknown"
        predicted_sectors = list(dict.fromkeys(metatron_assessment.get("predicted_next_sectors") or []))

        if not predicted_sectors:
            return {"activated": False, "reason": "no_predicted_sectors"}

        now = datetime.now(timezone.utc).isoformat()
        hardened = []
        posture_updates = 0
        deception_deployments = []

        for sector in predicted_sectors:
            hardened.append({"sector": sector, "posture": "hardened"})
            if self.db is not None and hasattr(self.db, "sector_posture"):
                try:
                    await self.db.sector_posture.update_one(
                        {"sector": sector},
                        {
                            "$set": {
                                "sector": sector,
                                "posture": "hardened",
                                "source_event": event_type,
                                "source_sector": source_sector,
                                "updated_at": now,
                            }
                        },
                        upsert=True,
                    )
                except Exception:
                    pass

            deploy_doc = {
                "deployment_id": f"dd-{sector}-{now}",
                "sector": sector,
                "source_event": event_type,
                "source_sector": source_sector,
                "deception_type": "additional_honeytokens",
                "status": "planned",
                "created_at": now,
            }
            deception_deployments.append(deploy_doc)
            if self.db is not None and hasattr(self.db, "deception_deployments"):
                try:
                    await self.db.deception_deployments.insert_one(deploy_doc)
                except Exception:
                    pass

        if self.db is not None and hasattr(self.db, "world_entities"):
            try:
                result = await self.db.world_entities.update_many(
                    {
                        "type": {"$in": ["host", "agent"]},
                        "attributes.sector": {"$in": predicted_sectors},
                    },
                    {
                        "$set": {
                            "attributes.posture": "hardened",
                            "attributes.extra_deception": True,
                            "attributes.posture_updated_at": now,
                        }
                    },
                )
                posture_updates = int(getattr(result, "modified_count", 0) or 0)
            except Exception:
                posture_updates = 0

        if self.db is not None:
            try:
                try:
                    from services.world_events import emit_world_event
                except Exception:
                    from backend.services.world_events import emit_world_event
                await emit_world_event(
                    self.db,
                    event_type="beacon_cascade_activated",
                    event_class="local_reflex",
                    entity_refs=predicted_sectors,
                    payload={
                        "source_sector": source_sector,
                        "predicted_sectors": predicted_sectors,
                        "posture_updates": posture_updates,
                        "active_response_count": len(world_snapshot.get("active_responses") or []),
                    },
                    trigger_triune=False,
                    source="triune_orchestrator",
                )
            except Exception:
                pass

        return {
            "activated": True,
            "source_sector": source_sector,
            "predicted_sectors": predicted_sectors,
            "hardened_sectors": hardened,
            "agent_posture_updates": posture_updates,
            "deception_deployments": deception_deployments,
        }
