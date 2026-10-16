"""Prepare exact native serving-source ancestry, never a database clone/registration."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','offline-source-check-only')
import django
django.setup()
from mta.mdm import native_report_compatibility as c
from mta.mdm.production_families import adapter_digest
from mta.serialization import digest


def build(evidence):
    v8=(evidence.parent/'g3-three-gap-closure-20261016-v1/source-seal-compatibility-v8.json').read_bytes()
    assert c._sha(v8)==c.LOGISTICS_V8_SHA256
    prior=json.loads(v8)['current_files']
    files=c._files(ROOT)
    changed={n for n in set(files)|set(prior) if files.get(n)!=prior.get(n)}
    assert changed==c.LOGISTICS_FILES,(changed-c.LOGISTICS_FILES,c.LOGISTICS_FILES-changed)
    inverse={}
    for n in sorted(changed):
        before=subprocess.check_output(['git','show','7fe9722716ad255e1eadb4364d8774b48312e7d2:'+n],cwd=ROOT) if n in prior else b''
        assert n not in prior or c._sha(before)==prior[n],n
        inverse[n]=c.inverse_delta(before,(ROOT/n).read_bytes())
    identity=dict(adapter_digest=adapter_digest(),closing_projection_version=c.VERSION,
                  source_manifest_digest=digest(files))
    value=dict(schema=c.LOGISTICS_SCHEMA,v8_sha256=c.LOGISTICS_V8_SHA256,
               current_files=files,current_identity=identity,inverse=inverse)
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode()
    reconstructed,_,_=c.validate_logistics_ancestry(raw,c._sha(raw),v8,ROOT,files,identity)
    assert reconstructed==prior
    (evidence/'source-ancestry.json').write_bytes(raw)
    with zipfile.ZipFile(evidence/'integrated-source.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for n in sorted(files):archive.write(ROOT/n,n)
        for p in (ROOT/'baseline').rglob('*.json'):archive.write(p,p.relative_to(ROOT).as_posix())
    proof=dict(status='PASS',baseline='7fe9722716ad255e1eadb4364d8774b48312e7d2',
        source_files=len(files),prior_source_files=len(prior),changed=sorted(changed),
        exact_prior_reconstruction=True,declaration_sha256=c._sha(raw),
        archive_sha256=c._sha((evidence/'integrated-source.zip').read_bytes()),
        current_identity=identity,qualification='Only normal native source ancestry; original database, source, initialization, namespace, seal and receipt validators unchanged. No clone mode, registration or DB resource.')
    (evidence/'source-ancestry-proof.json').write_text(json.dumps(proof,indent=2))
    print(json.dumps({k:proof[k] for k in ('status','source_files','prior_source_files','declaration_sha256')}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('evidence',type=Path)
    build(parser.parse_args().evidence)
