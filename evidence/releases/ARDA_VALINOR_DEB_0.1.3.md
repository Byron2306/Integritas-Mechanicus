# ARDA Valinor Debian Candidate 0.1.3

Artifact:
`build/arda-valinor_0.1.3_amd64.deb`

SHA256:
`35dcbc26ee8e784a392e789358d8fb376755f0a99a3fea87c3e4e4ebdc67a8d1`

Verified:
- package runtime closure PASS
- verifier key ID uses arda-phase4-verifier
- package identity hygiene PASS
- private-key scan PASS
- TPM artifact scan PASS
- postinst execution mutation scan PASS

Boundary:
Portable enrollment machinery only.

Not portable:
- machine identity
- TPM contexts
- PCR state
- measured generation database
- signed verifier verdicts
- private signing keys
