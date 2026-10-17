import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import arda_gen11_release_qualification as q

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name)
  self.files={x:self.root/x for x in ('dossier','baseline','candidate','kernel','initrd')}
  for k,p in self.files.items():p.write_text(k)
  self.d={'schema':'arda-gen11-boot-release-candidate-v1','status':'CANDIDATE_ONLY',
          'active_generation':10,'target_generation':11,'target_kernel_release':'6.12.111-valinor-gen11',
          'boot_profile':'EXPERIMENTAL_RING0_MASKED','release_authorized':False,
          'first_boot_authorized':False,'baseline':{'manifest_id':q.MANIFEST},
          'artifacts':{k:{'sha256':v} for k,v in [('gen10_grub',q.OLD),('grub_candidate',q.NEW),('gen11_kernel',q.KERNEL),('gen11_initrd',q.INITRD)]}}
  self.files['dossier'].write_text(json.dumps(self.d))
 def run_inspect(self):
  with patch.object(q,'sha_file',side_effect=lambda p: {'baseline':q.OLD,'candidate':q.NEW,'kernel':q.KERNEL,'initrd':q.INITRD}.get(Path(p).name,'d'*64)),patch.object(q,'verify_fallback'):
   return q.inspect(self.files['dossier'],self.files['baseline'],self.files['candidate'],self.files['kernel'],self.files['initrd'],measured_verity=q.VERITY)
 def test_refusal_even_when_valid(self):
  r=self.run_inspect();self.assertFalse(r['production_install_authorized']);self.assertEqual(len(r['missing']),4)
 def test_bad_generation(self):
  self.d['target_generation']=True;self.files['dossier'].write_text(json.dumps(self.d))
  with self.assertRaises(q.Refuse): self.run_inspect()
 def test_bad_profile(self):
  self.d['boot_profile']='PRODUCTION';self.files['dossier'].write_text(json.dumps(self.d))
  with self.assertRaises(q.Refuse):self.run_inspect()
 def test_claimed_release(self):
  self.d['release_authorized']=True;self.files['dossier'].write_text(json.dumps(self.d))
  with self.assertRaises(q.Refuse):self.run_inspect()
 def test_wrong_fsverity(self):
  with patch.object(q,'sha_file',return_value=q.NEW):
   with self.assertRaises(q.Refuse):q.inspect(self.files['dossier'],self.files['baseline'],self.files['candidate'],self.files['kernel'],self.files['initrd'],measured_verity='0'*64)
 def test_missing_fallback(self):
  self.files['candidate'].write_text(q.EXPERIMENTAL+'\n}')
  with self.assertRaises(q.Refuse):q.verify_fallback(self.files['candidate'])
 def test_recovery_claims_refused(self):
  evidence=self.root/'recovery.json';evidence.write_text(json.dumps({'schema':'arda-gen11-cold-recovery-proof-v1','status':'PASSED'}))
  with self.assertRaises(q.Refuse):q.validate_recovery_evidence(evidence)
 def test_receipt_exclusive(self):
  d=self.root/'private';d.mkdir(mode=0o700)
  out=d/'receipt.json';q.write_receipt(out,{'status':'REFUSE'});
  with self.assertRaises(q.Refuse):q.write_receipt(out,{'status':'PASS'})
 def test_forbid_production_receipt(self):
  with self.assertRaises(q.Refuse):q.write_receipt(Path('/boot/arda-receipt.json'),{})

if __name__=='__main__':unittest.main()
