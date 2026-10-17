import base64
import json
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from arda_gen11_production_authority import (ACTION,DESTINATION,DIGEST_FIELDS,EXPECTED_GEN10_VERITY,
  PROFILE,POLICY_SCHEMA,SCHEMA,AdmissionLedger,Refuse,canonical,check_envelope,sha)

class AuthorityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.key=Ed25519PrivateKey.generate()
        raw=self.key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
        pem=self.key.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo).decode()
        self.policy={'schema':POLICY_SCHEMA,'status':'APPROVED','release_key_pem':pem,
           'key_fingerprint_sha256':sha(raw),'attestation_key_fingerprints_sha256':['1'*64],
           'scope':'GEN11_PROTECTED_BOOT_ADMISSION_ONLY'}
        self.policy_path=self.root/'policy.json'
        self.expected={k:sha(k.encode()) for k in DIGEST_FIELDS}
        self.expected['baseline_grub_fsverity']=EXPECTED_GEN10_VERITY
        self.now=datetime(2026,10,17,13,0,tzinfo=timezone.utc)
        self.payload={'schema':SCHEMA,'action':ACTION,'authorization_id':'gen11_release_20261017_A1',
            'generation':11,'boot_profile':PROFILE,'destination':DESTINATION,
            **self.expected,'issued_at':self.now.isoformat(),
            'expires_at':(self.now+timedelta(minutes=5)).isoformat()}
        self.save()
    def save(self):self.policy_path.write_text(json.dumps(self.policy))
    def sign(self):return {'payload':self.payload.copy(),'signature':base64.b64encode(self.key.sign(canonical(self.payload))).decode()}
    def verify(self,env=None,expected=None):
        return check_envelope(env or self.sign(),policy_path=self.policy_path,expected=expected or self.expected,now=self.now,enforce_ownership=False)
    def rejected(self,env=None,expected=None):
        with self.assertRaises(Refuse):self.verify(env,expected)
    def test_valid_review_only(self):
        d=self.verify();self.assertFalse(d['installation_authorized']);self.assertFalse(d['first_boot_authorized'])
    def test_replay_persistent(self):
        d=self.verify(); path=self.root/'admissions.db';AdmissionLedger(path).admit(d)
        with self.assertRaisesRegex(Refuse,'replay'):AdmissionLedger(path).admit(d)
    def test_wrong_action(self):self.payload['action']='install_now';self.rejected()
    def test_wrong_generation(self):self.payload['generation']=10;self.rejected()
    def test_wrong_profile(self):self.payload['boot_profile']='PRODUCTION';self.rejected()
    def test_wrong_destination(self):self.payload['destination']='/tmp/grub.cfg';self.rejected()
    def test_digest_mismatch(self):self.payload['gen11_kernel_sha256']='e'*64;self.rejected()
    def test_attestation_key_reuse(self):
        self.policy['attestation_key_fingerprints_sha256']=[self.policy['key_fingerprint_sha256']];self.save();self.rejected()
    def test_policy_unapproved(self):self.policy['status']='DRAFT';self.save();self.rejected()
    def test_policy_scope_wrong(self):self.policy['scope']='ALL';self.save();self.rejected()
    def test_expired(self):self.payload['expires_at']=(self.now-timedelta(seconds=1)).isoformat();self.rejected()
    def test_overlong(self):self.payload['expires_at']=(self.now+timedelta(minutes=15)).isoformat();self.rejected()
    def test_modified_signature(self):
        env=self.sign();env['payload']['destination']='/boot/other';self.rejected(env)
    def test_valid_scope_but_signature_tampered(self):
        env=self.sign();env['payload']['authorization_id']='gen11_release_20261017_B2';self.rejected(env)
    def test_invalid_signature(self):
        env=self.sign();env['signature']=base64.b64encode(bytes(64)).decode();self.rejected(env)
    def test_wrong_trust_key(self):
        other=Ed25519PrivateKey.generate().public_key();raw=other.public_bytes(Encoding.Raw,PublicFormat.Raw)
        self.policy['release_key_pem']=other.public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo).decode()
        self.policy['key_fingerprint_sha256']=sha(raw);self.save();self.rejected()
    def test_expectation_unbound(self):
        wrong=self.expected.copy();wrong.pop('installer_sha256');self.rejected(expected=wrong)
    def test_boolean_generation(self):self.payload['generation']=True;self.rejected()

if __name__=='__main__':unittest.main()
