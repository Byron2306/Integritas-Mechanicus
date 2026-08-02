# Sophia Writing Desk: Phased Implementation Plan Toward a World-Class Academic Integrity Environment

Generated: 2026-08-02T15:51:06Z  
System: Sophia / Arda OS / Presence UI  
Current integration rating: 7.5/10  
Target integration rating: 9.3+/10, with publishable evidence quality

## Executive Summary

Sophia has now crossed the threshold from a chat assistant into an early live academic writing environment. The current Writing Desk can accept a draft, import documents, preserve an editable writing surface, bind feedback to selected lines, route integrity/provenance/similarity/scaffold actions, and prevent the most damaging earlier failures: stale-document bleed, generic greetings, random source retrieval, and full-paper review fallback when the user is asking about a selected passage.

The next goal is not merely to make Sophia "better at writing help." The goal is to make her a claim-governance environment: a system where every academic claim can be inspected for authorship, provenance, source fit, warrant strength, scope control, similarity risk, and pedagogical next move. This would make Sophia materially different from ordinary AI writing tools because her value would not be substitution, but live integrity-preserving mediation.

The roadmap below phases the work from immediate reliability hardening to world-class academic proof.

## Current State

### What Is Already Working

- The Presence UI now exposes a `WRITING` tab with a live editable draft surface.
- The Writing Desk supports text/PDF import through `/api/extract-document`.
- User selection is line-aware: highlighted spans or cursor-line fallback are passed into the backend.
- The backend has a dedicated `writing_desk_feedback` path, preventing Writing Desk requests from being hijacked by source discovery or full-document review fallbacks.
- Sophia can now produce bounded selected-line feedback with provenance honesty and authorship boundaries.
- The system can mark missing support as `NEEDS SOURCE` rather than fabricating citations.
- The desk can pass live draft evidence to `/api/speak` using `document_uploads` and `document_evidence_task=live_writing_desk`.
- The UI already has adjacent academic actions: review, find sources, summarize, rank, map, ledger, and integrity.

### Current Weaknesses

- Feedback is still partly rule-synthesized rather than deeply model-mediated for every Writing Desk action.
- Source support is not yet directly resolved against selected claims inside the editor.
- Similarity checking is still basic and local; it does not yet perform robust semantic source alignment or paraphrase-risk analysis.
- There are no inline draft annotations yet.
- Writing projects are not yet separated into durable project workspaces with their own source pools, claim ledgers, and revision history.
- The pedagogy stack is present but not yet visibly adaptive inside the Writing Desk.
- Audit logs exist, but the UI does not yet expose a clear intervention ledger for academic reviewers.
- Citation management is now substantially first-class: Sophia can produce APA, BibTeX, RIS, and CSL-JSON/Zotero-importable leads, perform DOI/Crossref/OpenAlex metadata enrichment, expose source-quality ranking, preserve page-number honesty, carry container/journal/volume/issue/page metadata, and export page-aware source ledgers. Remaining citation limitations are true Zotero API synchronization, richer style rendering, and OCR/image-PDF page robustness.

## World-Class Definition

Sophia becomes world-class when she can do the following reliably:

- Inspect any selected claim and identify what kind of claim it is.
- Determine what evidence or source type the claim requires.
- Search, retrieve, rank, and summarize candidate sources without hallucinating support.
- Map source spans to draft claims with explicit confidence and limitations.
- Detect unsupported claims, overclaiming, vague constructs, weak warrants, missing limitations, and similarity/provenance risks.
- Preserve human authorship by scaffolding revision rather than substituting final academic prose.
- Adapt teaching mode to the learner's context, expertise, history, and purpose.
- Maintain a durable, auditable project ledger for every paper.
- Produce evidence that a human academic integrity committee, supervisor, journal reviewer, or methods auditor can inspect.

## ~~Phase 1: Reliability and UX Hardening~~

Status: completed and smoke-validated. Implemented visible desk state, scope selector, shortcuts, request locking, autosave continuity, compact/detailed response mode, local ledger objects, backend client-context routing, structured feedback fields, and live route verification.

Target rating after phase: 8.0/10  
Purpose: make the current Writing Desk dependable enough for daily use.

### Build

- ~~Add visual state indicators for `draft loaded`, `selection active`, `source pool available`, `similarity checked`, and `ledger synced`.~~
- ~~Add clear empty-state messages when Sophia cannot inspect a claim because no text, no source, or no selected span is available.~~
- ~~Add keyboard shortcuts:~~
  - ~~`Ctrl+Enter`: ask Sophia about selected text.~~
  - ~~`Ctrl+Shift+I`: integrity check.~~
  - ~~`Ctrl+Shift+P`: provenance check.~~
  - ~~`Ctrl+Shift+L`: add selected line to evidence ledger.~~
