"""
Token Broker / Secrets Vault
============================
Secure token issuance with scoped capability tokens.
Never exposes refresh tokens or secrets to agents/LLMs.
"""

import os
import json
import hashlib
import hmac
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import base64

logger = logging.getLogger(__name__)


@dataclass
class CapabilityToken:
    """Scoped capability token for tool access"""
    token_id: str
    token_type: str             # "capability" / "access"
    
    # Binding
    principal: str              # Who can use this token
    principal_identity: str     # SPIFFE ID or cert fingerprint
    audience: str               # Tool gateway
    
    # Scope
    action: str
    targets: List[str]
    tool_id: Optional[str]
    
    # Limits
    expires_at: str
    max_uses: int
    uses_remaining: int
    constraints: Dict[str, Any]
    
    # Signature
    signature: str
    
    # Metadata
    issued_at: str
    issuer: str
    nonce: str
    governance_decision_id: Optional[str] = None
    governance_queue_id: Optional[str] = None
    # Phase 1 placeholder seams for polyphonic notation/token work.
    polyphonic_token_context: Optional[Dict[str, Any]] = None
    future_notation_token_ref: Optional[str] = None


@dataclass
class SecretEntry:
    """Encrypted secret storage"""
    secret_id: str
    secret_type: str            # "api_key" / "oauth_refresh" / "password" / "private_key"
    owner: str                  # Service or user that owns this secret
    
    # Encrypted value (only broker can decrypt)
    encrypted_value: str
    
    # Metadata (not encrypted)
    created_at: str
    expires_at: Optional[str]
    rotation_schedule: Optional[str]
    last_accessed: Optional[str]
    access_count: int
    
    # Access control
    allowed_principals: List[str]
    allowed_scopes: List[str]


