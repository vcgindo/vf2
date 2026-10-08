"""One approved restore-image exception; no general schema normalization."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

POLICY = 'cohort2-seven-check-casts-20261008'
POLICY_SHA256 = 'e2486d173a3199635b18f517f32f6d3f9c0d86744780af3098c600b79555cfaf'
RUNTIME_POLICY = 'cohort2-eleven-runtime-check-casts-20261008'
RUNTIME_POLICY_SHA256 = 'b55b14a464f85f2e3427dc608b4a45502ecfb44eaef7f0211a302cfdbb902150'


def runtime_policy():
    raw=(Path(__file__).resolve().parents[2] /
         'baseline/cohort2-runtime-restore-cast-qualification.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=RUNTIME_POLICY_SHA256:
        raise ValueError('Approved runtime restore qualification identity differs')
    return json.loads(raw)


def runtime_cast_metadata(connection):
    """Read the approved pairs' native metadata in the same backup snapshot."""
    result=[]
    for item in runtime_policy()['constraints']:
        rows=connection.execute('''SELECT k.convalidated,k.connoinherit,k.condeferrable,k.condeferred,
            format_type(att.atttypid,att.atttypmod),coll.collname,coll.collprovider,
            coll.collisdeterministic,coll.collcollate,coll.collctype
            FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace
            JOIN pg_attribute att ON att.attrelid=c.oid AND att.attname=%s
            LEFT JOIN pg_collation coll ON coll.oid=att.attcollation
            WHERE n.nspname=%s AND c.relname=%s AND k.conname=%s''',
            (item['column'],item['schema'],item['table'],item['constraint'])).fetchall()
        result.append(dict(schema=item['schema'],table=item['table'],constraint=item['constraint'],
                           column=item['column'],rows=[list(row) for row in rows]))
    return result


def _compare_runtime(source,restored,source_digest,restored_digest):
    policy=runtime_policy()
    expected=[dict(schema=r['schema'],table=r['table'],constraint=r['constraint'],
                   column=r['column'],rows=[r['metadata']]) for r in policy['constraints']]
    if (len(expected)!=11 or source.get('runtime_cast_metadata')!=expected
            or restored.get('runtime_cast_metadata')!=expected):
        raise ValueError('Runtime restore cast metadata absent or differs from approval')
    compared=deepcopy(restored)
    for item in policy['constraints']:
        originals=[r for r in source['relations'] if (r['schema'],r['name'])==(item['schema'],item['table'])]
        targets=[r for r in compared['relations'] if (r['schema'],r['name'])==(item['schema'],item['table'])]
        if len(originals)!=1 or len(targets)!=1:
            raise ValueError('Runtime qualified relation absent or duplicated')
        before=[r for r in originals[0]['constraints'] if r[0]==item['constraint']]
        after=[r for r in targets[0]['constraints'] if r[0]==item['constraint']]
        if len(before)!=1 or len(after)!=1 or before[0][1]!=item['left'] or after[0][1]!=item['right']:
            raise ValueError('Runtime qualified constraint expression differs')
        after[0][1]=item['left']
    if compared!=source:
        raise ValueError('Additional unqualified runtime logical restore difference')
    return dict(status='QUALIFIED',comparison='QUALIFIED_LOGICAL_RESTORE',qualification=RUNTIME_POLICY,
                logical_digest=source_digest,restored_digest=restored_digest,
                qualification_sha256=RUNTIME_POLICY_SHA256,semantic_proof_sha256=policy['proof_sha256'])


def image_digest(image):
    return hashlib.sha256(json.dumps(image, ensure_ascii=False, separators=(',', ':'),
                                    allow_nan=False).encode('utf-8')).hexdigest()


def compare_restore_images(source, restored, *, qualification=None):
    source_digest, restored_digest = image_digest(source), image_digest(restored)
    if source == restored and source_digest == restored_digest:
        return dict(status='VERIFIED', comparison='EXACT', qualification='',
                    logical_digest=source_digest, restored_digest=restored_digest)
    if qualification == RUNTIME_POLICY:
        return _compare_runtime(source,restored,source_digest,restored_digest)
    if qualification != POLICY:
        raise ValueError('Restored complete logical rows/schema differ; target retained')
    raw = (Path(__file__).resolve().parents[2] / 'baseline/cohort2-restore-cast-qualification.json').read_bytes()
    if hashlib.sha256(raw).hexdigest() != POLICY_SHA256:
        raise ValueError('Approved restore qualification identity differs')
    policy = json.loads(raw)
    if (source_digest != policy['source_digest'] or restored_digest != policy['restored_digest']):
        raise ValueError('Restore qualification applies only to its exact approved images')
    compared = deepcopy(restored)
    if len(policy['constraints']) != 7:
        raise ValueError('Approved constraint roster differs')
    for item in policy['constraints']:
        matches = [row for row in compared['relations']
                   if row['schema'] == item['schema'] and row['name'] == item['table']]
        originals = [row for row in source['relations']
                     if row['schema'] == item['schema'] and row['name'] == item['table']]
        if len(matches) != 1 or len(originals) != 1:
            raise ValueError('Qualified relation absent or duplicated')
        target = [row for row in matches[0]['constraints'] if row[0] == item['constraint']]
        before = [row for row in originals[0]['constraints'] if row[0] == item['constraint']]
        if (len(target) != 1 or len(before) != 1 or target[0][1] != item['right']
                or before[0][1] != item['left']):
            raise ValueError('Qualified constraint expression differs')
        target[0][1] = item['left']
    if compared != source:
        raise ValueError('Additional unqualified logical restore difference')
    return dict(status='QUALIFIED', comparison='QUALIFIED_LOGICAL_RESTORE', qualification=POLICY,
                logical_digest=source_digest, restored_digest=restored_digest,
                qualification_sha256=POLICY_SHA256, semantic_proof_sha256=policy['proof_sha256'])
