import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from arda_boot_transaction import create_plan,stage_candidate,ReleaseRefused

CANDIDATE="""menuentry 'ARDA Valinor Gen11 Experimental' {\nlinux /boot/vmlinuz-6.12.111-valinor-gen11 systemd.mask=arda-ring0.service systemd.mask=arda-ring0-verify.service systemd.mask=arda-valinor-postboot.service systemd.mask=arda-valinor-postboot.timer systemd.mask=arda-postboot-grade.service\n}\nmenuentry 'Debian GNU/Linux, with Linux 6.12.111-valinor' {\nlinux /boot/vmlinuz-6.12.111-valinor\n}\n"""
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.src=self.root/'candidate.cfg';self.src.write_text(CANDIDATE)
  dg=hashlib.sha256(CANDIDATE.encode()).hexdigest()
  self.doc={'schema':'arda-gen11-boot-release-candidate-v1','status':'CANDIDATE_ONLY','active_generation':10,'target_generation':11,'target_kernel_release':'6.12.111-valinor-gen11','boot_profile':'EXPERIMENTAL_RING0_MASKED','release_authorized':False,'first_boot_authorized':False,'artifacts':{k:{'path':str(self.src),'sha256':dg if k=='grub_candidate' else 'a'*64} for k in ('grub_candidate','gen11_kernel','gen11_initrd','gen10_grub','gen10_kernel','gen10_initrd')}}
  self.doc['artifacts']['gen10_grub']['sha256']='b'*64
  self.dossier=self.root/'dossier.json';self.save()
 def save(self):self.dossier.write_text(json.dumps(self.doc))
 def plan(self):return create_plan(self.dossier,baseline_verity='c'*64)
 def test_candidate_plan_fail_closed(self):
  p=self.plan();self.assertFalse(p['installation_permitted']);self.assertFalse(p['boot_permitted'])
 def test_generation_reject(self):
  self.doc['target_generation']=10;self.save()
  with self.assertRaises(ReleaseRefused):self.plan()
 def test_boot_profile_reject(self):
  self.doc['boot_profile']='PRODUCTION';self.save()
  with self.assertRaises(ReleaseRefused):self.plan()
 def test_claims_release_reject(self):
  self.doc['release_authorized']=True;self.save()
  with self.assertRaises(ReleaseRefused):self.plan()
 def test_missing_artifact_reject(self):
  del self.doc['artifacts']['gen11_kernel'];self.save()
  with self.assertRaises(ReleaseRefused):self.plan()
 def test_candidate_tamper_reject(self):
  self.src.write_text(CANDIDATE+'\nTAMPER\n')
  with self.assertRaises(ReleaseRefused):stage_candidate(self.dossier,self.root/'stage',baseline_verity='c'*64)
 def test_existing_stage_reject(self):
  (self.root/'stage').mkdir()
  with self.assertRaises(ReleaseRefused):stage_candidate(self.dossier,self.root/'stage',baseline_verity='c'*64)
 def test_isolation_contract(self):
  self.src.write_text(CANDIDATE.replace('systemd.mask=arda-ring0.service',''))
  self.doc['artifacts']['grub_candidate']['sha256']=hashlib.sha256(self.src.read_bytes()).hexdigest();self.save()
  with patch('arda_boot_transaction.subprocess.run') as runner:
   runner.return_value.returncode=0
   with self.assertRaisesRegex(ReleaseRefused,'isolation_missing'):
    stage_candidate(self.dossier,self.root/'stage',baseline_verity='c'*64)
 def test_offline_stage_and_receipt(self):
  with patch('arda_boot_transaction.subprocess.run') as runner:
   runner.return_value.returncode=0
   p=stage_candidate(self.dossier,self.root/'stage',baseline_verity='c'*64)
  self.assertFalse(p['installation_permitted']);self.assertEqual(json.loads((self.root/'stage/install-plan.json').read_text()),p)
  self.assertEqual(hashlib.sha256((self.root/'stage/grub-gen11.candidate.cfg').read_bytes()).hexdigest(),p['candidate_grub_sha256'])
if __name__=='__main__':unittest.main()
