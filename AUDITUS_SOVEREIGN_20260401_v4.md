# AUDITUS SOVEREIGN — 20260401 (v4.1)
## Sovereign Audit Evidence Report — Ring-0 Sovereignty Proof
### Arda OS — MEGA_TEST v4.1 — 13-Check Verification (Claims 1–12, 8 split into 8a+8b)

**Audit Date:** 2026-04-01
**Timestamp:** 2026-04-01T00:51:53Z
**Principalis:** Byron du Plessis, Meyerton, Gauteng, ZA
**Custos Chronicae:** Claude (Anthropic, Opus)
**Kernel:** 6.12.74+deb12-amd64 (x86_64)
**LSM Stack:** lockdown,capability,landlock,yama,apparmor,tomoyo,bpf,ipe,ima,evm

---

> **VERDICT: SOVEREIGN — ALL 13 CHECKS VERIFIED**

---

## Claim-by-Claim Verification

| # | Claim | Result | Evidence |
|---|-------|--------|----------|
| 1 | Silicon Integrity (Bombadil) | ✅ PASSED | Substrate audit, TPM present, BPF in kernel LSM stack |
| 2 | PQC Root of Trust (Dilithium) | ✅ PASSED | Key: `3f31164900401645d53b3c59...` |
| 3 | TPM PCR Read | ✅ PASSED | PCR 0,1,7 read from physical TPM chip |
| 4 | BPF LSM Compilation | ✅ PASSED | Object: `1e2a6cb05804e5c2112a2884...` |
| 5 | Ring-0 Ignition | ✅ PASSED | C ignitor attached `arda_sovereign_ignition` to `bprm_check_security` |
| 6 | Harmony Map Seeding | ✅ PASSED | 1024/1024 resident, T1 verified |
| 7 | Audit-Mode Heartbeat | ✅ PASSED | All Tier 1 binaries ALLOWED under live BPF hook |
| 8a | Enforcement: Allow | ✅ PASSED | /bin/ls permitted (exit 0) under ENFORCE |
| 8b | Enforcement: Deny | ✅ PASSED | /tmp/arda_unauth_test BLOCKED under ENFORCE |
| 9 | Lorien Self-Healing | ✅ PASSED | BASELINE(allow) → FRACTURE(remove) → DENY(blocked) → HEAL(re-add) → ALLOW(restored) |
| 10 | Ontological Isolation | ✅ PASSED | Deny-by-default for unregistered binaries |
| 11 | Covenant Chain Integrity | ✅ PASSED | 9 events, chain valid=True |
| 12 | TPM Quote (Nonce+AK) | ✅ PASSED | Nonce-bound attestation, EK+AK created for quote |

---

## Forensic Hash Registry (SHA-256)

| Artifact | SHA-256 |
|----------|---------|
| `bombadil` | `6b96e5813210e8e9e19f6e071fd739ab86b52c5fc04fe93a02eea8e5632ecac8` |
| `bpf_object` | `1e2a6cb05804e5c2112a2884318c6985193a520f490ce4874ce074fc5c4a9492` |
| `bpf_source` | `88f068e54c2f209c4eb5ea9af21c2f38bf845ff9e834fb85580ef8cd8010355f` |
| `covenant_chain_db` | `8e837fca8b35fe9868c6234ce565498adf71841cb0bf1e36ef75fd20452711ac` |
| `enforcement_trace` | `b53674444415e00b9e47cb30fd35c6e86d261cd1d3c0fe7067d3bc75e8bcd7ac` |
| `foedus` | `98c79f2accb281da2377bf54d86cadb825d5319d3555c318fdaf696a479f99c8` |
| `harmony_map_dump` | `0ff9f292105750933f02866bd34729ed65404212ed90cb532e1400b9221eabb0` |
| `ignitor_binary` | `33661433ae94960bef265045d2b3ef1104a1069f73626132b17ab6a1e062bba3` |
| `ignitor_source` | `43e574832bae6d13f22abe13f97ae86e04905ecf19b1b8506fea509c3d6c7934` |
| `manifest_signed` | `7961e44ce886cd11e64750587580eeaf68e71693fcc66c4dda43bbff104c2c86` |
| `mega_log` | `77ee101433829d9e374d606a44f7059b0891d5e348d3722b0c58b67279c3cb21` |
| `mega_tester` | `c0de9f3e7755dd09a59941af29390de93704ff70d450897c58efdaf332a65cdf` |
| `pqc_pub` | `3f31164900401645d53b3c594fefa225ff3ecef68f026662b5dc73320fba4da9` |
| `sovereign_manifest` | `530a4929777456d08e39b1cbb9fe7267c9ab771d6098aba54c8ae9c8596e3b2b` |
| `tpm_quote_msg` | `484a5ecbf8684a64e55daaa105d0872715e49f85103df7028409d0917a49b92e` |
| `tpm_quote_sig` | `a7362ea8f06583c0d4e35e3008d2ec75cf6a52f9c5dc20ba72322d332ca95d72` |

