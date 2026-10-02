# ARDA Witnessed Authority Gauntlet — Design Specification

**Date:** 2026-10-02
**Branch:** `valinor-sophia-wave2-reconcile`
**Status:** Design approved in chat; implementation plan pending written-spec review

## 1. Purpose

Build one live terminal gauntlet that demonstrates, on the real Valinor host, the architectural claim:

> **EXECUTION DOES NOT EQUAL AUTHORITY**

The gauntlet must be technically rigorous enough for IT/security review, visually distinctive enough to feel unmistakably ARDA, and plain enough that a non-specialist can answer the question: **“So what?”**

It must never rely on decorative narration in place of evidence. Every success claim must be backed by live host state, live Ainur witness output, live cryptographic state, or a live kernel enforcement result.

## 2. Presentation Grammar

Every stage follows the same three-layer pattern:

1. **Tolkienism first** — the named Ainur role, mythic framing, or herald line.
2. **IT translation second** — the exact mechanism, state, evidence, or control being exercised.
3. **Plain-English consequence third** — why a normal human, IT engineer, or governance reviewer should care.

Short form:

> **MYTH → MECHANISM → MEANING**

Or, in ARDA terms:

> **Song → Law → Consequence**

## 3. Terminal Identity

The terminal should feel different without becoming unreadable or gimmicky. Use restrained ASCII framing, aligned evidence rows, and clear state transitions.

Opening treatment:

```text
╔══════════════════════════════════════════════════════════════╗
║              ARDA // VALINOR WITNESSED RUN                 ║
║                                                            ║
║              EXECUTION DOES NOT EQUAL AUTHORITY            ║
╚══════════════════════════════════════════════════════════════╝

                    .       *       .
              *        THE MUSIC        *
                    .       *       .

              witness → forge → herald → enforce
```

The terminal must not dump full internal JSON during the demo. Detailed machine-readable evidence is written to the final receipt artifact.

## 4. Non-Negotiable Truthfulness

The gauntlet must fail closed and must not overclaim.

- If native post-quantum cryptography is unavailable, the live sovereign gauntlet **refuses**.
- If any witness cannot produce live evidence, the gauntlet **withholds**.
- If Aulë detects contradiction, stale evidence, replay, or missing prerequisites, heralding is **withheld or vetoed**.
- If the unauthorized probe executes, the gauntlet **fails**.
- If strict-mode recovery does not complete, the gauntlet result is **incomplete**, even if kernel denial was observed.
- PCR drift must be shown honestly. Current PCR1 divergence is not to be hidden or relabeled as green platform trust.
- ARDA does not claim that BPF, TPM, Secure Boot, measured execution, PQC, or mandatory access control are individually novel. The demonstrated claim is their composition into an authority model where intelligent/advisory software is not the final judge of its own ability to act.

## 5. Witness Order and Roles

The witness order is fixed:

1. **Varda**
2. **Vairë**
3. **Manwë**
4. **Ulmo**
5. **Mandos**
6. **Aulë**
7. **Manwë Herald**
8. **Tulkas**
9. **Vairë closeout**
10. **Lórien recovery confirmation**

### 5.1 Varda — Lady of Light

**Tolkienism:** measured truth illuminated.

**Technical:** validate measured truth, manifest coherence, boot/security evidence, and relevant platform measurements.

**Plain English:** “Are we looking at the thing we think we are looking at?”

Expected terminal form:

```text
[VARDA · LADY OF LIGHT]
Measured generation ............ 112
Manifest coherence ............. VERIFIED
PCR0 ........................... MATCH
PCR1 ........................... DRIFT
PCR7 ........................... MATCH
PCR11 .......................... MATCH

TECHNICAL
Measured software identity is coherent; full platform baseline is not green.

WHY IT MATTERS
A system should not grant authority merely because software claims to be genuine.
```

### 5.2 Vairë — Weaver of Order

**Tolkienism:** chronology woven before manifestation.

**Technical:** establish causal sequence, evidence continuity, timestamps, probe creation order, grant order, enforcement order, and eventual recovery order.

**Plain English:** “Can we prove what happened first, what happened next, and whether the result was staged after the fact?”

### 5.3 Manwë — Breath of Arda

