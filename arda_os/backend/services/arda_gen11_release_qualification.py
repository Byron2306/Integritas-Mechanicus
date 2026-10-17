"""ARDA Gen11 independent boot qualification and evidence binder.

Never alters boot configuration, fs-verity, enrollment, or release authority.
A successful sandbox rehearsal is *not* physical rollback proof.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
from pathlib import Path

OLD = '3bd6231883dbb955901eb133067a1760bb58d23b3920ee185208027cebb5f441'
NEW = 'fb3c66c81df3dabcd9390597a124f2686e759549f70dff68fe41cf05f99ddc62'
VERITY = 'c7dd6c826af174ab7ba3d819e49f8d40d1b8f7188cb46363054b35cfa6579337'
KERNEL = 'b9d69566f01af50e46d96607d478c63d083586d000f51613a5b7f392ad348e27'
INITRD = 'cf67ea94591526dc126d0f94d00a3bbdf6e7ccef2f9ec441ebb64c6ebc449b09'
MANIFEST = 'measured-f926c576ad174fb295fdba9349092a09'
EXPERIMENTAL = "menuentry 'ARDA Valinor Gen11 Experimental'"
FALLBACK = "menuentry 'Debian GNU/Linux, with Linux 6.12.111-valinor'"
MASKED = ('arda-ring0.service', 'arda-ring0-verify.service', 'arda-valinor-postboot.service',
          'arda-valinor-postboot.timer', 'arda-postboot-grade.service')
HASH = re.compile(r'[0-9a-f]{64}\Z')

class Refuse(RuntimeError): pass

def need(condition, reason):
    if not condition: raise Refuse(reason)

def sha_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def regular_file(p):
    p=Path(p)
    need(p.is_absolute(), 'file_not_absolute')
    st=p.lstat()
    need(stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode), 'file_not_regular')
    return p

def verify_fallback(candidate):
    txt=regular_file(candidate).read_text()
    need(txt.count(EXPERIMENTAL)==1,'experimental_entry_missing_or_duplicate')
    need(FALLBACK in txt,'fallback_entry_missing')
    need(all('systemd.mask='+u in txt for u in MASKED),'experimental_masks_missing')
    # A source-text existence check does not prove which block contains masks.
    block = txt.split(EXPERIMENTAL,1)[1].split('\n}',1)[0]
    need(all('systemd.mask='+u in block for u in MASKED),'experimental_entry_not_isolated')
    result=subprocess.run(['grub-script-check',str(candidate)],capture_output=True,text=True,timeout=30)
    need(result.returncode==0,'grub_syntax_invalid')

def validate_recovery_evidence(path):
    """Validate independent cold-boot evidence with fail-closed provenance.

    No JSON alone is sufficient to establish real-world independent boot recovery.
    This returns a review record, never release permission.
    """
    p=regular_file(path)
    d=json.loads(p.read_text())
    required={'schema','environment','status','independent_verifier','fallback_sha256',
              'image_sha256','image_origin','test_protocol','cold_boot_log_sha256',
              'rollback_log_sha256','external_witness_digest','observed_kernel_release'}
    need(isinstance(d,dict) and set(d)==required,'recovery_evidence_fields')
    need(d['schema']=='arda-gen11-cold-recovery-proof-v1','recovery_schema')
    need(d['environment']=='DISPOSABLE_BOOT_ENVIRONMENT','not_disposable_boot')
    need(d['status']=='PASSED' and d['independent_verifier'] is True,'recovery_not_independent')
    need(d['fallback_sha256']==OLD,'wrong_fallback')
    need(d['observed_kernel_release']=='6.12.111-valinor','fallback_kernel_not_observed')
    need(d['image_origin']=='EXTERNAL_GUEST_DISK','invalid_image_origin')
    need(d['test_protocol']=='COLD_BOOT_INTERRUPT_RECOVER','invalid_test_protocol')
    for name in ('image_sha256','cold_boot_log_sha256','rollback_log_sha256','external_witness_digest'):
        need(type(d[name]) is str and HASH.fullmatch(d[name]),'bad_digest:'+name)
    return {'recovery_evidence_sha256':sha_file(p),'status':'EXTERNAL_REVIEW_REQUIRED',
            'reason':'SELF_REPORTED_JSON_DOES_NOT_ESTABLISH_INDEPENDENT_PROVENANCE'}

def inspect(dossier, baseline, candidate, kernel, initrd, *, measured_verity, recovery=None):
    dossier=regular_file(dossier)
    d=json.loads(dossier.read_text())
    need(d.get('schema')=='arda-gen11-boot-release-candidate-v1','dossier_schema')
    need(d.get('status')=='CANDIDATE_ONLY','dossier_status')
    need(type(d.get('active_generation')) is int and d['active_generation']==10,'active_generation')
    need(type(d.get('target_generation')) is int and d['target_generation']==11,'target_generation')
    need(d.get('target_kernel_release')=='6.12.111-valinor-gen11','target_kernel')
    need(d.get('boot_profile')=='EXPERIMENTAL_RING0_MASKED','profile')
    need(d.get('release_authorized') is False and d.get('first_boot_authorized') is False,'dossier_claims_release')
    need(d.get('baseline',{}).get('manifest_id')==MANIFEST,'baseline_manifest')
    artifacts=d.get('artifacts')
    need(isinstance(artifacts,dict),'artifacts_missing')
    expected={'gen10_grub':(baseline,OLD),'grub_candidate':(candidate,NEW),
              'gen11_kernel':(kernel,KERNEL),'gen11_initrd':(initrd,INITRD)}
    for key,(p,digest) in expected.items():
        need(key in artifacts and artifacts[key].get('sha256')==digest,'artifact_binding:'+key)
        need(sha_file(regular_file(p))==digest,'artifact_changed:'+key)
    need(type(measured_verity) is str and measured_verity==VERITY,'fsverity_baseline_mismatch')
    verify_fallback(candidate)
    recovery_review = None if recovery is None else validate_recovery_evidence(recovery)
    return {'schema':'arda-gen11-release-qualification-v1',
            'status':'RECOVERY_EVIDENCE_REVIEW_REQUIRED' if recovery else 'RECOVERY_EVIDENCE_MISSING',
            'candidate_dossier_sha256':sha_file(dossier), 'gen10_grub_sha256':OLD,
            'gen10_grub_fsverity':VERITY,'gen11_grub_sha256':NEW,
            'gen11_kernel_sha256':KERNEL,'gen11_initrd_sha256':INITRD,
            'recovery_review':recovery_review,'production_install_authorized':False,
            'gen11_first_boot_authorized':False,
            'missing':['separately_approved_release_trust_anchor',
                       'independently_reviewed_measured_policy_transition',
                       'privileged_fsverity_aware_install_mechanism',
                       'externally_verified_physical_recovery']}

def write_receipt(destination, doc):
    out=Path(destination)
    need(out.is_absolute() and not out.exists() and not out.is_symlink(),'receipt_exists_or_relative')
    need(not str(out).startswith(('/boot/','/etc/','/usr/','/sys/','/run/','/var/lib/arda/')),'protected_receipt_destination')
    need(out.parent.is_dir() and not out.parent.is_symlink(),'receipt_parent')
    need(out.parent.stat().st_uid==os.getuid() and not(out.parent.stat().st_mode & 0o022),'unsafe_receipt_parent')
    b=(json.dumps(doc,sort_keys=True,indent=2)+'\n').encode()
    fd=os.open(str(out),os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    try:os.write(fd,b);os.fsync(fd)
    finally:os.close(fd)
    fd=os.open(str(out.parent),os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)

def main():
    ap=argparse.ArgumentParser()
    for name in ('dossier','baseline','candidate','kernel','initrd','out'): ap.add_argument('--'+name,required=True)
    ap.add_argument('--recovery')
    ap.add_argument('--fsverity',required=True,help='independently measured baseline digest')
    args=ap.parse_args()
    try:
        result=inspect(args.dossier,args.baseline,args.candidate,args.kernel,args.initrd,
                       measured_verity=args.fsverity,recovery=args.recovery)
        write_receipt(args.out,result)
        print(json.dumps(result,sort_keys=True))
        return 0
    except Exception as e:
        print('GEN11_QUALIFICATION=REFUSE:'+type(e).__name__+':'+str(e))
        return 1
if __name__=='__main__':raise SystemExit(main())
