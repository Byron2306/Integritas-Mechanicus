from __future__ import annotations
import time
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from backend.schemas.polyphonic_models import ChorusState, ResonanceScore, VoiceProfile, PolyphonicContext
# from backend.arda.ainur.verdicts import ChoirVerdict (Removed for v2.0 Absolute Sanctuary)

logger = logging.getLogger("arda.resonance")

class ResonanceService:
    """
    The Conductor of the Great Music (Phase 26).
    Orchestrates the Micro, Meso, and Macro choirs to ensure continuous 
    polyphonic resonance across the Arda substrate and Seraph AI.
    """

    def __init__(self):
        self.micro_harmony: float = 1.0  # Substrate (BIOS/TPM)
        self.meso_harmony: float = 1.0   # OS/Memory/Logs
        self.macro_harmony: float = 1.0  # Seraph AI/Application
        self.global_resonance: float = 1.0
        
        self.voices: Dict[str, Dict[str, Any]] = {}
        self.last_update = time.time()
        self.dissonance_alerts: List[str] = []

    def sing_in_choir(self, tier: str, component_id: str, score: float, reasons: List[str] = None):
        """
        Record a 'Voice' in one of the hierarchical choirs.
        """
        tier = tier.lower()
        self.voices[component_id] = {
            "tier": tier,
            "score": score,
            "reasons": reasons or [],
            "timestamp": time.time()
        }
        
        # Update specific tier harmony
        self._recalculate_tier(tier)
        self._recalculate_global()
        
        if score < 0.5:
            msg = f"DISSONANCE DETECTED: {tier.upper()} Choir - {component_id} is strained ({score})"
            logger.warning(msg)
            self.dissonance_alerts.append(msg)

    def _recalculate_tier(self, tier: str):
        tier_voices = [v["score"] for v in self.voices.values() if v["tier"] == tier]
        if not tier_voices:
            return
        
        # In a polyphonic model, the lowest resonance in a tier drags down the whole tier.
        # This prevents "logic layer squatting" where a compromised voice hides in the average.
        new_score = min(tier_voices)
        
        if tier == "micro":
            self.micro_harmony = new_score
        elif tier == "meso":
            self.meso_harmony = new_score
        elif tier == "macro":
            self.macro_harmony = new_score

    def _recalculate_global(self):
        # Choral Handoff: Macro depends on Meso, which depends on Micro.
        # Resonance cascade: Infrasound (Micro) is the baseline.
        self.global_resonance = self.micro_harmony * 0.5 + self.meso_harmony * 0.3 + self.macro_harmony * 0.2
        
        # If Micro is zero, global resonance collapses regardless of others
        if self.micro_harmony == 0:
            self.global_resonance = 0.0

    def get_resonance_spectrum(self) -> Dict[str, float]:
        """Returns the current multi-layered harmony score."""
        return {
            "global": round(self.global_resonance, 4),
            "micro": round(self.micro_harmony, 4),
            "meso": round(self.meso_harmony, 4),
            "macro": round(self.macro_harmony, 4),
            "alerts": self.dissonance_alerts[-5:] # Last 5 alerts
        }

    def reset(self):
        """Resets the choir to its initial harmonic state."""
        self.voices = {}
        self.micro_harmony = 1.0
        self.meso_harmony = 1.0
        self.macro_harmony = 1.0
        self.global_resonance = 1.0
        self.dissonance_alerts = []
        self.last_update = time.time()
        logger.info("ResonanceService: Choral state reset to harmony.")

_resonance_service_singleton: Optional[ResonanceService] = None

def get_resonance_service() -> ResonanceService:
    global _resonance_service_singleton
    if _resonance_service_singleton is None:
        _resonance_service_singleton = ResonanceService()
    return _resonance_service_singleton
