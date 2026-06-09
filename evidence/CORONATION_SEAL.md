# ARDA OS — SOVEREIGN CORONATION SEAL

## Silicon Truth Protocol

- **Timestamp**: 2026-03-31T08:24:53Z
- **Machine ID**: c895237d07c64b029a495b62b878aeba
- **Kernel**: 6.12.74+deb12-amd64
- **CPU**: 13th Gen Intel(R) Core(TM) i7-1355U
- **Gates Passed**: 8/7 (Warnings: 1)
- **Bundle Hash**: 48938dc9bfee7e028120ec9ed7b22352facf388eeb414975aef5f4e1280a3bfc

## Gate Results

- ✅ **GATE_0**: Hardware Census Complete
- ✅ **GATE_1**: TPM 2.0 Verified — Real Silicon
- ✅ **GATE_2**: Attestation Key Enrolled — Identity Anchor Set
- ✅ **GATE_3**: Boot Quote Captured — Silicon Root of Trust
- ✅ **GATE_4**: eBPF LSM Compiled — Kernel Object Ready
- ✅ **GATE_4.5**: Harmony Discovery Complete — 257 Binaries Mapped
- ⚠️ **GATE_5**: LSM loaded and seeded but test binary was not denied
- ✅ **GATE_5**: Ring-0 Enforcement PROVEN — 257 Binaries Sealed
- ✅ **GATE_6**: Attestation Bundle Assembled — Full Proof Object

## Evidence Manifest

drwxrwxr-x  3 byron byron   4096 Mar 31 03:25 .
drwxrwxr-x 10 byron byron   4096 Mar 30 21:48 ..
-rw-rw-r--  1 byron byron    321 Mar 31 03:24 00_hardware_census.json
-rw-rw-r--  1 byron byron   1758 Mar 31 03:24 01_tpm_properties.txt
-rw-rw-r--  1 byron byron    310 Mar 31 03:24 02_pcr_raw.txt
-rw-rw-r--  1 byron byron    386 Mar 31 03:24 02_pcr_values.json
-rw-rw-r--  1 byron byron    280 Mar 31 03:25 03_ak_public.pem
-rw-rw-r--  1 byron byron      0 Mar 31 03:25 04_quote.err
-rw-rw-r--  1 byron byron    372 Mar 31 03:25 04_quote_metadata.json
-rw-rw-r--  1 byron byron     33 Mar 31 03:25 04_quote_nonce.txt
-rw-rw-r--  1 byron byron    129 Mar 31 03:25 04_tpm_quote.bin
-rw-rw-r--  1 byron byron    668 Mar 31 03:25 04_tpm_quote_pcrs.bin
-rw-rw-r--  1 byron byron    262 Mar 31 03:25 04_tpm_quote_sig.bin
-rw-rw-r--  1 byron byron 822536 Mar 31 03:25 05_arda_physical_lsm.o
-rw-r--r--  1 root  root   37492 Mar 31 03:25 05_discovered_binaries.json
-rw-r--r--  1 root  root       0 Mar 31 03:25 05_ebpf_compile.log
-rw-r--r--  1 root  root   61400 Mar 31 03:25 05_harmony_manifest.json
-rw-r--r--  1 root  root   30543 Mar 31 03:25 05_tier_manifest.json
-rw-r--r--  1 root  root       0 Mar 31 03:25 06_bpf_load.log
-rw-rw-r--  1 byron byron    537 Mar 31 03:25 06_bpf_map_list.txt
-rw-rw-r--  1 byron byron   2747 Mar 31 03:25 06_bpf_prog_list.txt
-rw-r--r--  1 root  root      50 Mar 31 03:25 06_enforcement_test.log
-rw-rw-r--  1 byron byron   4299 Mar 31 03:25 07_sovereign_attestation.json
-rw-rw-r--  1 byron byron    914 Mar 31 03:18 08_covenant_chain.json
drwxrwxr-x  2 byron byron   4096 Mar 30 19:45 ak
-rw-r--r--  1 root  root   64408 Mar 31 03:25 coronation.log
-rw-rw-r--  1 byron byron      0 Mar 31 03:25 CORONATION_SEAL.md
-rw-rw-r--  1 byron byron    700 Mar 31 03:25 gate_results.txt

## Attestation

This seal was produced by executing the Arda OS Sovereign Coronation Script
on physical hardware with a real TPM 2.0 chip. The TPM quote is signed by
the machine's silicon. The eBPF object was compiled against the running kernel.

No mock mode was used. No simulation was employed.

The evidence in this bundle is either:
- **Proof** that the system works as designed, or
- **Documentation** of exactly where it does not, which is equally valuable.

---

*Probatio ante laudem. Lex ante actionem. Veritas ante vanitatem.*
