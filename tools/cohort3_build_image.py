"""Verify the approved local auth image ID, then build the no-port proof image."""
import argparse
import json
from pathlib import Path
import subprocess


BASE = 'freshvcf-daily3006-user-service:captcha-001'
BASE_ID = 'sha256:86418581f034614afd79dc60c4cedab03b0323c39b09073f759a2dd9e1ee1ccc'
MTA_BASE = 'freshvcf-cohort2:20261008-final001'
MTA_BASE_ID = 'sha256:a8d606b23e65f85b326d87fd86e960f343af4789eec69b03deee70341cf98ebd'


def run(*arguments):
    return subprocess.check_output(arguments, text=True, encoding='utf-8').strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    if '@' in args.tag or not args.tag.startswith('freshvcf-cohort3-proof:'):
        raise ValueError('Use a new explicit freshvcf-cohort3-proof:* local tag')
    inspected = json.loads(run('docker', 'image', 'inspect', BASE))[0]
    if inspected.get('Id') != BASE_ID:
        raise ValueError('Approved Cohort3 user image tag resolves to a different image ID')
    if json.loads(run('docker', 'image', 'inspect', MTA_BASE))[0].get('Id') != MTA_BASE_ID:
        raise ValueError('Accepted MTA dependency image identity changed')
    root = Path(__file__).resolve().parents[1]
    subprocess.run(['docker', 'build', '--pull=false', '--no-cache',
                    '-f', str(root / 'tools' / 'cohort3.Dockerfile'),
                    '-t', args.tag, str(root)], check=True)
    result = json.loads(run('docker', 'image', 'inspect', args.tag))[0]
    print(json.dumps({'status': 'COHORT3_PROOF_IMAGE_BUILT', 'tag': args.tag,
                      'image_id': result['Id'], 'approved_base_id': BASE_ID}))


if __name__ == '__main__':
    main()