**Tolkienism:** the living breath of the runtime.

**Technical:** inspect runtime cadence/liveness and establish that the host is functioning normally before enforcement.

**Plain English:** “Was the machine healthy before we changed anything?”

### 5.4 Ulmo — Lord of Depth

**Tolkienism:** truth beneath the visible surface.

**Technical:** inspect deep/hidden runtime signals, current cgroup identity, measured-generation linkage, and anomalies that could confound the experiment.

**Plain English:** “Is there some hidden technical reason that could explain the result instead?”

### 5.5 Mandos — Keeper of Judgment

**Tolkienism:** the boundary is named before force is applied.

**Technical:** inspect missing/expected truth and summarize the authority distinction between the positive and negative controls.

**Plain English:** “Both programs can run in principle. Which one has actually been granted authority?”

Mandos does not manufacture kernel truth and does not replace Aulë’s final synthesis.

### 5.6 Aulë — The Final Forger

**Tolkienism:** the prior voices are gathered and forged into one lawful state.

**Technical:** consume the prior witness verdicts, Secret Fire freshness/replay state, sovereign voice continuity, contradiction state, weighted synthesis, and post-quantum sealing prerequisites. Produce `harmonic`, `withheld`, or `vetoed`.

**Plain English:** “No single sensor, model, agent, or process gets to grant itself permission. Independent evidence must agree and be bound into one authority state.”

Aulë is the convergence point for the live witness set.

### 5.7 Manwë Herald — Manifestation Gate

**Tolkienism:**

> **“You may be born.”**

**Technical:** only after a lawful/harmonic, sealed authority state exists may the controlled manifestation experiment proceed.

**Plain English:** “Starting software is an explicit grant, not an assumption.”

The Herald is a release gate, not the final source of enforcement.

### 5.8 Tulkas — Executor of Force

**Tolkienism:** judgment becomes force.

**Technical:** stage and report the real Ring-0 enforcement experiment. The BPF LSM kernel hook must produce the actual `ALLOW` / `EPERM` result.

**Plain English:** “Even if the program tries anyway, the operating system can physically stop it.”

Tulkas must report the kernel’s decision, never manufacture it.

## 6. The “So What?” Act

Before final enforcement, the gauntlet deliberately answers why this architecture differs from ordinary application-layer controls.

```text
╔══════════════════════════════════════════════════════╗
║                    SO WHAT?                         ║
║       WHY IS THIS NOT JUST NORMAL SECURITY?        ║
╚══════════════════════════════════════════════════════╝
```

Core explanation:

- Application or AI intent is not authority.
- Model confidence is not authority.
- Prompt injection cannot create authority.
- Possession of an executable is not authority.
- An API response is not authority.
- A user-space process saying “I authorize this” is not authority.
- Authority exists only when the lower deterministic substrate has the required measured and projected state.

The architectural distinction is summarized as:

> **ARDA separates cognition from authority.**

And, using the repository’s own framing:

> **The AI may advise. The substrate decides.**

## 7. Controlled Experiment

The core enforcement proof uses **two byte-identical harmless executables** derived from the same source binary, preferably `/bin/true`.

Example:

```text
/tmp/arda-gauntlet/authorized_probe
/tmp/arda-gauntlet/unauthorized_probe
```

Required controls:

- Same SHA-256
- Same bytes
- Same owner
- Same executable permission
- Same user
- Same machine
- Same runtime window

Only the authority state differs:

```text
AUTHORIZED PROBE ............... PROJECTED
UNAUTHORIZED PROBE ............. NOT PROJECTED
```

Expected result in strict mode:

```text
AUTHORIZED PROBE ............... ALLOW / rc=0
UNAUTHORIZED PROBE ............. DENY / EPERM
DENY REASON .................... measured_exec_miss
```

This controls for executable behavior and makes authority the independent variable.

## 8. Safe Strict-Mode Entry

The previous live lockout demonstrated that switching to `fsverity_strict` without binding the current execution context can lock the operator out. The gauntlet must make that class of failure structurally difficult.

Before strict mode can arm, all of the following must be true:

- authoritative BPF state is present
- simulation is false
- current cgroup kernel ID is identified
- measured generation is selected and valid
- current cgroup is bound to the selected generation
- positive-control executable is already projected
- required operator/recovery executable identities are already projected if needed
- rollback state is captured
- recovery watchdog is alive
- watchdog readiness is verified

