"""Read the verified owned native schema for the complete-day storage supplement."""
import argparse
import hashlib
import json
import os
from pathlib import Path

from parity import legacy_isolation as isolation
from parity.adapters.legacy.complete_daily_sql import namespace, data_directory

ROOT = Path(__file__).resolve().parents[1]
POPULATIONS = {
    'Interface': ('FGTrendData',),
    'Importer': ('ScriptExecutedFlag', 'CriticalFiles', 'DataSanitizationResult', 'EmailAlertSettings'),
    'BPR': ('ProdOrderSuggestions', 'RuntimeReports', 'BPRReport_RemarkDetails',
            'OpenExpeditRequestRemarksHistory', 'InTransitWhereAboutsRemarks', 'SupplierDispatchReq'),
}


def capture(owner):
    if isolation._lease is not None:
        raise ValueError('Cannot change an active SQL owner')
    isolation.MAPPING.clear()
    isolation.MAPPING.update(namespace(owner))
    isolation.DATA = data_directory(owner)
    os.environ['VFTEST_PROFILE'] = 'fresh'
    tables, bindings, sources = {}, {}, {}
    with isolation.exclusive_replay():
        for role, names in POPULATIONS.items():
            receipt = json.loads((isolation.DATA/(isolation.MAPPING['VFTEST_'+role]+'-schema.json')).read_text())
            raw = Path(receipt['source']).read_bytes()
            if hashlib.sha256(raw).hexdigest() != receipt['source_sha256']:
                raise ValueError('Native schema source changed')
            sources[role] = {k: receipt[k] for k in ('source', 'source_sha256', 'schema_sha256')}
            with isolation.connection('VFTEST_'+role) as connection:
                for name in names:
                    columns = [list(row) for row in connection.execute(
                        'SELECT c.name,t.name FROM sys.columns c JOIN sys.types t '
                        'ON t.user_type_id=c.user_type_id WHERE c.object_id=OBJECT_ID(?) ORDER BY c.column_id',
                        'dbo.'+name)]
                    if not columns:
                        raise ValueError('Required native schema absent: '+role+'/'+name)
                    key = 'complete/'+role+'/'+name
                    tables[key] = columns
                    bindings['closing/complete/'+name] = key
    return dict(schema='fresh-complete-daily-state-schema-v1', tables=tables, bindings=bindings,
                sources=sources, qualification='Canonical column names/types only; not calculation parity')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = capture(args.owner)
    with args.output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'tables': len(result['tables']), 'output': str(args.output),
                      'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest()}))
