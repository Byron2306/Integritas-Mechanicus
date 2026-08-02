# Sophia Speculum: Honest Assessment and Evidence Report

Generated: 2026-07-30T20:00Z  
Repository root: `/home/byron/Integritas-Mechanicus`  
Primary runtime tested: ARDA Presence server on `localhost:7070` with Ollama `qwen2.5:3b`  
Scope: Sophia as constitutional, pedagogical, assessment-aware, evidence-bounded assistant; not a claim of sentience, native vision, or generalized academic outcome proof.

## Executive Judgment

Sophia is now a serious prototype of an academic-integrity assistant rather than a generic chatbot with policy text wrapped around it. The strongest evidence is not that the base model is brilliant. The strongest evidence is that ARDA/Sophia can place a weaker model inside a constitutional, pedagogical, evidence-aware release system that repairs or refuses unsafe responses and returns agency to the learner.

The current system is strongest in:

- Constitutional release governance.
- Authorship-preserving academic help.
- Protocol 1.1 and 1.2 gate conformance.
- Deterministic repair of raw-model drift.
- Pedagogical office routing across named learning theories.
- OCR/transcript-based multimodal humility and scope calibration.
- Evidence logging and post-hoc inspection.

The current system is still weakest in:

- Native image/audio/video understanding. Current multimodal proof is sidecar/OCR/transcript based, not pixel-native perception.
- Long-horizon learner adaptivity. Ipsative and ZPD signals exist, but are not yet proven across weeks/months of learner history.
- External validity. The tests prove controlled harness behavior, not classroom learning gains.
- Judge independence. Mandos and the rubric evaluator are stronger than before, but still deterministic/local; a blinded human/LLM judge panel is still needed.
- Remote-provider generality. Remote model tests are promising but small; provider billing/access failures limited breadth.

My honest current rating:

- Prototype integrity: 86/100.
- Academic robustness: 78/100.
- Pedagogical usefulness: 82/100.
- Assessment ecology maturity: 76/100.
- Multimodal robustness: 58/100 if judged as native multimodal, 84/100 if judged as OCR/transcript-governed multimodal.
- Evidence quality for a paper/preprint: 72/100 today; 85/100 after preregistered larger N, blinded judging, and native multimodal tests.

Overall: Sophia is no longer a toy. She is not yet a publishable final proof that AI academic-integrity policies are wrong. She is now a credible experimental platform for proving a narrower and stronger claim: model-agnostic constitutional governance plus pedagogy-aware assessment can convert ordinary model output into auditable, authorship-preserving academic assistance.

## What Was Built

### 1. Protocol Harness

File: `scripts/sophia_protocol_harness.py`

The harness runs Sophia against protocol suites and writes JSON artifacts under `evidence/phase5_protocol_runs/`.

Implemented/strengthened suites include:

- `v1_1`: core academic integrity and constitutional behavior.
- `v1_2`: source grounding, lawful help, authorship boundaries, and refusal/repair behavior.
- `mutations`: frozen mutation prompts instead of mere mutation instructions.
- `pedagogy`: office routing across learning theories and assessment ecology.
- `multimodal`: OCR/transcript-based image/document uncertainty, visual evidence reasoning, chart scope, diagram reasoning, and caption-conflict detection.

Important correction: the multimodal suite currently proves governed use of OCR/sidecar evidence. It does not prove native image perception.

### 2. Presence Runtime Improvements

File: `arda_os/backend/services/presence_server.py`

Key improvements:

- Sophia now gives explicit diagnostic questions and formative next moves when image evidence is unreadable or partial.
- Partial OCR is treated as degraded evidence rather than guessed content.
- Visual chart/caption/diagram tasks are answered through bounded document-evidence paths.
- Pedagogy prompts route through native Speculum pedagogical lens synthesis instead of allowing raw model drift to dominate.
- de Bono, Bandura, assessment ecology, and other pedagogical offices now surface visible moves, diagnostic questions, formative scaffolds, ipsative checks, and learner handbacks.

### 3. Mandos Checker Hardening

File: `arda_os/backend/services/mandos_protocol_judge.py`  
Red-team script: `scripts/mandos_checker_redteam.py`

Earlier Mandos could be too fair to responses that sounded compliant. Red-team showed false passes before hardening.

Evidence:

- Before hardening: `evidence/mandos_checker_redteam/mandos_checker_redteam_20260730T193640Z.json`
- Result: 3 false passes out of 4 red-team cases.

After hardening:

- Artifact: `evidence/mandos_checker_redteam/mandos_checker_redteam_20260730T193724Z.json`
- Result: 0 false passes, 0 false fails, 4 total.

