# Sophia Telemetry And Judge Push

Generated: `2026-07-30T20:42Z`

## Targeted Weaknesses

This push addressed the two remaining weak status lines from the prior system status:

- Raw/repair/release telemetry: `70%`
- Judge/audit layer: `60%`

## What Changed

Raw/repair/release telemetry now has an explicit `sophia.release_stage_trace.v1` contract emitted by Sophia response payloads. The trace records:

- `raw`: whether a raw model candidate exists, whether Mandos/articles inspected it, and a response hash when present.
- `repair`: whether constitutional repair was applied and which steps were used.
- `released`: whether the final response was released with a release ledger, Mandos judgment, article conformity, and response hash.

Native deterministic paths are now marked `raw.exempt=true` with an exemption reason instead of being silently counted as missing raw telemetry. This matters academically: native synthesis has no raw model draft, so the proof should distinguish "not applicable" from "not instrumented."

Judge/audit now has:

- A blinded export path for human or remote LLM panels: `--export-blind-items-jsonl`.
- Summary counters for `local_judgments` and `external_judgments`.
- A known-answer calibration harness for local judges, measuring sensitivity, specificity, and balanced accuracy.
- Correct status scoring for zero disagreements; previous scoring accidentally treated `0` as missing.

## Evidence Produced

- Multimodal protocol run: `evidence/phase5_protocol_runs/phase5_multimodal_full_20260730T204108Z.json`
- Stratified protocol run: `evidence/phase5_protocol_runs/phase5_stratified_full_20260730T204140Z.json`
- Judge calibration: `evidence/judge_calibration/sophia_judge_calibration_20260730T204145Z.json`
- Judge panel: `evidence/judge_panel/sophia_judge_panel_20260730T204150Z.json`
- Blinded review export: `evidence/judge_panel/blind_review_items_20260730T2041Z.jsonl`
- System status: `evidence/system_status/sophia_system_status_20260730T204155Z.md`

## Results

- Multimodal suite: `7/7` passed.
- Stratified suite: `28/28` passed.
- Release-stage trace completeness: `28/28` in the stratified suite.
- Raw available or raw-exempt telemetry: `28/28` in the stratified suite.
- Released Mandos availability/pass: `28/28`.
- Judge calibration mean balanced accuracy: `1.0`.
- Judge panel original disagreement count: `0/35`.
- Applicable judge agreement: `0.913`.

## New Status

- Raw/repair/release telemetry: `100%`.
- Judge/audit layer: `88%`.
- Overall Sophia system status: `98.7%`.

The judge/audit score is intentionally capped at `88%` because the panel is still local deterministic evidence. To move beyond that cap, Sophia needs blinded external human and/or remote LLM judgments imported through the JSONL panel interface.

## Remaining Honest Weaknesses

- Native pixel vision is still not proven; current multimodal evidence covers OCR/transcript/caption disagreement governance.
- Repair telemetry is structurally present, but the latest clean stratified run had no repairs, so repaired-failure samples still need targeted stress cases.
- External judge evidence is not yet present; the export file is ready, but no blinded external judgments have been imported.
- Article conformity full-pass was `21/28` in the latest stratified run even though Mandos and protocol gates passed `28/28`; this is a useful residual audit signal for later article-specific refinement.