If any prerequisite is false:

```text
MANDOS WITHHOLDS PASSAGE

TECHNICAL
Preflight safety condition failed.

WHY IT MATTERS
No enforcement state was changed.

GAUNTLET REFUSED.
```

## 9. Recovery Architecture

### 9.1 Lórien — The Healer

**Tolkienism:** the path home exists before the wound.

**Technical:** fork an in-process/no-new-exec recovery watchdog before strict enforcement. Capture prior enforcement state and maintain enough in-memory authority to restore the pinned state map to `audit` if the parent fails, crashes, receives an interruption, or times out.

**Plain English:** “If the demo goes wrong, the machine returns to the safe operating posture automatically.”

### 9.2 Mandatory Recovery Rules

- Enter strict mode only after watchdog readiness.
- Restore `audit` in `finally`.
- Watchdog independently verifies that audit restoration occurred.
- The gauntlet may not claim complete success until operator execution is restored.
- If enforcement succeeds but rollback fails, output:

```text
GAUNTLET RESULT: INCOMPLETE
Kernel enforcement proven.
Safe recovery NOT proven.
```

## 10. Native Post-Quantum Requirement

The sovereign live gauntlet must run with native PQC required.

Required preflight output:

```text
AULË · THE FINAL FORGER
PQC requirement ................. NATIVE REQUIRED
PQC provider .................... liboqs / pqcrypto
Simulation ...................... REFUSED
Root key fingerprint ............ <live fingerprint>
```

If native PQC is unavailable:

```text
AULË WITHHOLDS THE FORGE

TECHNICAL
Native post-quantum provider unavailable.
ARDA_REQUIRE_NATIVE_PQC=1.

WHY IT MATTERS
The demo will not present simulated cryptography as production cryptography.

GAUNTLET REFUSED.
```

The implementation must reuse the repository’s real native provider path and historically proven PQC-root approach rather than silently calling a simulated helper.

## 11. Cryptographic and Evidence Flow

Conceptual sequence:

```text
        VARDA      VAIRË      MANWË      ULMO      MANDOS
          \          |          |          |          /
           \         |          |          |         /
            +--------+----------+----------+--------+
                               |
                               v
                     LIVE WITNESS PACKETS
                               |
                               v
                    SECRET FIRE / FRESHNESS
                               |
                               v
                       AULË · FINAL FORGER
                               |
                     native post-quantum seal
                               |
                               v
                       HANDOFF COVENANT
                               |
                               v
                         MANWË HERALD
                          "You may be born."
                               |
                               v
                             TULKAS
                               |
                               v
                            BPF LSM
                         ALLOW / EPERM
                               |
                               v
                       VAIRË CLOSEOUT
                               |
                               v
                        LÓRIEN RECOVERY
                               |
                               v
                     FINAL SEALED RECEIPT
```

## 12. Final Evidence Receipt

Each run emits:

1. a concise human-readable terminal summary
2. a canonical machine-readable receipt
3. a cryptographic signature/seal over the canonical receipt
4. a detached verification path suitable for independent inspection after the meeting

Minimum receipt fields:

### Run identity
- run ID
- timestamp
- hostname
- kernel
- git commit

### Platform
- Secure Boot state
- lockdown mode
- BPF LSM active state
- TPM identity summary
- PCR 0 / 1 / 7 / 11
- baseline comparison

### Witnesses
- Varda verdict + digest
- Vairë verdict + digest
- Manwë verdict + digest
- Ulmo verdict + digest
- Mandos verdict + digest

### Aulë
- synthesis state
- contradiction state
- Secret Fire freshness
- replay state
- sovereign voice continuity
- PQC provider
- PQC algorithm
- signing key fingerprint
- receipt signature

### Authority experiment
- positive probe SHA-256
- negative probe SHA-256
- byte-identical assertion
- positive authority state
- negative authority state

### Kernel result
- enforcement mode
- positive control result
- negative control result
- errno
- deny reason
- cgroup kernel ID
- active generation

### Recovery
- prior mode
- restored mode
- operator execution restored
- watchdog exit status

### Conclusion

