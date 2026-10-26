"""Finite used0230 ->0231 report-source custody upgrade; seals stay original."""
import hashlib,re
from pathlib import Path

NAMES=('0231_runtime_report_placement_guards',)
# Complete independently reviewed951-entry rollback observation, including
# columns, generated indexes, guards, trigger bindings and all ACLs.
CATALOGUE_DELTA_DIGEST='d8ca8fbd434f277a050cedc06969831f69be3f86931dffac43e2c57ff80815f1'


def catalogue_contract(delta):
    from mta.serialization import digest
    owner=delta['functions:mta.ingestion_watch()']['before']['owner']
    consumers=[item['after']['grantee'] for name,item in delta.items()
        if name.startswith('grants:mta_state.placement_bpr_colorsequence:')
        and item['after']['privilege']=='SELECT' and item['after']['grantee']!=owner]
    if (len(consumers)!=1 or owner==consumers[0]
            or any(not re.fullmatch(r'[a-z_][a-z0-9_]{0,62}',role) for role in (owner,*consumers))):
        raise ValueError('Exact placement owner and SELECT-only consumer required')
    mapping={owner:'<namespace-owner>',consumers[0]:'<namespace-consumer>'}
    def normalized(value):
        if isinstance(value,dict):return {normalized(k):normalized(v) for k,v in value.items()}
        if isinstance(value,list):return [normalized(v) for v in value]
        if isinstance(value,str):
            if value in mapping:return mapping[value]
            if value.startswith('grants:'):return ':'.join(mapping.get(part,part) for part in value.split(':'))
        return value
    return digest(normalized(delta))


def migration_pins():
    root=Path(__file__).parent/'migrations'
    return [[name,hashlib.sha256((root/(name+'.py')).read_bytes()).hexdigest()] for name in NAMES]


def require_specification(spec):
    if spec['migration_pins']!=migration_pins():
        raise ValueError('Exact placement migration bytes required')
    try:matches=CATALOGUE_DELTA_DIGEST is not None and catalogue_contract(spec['catalogue_delta'])==CATALOGUE_DELTA_DIGEST
    except (KeyError,TypeError,ValueError):matches=False
    if not matches:raise ValueError('Exact reviewed placement catalogue/guards/ACLs required')


def require_start(cursor):
    from importlib import import_module
    from mta.runtime.ingestion_ownership import migration_history_guard
    prior=import_module('mta.runtime.migrations.0230_runtime_report_publication_guards')
    cursor.execute("SELECT to_regclass('fresh_control.ingestion_schema_compatibility')")
    if cursor.fetchone()!=(None,):raise ValueError('Placement upgrade requires qualified unextended0230 namespace')
    cursor.execute("SELECT max(name) FROM mta.django_migrations WHERE app='fresh_mta'")
    if cursor.fetchone()!=('0230_runtime_report_publication_guards',):
        raise ValueError('Placement upgrade requires exact admitted0230 start')
    for name,body in (('mta.ingestion_watch()',prior.NEW),
            ('mta.guard_runtime_report_publication()',prior.GUARD),
            ('mta.runtime_report_publication_source(mta.fresh_mta_runtimereportpublication)',prior.SOURCE)):
        cursor.execute('SELECT prosrc FROM pg_proc WHERE oid=to_regprocedure(%s)',[name])
        if cursor.fetchone()!=(body,):raise ValueError('Placement predecessor guard differs')
    if not migration_history_guard(cursor):raise ValueError('Placement migration history guard differs')


def approved_receipt(value):
    return value.get('migration_pins')==migration_pins()
