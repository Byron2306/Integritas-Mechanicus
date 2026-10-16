"""Sophia Phase 5 pedagogical adaptivity orchestrator.

This layer selects a pedagogical office and compact teaching plan for Writing
Desk work. It is deliberately deterministic and inspectable: theory informs the
move, but Sophia does not hide behind theory names or replace the learner's
authorship.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


OFFICES = {
    "auto": "Auto",
    "supervisor": "Supervisor",
    "peer_reviewer": "Peer reviewer",
    "methodologist": "Methodologist",
    "source_librarian": "Source librarian",
    "integrity_auditor": "Integrity auditor",
    "writing_coach": "Writing coach",
    "examiner": "Examiner",
    "novice_scaffold": "Novice scaffold",
    "expert_challenge": "Expert challenge",
}


@dataclass
class PedagogyPlan:
    selected_office: str
    requested_office: str = "auto"
    office_reason: str = ""
    learner_level: str = "intermediate"
    desired_depth: str = "compact"
    feedback_style: str = "balanced"
    assessment_layer: str = "formative"
    zpd_level: str = "moderate scaffold"
    scaffold_intensity: str = "medium"
    bloom_target: str = "analyze"
    barrett_depth: str = "inferential"
    facione_focus: str = "analysis"
    feuerstein_move: str = "intentionality and meaning"
    de_bono_hat: str = "white -> black -> green -> blue"
    costa_habit: str = "striving for accuracy"
    knowles_move: str = "self-directed next choice"
    mezirow_move: str = "premise reflection"
    torrance_move: str = "elaborate the promising idea"
    assessment_cycle: List[str] = field(default_factory=lambda: ["diagnostic", "formative", "criterion", "reflective", "ipsative"])
    response_contract: str = "diagnose first, scaffold second, hand authorship back"
    visible_summary: str = ""
    next_best_learning_move: str = ""
    authorship_boundary: str = "Sophia may diagnose, question, scaffold, and map evidence; the learner chooses wording, claims, and citations."
    adaptation_trace: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_office": self.selected_office,
            "requested_office": self.requested_office,
            "office_reason": self.office_reason,
            "learner_level": self.learner_level,
            "desired_depth": self.desired_depth,
            "feedback_style": self.feedback_style,
            "assessment_layer": self.assessment_layer,
            "zpd_level": self.zpd_level,
            "scaffold_intensity": self.scaffold_intensity,
            "bloom_target": self.bloom_target,
            "barrett_depth": self.barrett_depth,
            "facione_focus": self.facione_focus,
            "feuerstein_move": self.feuerstein_move,
            "de_bono_hat": self.de_bono_hat,
            "costa_habit": self.costa_habit,
            "knowles_move": self.knowles_move,
            "mezirow_move": self.mezirow_move,
            "torrance_move": self.torrance_move,
            "assessment_cycle": self.assessment_cycle,
            "response_contract": self.response_contract,
            "visible_summary": self.visible_summary,
            "next_best_learning_move": self.next_best_learning_move,
            "authorship_boundary": self.authorship_boundary,
            "adaptation_trace": self.adaptation_trace,
        }


class SophiaPedagogyOrchestrator:
    """Selects pedagogical office and teaching moves for Writing Desk turns."""

    def plan(
        self,
        *,
        task: str,
        selected_text: str,
        findings: Optional[List[str]] = None,
        source_count: int = 0,
        client_context: Optional[Dict[str, Any]] = None,
        history_summary: Optional[Dict[str, Any]] = None,
    ) -> PedagogyPlan:
        ctx = client_context or {}
        findings = findings or []
        text = selected_text or ""
        requested = self._normalize(ctx.get("pedagogical_office") or "auto")
        learner = self._normalize(ctx.get("learner_level") or "intermediate")
        depth = self._normalize(ctx.get("desired_depth") or ctx.get("response_mode") or "compact")
        style = self._normalize(ctx.get("feedback_style") or "balanced")
        layer = self._normalize(ctx.get("assessment_layer") or "formative")

        issue_labels = {
            str(item).split(":", 1)[0].strip().lower()
            for item in findings
            if str(item).strip()
        }
        history = history_summary or {}
        repeated = [
            str((item or {}).get("issue") or "").strip().lower()
            for item in (history.get("repeated_weakness_types") or [])
            if isinstance(item, dict)
        ]
        repeated_current = sorted(label for label in issue_labels if label in repeated)
        words = re.findall(r"[A-Za-z][A-Za-z'-]+", text)
        question_density = text.count("?")
        has_source_gap = bool({"needs source", "needs warrant", "operational definition"} & issue_labels)
        has_method_gap = bool({"method clarity", "method detail"} & issue_labels)
        has_scope_gap = bool({"scope limit", "overclaim"} & issue_labels)

        office = requested if requested != "auto" else self._infer_office(
            task=task,
            issue_labels=issue_labels,
            source_count=source_count,
            has_method_gap=has_method_gap,
            has_source_gap=has_source_gap,
            has_scope_gap=has_scope_gap,
        )

        scaffold = self._scaffold_intensity(learner, len(words), issue_labels, repeated_current)
        bloom = self._bloom_target(office, task, scaffold, has_scope_gap)
        facione = self._facione_focus(office, has_source_gap, has_scope_gap, has_method_gap)
        cycle = self._assessment_cycle(layer, office)
        ipsative_note = self._ipsative_note(history, repeated_current)

        plan = PedagogyPlan(
            selected_office=office,
            requested_office=requested,
            office_reason=self._office_reason(office, task, has_source_gap, has_method_gap, has_scope_gap),
            learner_level=learner,
            desired_depth=depth,
            feedback_style=style,
            assessment_layer=layer,
            zpd_level=self._zpd_level(scaffold),
            scaffold_intensity=scaffold,
            bloom_target=bloom,
            barrett_depth="evaluative" if office in {"examiner", "expert_challenge", "peer_reviewer"} else "inferential",
            facione_focus=facione,
            feuerstein_move=self._feuerstein_move(office, scaffold),
            de_bono_hat=self._de_bono_hat(office),
            costa_habit=self._costa_habit(office, has_source_gap, has_scope_gap),
            knowles_move=self._knowles_move(office),
            mezirow_move=self._mezirow_move(office, has_scope_gap),
            torrance_move=self._torrance_move(office, task),
            assessment_cycle=cycle,
            response_contract=self._response_contract(office, scaffold),
            next_best_learning_move=self._next_move(office, has_source_gap, has_method_gap, has_scope_gap, repeated_current),
            adaptation_trace={
                "word_count": len(words),
                "question_count": question_density,
                "issue_labels": sorted(issue_labels),
                "source_count": source_count,
                "history_summary": history,
                "repeated_current_weaknesses": repeated_current,
                "ipsative_note": ipsative_note,
            },
        )
        plan.visible_summary = (
            f"Office: {OFFICES.get(plan.selected_office, plan.selected_office)}. "
            f"Move: {plan.next_best_learning_move} "
            f"Target: {plan.bloom_target}/{plan.facione_focus}."
        )
        return plan

    @staticmethod
    def _normalize(value: Any) -> str:
        return re.sub(r"[^a-z0-9_]+", "_", str(value or "").strip().lower()).strip("_") or "auto"

    def _infer_office(self, *, task: str, issue_labels: set[str], source_count: int, has_method_gap: bool, has_source_gap: bool, has_scope_gap: bool) -> str:
        if task == "scaffold":
            return "novice_scaffold"
        if task in {"find_sources", "map_sources", "provenance"} or has_source_gap:
            return "source_librarian" if task == "find_sources" else "integrity_auditor"
        if has_method_gap:
            return "methodologist"
        if task == "similarity":
            return "integrity_auditor"
        if has_scope_gap:
            return "peer_reviewer"
        if source_count and task == "ask":
            return "writing_coach"
        return "writing_coach"

    @staticmethod
    def _scaffold_intensity(learner: str, word_count: int, issue_labels: set[str], repeated_current: Optional[List[str]] = None) -> str:
        if learner in {"novice", "beginner"}:
            return "high"
        if repeated_current:
            return "medium_high"
        if learner in {"expert", "advanced"}:
            return "low"
        if len(issue_labels) >= 4 or word_count > 220:
            return "medium_high"
        return "medium"

    @staticmethod
    def _zpd_level(scaffold: str) -> str:
        return {
            "high": "close scaffold",
            "medium_high": "guided scaffold",
            "medium": "moderate scaffold",
            "low": "light-touch challenge",
        }.get(scaffold, "moderate scaffold")

    @staticmethod
    def _bloom_target(office: str, task: str, scaffold: str, has_scope_gap: bool) -> str:
        if office == "novice_scaffold" or scaffold == "high":
            return "understand/apply"
        if office in {"examiner", "expert_challenge"}:
            return "evaluate/create"
        if office in {"methodologist", "source_librarian", "integrity_auditor"}:
            return "analyze/evaluate"
        if has_scope_gap:
            return "evaluate"
        return "analyze"

    @staticmethod
    def _facione_focus(office: str, has_source_gap: bool, has_scope_gap: bool, has_method_gap: bool) -> str:
        if has_source_gap:
            return "interpretation and evidence evaluation"
        if has_scope_gap:
            return "inference and self-regulation"
        if has_method_gap:
            return "analysis and explanation"
        if office == "examiner":
            return "evaluation"
        return "analysis"

    @staticmethod
    def _feuerstein_move(office: str, scaffold: str) -> str:
        if scaffold in {"high", "medium_high"}:
            return "intentionality, meaning, and competence"
        if office in {"examiner", "expert_challenge"}:
            return "challenge for transcendence"
        return "mediation of meaning"

    @staticmethod
    def _de_bono_hat(office: str) -> str:
        return {
            "source_librarian": "white -> yellow -> black -> blue",
            "integrity_auditor": "white -> black -> blue",
            "peer_reviewer": "yellow -> black -> green -> blue",
            "examiner": "white -> black -> blue",
            "novice_scaffold": "white -> yellow -> green -> blue",
            "expert_challenge": "black -> green -> blue",
        }.get(office, "white -> black -> green -> blue")

    @staticmethod
    def _costa_habit(office: str, has_source_gap: bool, has_scope_gap: bool) -> str:
        if has_source_gap:
            return "gathering data through all senses / striving for accuracy"
        if has_scope_gap:
            return "thinking flexibly"
        if office == "expert_challenge":
            return "questioning and problem posing"
        return "thinking about thinking"

    @staticmethod
    def _knowles_move(office: str) -> str:
        if office == "novice_scaffold":
            return "offer bounded choices for the learner's next action"
        if office == "expert_challenge":
            return "invite self-directed criterion setting"
        return "make the next self-directed revision choice explicit"

    @staticmethod
    def _mezirow_move(office: str, has_scope_gap: bool) -> str:
        if has_scope_gap or office in {"peer_reviewer", "examiner", "expert_challenge"}:
            return "test the assumption behind the claim"
        return "reflect on why this claim matters in the argument"

    @staticmethod
    def _torrance_move(office: str, task: str) -> str:
        if office == "expert_challenge":
            return "generate a stronger counter-possibility"
        if task == "scaffold":
            return "elaborate one promising revision path"
        return "refine originality without overclaiming"

    @staticmethod
    def _assessment_cycle(layer: str, office: str) -> List[str]:
        if layer in {"baseline", "diagnostic", "formative", "criterion", "reflective", "ipsative"}:
            primary = layer
        else:
            primary = "formative"
        cycle = [primary, "criterion", "reflective", "ipsative"]
        if office in {"examiner", "integrity_auditor"} and "criterion" not in cycle[:1]:
            cycle.insert(1, "criterion")
        return list(dict.fromkeys(cycle))

    @staticmethod
    def _response_contract(office: str, scaffold: str) -> str:
        if office == "examiner":
            return "criterion-first critique, then minimal revision direction"
        if office == "novice_scaffold":
            return "small steps, model pattern, learner choice"
        if office == "source_librarian":
            return "source leads only until spans prove support"
        if office == "integrity_auditor":
            return "risk diagnosis without accusation or substitution"
        if scaffold == "low":
            return "brief expert challenge with direct criteria"
        return "diagnose, scaffold, hand authorship back"

    @staticmethod
    def _office_reason(office: str, task: str, has_source_gap: bool, has_method_gap: bool, has_scope_gap: bool) -> str:
        if office == "source_librarian":
            return "The task or evidence state requires source discovery and provenance triage."
        if office == "integrity_auditor":
            return "The selected passage has provenance, similarity, or authorship-boundary risk."
        if office == "methodologist":
            return "The passage needs method transparency or construct operationalization."
        if office == "peer_reviewer":
            return "The passage needs skeptical but developmental critique."
        if office == "examiner":
            return "The requested mode prioritizes criteria, defensibility, and limits."
        if office == "novice_scaffold":
            return "The learner needs close scaffolding before critique."
        if office == "expert_challenge":
            return "The learner requested a higher-challenge mode."
        return "The passage needs writing-level diagnosis and revision scaffolding."

    @staticmethod
    def _next_move(office: str, has_source_gap: bool, has_method_gap: bool, has_scope_gap: bool, repeated_current: Optional[List[str]] = None) -> str:
        if repeated_current:
            return f"address repeated pattern: {', '.join(repeated_current[:2])}; revise one example and re-check"
        if office == "source_librarian" or has_source_gap:
            return "separate source lead, direct support, warrant, and limitation"
        if office == "methodologist" or has_method_gap:
            return "make method, construct, and evidence boundary explicit"
        if office in {"peer_reviewer", "examiner"} or has_scope_gap:
            return "tighten claim scope against what the evidence actually warrants"
        if office == "novice_scaffold":
            return "revise one sentence using claim -> evidence -> warrant -> limitation"
        if office == "expert_challenge":
            return "write the strongest reviewer objection before revising"
        return "strengthen the selected passage without replacing the learner's voice"

    @staticmethod
    def _ipsative_note(history: Dict[str, Any], repeated_current: List[str]) -> str:
        interventions = int(history.get("intervention_records") or 0)
        improvement = history.get("latest_intervention_improvement") or {}
        improvement_status = str(improvement.get("status") or "")
        if improvement_status == "improved":
            resolved = ", ".join(improvement.get("resolved_issue_labels") or [])
            return f"Ipsative movement: improved since the prior intervention; resolved pattern(s): {resolved or 'fewer issue labels'}."
        if improvement_status == "regressed_or_new_risk":
            new = ", ".join(improvement.get("new_issue_labels") or [])
            return f"Ipsative movement: new or stronger risk appeared since the prior intervention; check {new or 'the latest issue set'}."
        if improvement_status == "stable_unresolved":
            persistent = ", ".join(improvement.get("persistent_issue_labels") or [])
            return f"Ipsative movement: stable but unresolved; keep working on {persistent or 'the repeated issue pattern'}."
        if repeated_current:
            return f"This turn shows a repeated prior weakness pattern: {', '.join(repeated_current[:3])}."
        if interventions:
            return f"This turn follows {interventions} prior Writing Desk intervention(s); compare against the previous draft before polishing."
        return "No prior project-level intervention pattern is visible yet."


_ORCHESTRATOR: Optional[SophiaPedagogyOrchestrator] = None


def get_sophia_pedagogy_orchestrator() -> SophiaPedagogyOrchestrator:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        _ORCHESTRATOR = SophiaPedagogyOrchestrator()
    return _ORCHESTRATOR