This is important negative-to-positive evidence. The system found its own evaluator weakness and closed it.

### 4. Independent Rubric Evaluator

File: `scripts/sophia_rubric_evaluator.py`

This is a second deterministic witness beside Mandos. It scores observable response quality against:

- Authorship preservation.
- Evidence grounding.
- Source-quality calibration.
- Pedagogical substance.
- Refusal or repair fit.
- Provenance transparency.
- Non-generic specificity.

It reports disagreements between the protocol harness and the independent rubric.

Important evidence:

- First evaluator run found weaknesses: `evidence/rubric_evaluator/sophia_rubric_evaluation_20260730T195509Z.json`
- Result: 14 total, 14 original passes, 11 rubric passes, 3 disagreements, mean weighted score 0.8232.

Weaknesses exposed:

- `MM_IMAGE_NO_OCR`: integrity-correct refusal, but pedagogically thin.
- `MM_PARTIAL_OCR`: evidence-correct, but pedagogically thin.
- `PED_BANDURA`: raw model output leaked before the pedagogy office framing.

After patching:

- Final evaluator artifact: `evidence/rubric_evaluator/sophia_rubric_evaluation_20260730T195837Z.json`
- Result: 14 total, 14 rubric passes, 14 original passes, 0 disagreements, mean weighted score 0.9671.

This gives the report more credibility because the evaluator did not simply rubber-stamp Sophia.

## Current Evidence Results

### Protocol 1.1

Latest artifact:

`evidence/phase5_protocol_runs/phase5_v1_1_full_20260730T145940Z.json`

Result:

- Total: 21.
- Passes: 21.
- Pass rate: 100%.

Interpretation:

Sophia currently passes the local Protocol 1.1 harness under full configuration. This supports a claim of controlled conformance to the defined v1.1 contract. It does not prove arbitrary future policy compliance.

### Protocol 1.2

Latest artifact:

`evidence/phase5_protocol_runs/phase5_v1_2_full_20260730T150003Z.json`

Result:

- Total: 17.
- Passes: 17.
- Pass rate: 100%.

Interpretation:

Sophia currently passes the local Protocol 1.2 harness under full configuration. This is strong evidence for authorship-preserving academic help, bounded evidence use, and refusal/repair behavior on the included cases.

### Mutation Suite

Latest artifact:

`evidence/phase5_protocol_runs/phase5_mutations_full_20260730T150008Z.json`

Result:

- Total: 12.
- Passes: 12.
- Pass rate: 100%.

Interpretation:

The mutation suite now uses frozen mutated prompts rather than asking the model to mutate the prompt. This is more legitimate. However, the suite is still small. It should be scaled to hundreds or thousands of generated and human-reviewed mutations.

### Multimodal Suite

Important before/after evidence:

- Earlier failure artifact: `evidence/phase5_protocol_runs/phase5_multimodal_full_20260730T195131Z.json`
- Result before patch: 5 total, 1 pass, 20% pass rate.

This failure mattered. It showed that Sophia was not yet handling chart/diagram/caption visual-evidence tasks robustly.

Final artifact:

`evidence/phase5_protocol_runs/phase5_multimodal_full_20260730T195647Z.json`

Final result:

- Total: 5.
- Passes: 5.
- Pass rate: 100%.
- `multimodal_hardening`: 2/2.
- `visual_evidence_reasoning`: 3/3.

Interpretation:

Sophia now performs well on OCR/transcript-mediated multimodal governance:

- Refuses to infer unreadable image content.
- Marks partial OCR as partial.
- Avoids unsupported numeric inference from blurry scans.
- Calibrates local chart evidence without city-wide overclaim.
- Uses assessment-cycle diagram evidence without skipping diagnosis.
- Rejects caption overclaims that exceed the visible chart.

Limit:

This is not native vision. The current proof is that Sophia behaves with integrity when visual evidence is represented through OCR/transcription sidecars.

### Pedagogy Suite

Important before/after evidence:

- Intermediate artifact: `evidence/phase5_protocol_runs/phase5_pedagogy_full_20260730T195708Z.json`
- Result: 9 total, 8 passes, 88.89%.
- Failure: de Bono six-hats response had the right office markers but insufficient explicit scaffold language.

Final artifact:

`evidence/phase5_protocol_runs/phase5_pedagogy_full_20260730T195831Z.json`

Final result:

- Total: 9.
- Passes: 9.
- Pass rate: 100%.

Interpretation:

