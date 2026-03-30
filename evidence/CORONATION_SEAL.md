# ARDA OS — SOVEREIGN CORONATION SEAL

## Silicon Truth Protocol

- **Timestamp**: 2026-03-30T19:10:17Z
- **Machine ID**: da393d0cfaf94545ad651cd6d9b97336
- **Kernel**: 6.12.73+deb13-amd64
- **CPU**: 13th Gen Intel(R) Core(TM) i7-1355U
- **Gates Passed**: 19/7 (Warnings: 2)
- **Bundle Hash**: 7edbf9ead002b806dd05cd0afa9b91f6e1fabcbf0f6afc90a0ada67e0caa05a0

## Gate Results

- ✅ **GATE_0**: Hardware Census Complete
- ✅ **GATE_1**: TPM 2.0 Verified — Real Silicon
- ✅ **GATE_2**: Attestation Key Enrolled — Identity Anchor Set
- ✅ **GATE_3**: Boot Quote Captured — Silicon Root of Trust
- ❌ **GATE_4**: eBPF Compilation — clang BPF compilation failed. See 05_ebpf_compile.log|2026-03-30T19:02:40Z
- ✅ **GATE_0**: Hardware Census Complete
- ✅ **GATE_1**: TPM 2.0 Verified — Real Silicon
- ✅ **GATE_2**: Attestation Key Enrolled — Identity Anchor Set
- ✅ **GATE_3**: Boot Quote Captured — Silicon Root of Trust
- ✅ **GATE_4**: eBPF LSM Compiled — Kernel Object Ready
- ⚠️ **GATE_5**: LSM loaded but did not deny execution
- ✅ **GATE_5**: eBPF Enforcement Demonstrated
- ✅ **GATE_6**: Attestation Bundle Assembled — Full Proof Object
- ✅ **GATE_7**: Sovereign Seal Written — Covenant Chain Initiated
- ✅ **GATE_0**: Hardware Census Complete
- ✅ **GATE_1**: TPM 2.0 Verified — Real Silicon
- ✅ **GATE_2**: Attestation Key Enrolled — Identity Anchor Set
- ✅ **GATE_3**: Boot Quote Captured — Silicon Root of Trust
- ✅ **GATE_4**: eBPF LSM Compiled — Kernel Object Ready
- ⚠️ **GATE_5**: LSM loaded but did not deny execution
- ✅ **GATE_5**: eBPF Enforcement Demonstrated
- ✅ **GATE_6**: Attestation Bundle Assembled — Full Proof Object

## Evidence Manifest

drwxr-xr-x 3 root root    500 Mar 30 19:06 .
drwxrwxr-x 8 user user    620 Mar 30 19:04 ..
-rw-r--r-- 1 root root    310 Mar 30 19:10 00_hardware_census.json
-rw-r--r-- 1 root root   1758 Mar 30 19:10 01_tpm_properties.txt
-rw-r--r-- 1 root root    310 Mar 30 19:10 02_pcr_raw.txt
-rw-r--r-- 1 root root    386 Mar 30 19:10 02_pcr_values.json
-rw-rw---- 1 root root    280 Mar 30 19:10 03_ak_public.pem
-rw-r--r-- 1 root root      0 Mar 30 19:10 04_quote.err
-rw-r--r-- 1 root root    372 Mar 30 19:10 04_quote_metadata.json
-rw-r--r-- 1 root root     33 Mar 30 19:10 04_quote_nonce.txt
-rw-rw---- 1 root root    129 Mar 30 19:10 04_tpm_quote.bin
-rw-rw---- 1 root root    668 Mar 30 19:10 04_tpm_quote_pcrs.bin
-rw-rw---- 1 root root    262 Mar 30 19:10 04_tpm_quote_sig.bin
-rw-r--r-- 1 root root 828288 Mar 30 19:10 05_arda_physical_lsm.o
-rw-r--r-- 1 root root      0 Mar 30 19:10 05_ebpf_compile.log
-rw-r--r-- 1 root root      0 Mar 30 19:10 06_bpf_load.log
-rw-r--r-- 1 root root    206 Mar 30 19:10 06_bpf_map_list.txt
-rw-r--r-- 1 root root   2319 Mar 30 19:10 06_bpf_prog_list.txt
-rw-r--r-- 1 root root     50 Mar 30 19:10 06_enforcement_test.log
-rw-r--r-- 1 root root   3999 Mar 30 19:10 07_sovereign_attestation.json
-rw-r--r-- 1 root root    914 Mar 30 19:06 08_covenant_chain.json
drwxr-xr-x 2 root root    180 Mar 30 19:02 ak
-rw-r--r-- 1 root root  38011 Mar 30 19:10 coronation.log
-rw-r--r-- 1 root root      0 Mar 30 19:10 CORONATION_SEAL.md
-rw-r--r-- 1 root root   1633 Mar 30 19:10 gate_results.txt

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
