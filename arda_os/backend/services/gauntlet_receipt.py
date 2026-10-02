from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import json

from backend.services.quantum_security import (
    quantum_security,
    sign_native_pqc,
    verify_native_pqc,
)


@dataclass
class SealedGauntletReceipt:
    payload: bytes
    signature: str
    public_key: str
    public_key_fingerprint: str
    key_id: str
    provider: str
    algorithm: str


def build_canonical_receipt(context) -> bytes:
    document = {
        "schema": "arda_witnessed_authority_receipt_v1",
        "run_id": context.run_id,
        "started_at": context.started_at,
        "hostname": context.hostname,
        "enforcement_armed": context.enforcement_armed,
        "native_pqc_verified": context.native_pqc_verified,
        "heralded": context.heralded,
        "witness_digests": dict(
            sorted(context.witness_digests.items())
        ),
        "result": context.result.value,
    }

    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def seal_receipt(
    context,
    key_id: str,
) -> SealedGauntletReceipt:
    payload = build_canonical_receipt(context)
    signature = sign_native_pqc(key_id, payload)

    keypair = quantum_security.key_pairs[key_id]
    public_raw = base64.b64decode(keypair.public_key)

    fingerprint = hashlib.sha3_256(
        public_raw
    ).hexdigest()

    return SealedGauntletReceipt(
        payload=payload,
        signature=signature.signature,
        public_key=keypair.public_key,
        public_key_fingerprint=fingerprint,
        key_id=key_id,
        provider=quantum_security.mode,
        algorithm="ML-DSA-65",
    )


def verify_sealed_receipt(
    sealed: SealedGauntletReceipt,
) -> bool:
    return verify_native_pqc(
        sealed.public_key,
        sealed.payload,
        sealed.signature,
    )
