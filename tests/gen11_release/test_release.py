import hashlib
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from arda_os.backend.services.arda_gen11_release import Ledger, Refuse, canonical, validate_authorization
import base64
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
  p=Path(self.tmp.name); self.dossier=p/'dossier.json'; self.dossier.write_text('{}')
  self.key=Ed25519PrivateKey.generate(); self.other=Ed25519PrivateKey.generate()
  self.trust=p/'trust.pem'; self.trust.write_bytes(self.key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
  self.auth=p/'auth.json'; now=datetime.now(timezone.utc)
  self.payload=dict(schema='arda-boot-release-authorization-v2',action='verify_experimental_candidate',authorization_id='release-abcdefgh123456',generation=11,boot_profile='EXPERIMENTAL_RING0_MASKED',dossier_sha256=hashlib.sha256(b'{}').hexdigest(),issued_at=(now-timedelta(seconds=3)).isoformat(),expires_at=(now+timedelta(minutes=3)).isoformat())
 def write(self,key=None,change=None):
  p=dict(self.payload)
  if change:p.update(change)
  self.auth.write_text(json.dumps({'payload':p,'signature':base64.b64encode((key or self.key).sign(canonical(p))).decode()}))
 def verify(self):return validate_authorization(self.auth,self.dossier,self.trust)
 def refused(self):
  with self.assertRaises(Exception):self.verify()
 def test_valid(self):self.write();self.assertEqual(self.verify()['generation'],11)
 def test_wrong_signer(self):self.write(self.other);self.refused()
 def test_missing_key(self):self.write();self.trust.unlink();self.refused()
 def test_missing_authorization(self):self.refused()
 def test_wrong_dossier(self):self.write(change={'dossier_sha256':'0'*64});self.refused()
 def test_wrong_action(self):self.write(change={'action':'install_grub'});self.refused()
 def test_wrong_generation(self):self.write(change={'generation':10});self.refused()
 def test_expired(self):self.write(change={'expires_at':(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()});self.refused()
 def test_overlong_window(self):self.write(change={'expires_at':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()});self.refused()
 def test_id_absent(self):self.write(change={'authorization_id':''});self.refused()
 def test_signature_tampered(self):
  self.write(); env=json.loads(self.auth.read_text());env['payload']['authorization_id']='release-another123456';self.auth.write_text(json.dumps(env));self.refused()
 def test_replay_after_restart(self):
  p=str(Path(self.tmp.name)/'ledger.sqlite'); l=Ledger(p);l.reserve('release-abcdefgh123456','a'*64);l.conn.close();l=Ledger(p)
  with self.assertRaises(sqlite3.IntegrityError):l.reserve('release-abcdefgh123456','a'*64)
  l.mark('release-abcdefgh123456','recovery_required')
  with self.assertRaises(Refuse):l.mark('release-abcdefgh123456','committed')
 def test_commit(self):
  l=Ledger(str(Path(self.tmp.name)/'x.db'));l.reserve('release-abcdefgh123456','a'*64);l.mark('release-abcdefgh123456','committed')
  self.assertEqual(l.conn.execute('select status from releases').fetchone()[0],'committed')
if __name__=='__main__':unittest.main(verbosity=2)
