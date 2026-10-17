"""Separate exact retained optional operator package; never load or initialize it.

**DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.**
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def package(repository, commit, input_pack, destination):
    from release.native_identity import _pin
    if not _pin(commit,40):
        raise ValueError('Exact approved full commit required')
    destination=Path(destination).resolve()
    if destination.exists():
        raise ValueError('Optional package destination exists; never overwrite')
    contents={name:subprocess.check_output(['git','-C',str(repository),'show',commit+':release/'+name])
        for name in ('optional_initialize.py','optional-initialization.json')}
    declaration=json.loads(contents['optional-initialization.json'])
    original=Path(input_pack)
    actual=hashlib.sha256(original.read_bytes()).hexdigest()
    if actual != declaration['pack_sha256']:
        raise ValueError('Retained optional input ZIP differs; do not regenerate or substitute')
    destination.mkdir(parents=True)
    records={}
    for name,raw in contents.items():
        (destination/name).write_bytes(raw)
        records[name]=hashlib.sha256(raw).hexdigest()
    target=destination/'vectorflow-optional-initialization-input-pack.zip'
    shutil.copyfile(original,target)
    records[target.name]=actual
    result=dict(restriction=declaration['restriction'],status='SEPARATE_OPERATOR_PACKAGE_NOT_LOADED',
        source_commit=commit,files=records,input_sha256=declaration['input_sha256'],
        configuration_digest=declaration['configuration_digest'],recipe_digest=declaration['recipe_digest'],
        scope='Exact original adapter/manifest/data ZIP bytes, unchanged generic production initializer; optional target/input authority remains separate. Never place in production image or default source archive.')
    (destination/'optional-package-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository',type=Path,required=True)
    parser.add_argument('--commit',required=True)
    parser.add_argument('--input-pack',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(package(args.repository,args.commit,args.input_pack,args.output),sort_keys=True))