- ~~Add a "Use whole abstract / use current paragraph / use selected lines" selector.~~
- ~~Add stable local autosave metadata: title, imported filename, last edit time, and source-pool count.~~
- ~~Add frontend protection against repeated clicks while a Writing Desk task is already running.~~
- ~~Add a compact response mode and detailed response mode toggle.~~

### Backend

- ~~Add `client_context.ui_surface=writing_desk` to the backend routing logic instead of relying only on prompt text.~~
- ~~Add structured Writing Desk response fields:~~
  - ~~`claim_type`~~
  - ~~`source_need`~~
  - ~~`integrity_risk`~~
  - ~~`similarity_risk`~~
  - ~~`pedagogical_move`~~
  - ~~`authorship_boundary`~~
  - ~~`next_revision_move`~~
- ~~Keep the human-readable response, but return machine-readable fields for UI annotation.~~

### Evaluation Gate

- Run a 50-case Writing Desk smoke suite:
  - ~~Script added: `scripts/sophia_writing_desk_phase1_smoke.py`~~
  - ~~10 abstract passages~~
  - ~~10 introduction claims~~
  - ~~10 method claims~~
  - ~~10 discussion/conclusion claims~~
  - ~~10 ambiguous user questions~~
- Required pass criteria:
  - ~~0 stale-document bleed cases.~~
  - ~~0 random source-scout misroutes.~~
  - ~~0 generic greeting failures.~~
  - ~~At least 85% of responses name the selected passage's actual claim type.~~

Validation artifact: `evidence/sophia_writing_desk_phase1_smoke_latest.json`  
Validation result: 50/50 structured responses, 0 source-scout misroutes, 0 review misroutes, 0 generic greetings, 0 errors, 100% claim-type match rate, Phase 1 gate passed.

## ~~Phase 2: Inline Annotation Layer~~

Status: substantially completed and upgraded beyond the original textarea-safe slice. Implemented line-linked annotation cards, filters, Claim Inspector, annotated draft preview, table/list-aware segmentation, deterministic issue labels, a 30-case annotation suite, and a dependency-free `contenteditable` rich editor with inline line-level annotation highlights. Honest limitation: this is not yet a full ProseMirror/CodeMirror-class academic editor with collaborative editing, stable transaction history, or semantic citation nodes, but the core Phase 2 requirement of live academic markup is now working.

Target rating after phase: 8.4/10  
Purpose: move from chat-style feedback to live academic markup.

### Build

- Add inline annotations in the editor:
  - ~~`NEEDS SOURCE`~~
  - ~~`WEAK WARRANT`~~
  - ~~`OVERCLAIM`~~
  - ~~`DEFINE TERM`~~
  - ~~`SCOPE LIMIT`~~
  - ~~`SIMILARITY RISK`~~
  - ~~`STRONG CLAIM`~~
  - ~~`REVISION READY`~~
- ~~Allow clicking an annotation to open Sophia's explanation in the side panel.~~
- ~~Add a right-hand "Claim Inspector" panel with:~~
  - ~~selected claim~~
  - ~~claim type~~
  - ~~evidence needed~~
  - ~~source candidates~~
  - ~~current status~~
  - ~~revision move~~
- ~~Add annotation filters so the user can show only provenance issues, rigor issues, or similarity issues.~~

### Backend

- ~~Return span offsets or line ranges with each Writing Desk diagnosis.~~
- Add a claim segmentation function:
  - ~~sentence-level segmentation for short passages~~
  - ~~paragraph-level segmentation for abstracts and dense argument sections~~
  - ~~table/list-aware segmentation for evidence dossiers~~
- Add deterministic first-pass issue detection before model reasoning:
  - ~~unsupported universal claims~~
  - ~~causal verbs without evidence~~
  - ~~vague evaluative terms~~
  - ~~missing method nouns~~
  - ~~missing limitation language~~

### Evaluation Gate

- Test 30 passages with known issue labels.
  - Script added: `scripts/sophia_writing_desk_phase2_annotations.py`
- Required pass criteria:
  - ~~At least 80% annotation-location accuracy.~~
  - ~~At least 85% issue-category precision on high-confidence flags.~~
  - ~~No annotation may imply plagiarism unless similarity evidence exists.~~

Validation artifact: `evidence/sophia_writing_desk_phase2_annotations_latest.json`  
Validation result: 30 cases, 26 matched expected labels, 86.67% match rate, 100% line-range presence, 0 errors, 0 plagiarism accusations without similarity evidence, Phase 2 gate passed. Follow-up UI verification also confirms the Writing Desk now serves a `contenteditable` rich editor with inline annotation markup and wide writing-mode layout.

