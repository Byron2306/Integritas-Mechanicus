import os
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import secrets
import logging

try:
    from services.governance_epoch import get_governance_epoch_service
except Exception:
    from backend.services.governance_epoch import get_governance_epoch_service

try:
    from services.notation_token import get_notation_token_service
except Exception:
    from backend.services.notation_token import get_notation_token_service

try:
    from services.harmonic_engine import get_harmonic_engine
except Exception:
    from backend.services.harmonic_engine import get_harmonic_engine

try:
    from services.chorus_engine import get_chorus_engine
except Exception:
    from backend.services.chorus_engine import get_chorus_engine

try:
    from services.vns import vns
except Exception:
    from backend.services.vns import vns

try:
    from services.vns_alerts import vns_alert_service
except Exception:
    from backend.services.vns_alerts import vns_alert_service

try:
    from services.arda_fabric import get_arda_fabric
except Exception:
    from backend.services.arda_fabric import get_arda_fabric

try:
    from services.world_events import emit_world_event
except Exception:
    try:
        from backend.services.world_events import emit_world_event
    except Exception:
        emit_world_event = None

logger = logging.getLogger(__name__)


IMPACT_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
MANDATORY_HIGH_IMPACT_ACTIONS = {
    "response_execution",
    "response_block_ip",
    "response_unblock_ip",
    "swarm_command",
    "agent_command",
    "cross_sector_hardening",
    "quarantine_restore",
    "quarantine_delete",
    "quarantine_agent",
    "tool_execution",
    "mcp_tool_execution",
}


