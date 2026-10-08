"""Create new complete-assessment SQL owners; never reset or reuse a namespace.

Setup only, not a daily invocation. Canonical standard/site schema seeds are
retained. The site DDL's absent DROP statements receive the same explicit empty
bootstrap disposition as standard provisioning; calculation SQL is unchanged.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def prepare(owner, output):
    identifier = str(UUID(owner))
    if identifier != owner:
        raise ValueError('Canonical owner UUID required')
    output = Path(output).resolve()
    evidence_root = Path('D:/freshvcf-build/complete-daily-assessment').resolve()
    if not output.is_relative_to(evidence_root) or output.exists():
        raise ValueError('New owned setup receipt path required')
    from parity import legacy_isolation as isolation
    if isolation._lease is not None:
        raise ValueError('Cannot rebind active replay owner')
    isolation.MAPPING.clear()
    isolation.MAPPING.update({
        'VFTEST_'+role: 'VFTEST_Fresh_CompleteDaily_'+UUID(owner).hex+'_'+role
        for role in isolation.ROLES})
    isolation.DATA = Path('D:/freshvcf-build/sqlserver')/('complete-daily-'+owner)
    os.environ['VFTEST_PROFILE'] = 'fresh'
    manifest = json.loads((ROOT/'baseline/manifest.json').read_text(encoding='utf-8'))
    path = Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/SiteSpecific/GulfOil/Intermediate_DBCreation.sql')
    raw = path.read_bytes()
    expected = next(r['sha256'] for r in manifest['engine_sources'] if Path(r['path']) == path)
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Site Intermediate schema source changed')
    if isolation.DATA.exists():
        raise ValueError('Setup refuses existing owned data directory')
    with isolation.exclusive_replay(validate_schema=False), isolation.raw_connection('master') as master:
        if any(master.execute('SELECT DB_ID(?)', name).fetchval() is not None
               for name in isolation.MAPPING.values()):
            raise ValueError('Setup refuses existing namespace')
    # Import after binding: the existing provisioner captures DATA at import.
    from parity.provision_legacy import build, consume, schema_signature
    standard = build()
    database = isolation.MAPPING['VFTEST_Intermediate']
    skipped = []
    with isolation.exclusive_replay(), isolation.raw_connection(database) as target:
        target.autocommit = False
        try:
            for index, batch in enumerate(re.split(r'(?im)^\s*GO\s*(?:--.*)?$', raw.decode('cp1252')), 1):
                if not batch.strip():
                    continue
                drop = re.search(r'(?im)^\s*DROP TABLE \[dbo\]\.\[([^]]+)\]\s*$', batch)
                if drop:
                    name = drop[1]
                    if target.execute("SELECT OBJECT_ID(?, 'U')", 'dbo.'+name).fetchval() is not None:
                        raise ValueError('Site schema would replace an existing table: '+name)
                    remainder = batch[:drop.start()] + batch[drop.end():]
                    if re.sub(r'/\*[\s\S]*?\*/|--[^\r\n]*', '', remainder).strip():
                        raise ValueError('Unrecognized site DROP batch')
                    skipped.append(dict(batch=index, table=name,
                        disposition='absent table DROP on explicitly new empty schema',
                        sql_sha256=hashlib.sha256(batch.encode()).hexdigest()))
                    continue
                consume(target.execute(isolation.bind_sql(batch)))
            target.commit()
            signature = schema_signature(target)
        except Exception:
            target.rollback()
            raise
    # Keep the original standard receipt; install a separately identified schema
    # extension in the active ownership receipt so existing schema verification
    # checks the actual full site schema.
    receipt_path = isolation.DATA/(database+'-schema.json')
    original = receipt_path.read_bytes()
    preserved = isolation.DATA/(database+'-standard-schema.json')
    with preserved.open('xb') as stream:
        stream.write(original)
    receipt = json.loads(original)
    receipt.update(schema_sha256=signature, site_extension=dict(
        path=str(path), sha256=expected, bootstrap_exceptions=skipped,
        original_receipt_sha256=hashlib.sha256(original).hexdigest()))
    receipt_path.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    result = dict(schema='fresh-complete-daily-sql-setup-v1', owner_id=owner,
        namespace=dict(isolation.MAPPING), data_directory=str(isolation.DATA),
        schema_only=True, business_invocations=0, standard_schemas=standard,
        site_intermediate_receipt=receipt,
        configuration_approval='call_bcfe99ea9c2d40af8c9de82ff0f529bc')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.owner, args.output)
    print(json.dumps({'owner_id': result['owner_id'], 'schema_only': True,
                      'business_invocations': 0, 'receipt': str(args.output)}))
