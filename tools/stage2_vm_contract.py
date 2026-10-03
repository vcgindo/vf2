"""Frozen identity and atomic receipts for the one-time VM fixture load."""
import hashlib
import json


def atomic(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2), encoding='utf-8')
    temporary.replace(path)


def roster(manifest):
    result = {}
    for source in manifest['sources']:
        for table in source['tables']:
            if 'file' not in table:
                continue
            key = (source['source'], table['table_name'].casefold())
            if table['schema_name'] != 'dbo' or key in result:
                raise ValueError('Only unique dbo table identities are supported')
            result[key] = (source, table)
    return result


def sealed(data):
    raw = (data / 'dataset-manifest.json').read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    seal = json.loads((data / 'manifest-seal.json').read_text())
    manifest = json.loads(raw)
    if seal['manifest_sha256'] != digest or seal['identity'] != manifest['identity']:
        raise ValueError('Manifest seal changed')
    tables=roster(manifest)
    if seal['tables']!=len(tables) or seal['rows']!=sum(t['count'] for s,t in tables.values()):
        raise ValueError('Seal roster differs')
    return manifest, digest


def bind(pg, manifest_sha):
    pg.execute('CREATE TABLE IF NOT EXISTS stage2_owner.manifest (manifest_sha256 text PRIMARY KEY)')
    rows = pg.execute('SELECT manifest_sha256 FROM stage2_owner.manifest').fetchall()
    if rows and rows != [(manifest_sha,)]:
        raise ValueError('Different frozen manifest')
    if not rows:
        pg.execute('INSERT INTO stage2_owner.manifest VALUES (%s)', (manifest_sha,))
