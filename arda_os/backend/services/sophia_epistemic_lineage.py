from __future__ import annotations

import difflib
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

DIO_SCRIPTS = Path.home() / "DIO-Full-Audit" / "scripts"
if str(DIO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DIO_SCRIPTS))

from dio_epistemic_spine import append_hash_chained_event, claim_epistemic_state


def _norm_claim(value: str) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip().casefold()
    text = re.sub(r"[^a-z0-9%.' -]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _fingerprint(value: str) -> str:
    return hashlib.sha256(_norm_claim(value).encode("utf-8")).hexdigest()[:20]


def _support_counts(record: dict[str, Any]) -> tuple[int, int, int]:
    """Classify evidence labels without substring traps such as unsupported→supported."""
    values: list[str] = []
    for key in ["support_status", "entailment_status", "status", "evidence_state"]:
        if record.get(key) is not None:
            values.append(str(record.get(key)).casefold())
    for row in record.get("candidate_support") or []:
        if isinstance(row, dict):
            values.extend([
                str(row.get("support_label") or "").casefold(),
                str(row.get("entailment_status") or "").casefold(),
            ])

    support = partial = contradiction = 0
    for raw in values:
        label = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")

        if any(token in label for token in ["contradict", "refut", "conflict"]):
            contradiction += 1
            continue

        if any(token in label for token in ["partial", "mixed", "qualified", "weak_support"]):
            partial += 1
            continue

        # Explicit absence of support is not support and is not automatically contradiction.
        if label in {
            "unsupported",
            "not_supported",
            "no_support",
            "insufficient_support",
            "unverified",
            "unknown",
            "unmapped",
            "lead_only_unmapped",
        } or label.startswith("unsupported_"):
            continue

        if (
            label in {"supported", "verified", "grounded", "corroborated", "entailed"}
            or label.startswith("supported_")
            or "corroborat" in label
            or "entail" in label
        ):
            support += 1

    return support, partial, contradiction


def derive_epistemic_state(record: dict[str, Any]) -> str:
    status = str(record.get("status") or record.get("support_status") or "").casefold()
    support, partial, contradiction = _support_counts(record)
    return claim_epistemic_state(
        support_count=support,
        partial_support_count=partial,
        contradiction_count=contradiction,
        verification_required=bool(record.get("verification_required") or str(record.get("evidence_risk") or "").casefold() == "high"),
        human_judgment=any(token in status for token in ["author_judgment", "human_judgment", "author owned"]),
        outside_available_evidence=any(token in status for token in ["outside_available_evidence", "out of scope", "unknown_external"]),
    )


def _best_prior(claim: str, ledger: list[dict[str, Any]], draft_version_id: str) -> tuple[dict[str, Any] | None, float]:
    wanted = _norm_claim(claim)
    best = None
    best_score = 0.0
    for row in ledger:
        if not isinstance(row, dict) or not str(row.get("claim") or "").strip():
            continue
        if str(row.get("draft_version_id") or "") == str(draft_version_id or ""):
            continue
        score = difflib.SequenceMatcher(None, wanted, _norm_claim(str(row.get("claim") or ""))).ratio()
        if score > best_score:
            best = row
            best_score = score
    return best, best_score


def enrich_claim_record(record: dict[str, Any], ledger: list[dict[str, Any]], draft_version_id: str) -> dict[str, Any]:
    enriched = dict(record or {})
    claim = str(enriched.get("claim") or "").strip()
    if not claim:
        return enriched
    fingerprint = _fingerprint(claim)
    prior, similarity = _best_prior(claim, ledger, draft_version_id)
    if prior is not None and similarity >= 0.72:
        lineage_id = str(prior.get("claim_lineage_id") or f"lineage-{_fingerprint(str(prior.get('claim') or ''))}")
        parent_record_id = prior.get("record_id")
        relation = "unchanged" if similarity >= 0.985 else "revised"
        previous_state = prior.get("epistemic_state")
    else:
        lineage_id = f"lineage-{fingerprint}"
        parent_record_id = None
        relation = "new"
        previous_state = None
    current_state = derive_epistemic_state(enriched)
    transition = (
        "NEW_CLAIM"
        if previous_state is None
        else "STATE_CHANGED"
        if str(previous_state) != str(current_state)
        else "REVISED_STABLE_STATE"
        if relation == "revised"
        else "UNCHANGED_STATE"
    )
    enriched.update({
        "claim_fingerprint": fingerprint,
        "claim_lineage_id": lineage_id,
        "parent_record_id": parent_record_id,
        "revision_relation": relation,
        "lineage_similarity": round(similarity, 4) if prior is not None else None,
        "previous_epistemic_state": previous_state,
        "epistemic_state": current_state,
        "epistemic_transition": transition,
        "epistemic_schema": "dio.sophia.claim_lineage.v1",
    })
    return enriched


def summarize_claim_lineage(records: list[dict[str, Any]]) -> dict[str, Any]:
    states = Counter(str(row.get("epistemic_state") or "UNSPECIFIED") for row in records if isinstance(row, dict))
    lineages = {str(row.get("claim_lineage_id") or "") for row in records if isinstance(row, dict) and row.get("claim_lineage_id")}
    transitions = Counter(str(row.get("epistemic_transition") or "UNSPECIFIED") for row in records if isinstance(row, dict))
    return {
        "schema": "dio.sophia.claim_lineage_summary.v1",
        "claim_records": len([row for row in records if isinstance(row, dict)]),
        "lineage_count": len(lineages),
        "epistemic_states": dict(states),
        "transitions": dict(transitions),
    }


def append_project_event_chain(root: Path, event: dict[str, Any]) -> None:
    subject_id = str(event.get("project_id") or "sophia-project")
    append_hash_chained_event(
        Path(root) / "events_chain.jsonl",
        str(event.get("event") or "project_event"),
        subject_id,
        dict(event),
    )
