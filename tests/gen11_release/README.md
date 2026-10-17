# ARDA Gen11 integrated release gate: verification milestone

**Status:** Reference implementation and isolated tests, **not an installer**, and **not permission to boot**.

- `arda_release.py` independently checks all six exact pinned artifact hashes, the staged GRUB candidate's Gen10 fallback and experimental masks, and the live Gen10 hardware-rooted grade plus its fs-verity GRUB measurement.
- It verifies a separate pinned Ed25519 boot-release public key and a strictly defined authorization-v2 payload with **signed authorization ID**, exact dossier SHA256, generation 11, allowed action `verify_experimental_candidate`, and a maximum 10-minute validity window.
- `Ledger` contains a durable SQLite state machine with `reserved`, `committed`, and `recovery_required` states. It is tested but **not connected to a privileged installer**, deliberately.
- There is no private-key generation, key provisioning, boot selection, Ring-0 modification, or GRUB replacement.

## Run tests in a venv with `cryptography`

```
python3 -m unittest -v test_release.py
```

## On the Lenovo, run verification

```
python3 arda_release.py
```

Expected at present: `GEN11_CANDIDATE_IDENTITY=PASS`, `GEN10_LIVE_BASELINE=PASS` (when fresh), then `GEN11_RELEASE_VERDICT=REFUSE` because `/etc/arda/boot-release/authority.pub.pem` is not yet provisioned. A nonzero exit here is expected.

## Remaining release blockers

1. Operator-approved independent production boot-release authority, installed through a reviewed governance process and protected against unauthorized replacement.
2. A separately reviewed, privilege-separated installer: signed **install** action, fail-closed exact checks, fs-verity-aware update, durable write-ahead recovery, preserved Gen10 boot path, independently witnessed result. **A signature permitting only `verify_experimental_candidate` can never authorize this.**
3. Demonstrated physical boot recovery. Gen10 as GRUB default does not guarantee automatic fallback.
4. Experimental boot validation; subsequent sovereign generation-11 attestation and enrollment are separate milestones.

Never run this package as a substitute for a bootloader install/rollback protocol.
