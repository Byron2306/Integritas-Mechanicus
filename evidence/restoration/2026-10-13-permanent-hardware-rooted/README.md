# ARDA Permanent Hardware-Rooted Grade

Date: 2026-10-13

## Result

The restored Valinor host reached and now continuously maintains:

- `ok: true`
- `software_os_grade: true`
- `hardware_rooted_os_grade: true`
- `boundary: hardware-rooted OS-grade production milestone`
- `remote_verifier_signed_fresh: true`
- `signed_verdict_green: true`
- `verifier_signature_verified: true`

## Constitutional projection

Live authoritative BPF policy state:

- generation hash prefix: `13745055897814023361`
- redline rule count: `7`
- projection flags: `1`

The seven-rule state is the explicitly declared restoration reconstruction.
It is not claimed to be literal recovered July rule text.

## Permanence mechanism

The result is not made permanent by trusting an old verdict.

It is maintained by permanent machinery:

1. persistent verifier service
2. persistent postboot attestation service
3. five-minute refresh timer
4. constitutional projection reasserted from the active projection plan
5. fresh TPM-backed attestation
6. fresh signed verifier verdict
7. fresh OS-grade evaluation

## Identity boundary

The current host uses the restoration verifier identity:

- key id: `arda-gen1-restoration-verifier`
- verifier id: `arda-phase4-loopback-restoration`

This restoration identity is HOST-SPECIFIC.

It MUST NOT be copied into the portable Lenovo installer.

Portable enrollment must mint and use the target host's own state and must use
the configured production/off-box verifier path.

## Invariant

Migrate machinery, never machine identity.