## Phase 3: Source-Grounded Claim Support

Status: advanced active slice implemented, approximately 97% of the phase complete. Sophia now includes a KnowEdge Merger-inspired tri-artifact source-support bridge: selected learner claim as source artifact, candidate source span as target artifact, and citation/provenance rules as reference artifact. The Writing Desk exposes `Find Sources for Claim` and `Map Sources to Claim`; mapped sources are classified as `supports`, `partially supports`, `background only`, `does not support`, `contradicts`, or `insufficient text`, with visible rationale, span, quality score, citation hygiene, provenance status, DOI/URL extraction, APA-style citation candidates, BibTeX, RIS, CSL-JSON/Zotero-importable citation leads, container/journal metadata, publisher, volume, issue, source-page metadata, source-type badges, source-role classification, ranking scores, narrow construct-family overlap, broad scholarly field overlap, page locators, page-number honesty, entailment/scope warnings, deterministic entailment scores, lexical-vector scores, and optional live Crossref-then-OpenAlex metadata enrichment. The `Find Sources for Claim` route now derives a claim-specific query and calls the governed Academic Retrieval engine with external-first retrieval rather than using stale paper memory. Remaining limitation: this is now stronger than lexical matching and has live metadata verification plus deterministic NLI-style scoring, but still not neural embedding/NLI, true Zotero API synchronization, or human-judge validated source support.

Target rating after phase: 8.8/10  
Purpose: make `NEEDS SOURCE` actionable.

### Build

- Add a "Find Sources for Selected Claim" button.
- Add a "Map Sources to Selected Claim" button.
- Add a source-support panel:
  - `supports`
  - `partially supports`
  - `background only`
  - `does not support`
  - `contradicts`
  - `insufficient text available`
- Add source-quality badges:
  - peer-reviewed article
  - policy/guidance
  - technical standard
  - preprint
  - institutional report
  - encyclopedia/background
  - unknown quality
- Add citation candidate output:
  - APA-style draft citation
  - DOI/URL
  - source type
  - page-number status
  - exact source span when available

Implemented slice:

- ~~Add a "Find Sources for Selected Claim" button.~~
- ~~Add a "Map Sources to Selected Claim" button.~~
- ~~Add source-support labels for selected-claim mapping.~~
- ~~Add exact visible span when available.~~
- ~~Add provenance status and citation-hygiene status.~~
- ~~Add DOI/URL extraction for retrieved or pasted sources.~~
- ~~Add APA-style citation candidate strings.~~
- ~~Add BibTeX citation lead strings.~~
- ~~Add RIS citation lead strings.~~
- ~~Add CSL-JSON/Zotero-importable citation lead records.~~
- ~~Add page-number honesty: visible page/span marker versus "do not invent one."~~
- ~~Add page locator extraction from page markers and structured spans.~~
- ~~Add page-aware document spans for text/PDF extraction where page breaks are recoverable.~~
- ~~Add construct-family semantic overlap for key Sophia domains such as agency, academic-integrity policy, constitutional governance, pedagogy, and adversarial AI.~~
- ~~Add broad scholarly field overlap across education, psychology, computer science/AI, cybersecurity, medicine, biology, physical sciences/engineering, mathematics/statistics, social sciences, law/ethics/policy, business, humanities, and sustainability.~~
- ~~Keep broad field overlap separate from direct support so same-discipline sources are not overclaimed as evidence.~~
- ~~Add source-role classification: theory, method, evidence, policy, definition, contradiction, or background/context.~~
- ~~Add ranking scores that combine support strength, relevance, source quality, and citation hygiene.~~
- ~~Add container/journal, publisher, volume, issue, and source-page metadata to citation exports.~~
- ~~Add deterministic entailment/scope warnings for universal, causal, proof, and over-transfer claims.~~
- ~~Add deterministic entailment scores and lexical-vector scores for source-support ranking.~~
- ~~Add source-support rendering in Writing Desk feedback and Claim Inspector.~~
- ~~Add source-support Markdown ledger export for supervisor/auditor inspection.~~
- ~~Wire `Find Sources for Claim` to governed Academic Retrieval using the selected claim, not prior paper memory.~~
- ~~Prefer external scholarly retrieval for selected-claim discovery; use local/session source pools for follow-up mapping.~~
- ~~Add Python-native Merger bridge: `arda_os/backend/services/sophia_source_support.py`.~~
- ~~Add Phase 3 source-support suite: `scripts/sophia_writing_desk_phase3_source_support.py`.~~
- ~~Add Phase 3 citation-hygiene suite: `scripts/sophia_writing_desk_phase3_citation_hygiene.py`.~~
- ~~Add Phase 3 ranking-quality suite: `scripts/sophia_writing_desk_phase3_ranking_quality.py`.~~
- ~~Add Phase 3 export/semantic/page suite: `scripts/sophia_writing_desk_phase3_export_semantic.py`.~~
- ~~Add Phase 3 broad-domain guard suite: `scripts/sophia_writing_desk_phase3_broad_domains.py`.~~
- ~~Add Phase 3 live metadata enrichment probe: `scripts/sophia_writing_desk_phase3_metadata_enrichment.py`.~~
- ~~Add Phase 3 final robustness suite: `scripts/sophia_writing_desk_phase3_final_robustness.py`.~~
- ~~Add Phase 3 entailment-scoring suite: `scripts/sophia_writing_desk_phase3_entailment_scoring.py`.~~
- ~~Add optional live Writing Desk endpoint probe: `scripts/sophia_writing_desk_live_probe.py`.~~