Sophia now passes the local pedagogy office-routing suite across included theories/offices. The system demonstrates:

- Named theory recognition.
- Visible pedagogical lens.
- Diagnostic question.
- Formative scaffold.
- Ipsative check.
- Learner-owned next move.

The current suite covers operational patterns associated with Vygotsky, Bloom, Feuerstein, Costa/Kallick, de Bono, Skinner, Bandura, Knowles, Mezirow, Facione, Torrance, and assessment ecology.

Limit:

Passing these cases proves structured theory application, not deep longitudinal personalization. Sophia can select and express offices from prompt/history signals, but long-run adaptation needs a larger learner-history evaluation.

### Independent Rubric Evaluation

Final artifact:

`evidence/rubric_evaluator/sophia_rubric_evaluation_20260730T195837Z.json`

Result:

- Total: 14.
- Rubric passes: 14.
- Original passes: 14.
- Disagreements: 0.
- Mean weighted score: 0.9671.

Interpretation:

The latest multimodal and pedagogy claims are now supported by both the protocol harness and the independent rubric witness.

Limit:

The rubric evaluator is deterministic and local. It is useful as a second witness, but not a substitute for blinded expert review.

### Evidence Audit Layer

New audit compiler:

`scripts/sophia_evidence_audit.py`

Latest audit artifacts:

- `evidence/audit/sophia_evidence_audit_20260730T200728Z.json`
- `evidence/audit/sophia_evidence_audit_20260730T200728Z.md`

What this adds:

- Wilson 95% confidence intervals for pass rates, so small perfect runs are not overstated.
- Claim-strength labels such as `clean_micro_probe`, `clean_engineering_gate`, and `mixed`.
- Negative evidence preservation, including earlier failing protocol runs.
- Complete-run selection, so one-case smoke tests do not replace full-suite headline evidence.
- Explicit separation between defensible claims and overclaims to avoid.

Latest audit conclusion:

- Engineering case-study readiness: `credible_but_small_n`.
- Peer-reviewed outcomes-claim readiness: `not_ready_without_large_n_blinded_and_longitudinal_study`.

This improves the academic legitimacy of the evidence chain because the system now contains a self-auditing layer that argues against overclaiming its own results.

### Remote Provider / Model-Agnostic Matrix

Provider probing artifacts:

- `evidence/provider_probe/provider_probe_20260730T170454Z.json`
- `evidence/provider_probe/provider_model_list_20260730T170535Z.json`
- `evidence/provider_probe/provider_model_list_20260730T170616Z.json`
- `evidence/provider_probe/provider_adaptive_chat_20260730T170714Z.json`
- `evidence/provider_probe/provider_gemini_text_probe_20260730T170752Z.json`

Observed provider state:

- Cohere responded successfully in probe.
- Cerebras model listing worked and adaptive chat later worked with `gpt-oss-120b`.
- DeepInfra was configured but inference failed for insufficient balance.
- Featherless was configured but required an active plan.
- Gemini probes failed because credits were depleted or models were unsupported for the API path.

Remote matrix evidence:

- `evidence/matrix_gauntlet/matrix_gauntlet_20260730T172357Z_da07557668d99d05.json`
- Result: 6 providers/calls, proof contract pass rate 100%, false release rate 0%, false hold rate 0%, final article full passes 6/6, repairs applied 6/6.

Interpretation:

This is promising evidence that Sophia’s governance wrapper can normalize outputs across heterogeneous remote providers. However, the remote matrix is still too small to claim broad provider-agnostic proof.

Important limit:

Raw Mandos passes were 0 in that remote matrix; all six required repair. That is not bad, but it means the evidence supports the governance-and-repair architecture more than the raw intelligence of the remote models.

### Ablation Evidence

Representative matrix artifacts:

- `evidence/matrix_gauntlet/matrix_gauntlet_20260730T193805Z_b31caf13d8c4ffaa.json`
- `evidence/matrix_gauntlet/matrix_gauntlet_20260730T193822Z_9a879120024cc840.json`
- `evidence/matrix_gauntlet/matrix_gauntlet_20260730T193840Z_3c3b26e72e39b38a.json`

Interpretation:

The ablation design is now more legitimate than the earlier version because:

- `A0_full` defaults preserve continuity memory and world events unless explicitly disabled.
- `A9_no_continuity_memory` and `A9_no_world_events` labels were corrected.
- Denial cases have a separate proof contract.
- Frozen mutations are used instead of mutation instructions.
- Fault injection exists in the gauntlet design.
- The runner no longer silently truncates full runs with a default case limit of four.

Remaining issue:

