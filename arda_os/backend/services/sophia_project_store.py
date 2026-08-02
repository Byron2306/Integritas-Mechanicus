"""Durable project store for Sophia Writing Desk evidence ledgers.

The store is intentionally stdlib-only because the Presence server often runs
as a lightweight local bridge. Records are separated by project identity so an
uploaded Fides paper cannot silently inherit Gospel/BEAST ledger state.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "sophia.project_store.v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_slug(value: str, fallback: str = "project") -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value or "").strip("-._").lower()
    return slug[:80] or fallback


def _sha256_text(value: str, length: int = 16) -> str:
    return hashlib.sha256((value or "").encode("utf-8", errors="ignore")).hexdigest()[:length]


def _issue_label(value: Any) -> str:
    return str(value or "").split(":", 1)[0].strip().lower()


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as tmp:
        json.dump(payload, tmp, indent=2, sort_keys=True, default=str)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


class SophiaProjectStore:
    """Small file-backed project/version/ledger store."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.projects_dir = self.root / "projects"
        self.events_path = self.root / "events.jsonl"
        self.projects_dir.mkdir(parents=True, exist_ok=True)

    def derive_project_identity(
        self,
        *,
        session_token: str = "",
        document_name: str = "",
        document_hash: str = "",
        draft_text: str = "",
        explicit_project_id: str = "",
    ) -> Dict[str, Any]:
        """Derive a stable project identity from explicit ID or active document."""
        if explicit_project_id:
            project_id = _clean_slug(explicit_project_id)
            basis = "explicit_project_id"
        else:
            draft_hash = _sha256_text(draft_text[:12000], 16) if draft_text else ""
            identity_material = "|".join(
                part for part in (session_token[:24], document_name, document_hash, draft_hash) if part
            )
            if not identity_material:
                identity_material = f"sessionless-{_now()}"
            project_id = f"{_clean_slug(document_name or 'writing-desk')}-{_sha256_text(identity_material, 12)}"
            basis = "active_document_or_draft_hash"
        return {
            "project_id": project_id,
            "identity_basis": basis,
            "document_name": document_name,
            "document_hash": document_hash,
        }

    def _project_path(self, project_id: str) -> Path:
        return self.projects_dir / _clean_slug(project_id) / "project.json"

    def _load_project(self, project_id: str) -> Dict[str, Any]:
        path = self._project_path(project_id)
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "schema_version": SCHEMA_VERSION,
            "project_id": project_id,
            "created_at": _now(),
            "updated_at": _now(),
            "draft_versions": [],
            "uploaded_documents": [],
            "retrieved_sources": [],
            "claim_ledger": [],
            "intervention_ledger": [],
            "source_pool": [],
            "mandos_category": "writing_desk",
        }

    def _save_project(self, project: Dict[str, Any]) -> None:
        project["updated_at"] = _now()
        _atomic_write_json(self._project_path(str(project["project_id"])), project)

    def _append_event(self, event: Dict[str, Any]) -> None:
        self.events_path.parent.mkdir(parents=True, exist_ok=True)
        with self.events_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True, default=str) + "\n")

    def upsert_project(
        self,
        *,
        project_id: str,
        session_token: str = "",
        document_name: str = "",
        document_hash: str = "",
        mandos_category: str = "writing_desk",
    ) -> Dict[str, Any]:
        project = self._load_project(project_id)
        project["session_token_hash"] = _sha256_text(session_token, 16) if session_token else project.get("session_token_hash", "")
        project["mandos_category"] = mandos_category or project.get("mandos_category") or "writing_desk"
        if document_name or document_hash:
            doc_record = {
                "document_name": document_name,
                "document_hash": document_hash,
                "seen_at": _now(),
            }
            existing = {
                (doc.get("document_name"), doc.get("document_hash"))
                for doc in project.get("uploaded_documents", [])
                if isinstance(doc, dict)
            }
            if (document_name, document_hash) not in existing:
                project.setdefault("uploaded_documents", []).append(doc_record)
        self._save_project(project)
        return project

    def add_draft_version(
        self,
        *,
        project_id: str,
        draft_text: str,
        source: str = "writing_desk",
        line_start: int = 1,
        line_end: int = 1,
    ) -> Dict[str, Any]:
        project = self._load_project(project_id)
        draft_hash = _sha256_text(draft_text, 24)
        version_id = f"draft-{draft_hash}"
        version = {
            "version_id": version_id,
            "draft_hash": draft_hash,
            "source": source,
            "line_start": line_start,
            "line_end": line_end,
            "word_count": len(re.findall(r"\S+", draft_text or "")),
            "created_at": _now(),
        }
        if not any(v.get("version_id") == version_id for v in project.get("draft_versions", [])):
            project.setdefault("draft_versions", []).append(version)
            self._save_project(project)
            self._append_event({"event": "draft_version_added", "project_id": project_id, **version})
        return version

    def append_claim_records(
        self,
        *,
        project_id: str,
        draft_version_id: str,
        records: Iterable[Dict[str, Any]],
    ) -> Dict[str, Any]:
        project = self._load_project(project_id)
        existing = {str(item.get("record_id") or ""): item for item in project.get("claim_ledger", [])}
        appended = 0
        updated = 0
        for raw in records:
            record = dict(raw or {})
            record_id = str(record.get("record_id") or "")
            if not record_id:
                material = "|".join(
                    str(record.get(key) or "")[:500]
                    for key in ("claim", "source_name", "exact_span", "status")
                )
                record_id = f"claim-{_sha256_text(material, 18)}"
            record.update({
                "record_id": record_id,
                "project_id": project_id,
                "draft_version_id": draft_version_id,
                "schema_version": SCHEMA_VERSION,
                "updated_at": _now(),
            })
            if record_id in existing:
                prior = existing[record_id]
                prior.update(record)
                prior.setdefault("created_at", record.get("created_at") or _now())
                updated += 1
            else:
                record.setdefault("created_at", _now())
                project.setdefault("claim_ledger", []).append(record)
                existing[record_id] = record
                appended += 1
        self._save_project(project)
        self._append_event({
            "event": "claim_records_appended",
            "project_id": project_id,
            "draft_version_id": draft_version_id,
            "appended": appended,
            "updated": updated,
            "at": _now(),
        })
        return {
            "project_id": project_id,
            "draft_version_id": draft_version_id,
            "appended": appended,
            "updated": updated,
            "total_claim_records": len(project.get("claim_ledger", [])),
        }

    def append_intervention_record(
        self,
        *,
        project_id: str,
        draft_version_id: str,
        record: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Persist a pedagogical intervention for ipsative review."""
        project = self._load_project(project_id)
        payload = dict(record or {})
        material = "|".join(
            str(payload.get(key) or "")[:500]
            for key in ("task", "selected_excerpt", "pedagogical_move", "next_revision_move")
        )
        created_at = str(payload.get("created_at") or _now())
        intervention_id = str(payload.get("intervention_id") or f"intervention-{_sha256_text(material + '|' + created_at, 18)}")
        payload.update({
            "intervention_id": intervention_id,
            "project_id": project_id,
            "draft_version_id": draft_version_id,
            "schema_version": SCHEMA_VERSION,
            "created_at": created_at,
            "updated_at": _now(),
        })
        existing = {
            str(item.get("intervention_id") or ""): item
            for item in project.get("intervention_ledger", [])
            if isinstance(item, dict)
        }
        if intervention_id in existing:
            existing[intervention_id].update(payload)
            action = "updated"
        else:
            project.setdefault("intervention_ledger", []).append(payload)
            action = "appended"
        self._save_project(project)
        self._append_event({
            "event": "intervention_record_appended",
            "project_id": project_id,
            "draft_version_id": draft_version_id,
            "intervention_id": intervention_id,
            "action": action,
            "at": _now(),
        })
        return {
            "project_id": project_id,
            "draft_version_id": draft_version_id,
            "intervention_id": intervention_id,
            "action": action,
            "total_interventions": len(project.get("intervention_ledger", [])),
        }

    def append_retrieved_sources(
        self,
        *,
        project_id: str,
        sources: Iterable[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Attach retrieved source leads to a project without claiming support."""
        project = self._load_project(project_id)
        existing = {
            str(item.get("source_id") or item.get("title") or item.get("url") or "")
            for item in project.get("retrieved_sources", [])
            if isinstance(item, dict)
        }
        appended = 0
        for index, raw in enumerate(sources):
            if not isinstance(raw, dict):
                continue
            title = str(raw.get("title") or raw.get("source") or raw.get("name") or f"Retrieved Source {index + 1}").strip()
            url = str(raw.get("url") or raw.get("doi") or "").strip()
            material = "|".join(part for part in (title, url, str(raw.get("year") or "")) if part)
            source_id = str(raw.get("source_id") or f"source-{_sha256_text(material, 18)}")
            if source_id in existing:
                continue
            record = {
                "source_id": source_id,
                "title": title,
                "url": raw.get("url") or "",
                "doi": raw.get("doi") or "",
                "year": raw.get("year") or "",
                "authors": raw.get("authors") or [],
                "summary": raw.get("summary") or raw.get("abstract") or "",
                "source": raw.get("source") or raw.get("provider") or "academic_retrieval",
                "quality": raw.get("quality") or raw.get("quality_score"),
                "relevance": raw.get("relevance") or raw.get("relevance_score"),
                "captured_at": _now(),
                "support_status": "lead_only_unmapped",
            }
            project.setdefault("retrieved_sources", []).append(record)
            existing.add(source_id)
            appended += 1
        self._save_project(project)
        self._append_event({
            "event": "retrieved_sources_appended",
            "project_id": project_id,
            "appended": appended,
            "at": _now(),
        })
        return {
            "project_id": project_id,
            "appended": appended,
            "total_retrieved_sources": len(project.get("retrieved_sources", [])),
        }

    def append_source_records(
        self,
        *,
        project_id: str,
        sources: Iterable[Dict[str, Any]],
    ) -> Dict[str, Any]:
        project = self._load_project(project_id)
        existing = {
            (str(item.get("name") or ""), str(item.get("text_hash") or ""))
            for item in project.get("source_pool", [])
            if isinstance(item, dict)
        }
        appended = 0
        for raw in sources:
            if not isinstance(raw, dict):
                continue
            text = str(raw.get("text") or "")
            record = {
                "name": str(raw.get("name") or "Unnamed source"),
                "category": str(raw.get("category") or raw.get("source_type") or "session_source"),
                "text_hash": _sha256_text(text, 24) if text else "",
                "char_count": len(text),
                "recorded_at": _now(),
            }
            key = (record["name"], record["text_hash"])
            if key in existing:
                continue
            project.setdefault("source_pool", []).append(record)
            existing.add(key)
            appended += 1
        self._save_project(project)
        if appended:
            self._append_event({
                "event": "source_records_appended",
                "project_id": project_id,
                "appended": appended,
                "at": _now(),
            })
        return {
            "project_id": project_id,
            "appended": appended,
            "total_source_records": len(project.get("source_pool", [])),
        }

    def summarize_project(self, project_id: str) -> Dict[str, Any]:
        project = self._load_project(project_id)
        records = [r for r in project.get("claim_ledger", []) if isinstance(r, dict)]
        interventions = [r for r in project.get("intervention_ledger", []) if isinstance(r, dict)]
        status_counts: Dict[str, int] = {}
        for record in records:
            status = str(record.get("status") or "open")
            status_counts[status] = status_counts.get(status, 0) + 1
        issue_counts: Dict[str, int] = {}
        office_counts: Dict[str, int] = {}
        for item in interventions:
            office = str(((item.get("pedagogical_plan") or {}).get("selected_office")) or item.get("office") or "unknown")
            office_counts[office] = office_counts.get(office, 0) + 1
            for finding in item.get("findings") or []:
                label = str(finding).split(":", 1)[0].strip().lower() or "unknown"
                issue_counts[label] = issue_counts.get(label, 0) + 1
        repeated_weakness_types = [
            {"issue": key, "count": value}
            for key, value in sorted(issue_counts.items(), key=lambda pair: (-pair[1], pair[0]))
            if value >= 2
        ][:8]
        improvement = self._latest_intervention_improvement(interventions)
        return {
            "schema_version": SCHEMA_VERSION,
            "project_id": project_id,
            "draft_versions": len(project.get("draft_versions", [])),
            "uploaded_documents": len(project.get("uploaded_documents", [])),
            "retrieved_sources": len(project.get("retrieved_sources", [])),
            "source_pool": len(project.get("source_pool", [])),
            "source_pool_records": len(project.get("source_pool", [])),
            "claim_records": len(records),
            "intervention_records": len(interventions),
            "status_counts": status_counts,
            "pedagogy_office_counts": office_counts,
            "repeated_weakness_types": repeated_weakness_types,
            "latest_intervention_improvement": improvement,
            "weak_warrants": sum(1 for r in records if str(r.get("status") or "") in {"warrant-needed", "partial"}),
            "missing_limitations": sum(1 for r in records if not str(r.get("limitation") or "").strip()),
            "unsupported_claims": sum(1 for r in records if str(r.get("status") or "") in {"needs-source", "unsupported", "contradicted"}),
            "updated_at": project.get("updated_at"),
        }

    @staticmethod
    def _latest_intervention_improvement(interventions: List[Dict[str, Any]]) -> Dict[str, Any]:
        if len(interventions) < 2:
            return {
                "status": "insufficient_history",
                "prior_issue_count": None,
                "latest_issue_count": None,
                "resolved_issue_labels": [],
                "new_issue_labels": [],
                "persistent_issue_labels": [],
                "interpretation": "Need at least two Writing Desk interventions on this project to estimate revision movement.",
            }
        ordered = sorted(interventions, key=lambda item: str(item.get("created_at") or ""))
        prior = ordered[-2]
        latest = ordered[-1]
        prior_labels = {
            _issue_label(item)
            for item in prior.get("findings") or []
            if _issue_label(item)
        }
        latest_labels = {
            _issue_label(item)
            for item in latest.get("findings") or []
            if _issue_label(item)
        }
        resolved = sorted(prior_labels - latest_labels)
        new = sorted(latest_labels - prior_labels)
        persistent = sorted(prior_labels & latest_labels)
        prior_count = len(prior_labels)
        latest_count = len(latest_labels)
        if latest_count < prior_count and len(new) <= len(resolved):
            status = "improved"
        elif latest_count > prior_count or new:
            status = "regressed_or_new_risk"
        elif persistent:
            status = "stable_unresolved"
        else:
            status = "stable_clear"
        return {
            "status": status,
            "prior_intervention_id": prior.get("intervention_id"),
            "latest_intervention_id": latest.get("intervention_id"),
            "prior_issue_count": prior_count,
            "latest_issue_count": latest_count,
            "resolved_issue_labels": resolved,
            "new_issue_labels": new,
            "persistent_issue_labels": persistent,
            "interpretation": {
                "improved": "Latest feedback shows fewer or weaker issue labels than the prior intervention.",
                "regressed_or_new_risk": "Latest feedback introduced new issue labels or increased the issue count.",
                "stable_unresolved": "The same issue labels remain visible; Sophia should scaffold the repeated pattern.",
                "stable_clear": "Neither the prior nor latest intervention shows issue labels.",
            }.get(status, "Compare the two interventions before making a learning claim."),
        }

    def load_project(self, project_id: str) -> Dict[str, Any]:
        return self._load_project(project_id)

    def contamination_report(self, project_ids: Iterable[str]) -> Dict[str, Any]:
        ids = [str(project_id) for project_id in project_ids if str(project_id or "").strip()]
        projects = [self._load_project(project_id) for project_id in ids]
        document_sets = []
        source_sets = []
        claim_sets = []
        for project in projects:
            document_sets.append({
                str(doc.get("document_hash") or "")
                for doc in project.get("uploaded_documents", [])
                if isinstance(doc, dict) and str(doc.get("document_hash") or "")
            })
            source_sets.append({
                (str(src.get("name") or ""), str(src.get("text_hash") or ""))
                for src in project.get("source_pool", [])
                if isinstance(src, dict)
            })
            claim_sets.append({
                str(record.get("record_id") or "")
                for record in project.get("claim_ledger", [])
                if isinstance(record, dict) and str(record.get("record_id") or "")
            })

        pairwise = []
        contamination_signals = 0
        for i, left_id in enumerate(ids):
            for j, right_id in enumerate(ids):
                if j <= i:
                    continue
                shared_documents = sorted(document_sets[i] & document_sets[j])
                shared_sources = sorted(f"{name}|{text_hash}" for name, text_hash in (source_sets[i] & source_sets[j]))
                shared_claim_records = sorted(claim_sets[i] & claim_sets[j])
                if shared_documents or shared_claim_records:
                    contamination_signals += 1
                pairwise.append({
                    "left_project_id": left_id,
                    "right_project_id": right_id,
                    "shared_document_hashes": shared_documents,
                    "shared_source_records": shared_sources,
                    "shared_claim_record_ids": shared_claim_records,
                })
        return {
            "schema_version": SCHEMA_VERSION,
            "project_count": len(ids),
            "pair_count": len(pairwise),
            "contamination_signals": contamination_signals,
            "pairwise": pairwise,
            "passed": contamination_signals == 0,
        }


_STORE: Optional[SophiaProjectStore] = None


def get_sophia_project_store(evidence_dir: Path) -> SophiaProjectStore:
    global _STORE
    root = Path(evidence_dir) / "sophia_project_store"
    if _STORE is None or _STORE.root != root:
        _STORE = SophiaProjectStore(root)
    return _STORE