def _model_dump(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[no-any-return]
    if hasattr(model, "dict"):
        return model.dict()  # type: ignore[no-any-return]
    if hasattr(model, "__dict__"):
        return dict(model.__dict__)  # type: ignore[no-any-return]
    return dict(model)


class OutboundGateService:
    """Central outbound gate used before high-impact action execution."""

    def __init__(self, db: Any):
        self.db = db
        self.epoch_service = get_governance_epoch_service(db)
        self.notation_tokens = get_notation_token_service(db)
        self.harmonic = get_harmonic_engine(db)
        self.chorus = get_chorus_engine(db)
        self.fabric = get_arda_fabric()
        self.environment = str(os.environ.get("ENVIRONMENT") or "local").lower()

    @staticmethod
    def _normalize_impact(impact_level: str) -> str:
        normalized = str(impact_level or "high").lower().strip()
        return normalized if normalized in IMPACT_ORDER else "high"

    @staticmethod
    def _edge_type_for_action(action_type: str) -> Optional[str]:
        action = str(action_type or "").strip().lower()
        if action in {"agent_command", "swarm_command"}:
            return "agent_command_execution"
        if action in {"mcp_tool_execution", "tool_execution"}:
            return "mcp_tool_invocation"
        if action in MANDATORY_HIGH_IMPACT_ACTIONS:
            return "outbound_gated_action"
        return None

    def verify_transport_lock(self, node_id: str) -> bool:
        """
        Synchronously verifies that the peer is communication over 
        a cryptographically established and VERIFIED WireGuard tunnel.
        """
        from backend.services.arda_fabric import get_arda_fabric
        fabric = get_arda_fabric()
        peer = fabric.known_peers.get(node_id)
        
        if not peer:
            return False
            
        # Hardening: Check for real WireGuard public key AND the verification flag from the handshake
        has_real_transport = peer.get("wg_pubkey") != "local-only"
        is_verified = peer.get("is_peer_verified", False)
        
        if not (has_real_transport and is_verified):
            logger.warning(f"OutboundGate: Transport Lock VIOLATION for {node_id}. (Verified:{is_verified})")
            return False
            
        return True

    def attach_required_companions(
        self,
        *,
        payload: Dict[str, Any],
        spec: Dict[str, Any],
    ) -> List[str]:
        existing = [str(x) for x in (payload.get("required_companions") or []) if x]
        required = [str(x) for x in (spec.get("required_companions") or []) if x]
        merged = list(dict.fromkeys(existing + required))
        payload["required_companions"] = merged
        return merged

    def open_edge_context(
        self,
        *,
        action_type: str,
        action_id: str,
        payload: Dict[str, Any],
        polyphonic_context: Dict[str, Any],
        gate_seen_at_ms: int,
        world_state_bound: bool,
    ) -> Dict[str, Any]:
        edge_type = self._edge_type_for_action(action_type)
        if not edge_type:
            return {}
        spec_obj = self.chorus.load_edge_chorus_spec(
            edge_type=edge_type,
            genre_mode=str(payload.get("genre_mode") or polyphonic_context.get("genre_mode") or ""),
        )
        spec = _model_dump(spec_obj)
        required_companions = self.attach_required_companions(payload=payload, spec=spec)
        dispatch_ts = payload.get("dispatch_created_at_ms")
        try:
            dispatch_ts = int(float(dispatch_ts)) if dispatch_ts is not None else None
        except Exception:
            dispatch_ts = None
        observed_participants = ["outbound_gate"]
        observed_sequence = ["outbound_gate"]
        state_events = ["edge_opened"]
        timestamps_ms = {"edge_opened": float(gate_seen_at_ms), "outbound_gate": float(gate_seen_at_ms)}
        if dispatch_ts is not None:
            observed_participants.insert(0, "dispatch")
            observed_sequence.insert(0, "dispatch")
            timestamps_ms["dispatch"] = float(dispatch_ts)
        if world_state_bound:
            insertion_index = 1 if observed_participants and observed_participants[0] == "dispatch" else 0
            observed_participants.insert(insertion_index, "world_state_bind")
            observed_sequence.insert(insertion_index, "world_state_bind")
            state_events.append("state_bound_to_action")
            timestamps_ms["world_state_bind"] = float(gate_seen_at_ms)
        edge_context = {
            "edge_type": edge_type,
            "action_id": action_id,
            "required_companions": required_companions,
            "required_participants": list(spec.get("required_participants") or []),
            "optional_participants": list(spec.get("optional_participants") or []),
            "expected_sequence": list(spec.get("expected_sequence") or []),
            "settlement_timeout_ms": spec.get("settlement_timeout_ms"),
            "observed_participants": observed_participants,
            "observed_sequence": observed_sequence,
            "timestamps_ms": timestamps_ms,
            "state_events": state_events,
            "audit_events": [],
            "vns_events": [],
            "opened_at_ms": int(gate_seen_at_ms),
        }
        polyphonic_context["chorus_spec"] = spec
        polyphonic_context["edge_observation"] = {
            "action_id": action_id,
            "edge_type": edge_type,
            "observed_participants": observed_participants,
            "observed_sequence": observed_sequence,
            "timestamps_ms": timestamps_ms,
            "audit_events": [],
            "state_events": state_events,
            "vns_events": [],
            "missing_participants": [],
            "unexpected_participants": [],
        }
        polyphonic_context["edge_type"] = edge_type
        polyphonic_context["edge_context"] = edge_context
        return edge_context

    async def emit_edge_opened_event(
        self,
        *,
        edge_context: Dict[str, Any],
        refs: List[str],
        actor: str,
    ) -> None:
        if emit_world_event is None or self.db is None or not edge_context:
            return
        try:
            await emit_world_event(
                self.db,
                event_type="edge_opened",
                entity_refs=refs,
                payload={
                    "edge_type": edge_context.get("edge_type"),
                    "action_id": edge_context.get("action_id"),
                    "actor": actor,
                    "required_participants": edge_context.get("required_participants") or [],
                    "required_companions": edge_context.get("required_companions") or [],
                    "settlement_timeout_ms": edge_context.get("settlement_timeout_ms"),
                    "state_events": edge_context.get("state_events") or [],
                    "timestamps_ms": edge_context.get("timestamps_ms") or {},
                },
                trigger_triune=False,
                source="outbound_gate",
            )
        except Exception:
            logger.debug("Failed to emit edge_opened event", exc_info=True)

    def attach_gate_timing_observation(
        self,
        *,
        actor: str,
        action_type: str,
        payload: Dict[str, Any],
        polyphonic_context: Dict[str, Any],
        target_domain: str,
        impact_level: str,
        notation_valid: bool,
        gate_seen_at_ms: int,
    ) -> Dict[str, Any]:
        dispatch_created_at_ms = payload.get("dispatch_created_at_ms")
        if dispatch_created_at_ms is None and isinstance(polyphonic_context, dict):
            dispatch_created_at_ms = (polyphonic_context.get("harmonic_timeline") or {}).get(
                "dispatch_created_at_ms"
            )
        try:
            dispatch_created_at_ms = int(float(dispatch_created_at_ms)) if dispatch_created_at_ms is not None else None
        except Exception:
            dispatch_created_at_ms = None
        gate_lag_ms = (
            max(0, int(gate_seen_at_ms - dispatch_created_at_ms))
            if dispatch_created_at_ms is not None
            else None
        )
        harmonic_observation = self.harmonic.score_observation(
            actor_id=str(actor or "unknown"),
            tool_name=str(payload.get("command_type") or payload.get("tool") or action_type),
            target_domain=target_domain,
            environment=self.environment,
            stage="gate",
            timestamp_ms=float(gate_seen_at_ms),
            operation=action_type,
            context={
                "impact_level": impact_level,
                "notation_valid": notation_valid,
                "gate_lag_ms": gate_lag_ms,
            },
        )
        if isinstance(polyphonic_context, dict):
            polyphonic_context["timing_features"] = harmonic_observation.get("timing_features")
            polyphonic_context["harmonic_state"] = harmonic_observation.get("harmonic_state")
            polyphonic_context["baseline_ref"] = harmonic_observation.get("baseline_ref")
            history = list(polyphonic_context.get("harmonic_history") or [])
            history.append(
                {
                    "stage": "gate",
                    "timestamp_ms": gate_seen_at_ms,
                    "harmonic_state": harmonic_observation.get("harmonic_state"),
                }
            )
            polyphonic_context["harmonic_history"] = history[-20:]
            timeline = dict(polyphonic_context.get("harmonic_timeline") or {})
            if dispatch_created_at_ms is not None:
                timeline.setdefault("dispatch_created_at_ms", dispatch_created_at_ms)
            timeline["gate_seen_at_ms"] = gate_seen_at_ms
            if gate_lag_ms is not None:
                timeline["gate_lag_ms"] = gate_lag_ms
            polyphonic_context["harmonic_timeline"] = timeline
        return {
            "dispatch_created_at_ms": dispatch_created_at_ms,
            "gate_lag_ms": gate_lag_ms,
            "harmonic_observation": harmonic_observation,
        }

    def refresh_harmonic_state(
        self,
        *,
        actor: str,
        action_type: str,
        payload: Dict[str, Any],
        polyphonic_context: Dict[str, Any],
        target_domain: str,
        impact_level: str,
        notation_valid: bool,
        gate_seen_at_ms: int,
    ) -> Dict[str, Any]:
        return self.attach_gate_timing_observation(
            actor=actor,
            action_type=action_type,
            payload=payload,
            polyphonic_context=polyphonic_context,
            target_domain=target_domain,
            impact_level=impact_level,
            notation_valid=notation_valid,
            gate_seen_at_ms=gate_seen_at_ms,
        )

    async def gate_action(
        self,
        *,
        action_type: str,
        actor: str,
        payload: Dict[str, Any],
        impact_level: str = "high",
        subject_id: Optional[str] = None,
        entity_refs: Optional[List[str]] = None,
        requires_triune: bool = True,
        polyphonic_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Queue action for approval. Mandatory for high-impact action types."""
        normalized_action = str(action_type or "unknown").strip().lower()
        normalized_impact = self._normalize_impact(impact_level)
        resolved_polyphonic_context = polyphonic_context or payload.get("polyphonic_context") or {}
        gate_seen_at_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        voice_profile = (
            resolved_polyphonic_context.get("voice_profile")
            if isinstance(resolved_polyphonic_context, dict)
            else {}
        )

        # Governance hardening: these paths cannot skip triune and cannot be low impact.
        if normalized_action in MANDATORY_HIGH_IMPACT_ACTIONS:
            requires_triune = True
            if IMPACT_ORDER[normalized_impact] < IMPACT_ORDER["high"]:
                normalized_impact = "high"

        scope = str(
            (payload.get("target_domain") or (payload.get("parameters") or {}).get("target_domain") or "global")
        )
        active_epoch = await self.epoch_service.get_active_epoch(scope=scope)
        active_epoch_doc = (
            active_epoch.model_dump() if (active_epoch is not None and hasattr(active_epoch, "model_dump")) else (
                active_epoch.dict() if active_epoch is not None else {}
            )
        )
        notation_token = None
        notation_token_id = None
        if isinstance(resolved_polyphonic_context, dict):
            notation_token = resolved_polyphonic_context.get("notation_token")
            notation_token_id = resolved_polyphonic_context.get("notation_token_id")
            if active_epoch is not None:
                resolved_polyphonic_context.setdefault("governance_epoch", active_epoch.epoch_id)
                resolved_polyphonic_context.setdefault("score_id", active_epoch.score_id)
                resolved_polyphonic_context.setdefault("genre_mode", active_epoch.genre_mode)
                resolved_polyphonic_context.setdefault("strictness_level", active_epoch.strictness_level)
                resolved_polyphonic_context.setdefault("world_state_hash", active_epoch.world_state_hash)
        notation_token = notation_token or payload.get("notation_token")
        notation_token_id = notation_token_id or payload.get("notation_token_id")
        if (not notation_token and not notation_token_id) and active_epoch is not None:
            try:
                issued = await self.notation_tokens.mint_notation_token(
                    epoch_id=active_epoch.epoch_id,
                    score_id=active_epoch.score_id,
                    genre_mode=active_epoch.genre_mode,
                    voice_role=str((voice_profile or {}).get("voice_type") or "governance_voice"),
                    capability_class=str((voice_profile or {}).get("capability_class") or "governance"),
                    world_state_hash=active_epoch.world_state_hash,
                    issued_to=str(subject_id or actor or "unknown"),
                    entry_window_ms=payload.get("entry_window_ms") or [0, 300000],
                    sequence_slot=payload.get("sequence_slot"),
                    required_companions=payload.get("required_companions") or [],
                    response_class=normalized_action,
                    ttl_seconds=int(payload.get("notation_ttl_seconds") or 600),
                )
                notation_token = issued.model_dump() if hasattr(issued, "model_dump") else issued.dict()
                notation_token_id = notation_token.get("token_id")
                if isinstance(resolved_polyphonic_context, dict):
                    resolved_polyphonic_context["notation_token"] = notation_token
                    resolved_polyphonic_context["notation_token_id"] = notation_token_id
                    resolved_polyphonic_context["notation_auto_issued"] = True
            except Exception:
                logger.debug("Failed auto-issuing notation token in gate_action", exc_info=True)
        enforcement_profile = self.notation_tokens.resolve_enforcement_profile(
            genre_mode=(active_epoch.genre_mode if active_epoch is not None else payload.get("genre_mode")),
            strictness_level=(
                active_epoch.strictness_level if active_epoch is not None else payload.get("strictness_level")
            ),
        )
        validation_context = {
            "baseline_time": payload.get("created_at") or payload.get("requested_at"),
            "observed_slot": payload.get("sequence_slot"),
            "observed_companions": payload.get("observed_companions") or [],
            "enforce_sequence_slot": bool(enforcement_profile.get("enforce_sequence_slot", False)),
            "enforce_required_companions": bool(enforcement_profile.get("enforce_required_companions", False)),
        }
        notation_validation = await self.notation_tokens.validate_notation_token(
            token=notation_token or notation_token_id,
            active_epoch=active_epoch_doc if active_epoch_doc else None,
            world_state_hash=(
                active_epoch.world_state_hash
                if active_epoch is not None
                else (resolved_polyphonic_context.get("world_state_hash") if isinstance(resolved_polyphonic_context, dict) else None)
            ),
            context=validation_context,
        )
        notation_checks = notation_validation.get("checks") or {}
        notation_valid = bool(notation_validation.get("valid"))
        notation_failure_reason = ";".join(notation_validation.get("reasons") or []) or None
        world_state_hash_match = bool(notation_checks.get("world_state_hash_match", False))
        epoch_match = bool(notation_checks.get("epoch_match", False))
        score_match = bool(notation_checks.get("score_match", False))
        if isinstance(resolved_polyphonic_context, dict):
            if notation_validation.get("token"):
                resolved_polyphonic_context["notation_token"] = notation_validation.get("token")
                resolved_polyphonic_context["notation_token_id"] = (
                    (notation_validation.get("token") or {}).get("token_id")
                )
                notation_token_id = (notation_validation.get("token") or {}).get("token_id")
            if active_epoch is not None:
                resolved_polyphonic_context["governance_epoch_descriptor"] = active_epoch_doc
            resolved_polyphonic_context["notation_enforcement_profile"] = notation_validation.get(
                "enforcement_profile"
            )

        action_id = payload.get("command_id") or payload.get("action_id") or secrets.token_hex(8)
        world_state_bound = bool(
            (active_epoch is not None and active_epoch.world_state_hash)
            or payload.get("world_state_hash")
            or (
                resolved_polyphonic_context.get("world_state_hash")
                if isinstance(resolved_polyphonic_context, dict)
                else None
            )
        )
        edge_context: Dict[str, Any] = (
            self.open_edge_context(
                action_type=normalized_action,
                action_id=str(action_id),
                payload=payload,
                polyphonic_context=(
                    resolved_polyphonic_context if isinstance(resolved_polyphonic_context, dict) else {}
                ),
                gate_seen_at_ms=gate_seen_at_ms,
                world_state_bound=world_state_bound,
            )
            if isinstance(resolved_polyphonic_context, dict)
            else {}
        )

        dispatch_created_at_ms = None
        gate_lag_ms = None
        harmonic_observation: Dict[str, Any] = {}
        try:
            harmonic_payload = self.refresh_harmonic_state(
                actor=str(actor),
                action_type=normalized_action,
                payload=payload,
                polyphonic_context=(
                    resolved_polyphonic_context
                    if isinstance(resolved_polyphonic_context, dict)
                    else {}
                ),
                target_domain=scope,
                impact_level=normalized_impact,
                notation_valid=notation_valid,
                gate_seen_at_ms=gate_seen_at_ms,
            )
            dispatch_created_at_ms = harmonic_payload.get("dispatch_created_at_ms")
            gate_lag_ms = harmonic_payload.get("gate_lag_ms")
            harmonic_observation = harmonic_payload.get("harmonic_observation") or {}
            if hasattr(vns, "update_domain_pulse"):
                pulse_state = vns.update_domain_pulse(
                    domain=scope,
                    timing_features=harmonic_observation.get("timing_features") or {},
                    harmonic_state=harmonic_observation.get("harmonic_state") or {},
                    timestamp_ms=gate_seen_at_ms,
                )
                if (
                    pulse_state
                    and float(pulse_state.get("pulse_stability_index") or 1.0) < 0.45
                    and hasattr(vns_alert_service, "alert_pulse_instability_by_domain")
                ):
                    vns_alert_service.alert_pulse_instability_by_domain(pulse_state)
                    if edge_context:
                        (edge_context.setdefault("vns_events", [])).append("pulse_instability_warning")
            timing_features = harmonic_observation.get("timing_features") or {}
            if (
                float(timing_features.get("drift_norm") or 0.0) >= 0.6
                and hasattr(vns_alert_service, "alert_harmonic_drift_detected")
            ):
                vns_alert_service.alert_harmonic_drift_detected(
                    {
                        "scope": scope,
                        "action_type": normalized_action,
                        "actor": actor,
                        "drift_norm": timing_features.get("drift_norm"),
                        "confidence": float(
                            (harmonic_observation.get("harmonic_state") or {}).get("confidence") or 0.0
                        ),
                    }
                )
                if edge_context:
                    (edge_context.setdefault("vns_events", [])).append("harmonic_drift_detected")
            if (
                float(timing_features.get("burstiness") or 0.0) >= 0.6
                and hasattr(vns_alert_service, "alert_burst_cluster_detected")
            ):
                vns_alert_service.alert_burst_cluster_detected(
                    {
                        "scope": scope,
                        "action_type": normalized_action,
                        "burstiness": timing_features.get("burstiness"),
                        "discord_score": float(
                            (harmonic_observation.get("harmonic_state") or {}).get("discord_score") or 0.0
                        ),
                    }
                )
                if edge_context:
                    (edge_context.setdefault("vns_events", [])).append("burst_cluster_detected")
            discord = float((harmonic_observation.get("harmonic_state") or {}).get("discord_score") or 0.0)
            if discord >= 0.7 and hasattr(vns_alert_service, "alert_discord_threshold_crossed"):
                vns_alert_service.alert_discord_threshold_crossed(
                    {
                        "scope": scope,
                        "action_type": normalized_action,
                        "actor": actor,
                        "discord_score": discord,
                        "confidence": float(
                            (harmonic_observation.get("harmonic_state") or {}).get("confidence") or 0.0
                        ),
                    }
                )
                if edge_context:
                    (edge_context.setdefault("vns_events", [])).append("discord_threshold_crossed")
        except Exception:
            logger.debug("Failed to compute gate harmonic observation", exc_info=True)

        if edge_context and isinstance(resolved_polyphonic_context, dict):
            edge_observation = dict(resolved_polyphonic_context.get("edge_observation") or {})
            if not edge_observation:
                edge_observation = {
                    "action_id": str(action_id),
                    "edge_type": edge_context.get("edge_type"),
                    "observed_participants": [],
                    "observed_sequence": [],
                    "timestamps_ms": {},
                    "audit_events": [],
                    "state_events": [],
                    "vns_events": [],
                    "missing_participants": [],
                    "unexpected_participants": [],
                }
            edge_observation["vns_events"] = list(dict.fromkeys(edge_context.get("vns_events") or []))
            resolved_polyphonic_context["edge_observation"] = edge_observation
            resolved_polyphonic_context["edge_context"] = edge_context

        now = datetime.now(timezone.utc).isoformat()
        queue_id = secrets.token_hex(8)
        decision_id = secrets.token_hex(8)

        refs = [r for r in (entity_refs or []) if r]
        if subject_id and subject_id not in refs:
            refs.insert(0, subject_id)
        if isinstance(voice_profile, dict):
            if voice_profile.get("component_id"):
                refs.append(str(voice_profile.get("component_id")))
            if voice_profile.get("voice_type"):
                refs.append(str(voice_profile.get("voice_type")))

        payload_with_polyphonic = dict(payload or {})
        if resolved_polyphonic_context:
            payload_with_polyphonic["polyphonic_context"] = resolved_polyphonic_context
        if edge_context:
            payload_with_polyphonic["edge_type"] = edge_context.get("edge_type")
            payload_with_polyphonic["edge_context"] = edge_context
            payload_with_polyphonic["required_companions"] = edge_context.get("required_companions") or []
            payload_with_polyphonic["settlement_timeout_ms"] = edge_context.get("settlement_timeout_ms")
        payload_with_polyphonic["gate_seen_at_ms"] = gate_seen_at_ms
        if gate_lag_ms is not None:
            payload_with_polyphonic["gate_lag_ms"] = gate_lag_ms
        if harmonic_observation:
            payload_with_polyphonic["timing_features_at_gate"] = harmonic_observation.get("timing_features")
            payload_with_polyphonic["harmonic_state_at_gate"] = harmonic_observation.get("harmonic_state")
            payload_with_polyphonic["baseline_ref"] = harmonic_observation.get("baseline_ref")
        if notation_token_id:
            payload_with_polyphonic["notation_token_id"] = notation_token_id
        if active_epoch is not None:
            payload_with_polyphonic.setdefault("governance_epoch", active_epoch.epoch_id)
            payload_with_polyphonic.setdefault("score_id", active_epoch.score_id)
            payload_with_polyphonic.setdefault("genre_mode", active_epoch.genre_mode)
            payload_with_polyphonic.setdefault("strictness_level", active_epoch.strictness_level)
            payload_with_polyphonic.setdefault("world_state_hash", active_epoch.world_state_hash)

        harmonic_state_at_gate = harmonic_observation.get("harmonic_state") if harmonic_observation else {}
        harmonic_discord = float((harmonic_state_at_gate or {}).get("discord_score") or 0.0)
        harmonic_confidence = float((harmonic_state_at_gate or {}).get("confidence") or 0.0)
        harmonic_review_required = bool(
            harmonic_discord >= 0.65
            or (harmonic_discord >= 0.45 and harmonic_confidence < 0.4)
        )
        harmonic_mode_recommendation = (harmonic_state_at_gate or {}).get("mode_recommendation")
        if harmonic_review_required:
            requires_triune = True

        # Constitutional Veto: Mandatory Attestation Guard (Phase D Hardening)
        attestation_state = self.fabric.get_subject_state(str(subject_id or actor or "unknown"))
        is_attestation_failed = attestation_state in {"fallen", "dissonant", "strained", "unknown"}

        # Physical Veto: Transport Lock (Phase Q Hardening)
        transport_verified = self.verify_transport_lock(str(subject_id or actor or "unknown"))

        deny_for_notation = (
            (not notation_valid)
            and normalized_action in MANDATORY_HIGH_IMPACT_ACTIONS
        )
        
        deny_for_attestation = is_attestation_failed and normalized_action in MANDATORY_HIGH_IMPACT_ACTIONS
        
        # Deny if action is high-impact but transport is not cryptographically locked (no WireGuard)
        deny_for_transport = (not transport_verified) and normalized_action in MANDATORY_HIGH_IMPACT_ACTIONS

        is_denied = deny_for_notation or deny_for_attestation or deny_for_transport
        
        queue_status = "denied" if is_denied else "pending"
        decision_status = "denied" if is_denied else "pending"
        execution_status = "skipped" if is_denied else "awaiting_decision"

        queue_doc = {
            "queue_id": queue_id,
            "action_id": action_id,
            "action_type": normalized_action,
            "subject_id": subject_id,
            "actor": actor,
            "impact_level": normalized_impact,
            "payload": payload_with_polyphonic,
            "voice_type": voice_profile.get("voice_type") if isinstance(voice_profile, dict) else None,
            "capability_class": voice_profile.get("capability_class") if isinstance(voice_profile, dict) else None,
            "polyphonic_context": resolved_polyphonic_context or None,
            "edge_type": edge_context.get("edge_type") if edge_context else None,
            "edge_context": edge_context or None,
            "governance_epoch": active_epoch.epoch_id if active_epoch is not None else None,
            "score_id": active_epoch.score_id if active_epoch is not None else None,
            "genre_mode": active_epoch.genre_mode if active_epoch is not None else None,
            "strictness_level": active_epoch.strictness_level if active_epoch is not None else None,
            "world_state_hash": active_epoch.world_state_hash if active_epoch is not None else None,
            "notation_token_id": notation_token_id,
            "notation_valid": notation_valid,
            "notation_failure_reason": notation_failure_reason,
            "notation_enforcement_profile": notation_validation.get("enforcement_profile"),
            "world_state_hash_match": world_state_hash_match,
            "epoch_match": epoch_match,
            "score_match": score_match,
            "gate_seen_at_ms": gate_seen_at_ms,
            "gate_lag_ms": gate_lag_ms,
            "timing_features_at_gate": harmonic_observation.get("timing_features") if harmonic_observation else None,
            "harmonic_state_at_gate": harmonic_observation.get("harmonic_state") if harmonic_observation else None,
            "baseline_ref": harmonic_observation.get("baseline_ref") if harmonic_observation else None,
            "harmonic_review_required": harmonic_review_required,
            "harmonic_mode_recommendation": harmonic_mode_recommendation,
            "status": queue_status,
            "execution_status": execution_status,
            "created_at": now,
            "updated_at": now,
        }

        decision_doc = {
            "decision_id": decision_id,
            "related_queue_id": queue_id,
            "action_id": action_id,
            "action_type": normalized_action,
            "subject_id": subject_id,
            "actor": actor,
            "source": "outbound_gate",
            "status": decision_status,
            "execution_status": execution_status,
            "voice_type": voice_profile.get("voice_type") if isinstance(voice_profile, dict) else None,
            "capability_class": voice_profile.get("capability_class") if isinstance(voice_profile, dict) else None,
            "polyphonic_context": resolved_polyphonic_context or None,
            "edge_type": edge_context.get("edge_type") if edge_context else None,
            "edge_context": edge_context or None,
            "governance_epoch": active_epoch.epoch_id if active_epoch is not None else None,
            "score_id": active_epoch.score_id if active_epoch is not None else None,
            "genre_mode": active_epoch.genre_mode if active_epoch is not None else None,
            "strictness_level": active_epoch.strictness_level if active_epoch is not None else None,
            "world_state_hash": active_epoch.world_state_hash if active_epoch is not None else None,
            "notation_token_id": notation_token_id,
            "notation_valid": notation_valid,
            "notation_failure_reason": notation_failure_reason,
            "notation_enforcement_profile": notation_validation.get("enforcement_profile"),
            "world_state_hash_match": world_state_hash_match,
            "epoch_match": epoch_match,
            "score_match": score_match,
            "gate_seen_at_ms": gate_seen_at_ms,
            "gate_lag_ms": gate_lag_ms,
            "timing_features_at_gate": harmonic_observation.get("timing_features") if harmonic_observation else None,
            "harmonic_state_at_gate": harmonic_observation.get("harmonic_state") if harmonic_observation else None,
            "baseline_ref": harmonic_observation.get("baseline_ref") if harmonic_observation else None,
            "harmonic_review_required": harmonic_review_required,
            "harmonic_mode_recommendation": harmonic_mode_recommendation,
            "status": decision_status,
            "created_at": now,
            "updated_at": now,
            "notes": (
                f"Notation denied before triune approval: {normalized_action} | {notation_failure_reason}"
                if deny_for_notation
                else (
                    f"Attestation denied: subject '{subject_id or actor}' is {attestation_state.upper()}"
                    if deny_for_attestation
                    else f"Queued for triune approval: {normalized_action}"
                )
            ),
        }

        try:
            await self.db.triune_outbound_queue.insert_one(queue_doc)
            await self.db.triune_decisions.insert_one(decision_doc)
        except Exception as exc:
            logger.exception("Failed to gate outbound action '%s': %s", normalized_action, exc)
            raise

        if edge_context:
            await self.emit_edge_opened_event(
                edge_context=edge_context,
                refs=refs + [action_id, queue_id, decision_id],
                actor=str(actor or "unknown"),
            )

        if emit_world_event is not None and self.db is not None:
            try:
                await emit_world_event(
                    self.db,
                    event_type="outbound_gate_action_queued",
                    entity_refs=refs + [action_id, queue_id, decision_id],
                    payload={
                        "status": queue_status,
                        "action_type": normalized_action,
                        "impact_level": normalized_impact,
                        "actor": actor,
                        "voice_type": voice_profile.get("voice_type") if isinstance(voice_profile, dict) else None,
                        "capability_class": voice_profile.get("capability_class") if isinstance(voice_profile, dict) else None,
                        "polyphonic_context": resolved_polyphonic_context or None,
                        "edge_type": edge_context.get("edge_type") if edge_context else None,
                        "edge_context": edge_context or None,
                        "governance_epoch": active_epoch.epoch_id if active_epoch is not None else None,
                        "score_id": active_epoch.score_id if active_epoch is not None else None,
                        "genre_mode": active_epoch.genre_mode if active_epoch is not None else None,
                        "world_state_hash": active_epoch.world_state_hash if active_epoch is not None else None,
                        "notation_token_id": notation_token_id,
                        "notation_valid": notation_valid,
                        "notation_failure_reason": notation_failure_reason,
                        "notation_enforcement_profile": notation_validation.get("enforcement_profile"),
                        "world_state_hash_match": world_state_hash_match,
                        "epoch_match": epoch_match,
                        "score_match": score_match,
                        "gate_seen_at_ms": gate_seen_at_ms,
                        "gate_lag_ms": gate_lag_ms,
                        "timing_features_at_gate": harmonic_observation.get("timing_features") if harmonic_observation else None,
                        "harmonic_state_at_gate": harmonic_observation.get("harmonic_state") if harmonic_observation else None,
                        "harmonic_review_required": harmonic_review_required,
                        "harmonic_mode_recommendation": harmonic_mode_recommendation,
                    },
                    trigger_triune=requires_triune,
                    source="outbound_gate",
                )
            except Exception:
                logger.debug("World event emit failed for queued outbound action", exc_info=True)

        return {
            "status": "denied" if is_denied else "queued",
            "action_id": action_id,
            "queue_id": queue_id,
            "decision_id": decision_id,
            "action_type": normalized_action,
            "impact_level": normalized_impact,
            "voice_type": voice_profile.get("voice_type") if isinstance(voice_profile, dict) else None,
            "capability_class": voice_profile.get("capability_class") if isinstance(voice_profile, dict) else None,
            "polyphonic_context": resolved_polyphonic_context or None,
            "edge_type": edge_context.get("edge_type") if edge_context else None,
            "edge_context": edge_context or None,
            "governance_epoch": active_epoch.epoch_id if active_epoch is not None else None,
            "score_id": active_epoch.score_id if active_epoch is not None else None,
            "genre_mode": active_epoch.genre_mode if active_epoch is not None else None,
            "world_state_hash": active_epoch.world_state_hash if active_epoch is not None else None,
            "notation_token_id": notation_token_id,
            "notation_valid": notation_valid,
            "notation_failure_reason": notation_failure_reason,
            "notation_enforcement_profile": notation_validation.get("enforcement_profile"),
            "world_state_hash_match": world_state_hash_match,
            "epoch_match": epoch_match,
            "score_match": score_match,
            "gate_seen_at_ms": gate_seen_at_ms,
            "gate_lag_ms": gate_lag_ms,
            "timing_features_at_gate": harmonic_observation.get("timing_features") if harmonic_observation else None,
            "harmonic_state_at_gate": harmonic_observation.get("harmonic_state") if harmonic_observation else None,
            "harmonic_review_required": harmonic_review_required,
            "harmonic_mode_recommendation": harmonic_mode_recommendation,
            "message": (
                "Action denied due to notation validation failure"
                if deny_for_notation
                else "Action queued for triune approval"
            ),
        }

    async def enqueue_command_for_approval(self, agent_id: str, command: Dict[str, Any]) -> Dict[str, Any]:
        """Backward-compatible command-gating wrapper."""
        return await self.gate_action(
            action_type="agent_command",
            actor="system",
            payload=command,
            impact_level="high",
            subject_id=agent_id,
            entity_refs=[agent_id, command.get("command_id")],
            requires_triune=True,
        )
