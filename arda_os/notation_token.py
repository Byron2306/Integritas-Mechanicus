from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from schemas.polyphonic_models import GovernanceEpoch, NotationToken
except Exception:
    from backend.schemas.polyphonic_models import GovernanceEpoch, NotationToken

try:
    from services.quantum_security import quantum_security
except Exception:
    from backend.services.quantum_security import quantum_security

try:
    from services.world_events import emit_world_event
except Exception:
    try:
        from backend.services.world_events import emit_world_event
    except Exception:
        emit_world_event = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _model_dump(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[no-any-return]
    if hasattr(model, "dict"):
        return model.dict()  # type: ignore[no-any-return]
    if hasattr(model, "__dict__"):
        return dict(model.__dict__)  # type: ignore[no-any-return]
    return dict(model)


def _token_storage_doc(token: NotationToken) -> Dict[str, Any]:
    doc = _model_dump(token)
    for field in ("issued_at", "expires_at"):
        value = doc.get(field)
        if isinstance(value, datetime):
            doc[field] = value.astimezone(timezone.utc).isoformat()
    return doc


class NotationTokenService:
    """Phase 2 notation token lifecycle + validation service."""

    DEFAULT_TTL_SECONDS = 10 * 60
    DEFAULT_ENTRY_WINDOW = [0, 300000]  # 0ms to 5min from baseline

    @staticmethod
    def resolve_enforcement_profile(
        *,
        genre_mode: Optional[str],
        strictness_level: Optional[str],
    ) -> Dict[str, bool]:
        genre = str(genre_mode or "").strip().lower()
        strictness = str(strictness_level or "").strip().lower()
        enforce_sequence = False
        enforce_companions = False
        if strictness in {"strict", "high", "elevated"} or genre in {"fortified"}:
            enforce_sequence = True
        if strictness in {"emergency", "critical"} or genre in {"siege", "containment"}:
            enforce_sequence = True
            enforce_companions = True
        return {
            "enforce_sequence_slot": enforce_sequence,
            "enforce_required_companions": enforce_companions,
        }

    def __init__(self, db: Any = None):
        self.db = db
        self._cache: Dict[str, NotationToken] = {}

    def set_db(self, db: Any) -> None:
        self.db = db

    async def _persist_token(self, token: NotationToken) -> None:
        self._cache[token.token_id] = token
        if self.db is None or not hasattr(self.db, "notation_tokens"):
            return
        await self.db.notation_tokens.update_one(
            {"token_id": token.token_id},
            {"$set": _token_storage_doc(token)},
            upsert=True,
        )

    async def _get_token_from_store(self, token_id: str) -> Optional[NotationToken]:
        cached = self._cache.get(token_id)
        if cached is not None:
            return cached
        if self.db is None or not hasattr(self.db, "notation_tokens"):
            return None
        doc = await self.db.notation_tokens.find_one({"token_id": token_id}, {"_id": 0})
        if not doc:
            return None
        issued_at = _to_datetime(doc.get("issued_at"))
        expires_at = _to_datetime(doc.get("expires_at"))
        if issued_at is None or expires_at is None:
            return None
        token = NotationToken(
            token_id=str(doc.get("token_id")),
            epoch_id=str(doc.get("epoch_id")),
            score_id=str(doc.get("score_id")),
            genre_mode=str(doc.get("genre_mode")),
            voice_role=str(doc.get("voice_role")),
            capability_class=str(doc.get("capability_class")),
            entry_window_ms=list(doc.get("entry_window_ms") or []),
            sequence_slot=doc.get("sequence_slot"),
            required_companions=list(doc.get("required_companions") or []),
            response_class=doc.get("response_class"),
            world_state_hash=str(doc.get("world_state_hash")),
            issued_to=str(doc.get("issued_to")),
            issued_at=issued_at,
            expires_at=expires_at,
            status=str(doc.get("status") or "issued"),
            signature_ref=doc.get("signature_ref"),
        )
        self._cache[token.token_id] = token
        return token

    @staticmethod
    def _resolve_epoch(epoch: Union[GovernanceEpoch, Dict[str, Any], None]) -> Optional[GovernanceEpoch]:
        if epoch is None:
            return None
        if isinstance(epoch, GovernanceEpoch):
            return epoch
        started_at = _to_datetime(epoch.get("started_at"))
        expires_at = _to_datetime(epoch.get("expires_at"))
        if started_at is None or expires_at is None:
            return None
        try:
            return GovernanceEpoch(
                epoch_id=str(epoch.get("epoch_id")),
                score_id=str(epoch.get("score_id")),
                genre_mode=str(epoch.get("genre_mode")),
                strictness_level=str(epoch.get("strictness_level")),
                world_state_hash=str(epoch.get("world_state_hash")),
                started_at=started_at,
                expires_at=expires_at,
                reason=epoch.get("reason"),
                status=str(epoch.get("status") or "active"),
                scope=epoch.get("scope"),
                signature_ref=epoch.get("signature_ref"),
            )
        except Exception:
            return None

    async def mint_notation_token(
        self,
        *,
        epoch_id: str,
        score_id: str,
        genre_mode: str,
        voice_role: str,
        capability_class: str,
        world_state_hash: str,
        issued_to: str,
        entry_window_ms: Optional[List[int]] = None,
        sequence_slot: Optional[int] = None,
        required_companions: Optional[List[str]] = None,
        response_class: Optional[str] = None,
        ttl_seconds: Optional[int] = None,
        token_id: Optional[str] = None,
    ) -> NotationToken:
        now = _utc_now()
        ttl = max(30, int(ttl_seconds or self.DEFAULT_TTL_SECONDS))
        resolved_token_id = str(token_id or f"nt_{now.strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}")
        token = NotationToken(
            token_id=resolved_token_id,
            epoch_id=str(epoch_id),
            score_id=str(score_id),
            genre_mode=str(genre_mode),
            voice_role=str(voice_role),
            capability_class=str(capability_class),
            entry_window_ms=list(entry_window_ms or self.DEFAULT_ENTRY_WINDOW),
            sequence_slot=sequence_slot,
            required_companions=[str(x) for x in (required_companions or []) if x],
            response_class=response_class,
            world_state_hash=str(world_state_hash),
            issued_to=str(issued_to),
            issued_at=now,
            expires_at=now + timedelta(seconds=ttl),
            status="issued",
            signature_ref=None,
        )
        signed = quantum_security.sign_notation_token(_token_storage_doc(token))
        token.signature_ref = signed.get("signature_ref")
        await self._persist_token(token)
        if emit_world_event is not None and self.db is not None:
            await emit_world_event(
                self.db,
                event_type="notation_token_issued",
                entity_refs=[token.token_id, token.epoch_id, token.score_id, token.issued_to],
                payload={
                    "token_id": token.token_id,
                    "epoch_id": token.epoch_id,
                    "score_id": token.score_id,
                    "genre_mode": token.genre_mode,
                    "voice_role": token.voice_role,
                    "capability_class": token.capability_class,
                    "world_state_hash": token.world_state_hash,
                    "entry_window_ms": token.entry_window_ms,
                    "sequence_slot": token.sequence_slot,
                    "required_companions": token.required_companions,
                    "expires_at": token.expires_at.isoformat(),
                    "signature_ref": token.signature_ref,
                },
                trigger_triune=False,
                source="notation_token",
            )
        return token

    @staticmethod
    def enforce_entry_window(
        token: NotationToken,
        now_ms: int,
        baseline_time_ms: Optional[int],
    ) -> bool:
        window = token.entry_window_ms or []
        if len(window) != 2:
            return True
        if baseline_time_ms is None:
            return True
        delta = int(now_ms - baseline_time_ms)
        min_ms = int(window[0])
        max_ms = int(window[1])
        return min_ms <= delta <= max_ms

    @staticmethod
    def enforce_sequence_slot(token: NotationToken, observed_slot: Optional[int]) -> bool:
        if token.sequence_slot is None:
            return True
        if observed_slot is None:
            return False
        return int(token.sequence_slot) == int(observed_slot)

    @staticmethod
    def enforce_required_companions(token: NotationToken, observed_companions: Optional[List[str]]) -> bool:
        required = set(str(x) for x in (token.required_companions or []) if x)
        if not required:
            return True
        observed = set(str(x) for x in (observed_companions or []) if x)
        return required.issubset(observed)

    async def validate_notation_token(
        self,
        token: Union[str, NotationToken, Dict[str, Any], None],
        active_epoch: Union[GovernanceEpoch, Dict[str, Any], None],
        world_state_hash: Optional[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        ctx = context or {}
        resolved_token: Optional[NotationToken] = None
        if token is None:
            resolved_token = None
        elif isinstance(token, NotationToken):
            resolved_token = token
        elif isinstance(token, dict):
            issued_at = _to_datetime(token.get("issued_at"))
            expires_at = _to_datetime(token.get("expires_at"))
            if issued_at is not None and expires_at is not None:
                resolved_token = NotationToken(
                    token_id=str(token.get("token_id")),
                    epoch_id=str(token.get("epoch_id")),
                    score_id=str(token.get("score_id")),
                    genre_mode=str(token.get("genre_mode")),
                    voice_role=str(token.get("voice_role")),
                    capability_class=str(token.get("capability_class")),
                    entry_window_ms=list(token.get("entry_window_ms") or []),
                    sequence_slot=token.get("sequence_slot"),
                    required_companions=list(token.get("required_companions") or []),
                    response_class=token.get("response_class"),
                    world_state_hash=str(token.get("world_state_hash")),
                    issued_to=str(token.get("issued_to")),
                    issued_at=issued_at,
                    expires_at=expires_at,
                    status=str(token.get("status") or "issued"),
                    signature_ref=token.get("signature_ref"),
                )
        else:
            resolved_token = await self._get_token_from_store(str(token))

        checks: Dict[str, bool] = {
            "token_present": resolved_token is not None,
            "token_status_valid": False,
            "token_expiry_valid": False,
            "epoch_match": False,
            "score_match": False,
            "genre_match": False,
            "world_state_hash_match": False,
            "entry_window_valid": False,
            "sequence_slot_valid": False,
            "required_companions_valid": False,
            "signature_valid": False,
        }
        reasons: List[str] = []

        if resolved_token is None:
            reasons.append("notation_token_missing")
            return {"valid": False, "reasons": reasons, "checks": checks, "token": None}

        now = _utc_now()
        checks["token_status_valid"] = resolved_token.status in {"issued", "active"}
        if not checks["token_status_valid"]:
            reasons.append(f"notation_token_status_invalid:{resolved_token.status}")

        checks["token_expiry_valid"] = resolved_token.expires_at > now
        if not checks["token_expiry_valid"]:
            reasons.append("notation_token_expired")

        resolved_epoch = self._resolve_epoch(active_epoch)
        enforcement_profile = self.resolve_enforcement_profile(
            genre_mode=(resolved_epoch.genre_mode if resolved_epoch is not None else resolved_token.genre_mode),
            strictness_level=(resolved_epoch.strictness_level if resolved_epoch is not None else None),
        )
        enforce_sequence_slot = bool(
            ctx.get("enforce_sequence_slot", enforcement_profile.get("enforce_sequence_slot", False))
        )
        enforce_required_companions = bool(
            ctx.get(
                "enforce_required_companions",
                enforcement_profile.get("enforce_required_companions", False),
            )
        )
        if resolved_epoch is None:
            # No active epoch context means we can only validate token internals.
            checks["epoch_match"] = True
            checks["score_match"] = True
            checks["genre_match"] = True
        else:
            checks["epoch_match"] = resolved_token.epoch_id == resolved_epoch.epoch_id
            checks["score_match"] = resolved_token.score_id == resolved_epoch.score_id
            checks["genre_match"] = resolved_token.genre_mode == resolved_epoch.genre_mode
            if not checks["epoch_match"]:
                reasons.append("notation_epoch_mismatch")
            if not checks["score_match"]:
                reasons.append("notation_score_mismatch")
            if not checks["genre_match"]:
                reasons.append("notation_genre_mismatch")

        resolved_world_hash = str(world_state_hash or "").strip()
        if not resolved_world_hash and resolved_epoch is not None:
            resolved_world_hash = str(resolved_epoch.world_state_hash or "").strip()
        if not resolved_world_hash:
            checks["world_state_hash_match"] = True
        else:
            checks["world_state_hash_match"] = resolved_token.world_state_hash == resolved_world_hash
            if not checks["world_state_hash_match"]:
                reasons.append("notation_world_state_hash_mismatch")

        now_ms = int(now.timestamp() * 1000)
        baseline_time_ms = ctx.get("baseline_time_ms")
        if baseline_time_ms is None:
            baseline = ctx.get("baseline_time")
            baseline_dt = _to_datetime(baseline) if baseline is not None else None
            if baseline_dt is not None:
                baseline_time_ms = int(baseline_dt.timestamp() * 1000)
        if baseline_time_ms is None:
            baseline_time_ms = int(resolved_token.issued_at.timestamp() * 1000)
        checks["entry_window_valid"] = self.enforce_entry_window(resolved_token, now_ms, baseline_time_ms)
        if not checks["entry_window_valid"]:
            reasons.append("notation_entry_window_violation")

        observed_slot = ctx.get("observed_slot")
        checks["sequence_slot_valid"] = self.enforce_sequence_slot(resolved_token, observed_slot)
        if not checks["sequence_slot_valid"] and enforce_sequence_slot:
            reasons.append("notation_sequence_slot_violation")

        observed_companions = ctx.get("observed_companions") or []
        checks["required_companions_valid"] = self.enforce_required_companions(
            resolved_token, observed_companions
        )
        if not checks["required_companions_valid"] and enforce_required_companions:
            reasons.append("notation_required_companions_missing")

        checks["signature_valid"] = quantum_security.verify_notation_token_signature(
            _token_storage_doc(resolved_token),
            resolved_token.signature_ref,
        )
        if not checks["signature_valid"]:
            reasons.append("notation_signature_invalid")

        mandatory = (
            checks["token_present"],
            checks["token_status_valid"],
            checks["token_expiry_valid"],
            checks["epoch_match"],
            checks["score_match"],
            checks["genre_match"],
            checks["world_state_hash_match"],
            checks["entry_window_valid"],
            checks["signature_valid"],
        )
        valid = all(mandatory)
        if enforce_sequence_slot:
            valid = valid and checks["sequence_slot_valid"]
        if enforce_required_companions:
            valid = valid and checks["required_companions_valid"]
        return {
            "valid": bool(valid),
            "reasons": reasons,
            "checks": checks,
            "token": _token_storage_doc(resolved_token),
            "enforcement_profile": {
                "enforce_sequence_slot": enforce_sequence_slot,
                "enforce_required_companions": enforce_required_companions,
                "genre_mode": resolved_token.genre_mode,
                "strictness_level": resolved_epoch.strictness_level if resolved_epoch is not None else None,
            },
        }

    async def revoke_notation_token(self, token_id: str, reason: Optional[str] = None) -> bool:
        token = await self._get_token_from_store(str(token_id))
        if token is None:
            return False
        token.status = "revoked"
        await self._persist_token(token)
        if emit_world_event is not None and self.db is not None:
            await emit_world_event(
                self.db,
                event_type="notation_token_revoked",
                entity_refs=[token.token_id, token.epoch_id, token.score_id],
                payload={"token_id": token.token_id, "reason": reason},
                trigger_triune=False,
                source="notation_token",
            )
        return True

    async def consume_notation_token(self, token_id: str, *, outcome: str) -> bool:
        token = await self._get_token_from_store(str(token_id))
        if token is None:
            return False
        token.status = str(outcome or "consumed")
        await self._persist_token(token)
        return True

    async def narrow_token_scope(
        self,
        token_id: str,
        *,
        new_entry_window_ms: Optional[List[int]] = None,
        remove_companions: Optional[List[str]] = None,
        new_sequence_slot: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Phase 6: Narrow the scope of an existing notation token.

        Reduces permissions on a live token without revoking it.  Used by
        governance consequences to constrain a voice that is showing mild
        dissonance without fully revoking its participation.
        """
        token = await self._get_token_from_store(str(token_id))
        if token is None or token.status not in {"issued", "active"}:
            return None

        changed: Dict[str, Any] = {}

        if new_entry_window_ms is not None and len(new_entry_window_ms) == 2:
            old_window = list(token.entry_window_ms or [])
            token.entry_window_ms = list(new_entry_window_ms)
            changed["entry_window_ms"] = {"old": old_window, "new": list(new_entry_window_ms)}

        if remove_companions:
            removed = set(str(c) for c in remove_companions)
            old_companions = list(token.required_companions or [])
            token.required_companions = [c for c in old_companions if c not in removed]
            changed["required_companions"] = {"removed": list(removed)}

        if new_sequence_slot is not None:
            old_slot = token.sequence_slot
            token.sequence_slot = new_sequence_slot
            changed["sequence_slot"] = {"old": old_slot, "new": new_sequence_slot}

        if not changed:
            return {"token_id": token_id, "narrowed": False, "reason": "no_changes_requested"}

        await self._persist_token(token)

        if emit_world_event is not None and self.db is not None:
            await emit_world_event(
                self.db,
                event_type="notation_token_narrowed",
                entity_refs=[token.token_id, token.epoch_id, token.score_id],
                payload={
                    "token_id": token.token_id,
                    "changes": changed,
                    "reason": reason or "governance_consequence_narrowing",
                },
                trigger_triune=False,
                source="notation_token",
            )

        return {"token_id": token_id, "narrowed": True, "changes": changed}

    async def reissue_notation_token(
        self,
        token_id: str,
        *,
        stricter_score: bool = False,
        reason: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Phase 6: Revoke an existing token and mint a fresh replacement.

        The replacement inherits all parameters of the original but can
        optionally tighten the entry window and shorten the TTL when
        ``stricter_score`` is True.
        """
        original = await self._get_token_from_store(str(token_id))
        if original is None:
            return None

        # Revoke the original.
        await self.revoke_notation_token(str(token_id), reason=reason or "reissued")

        # Derive replacement parameters.
        entry_window = list(original.entry_window_ms or self.DEFAULT_ENTRY_WINDOW)
        ttl = max(30, int((original.expires_at - original.issued_at).total_seconds()))
        if stricter_score:
            # Halve the entry window and TTL.
            if len(entry_window) == 2:
                entry_window = [entry_window[0], max(entry_window[0] + 1000, entry_window[1] // 2)]
            ttl = max(30, ttl // 2)

        new_token = await self.mint_notation_token(
            epoch_id=original.epoch_id,
            score_id=original.score_id,
            genre_mode=original.genre_mode,
            voice_role=original.voice_role,
            capability_class=original.capability_class,
            world_state_hash=original.world_state_hash,
            issued_to=original.issued_to,
            entry_window_ms=entry_window,
            sequence_slot=original.sequence_slot,
            required_companions=list(original.required_companions or []),
            response_class=original.response_class,
            ttl_seconds=ttl,
        )

        if emit_world_event is not None and self.db is not None:
            await emit_world_event(
                self.db,
                event_type="notation_token_reissued",
                entity_refs=[original.token_id, new_token.token_id, original.epoch_id],
                payload={
                    "original_token_id": original.token_id,
                    "new_token_id": new_token.token_id,
                    "stricter_score": stricter_score,
                    "reason": reason or "governance_consequence_reissue",
                },
                trigger_triune=False,
                source="notation_token",
            )

        return {
            "original_token_id": original.token_id,
            "new_token_id": new_token.token_id,
            "stricter_score": stricter_score,
            "new_token": _token_storage_doc(new_token),
        }

    async def revoke_notation_tokens_for_epoch(self, epoch_id: str, reason: Optional[str] = None) -> int:
        count = 0
        if self.db is not None and hasattr(self.db, "notation_tokens"):
            cursor = self.db.notation_tokens.find({"epoch_id": str(epoch_id), "status": {"$in": ["issued", "active"]}})
            docs = await cursor.to_list(length=1000)
            for doc in docs:
                token_id = str(doc.get("token_id") or "")
                if token_id and await self.revoke_notation_token(token_id, reason=reason):
                    count += 1
            return count
        # Fallback for in-memory mode.
        for token in list(self._cache.values()):
            if token.epoch_id == str(epoch_id) and token.status in {"issued", "active"}:
                token.status = "revoked"
                self._cache[token.token_id] = token
                count += 1
        return count


_notation_token_service_singleton: Optional[NotationTokenService] = None


def get_notation_token_service(db: Any = None) -> NotationTokenService:
    global _notation_token_service_singleton
    if _notation_token_service_singleton is None:
        _notation_token_service_singleton = NotationTokenService(db=db)
    elif db is not None and _notation_token_service_singleton.db is None:
        _notation_token_service_singleton.set_db(db)
    return _notation_token_service_singleton
