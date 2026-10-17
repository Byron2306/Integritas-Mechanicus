#!/usr/bin/env python3
"""ARDA Gen11 release-gate reference implementation. No boot mutations.

A verifier is intentionally not an installer. In particular, fs-verity protected
GRUB updates require a separately reviewed privileged installer and recovery path.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

KERNEL = '6.12.111-valinor-gen11'
MANIFEST = 'measured-f926c576ad174fb295fdba9349092a09'
EXPECTED = {
 'grub_candidate':'fb3c66c81df3dabcd9390597a124f2686e759549f70dff68fe41cf05f99ddc62',
 'gen11_kernel':'b9d69566f01af50e46d96607d478c63d083586d000f51613a5b7f392ad348e27',
 'gen11_initrd':'cf67ea94591526dc126d0f94d00a3bbdf6e7ccef2f9ec441ebb64c6ebc449b09',
 'gen10_grub':'3bd6231883dbb955901eb133067a1760bb58d23b3920ee185208027cebb5f441',
 'gen10_kernel':'550802122775e251e60aabfbb16633a9bc672180a9020d9d7e265f92756a5265',
 'gen10_initrd':'afd735f6f655aaabc80369d0072c02ee216aacb20bfa5c61a389ca7122942e4c',
}
EXPECTED_VERITY = 'c7dd6c826af174ab7ba3d819e49f8d40d1b8f7188cb46363054b35cfa6579337'
PATHS = {
 'grub_candidate':None,
 'gen11_kernel':'/boot/vmlinuz-6.12.111-valinor-gen11',
 'gen11_initrd':'/boot/initrd.img-6.12.111-valinor-gen11',
 'gen10_grub':'/boot/grub/grub.cfg',
 'gen10_kernel':'/boot/vmlinuz-6.12.111-valinor',
 'gen10_initrd':'/boot/initrd.img-6.12.111-valinor',
}
class Refuse(Exception): pass

def require(condition, why):
    if not condition: raise Refuse(why)

def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()

def digest_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def checked(*args):
    p=subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
    require(p.returncode==0, 'command_failed:'+str(args[0])+':'+p.stderr[:150])
    return p.stdout.strip()

def hash_protected(path):
    p=subprocess.run(['/usr/bin/sha256sum',str(path)], capture_output=True, text=True)
    if p.returncode!=0:
        return checked('sudo','-n','/usr/bin/sha256sum',str(path)).split()[0]
    return p.stdout.split()[0]

def validate_candidate(path):
    doc=json.loads(Path(path).read_text())
    require(doc.get('schema')=='arda-gen11-boot-release-candidate-v1','schema')
    require(doc.get('status')=='CANDIDATE_ONLY','candidate_state')
    require(type(doc.get('active_generation')) is int and doc['active_generation']==10,'active_generation')
    require(type(doc.get('target_generation')) is int and doc['target_generation']==11,'target_generation')
    require(doc.get('target_kernel_release')==KERNEL,'kernel_release')
    require(doc.get('boot_profile')=='EXPERIMENTAL_RING0_MASKED','profile')
    require(doc.get('release_authorized') is False and doc.get('first_boot_authorized') is False,'claims_authority')
    require(doc.get('baseline',{}).get('manifest_id')==MANIFEST,'manifest_id')
    a=doc.get('artifacts')
    require(isinstance(a,dict) and set(a)==set(EXPECTED),'artifact_set')
    for name,expected in EXPECTED.items():
        item=a[name]
        require(item.get('sha256')==expected,'pinned_digest:'+name)
        require(type(item.get('size')) is int and item['size']>0,'size:'+name)
        expected_path=PATHS[name]
        if expected_path: require(item.get('path')==expected_path,'path:'+name)
        path=Path(item['path'])
        require(path.is_file() and path.stat().st_size==item['size'],'file_missing_or_size:'+name)
        observed = hash_protected(path) if name.startswith('gen10_') else digest_file(path)
        require(observed==expected,'content_digest:'+name)
    cfg=Path(a['grub_candidate']['path']).read_text()
    require("menuentry 'ARDA Valinor Gen11 Experimental'" in cfg,'missing_experimental_entry')
    require("menuentry 'Debian GNU/Linux, with Linux 6.12.111-valinor'" in cfg,'missing_gen10_fallback')
    for service in ('arda-ring0.service','arda-ring0-verify.service','arda-valinor-postboot.service','arda-valinor-postboot.timer','arda-postboot-grade.service'):
        require('systemd.mask='+service in cfg,'experimental_mask_missing:'+service)
    checked('grub-script-check',a['grub_candidate']['path'])
    return doc

def validate_live(doc):
    require(checked('uname','-r')=='6.12.111-valinor','active_kernel')
    grade=json.loads(checked('sudo','-n','/usr/bin/arda-grade'))
    require(grade.get('ok') is True and grade.get('hardware_rooted_os_grade') is True,'hardware_grade')
    require(grade.get('software_os_grade') is True and grade.get('verifier_signature_verified') is True,'software_or_signature')
    require(grade.get('remote_verifier_signed_fresh') is True,'stale_signed_verdict')
    require(type(grade.get('verdict_age_seconds')) in (int,float) and 0<=grade['verdict_age_seconds']<300,'signed_verdict_age')
    require(grade.get('active_generation')==10 and grade.get('active_manifest_id')==MANIFEST,'active_manifest')
    require(not grade.get('failures'),'grade_failures')
    v=checked('sudo','-n','fsverity','measure','/boot/grub/grub.cfg')
    require(re.search(r'\b'+EXPECTED_VERITY+r'\b',v) is not None,'grub_fsverity_identity')
    return grade

def validate_authorization(path,dossier,trust):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    require(Path(trust).is_file(),'release_authority_not_provisioned')
    require(Path(path).is_file(),'authorization_missing')
    env=json.loads(Path(path).read_text())
    require(type(env) is dict and set(env)=={'payload','signature'},'authorization_envelope')
    payload=env['payload']
    keys={'schema','action','authorization_id','generation','boot_profile','dossier_sha256','issued_at','expires_at'}
    require(type(payload) is dict and set(payload)==keys,'signed_fields')
    require(payload['schema']=='arda-boot-release-authorization-v2','authorization_schema')
    require(payload['action']=='verify_experimental_candidate','action')
    require(type(payload['generation']) is int and payload['generation']==11,'generation')
    require(payload['boot_profile']=='EXPERIMENTAL_RING0_MASKED','boot_profile')
    require(isinstance(payload['authorization_id'],str) and re.fullmatch('[a-zA-Z0-9_-]{16,100}',payload['authorization_id']) is not None,'authorization_id')
    require(payload['dossier_sha256']==digest_file(dossier),'dossier_digest')
    def parse(s):
        require(isinstance(s,str),'timestamp_type')
        dt=datetime.fromisoformat(s.replace('Z','+00:00'))
        require(dt.tzinfo is not None,'naive_timestamp')
        return dt.astimezone(timezone.utc)
    now=datetime.now(timezone.utc)
    issued,expires=parse(payload['issued_at']),parse(payload['expires_at'])
    require(issued<=now<expires and 0<(expires-issued).total_seconds()<=600,'time_window')
    pub=serialization.load_pem_public_key(Path(trust).read_bytes())
    require(isinstance(pub,Ed25519PublicKey),'authority_key_type')
    signature=base64.b64decode(env['signature'], validate=True)
    require(len(signature)==64,'signature_length')
    pub.verify(signature,canonical(payload))
    return payload

class Ledger:
    """Only an independently approved installer may use reserve() or commit()."""
    def __init__(self,db):
        self.conn=sqlite3.connect(db, isolation_level=None, timeout=10)
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA synchronous=FULL')
        self.conn.execute('''CREATE TABLE IF NOT EXISTS releases
           (id TEXT PRIMARY KEY, digest TEXT NOT NULL, status TEXT NOT NULL
            CHECK(status IN ('reserved','committed','recovery_required')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
    def reserve(self,auth_id,digest):
        require(re.fullmatch('[A-Za-z0-9_-]{16,100}',auth_id) is not None,'id')
        require(re.fullmatch('[a-f0-9]{64}',digest) is not None,'digest')
        try:
            self.conn.execute('BEGIN IMMEDIATE')
            self.conn.execute('INSERT INTO releases(id,digest,status) VALUES(?,?,?)',(auth_id,digest,'reserved'))
            self.conn.execute('COMMIT')
        except Exception:
            if self.conn.in_transaction:self.conn.execute('ROLLBACK')
            raise
    def mark(self,auth_id,status):
        require(status in ('committed','recovery_required'),'state')
        self.conn.execute('BEGIN IMMEDIATE')
        try:
            row=self.conn.execute('SELECT status FROM releases WHERE id=?',(auth_id,)).fetchone()
            require(row is not None and row[0]=='reserved','invalid_state_transition')
            self.conn.execute('UPDATE releases SET status=? WHERE id=?',(status,auth_id))
            self.conn.execute('COMMIT')
        except Exception:
            if self.conn.in_transaction:self.conn.execute('ROLLBACK')
            raise

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--dossier',default=str(Path.home()/'arda-gen11-admission/boot-release/gen11-release-dossier.json'))
    ap.add_argument('--authorization',default=str(Path.home()/'arda-gen11-admission/boot-release/gen11-release-authorization.json'))
    ap.add_argument('--trust',default='/etc/arda/boot-release/authority.pub.pem')
    ap.add_argument('--offline',action='store_true',help='candidate proof only, skips live Gen10 grade')
    args=ap.parse_args()
    try:
        d=validate_candidate(args.dossier)
        print('GEN11_CANDIDATE_IDENTITY=PASS',flush=True)
        if not args.offline:
            validate_live(d)
            print('GEN10_LIVE_BASELINE=PASS',flush=True)
        validate_authorization(args.authorization,args.dossier,args.trust)
        print('SIGNED_CANDIDATE_VERIFICATION=PASS')
        print('GEN11_INSTALL_AUTHORIZED=false')
        print('GEN11_FIRST_BOOT_AUTHORIZED=false')
        print('NOTE=Verification alone never authorizes an install')
    except Exception as e:
        print('GEN11_RELEASE_VERDICT=REFUSE')
        print('REASON='+str(e.__class__.__name__)+':'+str(e))
        print('GEN11_INSTALL_AUTHORIZED=false')
        print('GEN11_FIRST_BOOT_AUTHORIZED=false')
        return 1
    return 0
if __name__=='__main__':sys.exit(main())
