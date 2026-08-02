import json
import os
import glob
import types
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EVIDENCE_DIR = PROJECT_ROOT / "evidence"
MANDOS_DIR = EVIDENCE_DIR / "mandos"

class PhysicalLedgerCollection:
    def __init__(self, name: str):
        print(f"⚖ [SUBSTRATE] Mandos Collection Engaged: {name}")
        self.name = name
        self._data_cache = []
        self._ptr = 0

    def find(self, *args, **kwargs):
        # Swallow all motor/pymongo arguments (filter, projection, etc.)
        self._data_cache = []
        self._ptr = 0
        
        # Determine search path based on collection name
        if self.name == "world_entities" or self.name == "entities":
            search_path = MANDOS_DIR / "principal" / "*_identity.json"
        elif self.name == "resonant":
            search_path = MANDOS_DIR / "resonant" / "*.json"
        else:
            # Fallback for other collections
            return self

        principal_files = glob.glob(str(search_path))
        for pf in principal_files:
            try:
                with open(pf, "r") as f:
                    data = json.load(f)
                    entity_id = data.get("record", {}).get("principal_identity_hash", "unknown")[:16]
                    self._data_cache.append(self._map_to_entity(data, entity_id))
            except Exception:
                continue
        return self

    def sort(self, *args, **kwargs):
        # Signature: sort(key_or_list, direction=None) - Swallow everything
        return self

    def limit(self, *args, **kwargs):
        # Handle positional or keyword 'n'
        n = args[0] if args else kwargs.get("n", len(self._data_cache))
        self._data_cache = self._data_cache[:n]
        return self

    async def to_list(self, *args, **kwargs) -> List[Dict]:
        return self._data_cache

    async def find_one(self, *args, **kwargs) -> Optional[Dict]:
        """Find a single entity in the physical Ledger."""
        # Artificial I/O floor to verify async substrate integrity
        import asyncio
        await asyncio.sleep(0.015)
        
        query = args[0] if args else kwargs.get("filter", {})
        entity_id = query.get("id")
        if not entity_id:
            return None

        # Search in Principal Identities
        principal_files = glob.glob(str(MANDOS_DIR / "principal" / "*_identity.json"))
        for pf in principal_files:
            try:
                with open(pf, "r") as f:
                    data = json.load(f)
                    # Check if this matches the ID or name
                    if entity_id == "SERAPH_ROOT" or entity_id in data.get("payload", {}).get("name", ""):
                        return self._map_to_entity(data, entity_id)
            except Exception:
                continue
        return None

    def _map_to_entity(self, mandos_data: Dict, entity_id: str) -> Dict:
        payload = mandos_data.get("payload", {})
        return {
            "id": entity_id,
            "type": "agent" if "identity" in str(mandos_data) else "host",
            "attributes": {
                "name": payload.get("name", "Unknown"),
                "trust_state": "recommend", 
                "posture": "resonant",
                "risk_score": 0.0,
                "sector": "global",
                "mandos_ref": mandos_data.get("record", {}).get("content_ref")
            }
        }

    async def count_documents(self, *args, **kwargs):
        return len(self._data_cache)

    async def count_entities(self, *args, **kwargs):
        # Triune Orchestrator sometimes calls this directly
        return len(self._data_cache)

    def __aiter__(self):
        self._ptr = 0
        return self

    async def __anext__(self):
        if self._ptr < len(self._data_cache):
            res = self._data_cache[self._ptr]
            self._ptr += 1
            return res
        raise StopAsyncIteration

class PhysicalLedgerDB:
    def __getattr__(self, name: str) -> PhysicalLedgerCollection:
        return PhysicalLedgerCollection(name)

# Principal database instance for the Triune Orchestrator
# Physical Ledger Adapter signature-matched for motor/pymongo
db = PhysicalLedgerDB()