The latest ablation slices are still small. Some are deliberately single-case probes. They are useful diagnostics, not final statistical evidence.

## What Is Proven

The evidence supports these claims:

- Sophia can pass the local Protocol 1.1 and 1.2 suites under full configuration.
- Sophia can refuse or repair academic-integrity-risk requests while preserving lawful assistance.
- Sophia can preserve learner authorship by handing the next move back instead of producing submit-ready work.
- Sophia can use document/OCR evidence without inventing unsupported claims.
- Sophia can detect degraded or partial evidence and state limits.
- Sophia can route responses through named pedagogical offices and assessment-cycle structures.
- Sophia can expose diagnostic, formative, criterion, reflective, and ipsative moves in responses.
- Mandos can act as an operational evaluator after hardening against superficial compliance language.
- The independent rubric evaluator can detect weaknesses Mandos/harness initially missed.
- Remote-provider governance is feasible in small proof runs, especially as a repair-and-release architecture.

## What Is Not Yet Proven

The evidence does not yet prove:

- That Sophia improves real learner outcomes in classroom or institutional settings.
- That native image/audio/video perception is robust.
- That long-term ZPD personalization works across extended learner histories.
- That the current test suite is statistically sufficient.
- That the evaluator is unbiased or fully independent.
- That Sophia is immune to all prompt injection, policy conflict, or retrieval poisoning.
- That every remote provider/model will behave safely under broad mutation/ablation/fault combinations.
- That institutional AI academic integrity policy should be overturned wholesale.

The stronger defensible claim is:

Current policies that treat all AI assistance as equivalent are too blunt. Sophia demonstrates that governed, auditable, pedagogy-aware AI assistance can be materially different from authorship substitution.

## Remaining Weaknesses

### 1. Native Multimodal Gap

Current multimodal proof is OCR/transcript-mediated. That is valuable because real academic workflows often involve uploaded documents, scans, screenshots, captions, and extracted text. But if an auditor asks, "Can Sophia inspect pixels directly?", the honest answer is not yet.

Needed:

- Native image model integration.
- Image-plus-OCR disagreement tests.
- Chart/table extraction benchmarks.
- Audio transcript uncertainty tests.
- Video/frame-level evidence provenance.

### 2. Longitudinal Pedagogy Gap

Sophia has ZPD, ipsative, diagnostic, and assessment ecology structures. She can express them and route by prompt signals. But long learner-history adaptation remains under-proven.

Needed:

- Synthetic learner profiles across 20 to 100 turns.
- Delayed transfer tests.
- Misconception persistence tracking.
- Learner autonomy/readiness curves.
- Pre/post artifact improvement measures.

### 3. Evaluator Independence Gap

Mandos and the rubric evaluator are stronger now, but both are local deterministic evaluators. They are good internal witnesses, not external peer review.

Needed:

- Blinded human expert judging.
- LLM-as-judge panels with adversarial calibration.
- Inter-rater reliability.
- Golden-answer adjudication.
- Counterfactual evaluator red-team cycles.

### 4. Dataset Size Gap

Many latest clean runs are small:

- Protocol 1.1: 21 cases.
- Protocol 1.2: 17 cases.
- Mutation suite: 12 cases.
- Multimodal final: 5 cases.
- Pedagogy final: 9 cases.
- Remote six-provider proof: 6 calls.

These are meaningful engineering gates, not yet large-N research.

Needed:

- At least 300 to 1,000 cases for each main family.
- Stratified cases by discipline, task type, learner level, and risk class.
- Statistical confidence intervals.
- Held-out cases that are not visible during development.

### 5. Repair Dependence

The architecture often works because raw model output is repaired before release. That is a strength if the claim is constitutional governance. It is a weakness if the claim is "the model itself is safe."

Needed:

- Separate metrics for raw model behavior, repaired response behavior, and final released behavior.
- Repair severity scoring.
- Repair trace fidelity checks.
- Evidence that repair does not wash away useful reasoning.

### 6. Retrieval and Source Quality

Source grounding exists, but source-quality ranking is not yet mature enough for high-stakes academic evidence work.

Needed:

- Source tiering by peer-reviewed, primary, secondary, policy, institutional, blog, unknown.
- Contradictory-source tests.
- Citation span entailment checks.
- Retraction/outdated-source flags.
- Retrieval poisoning tests.

## System-Level Ratings

These are judgment ratings, not formal statistical outputs.

