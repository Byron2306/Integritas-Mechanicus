"""Fail-closed ARDA boot release transaction planner and offline staging.

No production install actuator. Only prepare an isolated stage and verify it.
All release state transitions belong to an authorized installer after offline review.
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
from pathlib import Path

class ReleaseRefused(RuntimeError): pass

def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def require(ok,reason):
    if not ok:raise ReleaseRefused(reason)

def create_plan(dossier_path:Path, *, baseline_verity:str, expected_kernel:str='6.12.111-valinor-gen11') -> dict:
    d=json.loads(Path(dossier_path).read_text())
    require(d.get('schema')=='arda-gen11-boot-release-candidate-v1','dossier_schema')
    require(d.get('status')=='CANDIDATE_ONLY','candidate_status')
    require(d.get('active_generation')==10 and d.get('target_generation')==11,'generation_boundary')
    require(d.get('target_kernel_release')==expected_kernel,'kernel_release')
    require(d.get('boot_profile')=='EXPERIMENTAL_RING0_MASKED','boot_profile')
    require(d.get('release_authorized') is False and d.get('first_boot_authorized') is False,'claims_authorization')
    a=d.get('artifacts',{})
    for key in ('grub_candidate','gen11_kernel','gen11_initrd','gen10_grub','gen10_kernel','gen10_initrd'):
        require(key in a,'missing_artifact_'+key)
        require(isinstance(a[key].get('sha256'),str) and len(a[key]['sha256'])==64,'bad_digest_'+key)
    require(a['gen10_grub']['sha256'] != a['grub_candidate']['sha256'],'unchanged_grub')
    require(isinstance(baseline_verity,str) and len(baseline_verity)==64,'bad_fsverity')
    return {
      'schema':'arda-gen11-install-plan-v1',
      'mode':'EXPERIMENTAL_RING0_MASKED',
      'dossier_sha256':sha(dossier_path),
      'candidate_grub_sha256':a['grub_candidate']['sha256'],
      'baseline_grub_sha256':a['gen10_grub']['sha256'],
      'baseline_grub_fsverity':baseline_verity,
      'gen11_kernel_sha256':a['gen11_kernel']['sha256'],
      'gen11_initrd_sha256':a['gen11_initrd']['sha256'],
      'fallback_generation':10,
      'candidate_generation':11,
      'installation_permitted':False,
      'boot_permitted':False,
      'reason':'NO_PROVISIONED_INSTALL_AUTHORITY_OR_VERIFIED_RECOVERY_ACTUATOR',
    }

def stage_candidate(dossier_path:Path, stage_dir:Path, *, baseline_verity:str):
    """Build offline stage and receipt; never write to /boot, /etc or enrollment."""
    d=json.loads(Path(dossier_path).read_text())
    plan=create_plan(dossier_path,baseline_verity=baseline_verity)
    source=Path(d['artifacts']['grub_candidate']['path'])
    require(source.is_file() and not source.is_symlink(),'candidate_absent_or_symlink')
    require(sha(source)==plan['candidate_grub_sha256'],'candidate_hash_mismatch')
    require(stage_dir.is_absolute(),'stage_dir_not_absolute')
    require(not stage_dir.exists(),'stage_dir_already_exists')
    stage_dir.mkdir(parents=True,mode=0o700)
    candidate=stage_dir/'grub-gen11.candidate.cfg'
    try:
        with source.open('rb') as inp, candidate.open('xb') as out:
            for chunk in iter(lambda:inp.read(1<<20),b''):out.write(chunk)
            out.flush();os.fsync(out.fileno())
        require(sha(candidate)==plan['candidate_grub_sha256'],'stage_digest_mismatch')
        verify=subprocess.run(['grub-script-check',str(candidate)],capture_output=True,text=True)
        require(verify.returncode==0,'grub_script_invalid:'+verify.stderr[:150])
        cfg=candidate.read_text(errors='replace')
        require("menuentry 'ARDA Valinor Gen11 Experimental'" in cfg,'gen11_entry_missing')
        require("menuentry 'Debian GNU/Linux, with Linux 6.12.111-valinor'" in cfg,'gen10_entry_missing')
        for unit in ('arda-ring0.service','arda-ring0-verify.service','arda-valinor-postboot.service','arda-valinor-postboot.timer','arda-postboot-grade.service'):
            require('systemd.mask='+unit in cfg,'isolation_missing_'+unit)
        receipt=stage_dir/'install-plan.json'
        with receipt.open('x') as f:
            json.dump(plan,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
        os.chmod(candidate,0o600);os.chmod(receipt,0o600)
        directory_fd=os.open(str(stage_dir),os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory_fd)
        finally:os.close(directory_fd)
    except Exception:
        # Preserve failed stage for inspection. Never try privileged cleanup.
        raise
    return plan