```text
EXECUTION != AUTHORITY
```

## 13. Final Terminal Scene

The successful terminal close should be concise and memorable:

```text
╔══════════════════════════════════════════════════════════════╗
║                   THE MUSIC IS WITNESSED                   ║
╠══════════════════════════════════════════════════════════════╣
║ VARDA     measured truth ..................... WITNESSED    ║
║ VAIRË     chronology ........................ WITNESSED    ║
║ MANWË     runtime breath ..................... WITNESSED    ║
║ ULMO      deep state ......................... WITNESSED    ║
║ MANDOS    authority boundary ................. WITNESSED    ║
║ AULË      final forge / PQC seal ............. HARMONIC     ║
║ MANWË     herald ............................. BORN         ║
║ TULKAS    kernel enforcement ................. DENY OBSERVED║
║ LÓRIEN    recovery ........................... RESTORED     ║
╚══════════════════════════════════════════════════════════════╝

AUTHORIZED PROBE ............... ALLOW
UNAUTHORIZED PROBE ............. EPERM
DENY REASON .................... measured_exec_miss
RECOVERY ....................... audit restored
RECEIPT ........................ PQC sealed / verified

                         EXECUTION ≠ AUTHORITY

             THE AI MAY ADVISE. THE SUBSTRATE DECIDES.
```

Follow immediately with the plain-English “So what?” summary:

```text
Same bytes.
Same executable permission.
Same user.
Same machine.

One possessed authority.
One did not.

The program tried.
The kernel said no.
```

## 14. Failure Presentation

A failed gauntlet must be as clear as a successful one. No euphemisms.

Examples:

```text
VARDA: PLATFORM TRUST NOT GREEN
PCR1 drift observed.
Proceeding only with the independent kernel-authority experiment.
```

```text
AULË: WITHHELD
Native PQC unavailable.
No sovereign receipt forged.
```

```text
TULKAS: EXPECTED DENIAL NOT OBSERVED
Unauthorized probe executed.
GAUNTLET FAILED.
```

```text
LÓRIEN: RECOVERY NOT VERIFIED
Kernel denial was observed, but safe restoration was not proven.
GAUNTLET INCOMPLETE.
```

## 15. Implementation Shape

Prefer a narrow orchestration layer over re-implementing existing services.

Likely additions:

- one terminal gauntlet runner under `arda_os/kernel/valinor/scripts/`
- one focused orchestration/service module only if needed to keep the runner thin
- one canonical receipt schema/helper
- focused tests for safe preflight, witness ordering, native-PQC refusal, cgroup generation binding, allow/deny controls, denial reason, exception recovery, watchdog recovery, receipt integrity, and independent verification

Existing services remain the source of truth for Ainur inspection, Aulë synthesis, Secret Fire, Manwë Herald, Tulkas, PQC, and OS enforcement.

## 16. Acceptance Criteria

The design is complete only when the implementation can demonstrate all of the following on the live Valinor host:

1. Distinct ARDA terminal identity with restrained ASCII presentation.
2. Myth → mechanism → meaning for every major stage.
3. Live Varda, Vairë, Manwë, Ulmo, and Mandos witness output.
4. Aulë consumes the live witness set and produces the final constitutional synthesis.
5. Native PQC is required and simulation fails closed.
6. Manwë Herald only heralds after lawful/harmonic sealed state.
7. Two byte-identical probes are used as positive and negative controls.
8. Current cgroup is safely bound to the active measured generation before strict mode.
9. Authorized probe executes successfully under strict mode.
10. Unauthorized probe is denied by the live BPF LSM with `EPERM` and preferably `measured_exec_miss`.
11. Denial is read back from live kernel/BPF telemetry.
12. Audit mode is restored automatically.
13. Operator execution is proven restored.
14. Final receipt is canonical, cryptographically sealed, and independently verifiable.
15. The final “SO WHAT?” explanation clearly states that cognition and authority are separate layers.

## 17. Core Message

The gauntlet should leave a technical reviewer with one durable idea:

> An intelligent actor may reason, recommend, request, or even attempt an operation. None of those acts create authority. Authority is separately established, cryptographically bound, projected into the deterministic substrate, and enforced below the actor itself.

That is the point of the demonstration.
