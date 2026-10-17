"""Offline tests for the signed, destination-bound Gen11 workflow."""
import base64
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from arda_gen11_release_workflow import verify_install_envelope, Refuse
from arda_gen11_release import canonical

class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.dest=self.root/'sandbox'; self.dest.mkdir()
        self.dossier=self.root/'dossier.json';self.dossier.write_text('{"x":1}')
        self.auth=self.root/'auth.json';self.trust=self.root/'pub.pem'
        self.sk=Ed25519PrivateKey.generate()
        self.trust.write_bytes(self.sk.public_key().public_bytes(
            serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
        self.plan={x:c*64 for x,c in [('candidate_grub_sha256','a'),('baseline_grub_sha256','b'),
            ('baseline_grub_fsverity','c'),('gen11_kernel_sha256','d'),('gen11_initrd_sha256','e')]}
        from arda_gen11_release import digest_file
        now=datetime.now(timezone.utc)
        self.payload=dict(schema='arda-gen11-sandbox-install-authorization-v1',action='install_sandbox_experimental_candidate',
            authorization_id='abcDEF_1234567890',generation=11,boot_profile='EXPERIMENTAL_RING0_MASKED',
            dossier_sha256=digest_file(self.dossier),destination_kind='SANDBOX_ONLY',destination_path=str(self.dest),
            issued_at=(now-timedelta(seconds=10)).isoformat(),expires_at=(now+timedelta(seconds=120)).isoformat(),**self.plan)
        self.write()
    def write(self):
        b=canonical(self.payload)
        self.auth.write_text(json.dumps({'payload':self.payload,'signature':base64.b64encode(self.sk.sign(b)).decode()}))
    def verify(self):return verify_install_envelope(self.auth,self.dossier,self.trust,self.plan,self.dest)
    def test_valid(self):self.assertEqual(self.verify()['generation'],11)
    def test_missing_authority(self):
        self.trust.unlink()
        with self.assertRaisesRegex(Refuse,'release_authority_not_provisioned'):self.verify()
    def test_wrong_action(self):
        self.payload['action']='verify_experimental_candidate';self.write()
        with self.assertRaisesRegex(Refuse,'action'):self.verify()
    def test_wrong_destination(self):
        self.payload['destination_path']=str(self.root/'other');self.write()
        with self.assertRaisesRegex(Refuse,'destination_path'):self.verify()
    def test_wrong_kernel(self):
        self.payload['gen11_kernel_sha256']='f'*64;self.write()
        with self.assertRaisesRegex(Refuse,'binding_mismatch:gen11_kernel'):self.verify()
    def test_signature_tampered(self):
        data=json.loads(self.auth.read_text());data['payload']['authorization_id']='other-123456789012';self.auth.write_text(json.dumps(data))
        with self.assertRaises(Exception):self.verify()
    def test_expired(self):
        self.payload['expires_at']=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat();self.write()
        with self.assertRaisesRegex(Refuse,'authorization_freshness'):self.verify()
    def test_extra_field(self):
        self.payload['first_boot_authorized']=True;self.write()
        with self.assertRaisesRegex(Refuse,'signed_field_set'):self.verify()
    def test_boolean_generation(self):
        self.payload['generation']=True;self.write()
        with self.assertRaisesRegex(Refuse,'generation'):self.verify()
if __name__=='__main__':unittest.main()
