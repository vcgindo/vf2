"""Bounded commands on the exclusively owned3006 database, never preview3005."""
import argparse
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OWNER=Path('D:/freshvcf-build/daily-3006')
EVIDENCE=Path('D:/freshvcf-build/evidence/daily-publication-3006-20261006-001')


def invoke(args, label):
    target=EVIDENCE/(label+'.log')
    if target.exists(): raise ValueError('Use a new proof identity; never replace evidence')
    cmd=['docker','compose','-f',str(OWNER/'compose.json'),'run','--rm','--no-deps','-T']
    for folder in ['mta','vectorflow','tests','baseline']:
        cmd+=['-v',str(ROOT/folder)+':/app/'+folder+':ro']
    cmd+=['-v',str(EVIDENCE)+':/evidence:ro']
    cmd+=['--entrypoint','python','mta',*args]
    with target.open('w',encoding='utf-8') as log:
        proc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
    print(f'{label}: exit {proc.returncode}; {target}')
    if proc.returncode:
        print('\n'.join(target.read_text().splitlines()[-22:]))
    return proc.returncode


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    parser.add_argument('arguments',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    raise SystemExit(invoke(args.arguments,args.label))