Validation artifact: `evidence/sophia_writing_desk_phase3_source_support_latest.json`  
Validation result: 120 cases, 120 matched expected labels, 100% match rate, 0 false supports, Phase 3 source-support slice gate passed.

Validation artifact: `evidence/sophia_writing_desk_phase3_citation_hygiene_latest.json`  
Validation result: 60 cases, 60 passed, 100% pass rate, citation-hygiene gate passed. This verifies DOI extraction, URL retention, APA candidate presence, citation-ready status where warranted, and page-number honesty without invented pages.

Validation artifact: `evidence/sophia_writing_desk_phase3_ranking_quality_latest.json`  
Validation result: 40 cases, 40 passed, 100% pass rate, ranking-quality gate passed. This verifies that direct-support scholarly sources outrank background leads, contradicters do not surface as support, citation hygiene affects rank, and role labels remain visible to the user.

UI artifact push: the Writing Desk now includes an `Export Source Ledger` control. After source discovery or source mapping, Sophia can export a Markdown ledger containing the inspected claim, support labels, source roles, ranking scores, provenance status, citation status, page-number status, DOI/URL/APA leads, visible spans, and the learner's next revision move. This supports academic auditability without converting source leads into fabricated proof.

Validation artifact: `evidence/sophia_writing_desk_phase3_export_semantic_latest.json`  
Validation result: 60 cases, 60 passed, 100% pass rate, export/semantic/page gate passed. This verifies BibTeX/RIS citation leads, page locator extraction from text and structured spans, construct-family overlap, contradiction preservation, and an explicit export rule that treats citations as leads requiring verification.

Validation artifact: `evidence/sophia_writing_desk_phase3_broad_domains_latest.json`  
Validation result: 60 cases, 60 passed, 100% pass rate, 0 false supports, broad-domain gate passed. This verifies that Sophia can recognize a broad general base of scientific and scholarly fields while keeping field-context distinct from direct support.

Validation artifact: `evidence/sophia_writing_desk_phase3_metadata_enrichment_latest.json`  
Validation result: live metadata enrichment probe passed. DOI `10.1038/nature16961` returned verified Crossref metadata, title-only OpenAlex fallback also verified, support classification remained stable, and APA/BibTeX/RIS/CSL-JSON exports remained present.

Validation artifact: `evidence/sophia_writing_desk_phase3_final_robustness_latest.json`  
Validation result: 3 cases, 3 passed, 100% pass rate. This verifies deterministic entailment/scope warnings, rich container/volume/issue/page metadata export, CSL-JSON container fields, and page-aware span extraction with page locators.

Validation artifact: `evidence/sophia_writing_desk_phase3_entailment_scoring_latest.json`  
Validation result: 1 focused score-ordering case passed. This verifies that direct support outranks partial support, partial support outranks background, and contradiction does not masquerade as entailment.

Validation artifact: `evidence/sophia_writing_desk_live_probe_latest.json`  
Validation result: optional live endpoint probe passed against `http://localhost:7070`. The probe confirmed server health, session-token availability, `/api/speak` release, Writing Desk structured output, source-support presence, and retrieval/source-pool presence in 180.738 ms.

Additional validation note: direct-path source-support validation confirmed a scholarly/OpenAlex-style lead is classified as `supports` with citation-ready status when its visible span directly overlaps the selected claim.

### Backend

- ~~Add retrieval specifically keyed to selected claim text, not whole-paper memory.~~
- Rank sources using:
  - ~~topical relevance~~
  - recency
  - ~~source type quality~~
  - ~~abstract/span overlap~~
  - methodological fit
  - ~~policy/theory/evidence role fit~~
- Add source-support classification:
  - ~~claim tokens~~
  - ~~construct match~~
  - ~~evidence type match~~
  - ~~contradiction markers~~
  - ~~absence of direct support~~