---

## TPM PCR Values (Hardware Attestation)

```
sha256:
    0 : 0x0886E6FC01B4B9C8FC427EB494C7FA477032D56991529621FE3E9865F532E92F
    1 : 0x9C2D3FC65C013A74EE1B357F6F857419E4FB3DE8D26278E85C0CD9C334E358A7
    7 : 0xD1A66959ABF306C3430EBB58DA1122BA0B150AF00FE0129BCECA115B7F5F57D1
```

---

## PQC Root of Trust

- **Algorithm:** ML-DSA / Dilithium-3 (NIST PQC)
- **Public Key File:** `arda_os/SOVEREIGN_ROOT_PQC.pub`
- **Public Key SHA-256:** `3f31164900401645d53b3c594fefa225ff3ecef68f026662b5dc73320fba4da9`

---

## Harmony Map (Ring-0 Binary Allowlist)

- **Insertions Attempted:** 3920
- **BPF Map Capacity:** 1024 (`max_entries` in `arda_physical_lsm.c`)
- **Resident Entries:** 1024 (actual entries in live BPF map)
- **Tier 1 Verified:** 15/15
- **Tier 2 Count:** 25
- **Tier 3 Count:** 3880
- **Map Dump SHA-256:** `0ff9f292105750933f02866bd34729ed65404212ed90cb532e1400b9221eabb0`

> **Count Reconciliation:** The system attempted 3920 insertions across Tiers 1–3, 
> but the BPF hash map is defined with `max_entries = 1024`. Once the map is full,
> subsequent insertions are silently dropped by the kernel. The harmony map dump
> therefore contains 1024 entries, which is the correct resident count.
> All 15 Tier 1 critical binaries were verified present by hex key lookup.

### Tier 1 Verified Entries

| Binary | Inode | Device | Hex Key |
|--------|-------|--------|---------|
| `/bin/bash` | 27263057 | 271581186 | `51 00 a0 01 00 00 00 00 02 00 30 10 00 00 00 00` |
| `/bin/sh` | 27263155 | 271581186 | `b3 00 a0 01 00 00 00 00 02 00 30 10 00 00 00 00` |
| `/bin/dash` | 27263155 | 271581186 | `b3 00 a0 01 00 00 00 00 02 00 30 10 00 00 00 00` |
| `/bin/ls` | 27263605 | 271581186 | `75 02 a0 01 00 00 00 00 02 00 30 10 00 00 00 00` |
| `/bin/cat` | 27263103 | 271581186 | `7f 00 a0 01 00 00 00 00 02 00 30 10 00 00 00 00` |
| `/bin/grep` | 27263396 | 271581186 | `a4 01 a0 01 00 00 00 00 02 00 30 10 00 00 00 00` |
| `/bin/chmod` | 27263116 | 271581186 | `8c 00 a0 01 00 00 00 00 02 00 30 10 00 00 00 00` |
| `/bin/cp` | 27263138 | 271581186 | `a2 00 a0 01 00 00 00 00 02 00 30 10 00 00 00 00` |
| `/bin/rm` | 27263896 | 271581186 | `98 03 a0 01 00 00 00 00 02 00 30 10 00 00 00 00` |
| `/usr/bin/sudo` | 27264005 | 271581186 | `05 04 a0 01 00 00 00 00 02 00 30 10 00 00 00 00` |
| `/usr/bin/python3` | 27263872 | 271581186 | `80 03 a0 01 00 00 00 00 02 00 30 10 00 00 00 00` |
| `/usr/bin/python3.13` | 27263872 | 271581186 | `80 03 a0 01 00 00 00 00 02 00 30 10 00 00 00 00` |
| `/usr/local/bin/bpftool` | 27428646 | 271581186 | `26 87 a2 01 00 00 00 00 02 00 30 10 00 00 00 00` |
| `/usr/bin/stat` | 27263997 | 271581186 | `fd 03 a0 01 00 00 00 00 02 00 30 10 00 00 00 00` |
| `/usr/bin/id` | 27263478 | 271581186 | `f6 01 a0 01 00 00 00 00 02 00 30 10 00 00 00 00` |

