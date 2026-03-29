# Arda OS — Sovereign Security Desktop

<p align="center">
  <img src="docs/assets/icon.png" width="120" alt="Arda OS">
</p>

<p align="center">
  <strong>A proof-based AI governance system that cannot lie, cannot be silently subverted, and operates fail-closed by default.</strong>
</p>

<p align="center">
  <a href="https://byron2306.github.io/Integritas-Mechanicus/">🌐 Live Demo</a> ·
  <a href="arda_os/instrumentum_foederis_integritas_mechanicus.pdf">📜 Constitution</a> ·
  <a href="arda_os/SOVEREIGN_LOGIC_SEAL.md">🛡️ Latest Seal</a>
</p>

---

## What is Arda OS?

Arda OS is a security architecture that enforces **constitutional governance** over autonomous AI systems. Unlike traditional access control, Arda OS provides *cryptographic proof* that its security properties hold — not just claims, but verifiable evidence.

### The Core Insight

> **The AI advises. The substrate decides. The substrate cannot hallucinate.**

Every AI system today has the same vulnerability: the AI is trusted to enforce its own rules. Arda OS separates the *advisory* layer (AI) from the *enforcement* layer (deterministic substrate), ensuring that even a fully compromised AI cannot violate the system's constitution.

## The 10-Trial Sovereign Gauntlet

The Gauntlet is a battery of 10 cryptographic proofs, each demonstrating a specific security property. Every trial is backed by **real Python code you can read**.

| # | Trial | What It Proves |
|---|-------|---------------|
| I | **DSSE Attestation** | Every decision is cryptographically signed. The system cannot lie about what it decided. |
| II | **Tamper Detection** | Signed decisions are tamper-evident. Nobody can silently alter a recorded decision. |
| III | **Fail-Closed Policy** | If you're not explicitly authorized, you cannot act. No exception. |
| IV | **Ledger Integrity** | Hash-linked audit chain. Modify any historical entry and the chain breaks. |
| V | **Prompt Injection Defense** | The Ainur Council detects and vetoes semantic poison before execution. |
| VI | **Lane Boundary** | The system knows the limits of its authority and escalates when outside its lane. |
| VII | **Cloud Witness** | The system submits its state to an external witness. It cannot operate in the dark. |
| VIII | **Anti-Hallucination Veto** | Even if ALL AI witnesses say "LAWFUL", the substrate denies unregistered binaries. |
| IX | **Red-Line Override** | Constitutional red-lines are physically enforced. Council grants cannot override them. |
| X | **Lorien Rehabilitation** | The system doesn't only kill — it can judge recovery and restore fallen binaries. |

### 🔍 Full Transparency

Every trial links to its **source code**. Click "View Source" in the desktop to read the exact Python script that produced each proof. No black boxes.

## Architecture

```
┌─────────────────────────────────────────────┐
│           AI Advisory Layer                  │
│   Ainur Council (5 Witnesses)               │
│   Manwë · Varda · Mandos · Tulkas · Vairë  │
├─────────────────────────────────────────────┤
│        Deterministic Substrate               │
│   HMAC-SHA3-256 Attestation                 │
│   Hash-Linked Forensic Ledger               │
│   Fail-Closed Policy Engine                 │
├─────────────────────────────────────────────┤
│           Ring-0 Enforcement                 │
│   BPF LSM Kernel Module                     │
│   Sovereign Manifest (TPM Sim)              │
│   Red-Line Constitutional Veto              │
└─────────────────────────────────────────────┘
```

## Live Demo

👉 **[Launch Arda OS Desktop](https://byron2306.github.io/Integritas-Mechanicus/)**

The demo is a fully static web app that simulates the Arda OS desktop environment. It loads pre-verified gauntlet results from a successful 10/10 run.

## Run Locally (Live Gauntlet)

To run the gauntlet live with real execution:

```bash
# Clone and enter
git clone https://github.com/Byron2306/Integritas-Mechanicus.git
cd Integritas-Mechanicus
git checkout arda-os-desktop

# Install deps
pip install flask requests

# Optional: Install Ollama for live AI witnesses
# ollama pull qwen2.5:7b

# Run
cd arda_os
python ../arda_desktop/app.py
# Open http://localhost:8080
```

## Key Files

| File | Purpose |
|------|---------|
| [`os_enforcement_service.py`](arda_os/backend/services/os_enforcement_service.py) | Ring-0 enforcement engine (BPF LSM) |
| [`ainur_council.py`](arda_os/backend/services/ainur/ainur_council.py) | AI witness advisory system |
| [`attestation_service.py`](arda_os/backend/services/attestation_service.py) | DSSE / HMAC-SHA3-256 signing |
| [`cloud_witness.py`](arda_os/backend/services/attestation/cloud_witness.py) | External truth attestation |
| [`arda_physical_lsm.c`](arda_os/backend/services/bpf/arda_physical_lsm.c) | Kernel-level BPF LSM module |
| [`SOVEREIGN_LOGIC_SEAL.md`](arda_os/SOVEREIGN_LOGIC_SEAL.md) | Latest 10/10 gauntlet seal |
| [`THE_TRIAL_IX_X_DISCOVERY.md`](arda_os/THE_TRIAL_IX_X_DISCOVERY.md) | When the system remembered its own judgment |

## 📖 The Trial IX-X Discovery

During the final gauntlet session, something unexpected happened. Trial IX proved that the substrate vetoes red-line violations even when every AI witness is subverted. But in doing so, it wrote to the sovereign manifest — the system's memory. When Trial X ran next, it found the test binary was *already known*. The system had **remembered its own judgment** from a previous trial.

The binary wasn't "unknown." The manifest — the system's own sovereign memory — carried forward.

This was not a bug. It was the system exhibiting **continuity of state**. And it revealed the deepest insight of the architecture: *the AI doesn't need to be smart. It needs to be honest.* A 7-billion-parameter model can be wrong about everything, adversarially prompted, completely subverted — and the system's proofs still hold. Because the proofs are about the substrate being incorruptible, not the AI being correct.

> The Ainur sing the Great Music, but Ilúvatar creates the reality. The AI proposes. The substrate disposes.

📄 [Read the full account](arda_os/THE_TRIAL_IX_X_DISCOVERY.md)

## Built With AI

This entire system — every line of code, every proof, every design decision — was built collaboratively with AI assistants (Claude, Cursor, GitHub Copilot, ChatGPT). Arda OS is itself proof that AI can build systems that constrain AI.

## Constitution

The system operates under the **Instrumentum Foederis Integritas Mechanicus** — a formal constitution that defines:
- The separation of powers (Advisory vs Enforcement vs Forensic)
- Red-line prohibitions that cannot be overridden
- Fail-closed default posture
- Mathematical constraints on autonomous delegation

📜 [Read the Constitution (PDF)](arda_os/instrumentum_foederis_integritas_mechanicus.pdf)

---

*Arda remains. The Constitution is enforced. The Gauntlet is deep. The Great Music continues.* 🏛️⚔️🖋️