class TokenBroker:
    """
    Secure token broker / secrets vault.
    
    Features:
    - Never exposes raw secrets to agents/LLMs
    - Issues short-lived, scoped capability tokens
    - Automatic revocation on trust degradation
    - Audit logging of all secret access
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
        
        # Master encryption key (in production, use HSM/KMS)
        self.master_key = os.environ.get('BROKER_MASTER_KEY', secrets.token_hex(32))
        self.signing_key = os.environ.get('BROKER_SIGNING_KEY', secrets.token_hex(32))
        
        # Token storage
        self.active_tokens: Dict[str, CapabilityToken] = {}
        self.revoked_tokens: set = set()
        
        # Secret storage (in production, use proper vault)
        self.secrets: Dict[str, SecretEntry] = {}
        
        # Token usage tracking
        self.token_uses: Dict[str, int] = defaultdict(int)
        
        # Access audit log
        self.access_log: List[Dict] = []
        self.token_admin_audit_log: List[Dict] = []
        self.db = None
        
        logger.info("Token Broker / Secrets Vault initialized")

    def set_db(self, db: Any) -> None:
        self.db = db

    @staticmethod
    def _governance_required_for_admin_actions() -> bool:
        allow_ungoverned = str(os.environ.get("TOKEN_BROKER_ALLOW_UNGOVERNED_ADMIN_ACTIONS", "false")).lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        return not allow_ungoverned

    def _assert_approved_governance_context(
        self,
        governance_context: Optional[Dict[str, Any]],
        *,
        operation: str,
    ) -> Dict[str, Any]:
        if not self._governance_required_for_admin_actions():
            return {}
        context = governance_context or {}
        if not context.get("approved"):
            raise PermissionError(f"Approved governance context required for token broker operation '{operation}'")
        decision_id = context.get("decision_id")
        queue_id = context.get("queue_id")
        if not decision_id and not queue_id:
            raise PermissionError(
                f"Governance context for token broker operation '{operation}' must include decision_id or queue_id"
            )
        return {
            "decision_id": decision_id,
            "queue_id": queue_id,
            "action_type": context.get("action_type"),
        }

    def _audit_token_admin_action(
        self,
        *,
        operation: str,
        actor: str,
        token_id: Optional[str],
        principal: Optional[str],
        governance_context: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.token_admin_audit_log.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "operation": operation,
                "actor": actor,
                "token_id": token_id,
                "principal": principal,
                "decision_id": governance_context.get("decision_id"),
                "queue_id": governance_context.get("queue_id"),
                "metadata": metadata or {},
            }
        )
    
    def _encrypt(self, plaintext: str) -> str:
        """Simple encryption (in production, use proper crypto)"""
        # XOR with key-derived pad (demo only - use AES-GCM in production)
        key_bytes = hashlib.sha256(self.master_key.encode()).digest()
        plaintext_bytes = plaintext.encode()
        encrypted = bytes(p ^ k for p, k in zip(plaintext_bytes, key_bytes * (len(plaintext_bytes) // len(key_bytes) + 1)))
        return base64.b64encode(encrypted).decode()
    
    def _decrypt(self, ciphertext: str) -> str:
        """Simple decryption"""
        key_bytes = hashlib.sha256(self.master_key.encode()).digest()
        encrypted = base64.b64decode(ciphertext)
        decrypted = bytes(e ^ k for e, k in zip(encrypted, key_bytes * (len(encrypted) // len(key_bytes) + 1)))
        return decrypted.decode()
    
    def _sign_token(self, token_data: Dict) -> str:
        """Sign token data"""
        payload = json.dumps(token_data, sort_keys=True)
        return hmac.new(self.signing_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    
    def _verify_token_signature(self, token: CapabilityToken) -> bool:
        """Verify token signature"""
        token_data = {
            "token_id": token.token_id,
            "principal": token.principal,
            "action": token.action,
            "targets": token.targets,
            "expires_at": token.expires_at,
            "nonce": token.nonce
        }
        expected = self._sign_token(token_data)
        return hmac.compare_digest(expected, token.signature)
    
    # =========================================================================
    # SECRET MANAGEMENT
    # =========================================================================
    
    def store_secret(self, secret_id: str, secret_type: str, value: str,
                     owner: str, allowed_principals: List[str] = None,
                     allowed_scopes: List[str] = None,
                     expires_at: str = None) -> bool:
        """Store a secret securely"""
        
        entry = SecretEntry(
            secret_id=secret_id,
            secret_type=secret_type,
            owner=owner,
            encrypted_value=self._encrypt(value),
            created_at=datetime.now(timezone.utc).isoformat(),
            expires_at=expires_at,
            rotation_schedule=None,
            last_accessed=None,
            access_count=0,
            allowed_principals=allowed_principals or [owner],
            allowed_scopes=allowed_scopes or ["*"]
        )
        
        self.secrets[secret_id] = entry
        
        logger.info(f"SECRET: Stored {secret_type} '{secret_id}' for {owner}")
        
        return True
    
    def get_secret(self, secret_id: str, principal: str, 
                   scope: str = "*") -> Tuple[Optional[str], str]:
        """
        Get a secret (internal use only).
        Returns (value, message) tuple.
        """
        if secret_id not in self.secrets:
            return None, "Secret not found"
        
        entry = self.secrets[secret_id]
        
        # Check principal permission
        if principal not in entry.allowed_principals and "*" not in entry.allowed_principals:
            self._log_access(secret_id, principal, "denied", "Principal not allowed")
            return None, "Access denied"
        
        # Check scope
        if scope not in entry.allowed_scopes and "*" not in entry.allowed_scopes:
            self._log_access(secret_id, principal, "denied", "Scope not allowed")
            return None, "Scope not allowed"
        
        # Check expiry
        if entry.expires_at:
            exp = datetime.fromisoformat(entry.expires_at.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > exp:
                self._log_access(secret_id, principal, "denied", "Secret expired")
                return None, "Secret expired"
        
        # Update access tracking
        entry.last_accessed = datetime.now(timezone.utc).isoformat()
        entry.access_count += 1
        
        self._log_access(secret_id, principal, "granted", "Success")
        
        return self._decrypt(entry.encrypted_value), "Success"
    
    def _log_access(self, secret_id: str, principal: str, 
                    result: str, message: str):
        """Log secret access"""
        self.access_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "secret_id": secret_id,
            "principal": principal,
            "result": result,
            "message": message
        })
    
    def rotate_secret(self, secret_id: str, new_value: str) -> bool:
        """Rotate a secret"""
        if secret_id not in self.secrets:
            return False
        
        self.secrets[secret_id].encrypted_value = self._encrypt(new_value)
        self.secrets[secret_id].created_at = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"SECRET: Rotated '{secret_id}'")
        
        return True
    
    def revoke_secret(self, secret_id: str) -> bool:
        """Revoke a secret"""
        if secret_id in self.secrets:
            del self.secrets[secret_id]
            logger.info(f"SECRET: Revoked '{secret_id}'")
            return True
        return False
    
    # =========================================================================
    # CAPABILITY TOKEN MANAGEMENT
    # =========================================================================
    
    def issue_token(self, principal: str, principal_identity: str,
                    action: str, targets: List[str],
                    tool_id: str = None, ttl_seconds: int = 300,
                    max_uses: int = 1, constraints: Dict = None,
                    governance_context: Optional[Dict[str, Any]] = None,
                    polyphonic_token_context: Optional[Dict[str, Any]] = None,
                    future_notation_token_ref: Optional[str] = None,
                    issued_by: str = "unknown") -> CapabilityToken:
        """
        Issue a scoped capability token.
        
        Args:
            principal: Who is requesting
            principal_identity: SPIFFE ID or cert fingerprint (for binding)
            action: What action is allowed
            targets: What targets are allowed
            tool_id: Optional specific tool
            ttl_seconds: Token lifetime
            max_uses: Maximum uses
            constraints: Additional constraints
        
        Returns:
            CapabilityToken
        """
        import uuid
        governance = self._assert_approved_governance_context(
            governance_context,
            operation="issue_token",
        )
        
        token_id = f"tok-{uuid.uuid4().hex[:16]}"
        nonce = secrets.token_hex(8)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(seconds=ttl_seconds)
        
        # Build token data for signing
        token_data = {
            "token_id": token_id,
            "principal": principal,
            "action": action,
            "targets": targets,
            "expires_at": expires.isoformat(),
            "nonce": nonce
        }
        
        signature = self._sign_token(token_data)
        
        merged_constraints = dict(constraints or {})
        if governance.get("decision_id"):
            merged_constraints.setdefault("governance_decision_id", governance.get("decision_id"))
        if governance.get("queue_id"):
            merged_constraints.setdefault("governance_queue_id", governance.get("queue_id"))

        token = CapabilityToken(
            token_id=token_id,
            token_type="capability",
            principal=principal,
            principal_identity=principal_identity,
            audience="tool_gateway",
            action=action,
            targets=targets,
            tool_id=tool_id,
            expires_at=expires.isoformat(),
            max_uses=max_uses,
            uses_remaining=max_uses,
            constraints=merged_constraints,
            signature=signature,
            issued_at=now.isoformat(),
            issuer="token_broker",
            nonce=nonce,
            governance_decision_id=governance.get("decision_id"),
            governance_queue_id=governance.get("queue_id"),
            polyphonic_token_context=polyphonic_token_context or None,
            future_notation_token_ref=future_notation_token_ref or None,
        )
        
        self.active_tokens[token_id] = token
        self._audit_token_admin_action(
            operation="issue_token",
            actor=issued_by,
            token_id=token_id,
            principal=principal,
            governance_context=governance,
            metadata={
                "action": action,
                "targets": targets,
                "tool_id": tool_id,
                "ttl_seconds": ttl_seconds,
                "future_notation_token_ref": future_notation_token_ref,
                "polyphonic_token_context": polyphonic_token_context or {},
            },
        )
        
        logger.info(
            "TOKEN: Issued %s for %s | Action: %s | TTL: %ss | decision=%s queue=%s",
            token_id,
            principal,
            action,
            ttl_seconds,
            governance.get("decision_id"),
            governance.get("queue_id"),
        )
        
        return token
    
    def issue_constitutional_token(self, **kwargs) -> CapabilityToken:
        """
        Issue a high-security constitutional capability token.
        Requires valid boot truth, herald identity, and order state.
        """
        try:
            from services.boot_attestation import boot_attestation
            from services.manwe_herald import manwe_herald
            from services.world_model import WorldModelService
        except Exception:
            from backend.services.boot_attestation import boot_attestation
            from backend.services.manwe_herald import manwe_herald
            from backend.services.world_model import WorldModelService

        # 1. Check Boot Truth
        bundle = boot_attestation.get_current_bundle()
        if not bundle or bundle.status != "lawful":
             logger.error("Constitutional Token: Birth is UNLAWFUL. Refusing to issue.")
             raise PermissionError("Unlawful boot state detected; constitutional actions prohibited.")
             
        # 2. Check Herald
        herald = manwe_herald.get_state()
        if not herald or herald.status != "active":
             logger.error("Constitutional Token: No active Herald detected. Refusing to issue.")
             raise PermissionError("No active constitutional herald found; manifestation prohibited.")

        # 3. Augment constraints
        constraints = kwargs.get("constraints", {})
        constraints.update({
             "boot_truth_id": bundle.bundle_id,
             "herald_id": herald.herald_id,
             "runtime_identity": herald.runtime_identity,
             "constitutional": True
        })
        
        # 4. Standard issuance with constitutional context
        return self.issue_token(
             **kwargs,
             constraints=constraints,
             issued_by=herald.herald_id
        )

    def validate_token(self, token_id: str, principal: str,
                       principal_identity: str, action: str,
                       target: str) -> Tuple[bool, str]:
        """
        Validate a capability token.
        
        Returns (valid, message) tuple.
        """
        # Check if revoked
        if token_id in self.revoked_tokens:
            return False, "Token revoked"
        
        # Check if exists
        if token_id not in self.active_tokens:
            return False, "Token not found"
        
        token = self.active_tokens[token_id]
        
        # Verify signature
        if not self._verify_token_signature(token):
            return False, "Invalid token signature"
        
        # Check principal binding
        if token.principal != principal:
            return False, "Token not bound to this principal"
        
        if token.principal_identity != principal_identity:
            return False, "Token identity mismatch"
        
        # Check expiry
        exp = datetime.fromisoformat(token.expires_at.replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > exp:
            del self.active_tokens[token_id]
            return False, "Token expired"
        
        # Check action
        if token.action != action:
            return False, f"Token not valid for action '{action}'"
        
        # Check target
        if target not in token.targets and "*" not in token.targets:
            return False, f"Token not valid for target '{target}'"
        
        # Check uses
        if token.uses_remaining <= 0:
            del self.active_tokens[token_id]
            return False, "Token usage exhausted"
        
        # Decrement uses
        token.uses_remaining -= 1
        
        if token.uses_remaining <= 0:
            del self.active_tokens[token_id]
        
        logger.debug(f"TOKEN: Validated {token_id} | Remaining uses: {token.uses_remaining}")
        
        return True, "Token valid"
    
    def revoke_token(
        self,
        token_id: str,
        *,
        governance_context: Optional[Dict[str, Any]] = None,
        revoked_by: str = "unknown",
    ) -> bool:
        """Revoke a token"""
        governance = self._assert_approved_governance_context(
            governance_context,
            operation="revoke_token",
        )
        principal = None
        if token_id in self.active_tokens:
            principal = self.active_tokens[token_id].principal
        if token_id in self.active_tokens:
            del self.active_tokens[token_id]
        
        self.revoked_tokens.add(token_id)
        self._audit_token_admin_action(
            operation="revoke_token",
            actor=revoked_by,
            token_id=token_id,
            principal=principal,
            governance_context=governance,
            metadata={},
        )
        
        logger.info(
            "TOKEN: Revoked %s | decision=%s queue=%s",
            token_id,
            governance.get("decision_id"),
            governance.get("queue_id"),
        )
        
        return True
    
    def revoke_tokens_for_principal(
        self,
        principal: str,
        *,
        governance_context: Optional[Dict[str, Any]] = None,
        revoked_by: str = "unknown",
    ) -> int:
        """Revoke all tokens for a principal (e.g., on trust degradation)"""
        governance = self._assert_approved_governance_context(
            governance_context,
            operation="revoke_tokens_for_principal",
        )
        count = 0
        
        tokens_to_revoke = [
            tid for tid, tok in self.active_tokens.items()
            if tok.principal == principal
        ]
        
        for token_id in tokens_to_revoke:
            self.revoke_token(
                token_id,
                governance_context=governance_context,
                revoked_by=revoked_by,
            )
            count += 1
        
        self._audit_token_admin_action(
            operation="revoke_tokens_for_principal",
            actor=revoked_by,
            token_id=None,
            principal=principal,
            governance_context=governance,
            metadata={"count": count},
        )
        logger.warning(
            "TOKEN: Revoked %s tokens for principal %s | decision=%s queue=%s",
            count,
            principal,
            governance.get("decision_id"),
            governance.get("queue_id"),
        )
        
        return count
    
    def get_active_tokens(self, principal: str = None) -> List[Dict]:
        """Get active tokens (optionally filtered by principal)"""
        tokens = []
        
        for token in self.active_tokens.values():
            if principal and token.principal != principal:
                continue
            
            # Don't expose signature
            token_dict = asdict(token)
            token_dict['signature'] = '[REDACTED]'
            tokens.append(token_dict)
        
        return tokens
    
    def get_broker_status(self) -> Dict:
        """Get broker status"""
        return {
            "active_tokens": len(self.active_tokens),
            "revoked_tokens": len(self.revoked_tokens),
            "stored_secrets": len(self.secrets),
            "access_log_size": len(self.access_log),
            "token_admin_audit_log_size": len(self.token_admin_audit_log),
        }

    # =========================================================================
    # PHASE 2 NOTATION TOKEN BRIDGE METHODS
    # =========================================================================

    async def issue_notation_token(self, **kwargs) -> Dict[str, Any]:
        try:
            from services.notation_token import get_notation_token_service
        except Exception:
            from backend.services.notation_token import get_notation_token_service
        svc = get_notation_token_service(self.db)
        token = await svc.mint_notation_token(**kwargs)
        return token.model_dump() if hasattr(token, "model_dump") else token.dict()

    async def validate_notation_token(
        self,
        token: Any,
        active_epoch: Any,
        world_state_hash: Optional[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            from services.notation_token import get_notation_token_service
        except Exception:
            from backend.services.notation_token import get_notation_token_service
        svc = get_notation_token_service(self.db)
        return await svc.validate_notation_token(
            token=token,
            active_epoch=active_epoch,
            world_state_hash=world_state_hash,
            context=context or {},
        )

    async def bind_token_to_epoch(
        self,
        token_id: str,
        *,
        epoch_id: str,
        score_id: str,
        genre_mode: str,
    ) -> bool:
        if self.db is None or not hasattr(self.db, "notation_tokens"):
            return False
        result = await self.db.notation_tokens.update_one(
            {"token_id": str(token_id)},
            {
                "$set": {
                    "epoch_id": str(epoch_id),
                    "score_id": str(score_id),
                    "genre_mode": str(genre_mode),
                }
            },
        )
        return bool(getattr(result, "modified_count", 0))

    async def narrow_token_scope(
        self,
        token_id: str,
        *,
        new_entry_window_ms: Optional[List[int]] = None,
        remove_companions: Optional[List[str]] = None,
        new_sequence_slot: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            from services.notation_token import get_notation_token_service
        except Exception:
            from backend.services.notation_token import get_notation_token_service
        svc = get_notation_token_service(self.db)
        return await svc.narrow_token_scope(
            token_id=token_id,
            new_entry_window_ms=new_entry_window_ms,
            remove_companions=remove_companions,
            new_sequence_slot=new_sequence_slot,
            reason=reason,
        )

    async def reissue_notation_token(
        self,
        token_id: str,
        *,
        stricter_score: bool = False,
        reason: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            from services.notation_token import get_notation_token_service
        except Exception:
            from backend.services.notation_token import get_notation_token_service
        svc = get_notation_token_service(self.db)
        return await svc.reissue_notation_token(
            token_id=token_id,
            stricter_score=stricter_score,
            reason=reason,
        )

    async def bind_token_to_world_state(self, token_id: str, *, world_state_hash: str) -> bool:
        if self.db is None or not hasattr(self.db, "notation_tokens"):
            return False
        result = await self.db.notation_tokens.update_one(
            {"token_id": str(token_id)},
            {"$set": {"world_state_hash": str(world_state_hash)}},
        )
        return bool(getattr(result, "modified_count", 0))

    async def revoke_notation_tokens_for_epoch(self, epoch_id: str, reason: Optional[str] = None) -> int:
        try:
            from services.notation_token import get_notation_token_service
        except Exception:
            from backend.services.notation_token import get_notation_token_service
        svc = get_notation_token_service(self.db)
        return await svc.revoke_notation_tokens_for_epoch(str(epoch_id), reason=reason)


# Global singleton
token_broker = TokenBroker()