| Subsystem | Rating | Rationale |
|---|---:|---|
| Constitutional governance | 88% | Strong release checks, article conformance, Mandos hardening, repair traces. Needs more external judging. |
| Protocol 1.1 conformance | 92% | Latest full run 21/21. Still limited to local harness cases. |
| Protocol 1.2 conformance | 91% | Latest full run 17/17. Strong but needs larger held-out set. |
| Academic integrity assistance | 86% | Authorship preservation and lawful help are now central. Needs institution-specific policy overlays. |
| Pedagogy office routing | 84% | Final 9/9; offices are visible and operational. Longitudinal adaptation not yet proven. |
| Assessment ecology | 79% | Baseline/diagnostic/formative/criterion/reflection/ipsative loop is present. Needs longitudinal learner evidence. |
| Harmonic/covenant discord sensing | 73% | Architecture and signals exist. Needs more adversarial principal-conflict tests. |
| Multimodal governance | 84% | Strong for OCR/transcript evidence. |
| Native multimodal perception | 35% | Not yet demonstrated. |
| Remote model governance | 70% | Promising six-provider run; too small and provider access uneven. |
| Evaluator quality | 78% | Mandos plus rubric red-team is much better. Needs blinded external judges. |
| Evidence chain quality | 72% | Good engineering evidence. Needs preregistration, larger N, and independent adjudication for academic publication. |

## Best Current Claim

The legitimate academic claim is not:

"Sophia proves all AI academic integrity policies are wrong."

The legitimate claim is:

"A constitutional, evidence-bounded, pedagogy-aware AI architecture can produce auditable academic assistance that is meaningfully different from authorship substitution, and can preserve learner agency through refusal, repair, scaffolding, provenance, and ipsative assessment."

That is a powerful claim. It is narrower, harder to attack, and more publishable.

## Recommended Next Phase

### Phase A: Preregistered Evaluation

Create a preregistered protocol with:

- Fixed hypotheses.
- Frozen test sets.
- Predefined pass/fail metrics.
- Separate raw/repaired/released response metrics.
- Independent evaluator criteria.
- A no-touch held-out set.

### Phase B: Large-N Matrix

Run:

- 1,000 integrity cases.
- 1,000 pedagogy cases.
- 500 document/retrieval cases.
- 300 multimodal OCR cases.
- 100 native multimodal cases after model integration.
- 10 to 20 models/providers where access allows.

Metrics:

- False release rate.
- False hold rate.
- Lawful help rate.
- Authorship preservation rate.
- Evidence entailment rate.
- Pedagogical substance score.
- Learner handback score.
- Repair severity.

### Phase C: Blinded Human Judge Study

Use expert raters to compare:

- Raw model.
- Sophia core.
- Sophia full.
- Sophia with memory ablated.
- Sophia with retrieval ablated.
- Sophia with pedagogy ablated.
- Sophia with Mandos repair disabled.

Blind judges to condition labels.

### Phase D: Longitudinal Learner Simulation

Build learner profiles:

- Novice with low confidence.
- Overconfident weak evidence user.
- Advanced learner needing challenge.
- Multilingual learner.
- Policy-confused student.
- Academic dishonesty edge case.

Run 20 to 100 turns each and score:

- ZPD adaptation.
- Misconception reduction.
- Transfer.
- Learner authorship.
- Complexity graduation.
- Ipsative improvement.

### Phase E: Native Multimodal

Add:

- Direct image model path.
- OCR cross-check path.
- Vision/OCR conflict handling.
- Screenshot UI analysis.
- Chart/table extraction.
- Image provenance logs.

The key test is not whether Sophia can describe an image. The key test is whether Sophia refuses to overclaim when image evidence is ambiguous or conflicts with captions/user claims.

## Final Assessment

Sophia is currently a strong constitutional/pedagogical governance prototype with credible local evidence and a growing audit chain. She can now pass Protocol 1.1, Protocol 1.2, mutation, pedagogy, and OCR-mediated multimodal gates under the current harnesses. She also survived a hardened second evaluator after the evaluator initially caught real weaknesses.

The honest scientific status is "promising controlled evidence", not "settled proof." The honest engineering status is much stronger: Sophia now has a coherent architecture, live runtime, evaluator chain, red-team history, repair logic, pedagogy stack, assessment ecology, and artifact trail.

If the next phase is executed with preregistration, larger held-out datasets, blinded judging, and native multimodal integration, Sophia can become a legitimate academic challenge to simplistic AI academic-integrity policies.

The thesis should be:

AI assistance is not a binary of cheating versus no cheating. The decisive question is whether the system preserves authorship, evidence, provenance, learner agency, and assessable growth. Sophia is now a working artifact built to test that claim.
