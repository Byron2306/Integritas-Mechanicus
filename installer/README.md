# ARDA Hardware-Rooted Enrollment Installer

This installer migrates ARDA machinery, not machine identity.

## Portable

- ARDA runtime/source
- Valinor/BPF machinery
- policy compiler and projection plan
- reconstructed constitutional policy with provenance
- manufacturer trust anchors
- verifier public trust
- enrollment orchestration

## Never migrated

- `/var/lib/arda/projection/arda_measured_generation.sqlite3`
- active measured manifests from another machine
- PCR values or PCR11 binding state
- TPM EK/AK contexts
- leaf EK certificate from another machine
- TPM quotes
- signed verifier verdicts
- machine-id / boot-id
- cgroup kernel IDs
- verifier private keys

## Flow

1. `sudo arda-install`
2. reboot into Valinor if required
3. `sudo arda-preflight`
4. `sudo arda-enroll`
5. fresh target identity is created
6. Phase 4 attestation runs
7. signed verifier verdict is obtained
8. `sudo arda-grade`

The current scaffold deliberately stops at `30_measured_identity` until the canonical
fresh-generation API from ARDA is wired in. This is fail-closed by design.
