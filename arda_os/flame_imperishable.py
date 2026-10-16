import logging
import os
import uuid
import base64
from typing import Optional
from backend.services.tpm_attestation_service import get_tpm_service

logger = logging.getLogger(__name__)

class FlameImperishableService:
    """
    Manages the 'Flame Imperishable' (Sealed HMAC Key).
    Ensures that the secret fire of the telemetry chain 
    is bound to the physical hardware state (PCRs 0, 1, 7).
    """
    
    def __init__(self, seal_path: str = "/run/seraph/flame_imperishable.sealed"):
        self.seal_path = seal_path
        self._unsealed_key: Optional[str] = None
        self._is_mock = os.environ.get("TPM_MOCK_ENV") != "production"

    async def initialize_flame(self) -> str:
        """
        Attempts to unseal the key. If it doesn't exist, generates and seals it.
        This provides a 'Secret Fire' that is bound to the lawful boot state.
        """
        if os.path.exists(self.seal_path):
            logger.info("PHASE VI: Found existing Flame Imperishable blob. Unsealing...")
            unsealed = await self._unseal_key()
            if unsealed:
                self._unsealed_key = unsealed.decode()
                return self._unsealed_key
            else:
                logger.error("PHASE VI: Unsealing FAILED. Boot state may be UNLAWFUL.")
        
        # Generation path (First lawful boot or lost key)
        logger.info("PHASE VI: Generating new Flame Imperishable (Secret Fire)...")
        new_key = uuid.uuid4().hex.encode()
        await self._seal_key(new_key)
        self._unsealed_key = new_key.decode()
        return self._unsealed_key

    async def get_key(self) -> str:
        """Returns the unsealed key, or falls back to environment if unsealing failed."""
        if self._unsealed_key:
            return self._unsealed_key
        
        # Fallback for degraded/mock environments
        return os.environ.get('TELEMETRY_SIGNING_KEY', 'default-key-change-me')

    async def _seal_key(self, key: bytes):
        """Seals the key to the hardware TPM."""
        tpm = get_tpm_service()
        sealed_blob = await tpm.tpm_seal(key, pcr_indices=[0, 1, 7])
        
        if sealed_blob:
            os.makedirs(os.path.dirname(self.seal_path), exist_ok=True)
            with open(self.seal_path, "wb") as f:
                f.write(sealed_blob)
            logger.info(f"PHASE VI: Secret Fire sealed and persisted at {self.seal_path}")
        else:
            logger.error("PHASE VI: FAILED to seal the secret fire to hardware.")

    async def _unseal_key(self) -> Optional[bytes]:
        """Unseals the key from the hardware TPM."""
        if not os.path.exists(self.seal_path):
            return None
            
        with open(self.seal_path, "rb") as f:
            sealed_blob = f.read()
            
        tpm = get_tpm_service()
        return await tpm.tpm_unseal(sealed_blob, pcr_indices=[0, 1, 7])

# Singleton instance
flame_imperishable_service = FlameImperishableService()

def get_flame_imperishable_service():
    return flame_imperishable_service
