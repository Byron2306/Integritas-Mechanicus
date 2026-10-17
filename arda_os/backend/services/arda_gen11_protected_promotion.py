"""ARDA Gen11 protected boot promotion admission, deliberately non-mutating.

The production GRUB inode is fs-verity protected. An installer must not bypass
that protection; a separately reviewed trusted boot/update mechanism is needed.
This module can issue evidence-bound REFUSE or READY_FOR_INSTALLER_REVIEW, never ALLOW.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, stat, subprocess, sys
from pathlib import Path

class Refuse(RuntimeError): pass

def require(x, why):
    if not x: raise Refuse(why)

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def command(argv):
    p=subprocess.run(argv,capture_output=True,text=True,timeout=90)
    require(p.returncode==0,'command_failed:'+argv[0]+':'+p.stderr[:120])
    return p.stdout.strip()

def guard_target(path):
    p=Path(path)
    require(str(p)=='/boot/grub/grub.cfg','target_not_canonical')
    require(not p.is_symlink() and p.is_file(),'target_missing_or_symlink')
    require(p.stat().st_uid==0,'target_not_root_owned')
    require(stat.S_IMODE(p.stat().st_mode)&0o022==0,'target_group_or_world_writable')
    return p

def inspect(*, dossier, staged, target='/boot/grub/grub.cfg', expected_baseline=None,
            fsverity_digest=None, measured_verity=None, parsed_grub_ok=False,
            trusted_recovery_proven=False, boot_authority_provisioned=False):
    """Offline evidence inspection; caller passes fs-verity measurement from trusted tool.

    For the live system use CLI, which collects its own protected measurements.
    Never returns an installation authorization, even with all review inputs true.
    """
    t=guard_target(target)
    doc=json.loads(Path(dossier).read_text())
    require(doc.get('schema')=='arda-gen11-boot-release-candidate-v1','dossier_schema')
    require(doc.get('status')=='CANDIDATE_ONLY','not_candidate')
    require(type(doc.get('active_generation')) is int and doc['active_generation']==10,'baseline_generation')
    require(type(doc.get('target_generation')) is int and doc['target_generation']==11,'target_generation')
    require(doc.get('boot_profile')=='EXPERIMENTAL_RING0_MASKED','boot_profile')
    require(doc.get('release_authorized') is False and doc.get('first_boot_authorized') is False,'dossier_claims_authority')
    artifacts=doc.get('artifacts')
    require(isinstance(artifacts,dict),'artifacts')
    b=artifacts.get('gen10_grub',{})
    c=artifacts.get('grub_candidate',{})
    require(b.get('path')=='/boot/grub/grub.cfg','baseline_path')
    old=sha256(t)
    require(old==b.get('sha256'),'baseline_dossier_digest')
    require(expected_baseline is not None and old==expected_baseline,'baseline_pinned_digest')
    require(re.fullmatch('[a-f0-9]{64}',str(fsverity_digest)) is not None,'verity_pin_missing')
    require(measured_verity==fsverity_digest,'verity_measurement_mismatch')
    s=Path(staged)
    require(s.is_file() and not s.is_symlink(),'staged_candidate_missing')
    new=sha256(s)
    require(new==c.get('sha256'),'staged_candidate_digest')
    require(new!=old,'unchanged_candidate')
    cfg=s.read_text(errors='replace')
    require("menuentry 'ARDA Valinor Gen11 Experimental'" in cfg,'missing_gen11_entry')
    require("menuentry 'Debian GNU/Linux, with Linux 6.12.111-valinor'" in cfg,'missing_gen10_entry')
    for unit in ('arda-ring0.service','arda-ring0-verify.service','arda-valinor-postboot.service','arda-valinor-postboot.timer','arda-postboot-grade.service'):
        require('systemd.mask='+unit in cfg,'missing_isolation:'+unit)
    require(parsed_grub_ok is True,'grub_syntax_not_proven')
    # The production actuator is intentionally absent. These evidence fields document
    # the exact outstanding release requirements, never convert them into permission.
    missing=[]
    if not trusted_recovery_proven: missing.append('independent_recovery_not_proven')
    if not boot_authority_provisioned: missing.append('separate_boot_authority_not_provisioned')
    missing.append('reviewed_fsverity_aware_install_actuator_not_present')
    return {
        'schema':'arda-gen11-protected-boot-admission-v1',
        'baseline_sha256':old,'baseline_fsverity':measured_verity,
        'candidate_sha256':new,'candidate_dossier_sha256':sha256(dossier),
        'evidence_valid':True,'missing_release_gates':missing,
        'verdict':'REFUSE_PRODUCTION_INSTALL',
        'production_install_authorized':False,'first_boot_authorized':False,
        'original_bootloader_unchanged':True,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--dossier',required=True)
    ap.add_argument('--staged',required=True)
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    try:
        from arda_gen11_release import EXPECTED, EXPECTED_VERITY, validate_candidate, validate_live
        # Both read-only gates must pass, including current signed attestation.
        doc=validate_candidate(args.dossier)
        validate_live(doc)
        t=guard_target('/boot/grub/grub.cfg')
        v=command(['sudo','-n','fsverity','measure',str(t)])
        match=re.search(r'\b([a-f0-9]{64})\b',v)
        require(match is not None,'verity_measure_not_parseable')
        result=inspect(dossier=args.dossier,staged=args.staged,
                       expected_baseline=EXPECTED['gen10_grub'],
                       fsverity_digest=EXPECTED_VERITY,measured_verity=match.group(1),
                       parsed_grub_ok=(subprocess.run(['grub-script-check',args.staged],capture_output=True).returncode==0))
        dest=Path(args.out)
        require(dest.is_absolute() and not dest.exists() and not dest.is_symlink(),'receipt_destination_invalid')
        require(not str(dest.resolve()).startswith(('/boot/','/etc/','/usr/','/sys/','/run/','/var/lib/arda/')),'receipt_production_forbidden')
        with dest.open('x',encoding='utf8') as f:
            json.dump(result,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
        print(json.dumps(result,sort_keys=True))
    except Exception as exc:
        print('GEN11_STEP2=REFUSE:'+str(exc.__class__.__name__)+':'+str(exc))
        return 1
    return 0
if __name__=='__main__':sys.exit(main())
