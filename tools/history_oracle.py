"""Exact owned SQL namespace for the human-approved June6–7 reproduction.

Historical reproduction is now stopped by human instruction; retain this tool
for provenance, not as authorization to resume or as a90-day runner.

Only resource bindings differ from the retained replay. Canonical SQL, input,
actions and comparisons remain in the existing implementations.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def bind():
    from parity import legacy_isolation as isolation
    isolation.MAPPING.clear()
    isolation.MAPPING.update({
        'VFTEST_' + role: 'VFTEST_Fresh_History20261007_001_' + role
        for role in isolation.ROLES
    })
    isolation.DATA = Path('D:/freshvcf-build/sqlserver/history20261007-001')
    isolation.PRINCIPAL = 'freshvcf_history20261007_001'
    os.environ['VFTEST_PROFILE'] = 'fresh'
    return isolation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['provision', 'replay'])
    parser.add_argument('--modern', type=Path)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--day', type=int, choices=[0, 1])
    parser.add_argument('--continue-from', type=Path)
    args = parser.parse_args()
    isolation = bind()
    if args.action == 'provision':
        # This is a new namespace, never an alias for an existing oracle.
        with isolation.exclusive_replay(validate_schema=False), isolation.raw_connection('master') as db:
            for name in isolation.MAPPING.values():
                if db.execute('SELECT DB_ID(?)', name).fetchval() is not None:
                    raise ValueError('New history namespace already exists: ' + name)
        from parity.provision_legacy import build
        receipts = build()
        print(json.dumps(dict(status='PROVISIONED', databases=isolation.MAPPING,
                              schemas=len(receipts))))
        return
    if args.modern is None or args.destination is None or args.day is None:
        parser.error('Replay requires --modern, --destination and --day')
    if (args.day == 1) != (args.continue_from is not None):
        parser.error('June7 requires its own accepted June6 prefix')
    from parity.replay_temporal import replay
    replay(Path('D:/freshvcf-build/daily-3006/inputs/history1240-input-v1.json'),
           '0f3084b7a6fb60b84edbd7c4dc01fef3c4b40f1a7c389ec82f88b9ad22519546',
           args.modern, args.destination, args.day,
           continue_from=args.continue_from, automatic_actions=True)


if __name__ == '__main__':
    main()