- ~~Add BibTeX export where available.~~
- ~~Add RIS export where available.~~
- ~~Add live DOI/Crossref metadata enrichment where available.~~
- ~~Add OpenAlex fallback metadata enrichment by DOI or title.~~
- ~~Add Zotero-importable CSL-JSON export for accepted source leads.~~
- ~~Extend live metadata enrichment into journal/container/volume/issue/page metadata where providers expose it.~~
- ~~Add deterministic entailment warnings for overclaiming, causal overreach, and source limitation language.~~
- ~~Add deterministic NLI-style entailment scoring with lexical-vector similarity.~~
- ~~Run a supervisor-style live endpoint probe for the Writing Desk `/api/speak` path.~~

### Evaluation Gate

- Run a 120-row source-support benchmark:
  - 30 direct-support cases
  - 30 partial-support cases
  - 30 background-only cases
  - 30 non-support/contradiction cases
- Required pass criteria:
  - ~~False support rate below 3%.~~
  - ~~Background-only sources are not mislabeled as direct support more than 8% of the time.~~
  - ~~Every citation includes provenance status.~~

Remaining Phase 3 work before calling the phase complete:

- Add neural embedding or neural NLI-assisted matching so source support can move beyond lexical/vector heuristics, construct-family overlap, and deterministic scope checks.
- Add true Zotero API synchronization for accepted source leads if/when a Zotero connector or local API key is wired.
- Extend page-level OCR/image-PDF span extraction beyond text-layer PDFs where source files contain recoverable page boundaries.
- Add full browser automation for the Writing Desk UI, beyond the current live endpoint probe.

## Phase 4: Evidence Ledger as First-Class Infrastructure

Target rating after phase: 9.0/10  
Purpose: turn selected feedback into durable academic progress.

### Build

- ~~Add a persistent local evidence ledger beside the editor:~~
  - ~~claim~~
  - ~~source~~
  - ~~exact span~~
  - ~~warrant~~
  - ~~limitation~~
  - ~~draft location~~
  - ~~status~~
  - ~~Sophia intervention history~~
- Add ledger actions:
  - ~~add selected claim~~
  - ~~attach source from mapped source-support rows~~
  - mark warrant drafted
  - mark limitation added
  - resolve issue
  - ~~export ledger~~
- Add project-level dashboards:
  - unsupported claims remaining
  - weak warrants
  - missing limitations
  - source-quality distribution
  - similarity-risk count
  - resolved issues over time

### Backend

- ~~Create a durable project store:~~
  - ~~project ID~~
  - ~~draft versions~~
  - ~~uploaded documents~~
  - retrieved sources
  - ~~claim ledger~~
  - ~~intervention ledger in each claim record~~
  - source pool
  - ~~Mandos category~~
- ~~Separate projects by active document identity to prevent cross-paper contamination.~~
- ~~Add version snapshots so feedback can be linked to the exact draft state.~~

### Phase 4 Slice Implemented

- Added a full-width Writing Desk Evidence Ledger panel in the Presence UI.
- Added `Export Evidence Ledger`, separate from the existing latest source-support export.
- Converted source-support maps into durable local claim -> evidence -> warrant -> limitation records.
- Added stable client-side ledger deduplication, status classification, draft location, intervention history, and local persistence.
- Added manual selected-claim ledger marks as real claim objects instead of annotation-only crumbs.
- Added Markdown ledger export with draft hash, record count, integrity boundary, source metadata, exact span, warrant, limitation, and intervention history.
- Added static Phase 4 validation harness: `scripts/sophia_writing_desk_phase4_ledger_static.py`.
- Added backend file-backed project store: `arda_os/backend/services/sophia_project_store.py`.
- Added Writing Desk project persistence into `/api/speak` responses via `writing_project_state`.
- Added durable retrieval/source-pool persistence so source leads can be remembered as unmapped leads without being inflated into claim support.
- Added inspectable backend endpoints:
  - `GET /api/writing-project`
  - `POST /api/writing-ledger`
  - `POST /api/writing-project/contamination-report`
- Added visible Writing Desk project dashboard for project ID, backend sync state, claim count, source count, weak warrants, and unsupported claims.
- Added interactive ledger actions:
  - mark warrant drafted
  - mark limitation added
  - resolve record
  - queue backend sync after each ledger state change
- Added project-store contamination/unit gate: `scripts/sophia_writing_desk_phase4_project_store.py`.

Validation:

- `node --check /home/byron/Downloads/Metatron-triune-outbound-gate/evidence/Presence UI/script.js`: pass.
- `.venv/bin/python -m py_compile scripts/sophia_writing_desk_phase4_ledger_static.py`: pass.
- `.venv/bin/python scripts/sophia_writing_desk_phase4_ledger_static.py --out evidence/sophia_writing_desk_phase4_ledger_static_latest.json`: 28/28 pass.
- `.venv/bin/python -m py_compile arda_os/backend/services/sophia_project_store.py arda_os/backend/services/presence_server.py scripts/sophia_writing_desk_phase4_project_store.py`: pass.
- `.venv/bin/python scripts/sophia_writing_desk_phase4_project_store.py --out evidence/sophia_writing_desk_phase4_project_store_latest.json`: 8/8 pass.
- `node --check /home/byron/Downloads/Metatron-triune-outbound-gate/evidence/Presence UI/script.js`: pass.
- Live HTTP probe: Presence server launched on `localhost:7070`; `/api/health` passed with sealed covenant, Ollama connected, Mandos available, Whisper ready.
- Live Writing Project endpoint proof:
  - `GET /api/writing-project?session_token=phase4-live-probe`: pass.
  - `POST /api/writing-ledger` to `phase4-live-fides`: pass, 1 claim record persisted.
  - `POST /api/writing-ledger` to `phase4-live-gospel`: pass, 0 claim records persisted.
  - `GET /api/writing-project?project_id=phase4-live-fides`: pass, dashboard reported 1 claim record.
  - `GET /api/writing-project?project_id=phase4-live-gospel`: pass, dashboard reported 0 claim records.
  - `POST /api/writing-project/contamination-report`: pass, 0 contamination signals.

### Evaluation Gate

- Run multi-paper contamination tests:
  - Fides paper
  - Gospel dossier
  - BEAST paper
  - unrelated sample paper
- Required pass criteria:
  - 0 cross-project source contamination.
  - 0 stale claim-ledger reuse across projects.
  - 100% intervention records link to a draft version hash.

## Phase 5: Pedagogical Adaptivity and Offices

Target rating after phase: 9.2/10  
Purpose: make Sophia visibly pedagogical, not just evaluative.

Status: complete. Sophia has an inspectable pedagogical orchestrator, UI controls for learning-office selection, backend response contracts, office-shaped prose, project-level intervention memory, and draft-to-draft ipsative improvement scoring. The system exposes selected office, learning level, assessment layer, ZPD scaffold, Bloom target, authorship boundary, repeated weakness patterns, improvement/regression signals, and next learning moves.

### Build

- ~~Add mode selector:~~
  - ~~`Supervisor`~~
  - ~~`Peer reviewer`~~
  - ~~`Methodologist`~~
  - ~~`Source librarian`~~
  - ~~`Integrity auditor`~~
  - ~~`Writing coach`~~
  - ~~`Examiner`~~
  - ~~`Novice scaffold`~~
  - ~~`Expert challenge`~~
- ~~Add visible pedagogical lens:~~
  - ~~ZPD level~~
  - ~~Bloom target~~
  - ~~Barrett depth~~
  - ~~Facione critical-thinking focus~~
  - ~~Feuerstein mediation move~~
  - ~~De Bono thinking-hat move~~
  - ~~Costa habits-of-mind prompt~~
  - ~~Knowles self-directed learning move~~
  - ~~Mezirow reflective transformation move~~
  - ~~Torrance creativity move~~
- ~~Add response adaptation:~~
  - ~~shorter hints for advanced users~~
  - ~~stronger scaffolds for novice users~~
  - ~~more Socratic prompts when learner agency is at risk~~
  - ~~direct critique when the user asks for reviewer/examiner mode~~

### Backend

- ~~Extend Writing Desk requests with:~~
  - ~~`pedagogical_office`~~
  - ~~`learner_level`~~
  - ~~`desired_depth`~~
  - ~~`feedback_style`~~
  - ~~`assessment_layer`~~
- ~~Connect ZPD, assessment ecology, and named pedagogical lenses to Writing Desk telemetry.~~
- ~~Add ipsative tracking:~~
  - ~~previous issue count~~
  - ~~repeated weakness types~~
  - ~~improvement over draft versions~~
  - ~~next best learning move~~

### Implemented Artifacts

- `arda_os/backend/services/sophia_pedagogy_orchestrator.py`
- `scripts/sophia_writing_desk_phase5_pedagogy.py`
- `scripts/sophia_writing_desk_phase5_ui_static.py`
- `scripts/sophia_writing_desk_phase5_adaptation_suite.py`
- `scripts/sophia_writing_desk_phase5_ipsative_suite.py`
- `/home/byron/Downloads/Metatron-triune-outbound-gate/evidence/Presence UI/index.html`
- `/home/byron/Downloads/Metatron-triune-outbound-gate/evidence/Presence UI/script.js`
- `/home/byron/Downloads/Metatron-triune-outbound-gate/evidence/Presence UI/styles.css`

