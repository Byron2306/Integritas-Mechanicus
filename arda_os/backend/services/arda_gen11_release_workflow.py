"""Gen11 Step 1: bound authorization and single-use SANDBOX transaction.

No production installation, boot selection, key generation, or trust provisioning.
A v2 verification-only signature is never accepted as install authority.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from arda_gen11_release import (EXPECTED, EXPECTED_VERITY, Ledger,
                                canonical, digest_file, validate_candidate,
                                validate_live)
from arda_boot_transaction import create_plan
from arda_gen11_install_actuator import SandboxInstall

class Refuse(RuntimeError): pass

def require(ok, reason):
    if not ok: raise Refuse(reason)

def verify_install_envelope(authorization, dossier_path, trust_path, plan, destination_path, *, now=None):
    """Verify distinct, explicitly install-scoped Ed25519 authorization.

    All plan hashes and the exact sandbox target are bound in the signed payload.
    Production destinations and first boot are outside this contract.
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    trust_path=Path(trust_path)
    require(trust_path.is_file(), 'release_authority_not_provisioned')
    require(Path(authorization).is_file(), 'install_authorization_missing')
    doc=json.loads(Path(authorization).read_text())
    require(type(doc) is dict and set(doc)=={'payload','signature'}, 'envelope_structure')
    p=doc['payload']
    fields={'schema','action','authorization_id','generation','boot_profile','dossier_sha256',
            'candidate_grub_sha256','baseline_grub_sha256','baseline_grub_fsverity',
            'gen11_kernel_sha256','gen11_initrd_sha256','destination_kind','destination_path','issued_at','expires_at'}
    require(type(p) is dict and set(p)==fields,'signed_field_set')
    require(p['schema']=='arda-gen11-sandbox-install-authorization-v1','schema')
    require(p['action']=='install_sandbox_experimental_candidate','action')
    require(type(p['generation']) is int and p['generation']==11,'generation')
    require(p['boot_profile']=='EXPERIMENTAL_RING0_MASKED','boot_profile')
    require(p['destination_kind']=='SANDBOX_ONLY','destination_kind')
    require(p['destination_path']==str(Path(destination_path).resolve(strict=True)),'destination_path')
    require(isinstance(p['authorization_id'],str) and re.fullmatch('[A-Za-z0-9_-]{16,100}',p['authorization_id']) is not None,'authorization_id')
    bindings={'dossier_sha256':digest_file(dossier_path),
              'candidate_grub_sha256':plan['candidate_grub_sha256'],
              'baseline_grub_sha256':plan['baseline_grub_sha256'],
              'baseline_grub_fsverity':plan['baseline_grub_fsverity'],
              'gen11_kernel_sha256':plan['gen11_kernel_sha256'],
              'gen11_initrd_sha256':plan['gen11_initrd_sha256']}
    for key, value in bindings.items(): require(p[key]==value, 'binding_mismatch:'+key)
    def timeparse(v):
        require(isinstance(v,str),'timestamp_type')
        try: dt=datetime.fromisoformat(v.replace('Z','+00:00'))
        except ValueError: raise Refuse('timestamp_format')
        require(dt.tzinfo is not None,'timestamp_timezone')
        return dt.astimezone(timezone.utc)
    current=now or datetime.now(timezone.utc)
    issued, expires=timeparse(p['issued_at']), timeparse(p['expires_at'])
    require(issued <= current < expires and 0<(expires-issued).total_seconds()<=600,'authorization_freshness')
    pub=serialization.load_pem_public_key(trust_path.read_bytes())
    require(isinstance(pub,Ed25519PublicKey),'authority_type')
    try:
        signature=base64.b64decode(doc['signature'],validate=True)
        require(len(signature)==64,'signature_length')
        pub.verify(signature,canonical(p))
    except (ValueError,TypeError) as exc:
        raise Refuse('signature_encoding') from exc
    return p

def execute_sandbox_workflow(*, dossier_path, authorization, trust_path, ledger_path, sandbox_dir,
                              verify_live=True):
    """Fail closed unless each original gate succeeds; ledger prevents reuse.

    Ledger reservation survives errors. The caller must manually inspect and recover
    a failed sandbox; it must NOT auto-retry with a fresh authorization.
    """
    dossier_path=Path(dossier_path)
    candidate=validate_candidate(dossier_path)
    if verify_live: validate_live(candidate)
    plan=create_plan(dossier_path, baseline_verity=EXPECTED_VERITY)
    root=Path(sandbox_dir)
    require(root.is_absolute() and root.is_dir() and not root.is_symlink(),'sandbox_missing')
    install=SandboxInstall(root) # Ensures owner/mode and blocks production dirs
    p=verify_install_envelope(authorization,dossier_path,trust_path,plan,install.root)
    require(install.current.is_file(),'sandbox_baseline_missing')
    require(digest_file(install.current)==plan['baseline_grub_sha256'],'sandbox_baseline_digest')
    source=Path(candidate['artifacts']['grub_candidate']['path'])
    require(digest_file(source)==plan['candidate_grub_sha256'],'candidate_changed')
    # Require a durable, separately provisioned ledger outside sandbox and ensure
    # exclusive creation is managed by SQLite's unique authorization identifier.
    ledpath=Path(ledger_path)
    require(ledpath.is_absolute() and ledpath.parent.is_dir() and not ledpath.is_symlink(),'ledger_path_invalid')
    require(not str(ledpath.resolve()).startswith(('/boot/','/etc/','/usr/','/sys/','/run/')),'ledger_location_forbidden')
    ledger=Ledger(str(ledpath))
    auth_digest=digest_file(authorization)
    ledger.reserve(p['authorization_id'],auth_digest)
    try:
        install.stage(candidate=source, expected_old=plan['baseline_grub_sha256'],
                      expected_new=plan['candidate_grub_sha256'], approval_verified=True)
        install.commit()
        ledger.mark(p['authorization_id'],'committed')
    except BaseException:
        try: ledger.mark(p['authorization_id'],'recovery_required')
        except Exception: pass
        raise
    return {'status':'SANDBOX_COMMITTED','authorization_id':p['authorization_id'],
            'candidate_sha256':plan['candidate_grub_sha256'],
            'production_install_authorized':False,'first_boot_authorized':False}

def main():
    p=argparse.ArgumentParser(description='Gen11 signed sandbox installation workflow; never modifies production boot')
    for a in ('dossier','authorization','trust','ledger','sandbox'):p.add_argument('--'+a,required=True)
    p.add_argument('--offline',action='store_true',help='For laboratory validation only; skip live Gen10 check')
    args=p.parse_args()
    try:
        result=execute_sandbox_workflow(dossier_path=args.dossier,authorization=args.authorization,
            trust_path=args.trust,ledger_path=args.ledger,sandbox_dir=args.sandbox,verify_live=not args.offline)
        print(json.dumps(result,sort_keys=True));return 0
    except Exception as exc:
        print('GEN11_STEP1_VERDICT=REFUSE')
        print('REASON='+exc.__class__.__name__+':'+str(exc))
        print('GEN11_PRODUCTION_INSTALL_AUTHORIZED=false')
        print('GEN11_FIRST_BOOT_AUTHORIZED=false')
        return 1
if __name__=='__main__':sys.exit(main())
