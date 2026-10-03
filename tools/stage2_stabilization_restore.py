"""Restore June17 after the explicitly authorized3005 gateway/frontend update.

Preserve window010's historical proof. A new restoration checkpoint binds the
updated protected services; no identity comparison is waived. --check-only
validates the recorded current boundary without disabling accounts or restarting.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import stage2_fixture_window as window

EVIDENCE = Path('D:/freshvcf-build/evidence/3005-stabilization-20261004-001')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    recorded = json.loads((EVIDENCE/'restoration-checkpoint.json').read_text())
    previous = json.loads((window.DEST/'fixture-window-010/window-before.json').read_text())
    current = window.protected()
    if current != recorded['protected']:
        raise ValueError('Protected runtime changed after stabilization checkpoint')
    if current['accepted'] != previous['protected']['accepted']:
        raise ValueError('Accepted publication changed')
    if window.runtime(window.inspect(window.MTA)) != recorded['mta']:
        raise ValueError('Selected fixture runtime changed')
    restore_file = window.DEST/'compose.restore.json'
    if hashlib.sha256(restore_file.read_bytes()).hexdigest() != recorded['restore_sha256']:
        raise ValueError('Original restoration configuration changed')
    if args.check_only:
        print('Restoration boundary verified; no serving mutation')
        return
    window.WINDOW = EVIDENCE/'normal-restoration'
    window.WINDOW.mkdir(exist_ok=False)
    window.atomic(window.WINDOW/'window-before.json', dict(
        mta=previous['mta'], ready=previous['ready'], protected=current,
        provenance='June17 target from window010; updated protected services from authorized stabilization'))
    window.restore()


if __name__ == '__main__':
    main()
