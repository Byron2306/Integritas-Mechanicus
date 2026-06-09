# KnowEdge Merger V4.1 — Master Operational Manual
**Release: Socratic Pulse (V4.1)**
**Protocol: Omega-4.1 Forensic Integration**

## 0. V4.1 Changelog (21 April 2026)
- **ERTP Review Refinement**: Removed initialization gates; immediate full-UI render on tab mount.
- **AI Integrity Guard V4.1**: Fully offline heuristic engine (trigrams, voice profile, transition density).
- **Citation Validator Service**: APA 7th Edition compliance checking with 10 hard-coded validation rules.
- **Agent Swarm Definition**: Added CONDUCTOR, SUPERVISOR, CRITIC1, CRITIC2, and SWARM_COORDINATOR roles.
- **PWA Finalization**: Updated manifest with PNG logos (logo-192/512) and synchronized `knowedge-merger-v4` cache.

---

## 1. System Philosophy: The Recursive Audit
KnowEdge Merger V4.1 introduces a memory-first architecture where the system not only analyzes data but "remembers" its own analysis patterns. This version focuses on **ERTP Review** and **EdgeK Agents**—autonomous execution loops that bridge semantic gaps between siloed artifacts while ensuring strict compliance with NWU and SAQA standards.

---

## 2. Core v4.1 Architecture

### 2.1 Layered Memory System (L0–L4)
The system utilizes a structured, hierarchical memory stack managed in `src/lib/memory.ts`:
- **L0 — Meta Rules**: Core system constraints (Immutable).
- **L1 — Insight Index**: Transient session facts and fast-lookup triggers.
- **L2 — Global Facts**: Accumulated knowledge across runs (LocalStorage Persistent).
- **L3 — Skill Tree**: Knowledge SOPs—reusable sequences for complex tasks.
- **L4 — Session Archive**: Distilled, high-fidelity records of all completed forensic runs.

### 2.2 NWU Policy & Assessment Memory
Integration of specific compliance layers:
- **NWU Policy Memory**: `src/lib/nwuPolicyMemory.ts` stores POPIA, AI Policy (5P_5.10), and IT policies.
- **Assessment Standards**: `src/lib/assessmentStandardsMemory.ts` stores examiner rubrics and marking bands.

---

## 3. ERTP Review System
The Educational Research Theory & Practice (ERTP) Engine provides a postgraduate feedback package tailored to NWU standards.

### 3.1 Workflow Lifecycle
1. **SOURCE ARTIFACT Ingestion**: Drag/drop of thesis or chapter into the teal-accented forensic card.
2. **Pre-Check Execution**: Automatic trigger of `AI Integrity Guard` (offline heuristics) and `Citation Validator` (APA 7th).
3. **Qualification Selection**: Toggling between MEd, PhD, or EdD descriptors.
4. **Socratic Swarm Execution**: Tri-document generation via specialized agents.
5. **Collection**: ZIP downloading of individual Reviewer documents.

### 3.2 AI Integrity Guard (V4.1 Offline)
Operates on local heuristics to ensure compliance with **NWU Policy 5P_5.10 (2025)**:
- **Trigram Analysis**: Detects repetitive patterns indicative of synthetic generation.
- **Voice Profile**: Checks first-person pronoun density (Personal Voice Score).
- **Citation Density**: Validates academic rigor vs length.
- **Transition Overuse**: Flags 'furthermore/moreover' saturation.

### 3.3 Citation Validator (APA 7th)
Applies 10 strict rules for academic compliance:
- Author format validation (No first names).
- DOI format integrity.
- Year of publication presence.
- Ampersand usage in parenthetical citations.
- Punctuation logic for 'et al.' citations.

---

## 4. Agent Swarm Architecture
Autonomous execution loops defined in `src/lib/edgekAgents.ts`:

- **CONDUCTOR**: Orchestrates the multi-stage review pipeline.
- **SUPERVISOR**: Validates findings against CHE/HEQSF/SAQA postgraduate requirements.
- **CRITIC 1 (Methodology)**: Specialized forensic audit of research design and data tools.
- **CRITIC 2 (Language/Compliance)**: Evaluates APA 7th, grammar, and policy alignment.
- **SWARM_COORDINATOR**: Manages parallel execution nodes for high-intensity synthesis tasks.

---

## 5. PWA & MSI Deployment

### 5.1 PWA Deployment
- **Manifest**: `manifest.json` configured for `standalone` display with PNG icons.
- **Caching**: `sw.js` uses `knowedge-merger-v4` for static asset persistence.
- **Icon Utility**: `generate-icons.html` included in `/public` for local PNG generation.
- **Android Compatibility**: Full PWA prompt support for field research data ingestion.

### 5.2 Windows MSI Installer
Native distribution system via WiX Toolset:
- **WXS Configuration**: `setup/KnowEdgeMerger-Setup.wxs` maps the ecosystem.
- **Build Script**: `setup/build-msi.bat` compiles the bundle.
- **Environment**: Bundled Node.js 20, Python 3.11, and local model proxies (Zero PowerShell required).

---

## 6. Novelty Report: Omega-4.1
The V4.1 update achieves novelty through the integration of **Policy-Aware AI Reasoning**. Unlike generic LLMs, KnowEdge V4.1 cross-references every finding against the NWU 2025 AI Policy and SAQA level descriptors in real-time, producing an auditable compliance trail without requiring active internet connections for integrity heuristics.

---

**DOCUMENTATION-FIRST POLICY: ENFORCED**
**SYSTEM STATE: NEURAL OPTIMIZED (V4.1)**
