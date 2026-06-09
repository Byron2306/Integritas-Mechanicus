# PATCHSET INDEX

## Overview
This patchset implements a comprehensive architectural hardening of the KnowEdge Merger platform. It pivots the core execution logic from a loose Express shell to a deterministic **Run Controller** governed by **3.10-ZD state transitions**, integrates the **Brothers Gr4m Omega decision-state ledger**, and wires in the **GG_InternalFineWeb ingestion spine** for authoritative evidence processing.

## Changes

### 0001_server_ts.patch
- Replaces loose state management with a Pydantic-style (interface-guarded) `RunController`.
- Implements **Brothers Gr4m Omega decision-state memory** (Protected Nuclei, Admission Control).
- Integrates **GG_InternalFineWeb** for local artifact normalization.
- Implements the **3.10-ZD Heartbeat** and **Receipt Audit Ledger**.
- Adds a **Shadow Twin Parity Gate** for simulation/reality verification.
- Injects **Mashup Master Domains**: Container Classification, Human Approval Gate, and Diagnostic State Ledger.

### 0002_src_App_tsx.patch
- Updates the Synthesis Dashboard to reflect deterministic run states.
- Wires in the **Decision-State Ledger** view.
- Integrates the **Forensic Evidence Audit** telemetry.

### 0003_src_lib_retrieval_latticeKernel_ts.patch
- Refactors the kernel to support **NowEdge Lattice** provider abstractions and in-memory caching.

### 0004_src_lib_ingest_internalFineWeb_ts.patch
- Adds SHA-256 integrity verification and PII pseudonymization stubs.

## Combined Patch
- **ALL_CHANGES.patch**: Unified diff of all modifications.