### Phase 5 Validation Snapshot

- Static UI gate: 14/14 pass, including negative checks that browser/system fallback voice is absent.
- Pedagogical orchestrator gate: 8/8 pass.
- Wider adaptation gate: 100/100 pass.
- Ipsative improvement gate: 3/3 pass.
- Distinct visible pedagogical moves: 6 across 8 high-signal cases.
- Distinct visible pedagogical moves in wider gate: 66 across 100 cases.
- Substitute-authorship failures: 0.
- Wider gate failures: 0 office mismatches, 0 lens failures, 0 novice-scaffold failures, 0 ipsative failures, 0 authorship failures.
- Ipsative movement states proven: `improved`, `stable_unresolved`, and `regressed_or_new_risk`.
- Live Writing Desk probe: passed with explicit `examiner` office, `evaluate/create` Bloom target, `criterion` assessment layer, authorship boundary, and project state `ok`.
- Live ipsative proof: second turn against the same project appended a second intervention record, reported 2 intervention records, and surfaced repeated weakness types `needs source` and `needs warrant`.

### Evaluation Gate

- ~~Run a 100-case pedagogy adaptation suite.~~
- ~~Required pass criteria:~~
  - ~~Same selected passage receives meaningfully different feedback in supervisor, examiner, librarian, and novice-scaffold modes.~~
  - ~~At least 85% of responses include an appropriate pedagogical move.~~
  - ~~No mode produces substitute authorship when the task requires scaffolding.~~

## Phase 6: Similarity, Provenance, and Integrity Hardening

Target rating after phase: 9.35/10  
Purpose: make the integrity engine defensible under academic scrutiny.

Status: started. Phase 6 slice 1 is implemented: deterministic similarity/provenance guard, UI similarity card, repair-without-rewriting menu, policy-sensitive language, common-phrase false-positive protection, source-span evidence capture, and a focused validation suite. Remaining work: full 200-row gate, richer side-by-side source comparison, and optional true embedding similarity.

### Build

- ~~Add similarity visualization:~~
  - ~~exact overlap~~
  - ~~near paraphrase~~
  - ~~shared terminology~~
  - ~~citation-needed overlap~~
  - ~~acceptable common phrase~~
- ~~Add "repair without rewriting" tools:~~
  - ~~cite~~
  - ~~quote~~
  - ~~paraphrase with attribution~~
  - ~~narrow claim~~
  - ~~add limitation~~
  - ~~convert assertion to question~~
- Add side-by-side source comparison.

### Backend

- Add multi-layer similarity detection:
  - ~~exact n-gram overlap~~
  - ~~longest common subsequence~~
  - semantic embedding similarity
  - ~~source-span alignment~~
  - ~~citation-presence check~~
  - ~~paraphrase-risk classifier~~
- ~~Add policy-sensitive language:~~
  - ~~"similarity risk" not "plagiarism" unless evidence threshold is met~~
  - ~~"source support unavailable" not "unsupported" when no source corpus exists~~
  - ~~"needs verification" when retrieval metadata is abstract-only~~
- ~~Add protected false-positive behavior for common academic phrases.~~

### Implemented Artifacts

- `arda_os/backend/services/sophia_similarity_guard.py`
- `scripts/sophia_writing_desk_phase6_similarity_suite.py`
- `evidence/sophia_writing_desk_phase6_similarity_latest.json`
- Presence UI similarity/provenance card in `/home/byron/Downloads/Metatron-triune-outbound-gate/evidence/Presence UI/script.js`
- Presence UI similarity styling in `/home/byron/Downloads/Metatron-triune-outbound-gate/evidence/Presence UI/styles.css`

### Phase 6 Slice 1 Validation Snapshot

- Similarity/provenance suite: 7/7 pass.
- False accusation cases: 0.
- High-risk span failures: 0.
- Regression checks: Python compile pass; frontend JS syntax pass; Phase 5 adaptation suite remains 100/100.

### Evaluation Gate

- Run a 200-row similarity suite:
  - direct copy
  - attributed quote
  - close paraphrase
  - legitimate technical phrase
  - uncited source-dependent claim
  - independent synthesis
- Required pass criteria:
  - False accusation rate below 1%.
  - High-risk unattributed overlap recall above 90%.
  - Every high-risk flag includes the source span that triggered it.

## Phase 7: Multimodal and Document Intelligence

Target rating after phase: 9.45/10  
Purpose: make uploaded documents, screenshots, scans, tables, figures, and source PDFs usable with provenance honesty.

### Build