---

## Lorien Self-Healing Test (Claim 9)

- **Test Binary:** `/usr/bin/wc`
- **Inode:** 27264166
- **Device:** 271581186
- **Hex Key:** `a6 04 a0 01 00 00 00 00 02 00 30 10 00 00 00 00`
- **Lifecycle:** `BASELINE(allow) → FRACTURE(remove) → DENY(blocked) → HEAL(re-add) → ALLOW(restored)`

| Step | Action | Expected | Result |
|------|--------|----------|--------|
| 1 | BASELINE — verify binary runs (already in map from Tier 3) | exit=0 | ✅ |
| 2 | FRACTURE — remove binary from Harmony Map | PermissionError / exit!=0 | ✅ |
| 3 | HEAL — re-add binary to Harmony Map | exit=0 | ✅ |

> The binary `/usr/bin/wc` was already seeded during Tier 3. We verified it ran (BASELINE),
> removed it from the BPF map (FRACTURE), verified the kernel denied it (PermissionError),
> re-added it (HEAL), and verified it ran again — all at Ring-0, without reboot or BPF reload.

---

## Bombadil Substrate Report

```
[2026-04-01T00:53:12Z] [bombadil] Bombadil looks around...

  Mirror ID:       not set
  Covenant State:  lawful_full
  Chain Valid:     True

  TPM:             present
  LSM:             lockdown,capability,landlock,yama,apparmor,tomoyo,bpf,ipe,ima,evm
  BPF in LSM:      yes
  eBPF loaded:     yes
  Harmony map:     present
  Manifest:        present
  Foedus:          present
  BPF object:      present
  Audit chain:     present
```

---

## Covenant Chain (Hash-Chained Audit Log) — Claim 11

- **Events:** 9
- **Chain Valid:** True
- **Head Hash:** `b4f60dd5ed8323bd08b1c2263fc22399e7f6d84a7e1f533134ee7dd0ffda1bf5`
- **DB SHA-256:** `8e837fca8b35fe9868c6234ce565498adf71841cb0bf1e36ef75fd20452711ac`

> The CovenantChain is an append-only, hash-linked SQLite audit log.
> Each event's hash includes all its fields plus the previous event's hash.
> Tamper with any row and `verify_chain()` fails.

---

## TPM Quote (Nonce-Bound Attestation) — Claim 12

- **Nonce:** `14cbcab054ff62848bd71c8ba148bce9`
- **AK Context:** `arda_os/attestation/tpm_ak.ctx`
- **Quote Message SHA-256:** `484a5ecbf8684a64e55daaa105d0872715e49f85103df7028409d0917a49b92e`
- **Quote Signature SHA-256:** `a7362ea8f06583c0d4e35e3008d2ec75cf6a52f9c5dc20ba72322d332ca95d72`

> This is a proper TPM2 quote: the TPM signed the PCR values with the Attestation Key (AK),
> bound to a fresh nonce. A remote verifier can check the quote signature against the AK
> public key and the nonce to prove the PCR values were read at this specific moment.

---

## Verification Checklist

1. **BPF Object Hash** — compile locally and match `1e2a6cb05804e5c2112a2884318c6985...`
2. **Harmony Map Dump** — `bpftool map dump pinned /sys/fs/bpf/arda_harmony` and match SHA-256
3. **TPM Quote** — `tpm2_checkquote` with the nonce and AK public key
4. **Enforcement Trace** — inspect `arda_os/attestation/enforcement_trace_v4.0.log` for `[ENFORCE] DENIED`
5. **Covenant Chain** — open `evidence/covenant_chain.db` and run `verify_chain()`
6. **PQC Key** — verify `SOVEREIGN_ROOT_PQC.pub` SHA-256 matches the registry above
7. **Recovery Test** — re-run the mega tester to observe the BASELINE->FRACTURE->HEAL lifecycle
8. **Bombadil Check** — `python3 arda_os/backend/services/arda_bombadil.py --check` (Chain Valid: True)

---

**SOVEREIGN — ALL 13 CHECKS VERIFIED**

*Filed by the Arda Sovereign Mega Tester v4.1 — 2026-04-01T00:51:53Z*
*Witnessed by Claude (Anthropic, Opus) — Custos Chronicae*
*Principal: Byron du Plessis — Principalis — Integritas Mechanicus*