- Add document pane with extracted text, page anchors, figures, tables, and OCR confidence.
- Add page-specific source inspection:
  - "inspect page"
  - "summarize this page"
  - "cite this page"
  - "compare selected claim to this page"
- Add OCR disagreement warnings:
  - unreadable text
  - table structure uncertain
  - figure caption extracted but image not interpreted
  - page number unavailable

### Backend

- Add native multimodal extraction pipeline:
  - PDF text extraction
  - OCR fallback
  - image OCR
  - table extraction
  - page-number retention
  - caption extraction
  - figure/table uncertainty notes
- Add source-span objects with:
  - document ID
  - page number
  - bounding box when available
  - extracted text
  - confidence
  - parser name
- Add OCR disagreement tests and fallback paths.

### Evaluation Gate

- Run multimodal benchmark:
  - clean PDF
  - scanned PDF
  - two-column article
  - table-heavy paper
  - figure-caption evidence
  - blurry screenshot
  - OCR disagreement case
- Required pass criteria:
  - Sophia never claims page-specific evidence without page metadata.
  - OCR uncertainty is visible in 100% of degraded cases.
  - Table/figure evidence is not treated as body-text proof unless extracted.

## Phase 8: Full Auditability and Academic Proof

Target rating after phase: 9.5+/10  
Purpose: produce publishable proof that Sophia preserves integrity while improving academic work.

### Build

- Add an "Export Integrity Record" button:
  - draft version hashes
  - selected passages
  - Sophia advice
  - sources used
  - source-support labels
  - similarity reports
  - authorship-preservation notes
  - unresolved issues
  - final user decisions
- Add a read-only reviewer mode for supervisors or auditors.
- Add anonymized research export.

### Backend

- Add immutable intervention ledger:
  - timestamp
  - project ID
  - user action
  - selected span hash
  - source pool hash
  - response source
  - model/provider
  - deterministic checks
  - governance checks
  - release decision
  - final displayed response
- Add test harness for Writing Desk interventions.
- Add blinded evaluator package generation.

### Evaluation Gate

- Run a full academic proof gauntlet:
  - Writing Desk usability cases
  - source-grounding cases
  - similarity cases
  - multimodal cases
  - pedagogy adaptation cases
  - authorship boundary cases
  - false-support cases
  - stale-memory cases
- Required pass criteria:
  - 0 false releases in integrity-violating tasks.
  - 0 stale cross-document contamination.
  - False holds below 5% for lawful assistance.
  - Source-support false-positive rate below 3%.
  - Human/LLM judge agreement reported with inter-rater reliability.

## Recommended Build Order

1. Phase 1: harden the current Writing Desk.
2. Phase 2: add inline annotations.
3. Phase 3: make selected-claim source retrieval and source-support classification work.
4. Phase 4: introduce project memory and evidence ledger.
5. Phase 6: harden similarity/provenance risk.
6. Phase 5: deepen pedagogy and office switching.
7. Phase 7: complete multimodal document intelligence.
8. Phase 8: package the full academic proof chain.

The reason Phase 6 comes before full pedagogy polish is that source/provenance trust is the safety substrate for everything else. Sophia can be warm and pedagogical only if her evidence handling is disciplined.

## Key Design Principle

Sophia should not be optimized to produce polished paragraphs. She should be optimized to improve the human writer's judgment.

The highest-value interaction pattern is:

```text
selected claim
-> claim type
-> evidence need
-> source fit
-> warrant strength
-> limitation
-> revision scaffold
-> user-authored decision
-> auditable ledger update
```

That pattern is the core of Speculum: Sophia as mirror, not ghostwriter.

## Minimum World-Class Acceptance Criteria

Sophia can be called world-class for academic integrity writing support only when:

- She can inspect a selected line and tell the user exactly what kind of academic claim it is.
- She can identify whether the line needs a source, warrant, limitation, definition, method clarification, or scope reduction.
- She can retrieve and rank source candidates for that exact claim.
- She can distinguish direct support from background relevance.
- She can show exact source spans when available.
- She refuses to invent page numbers, citations, or source support.
- She can flag similarity risk without over-accusing.
- She can scaffold revision without replacing the student's authorship.
- She can preserve separate project memory.
- She can export an audit trail that proves what she did and did not do.

## Immediate Next Sprint

The next sprint should implement these five concrete items:

- Add structured Writing Desk JSON fields to `/api/speak`.
- Add inline annotations for selected passages.
- Add "Find Sources for Selected Claim."
- Add source-support labels: supports, partially supports, background only, does not support, insufficient text.
- Add project IDs so Fides, Gospel, BEAST, and other papers never share stale source pools.

If those five land cleanly, Sophia moves from a strong prototype to a serious academic writing-integrity platform.
