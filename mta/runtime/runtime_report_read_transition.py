"""One additive consumer EXECUTE ACL, preserving predicate bodies/recipes."""
from importlib import import_module
import hashlib,re
from pathlib import Path

NAMES=('0232_runtime_report_consumer_read',)
EXECUTE=('mta.runtime_report_publication_source(mta.fresh_mta_runtimereportpublication)',)
CATALOGUE_NAMES=('mta.runtime_report_publication_source(p fresh_mta_runtimereportpublication)',)


def bodies():
    return (import_module('mta.runtime.migrations.0231_runtime_report_placement_guards').SOURCE,)


def application_functions(catalogue):
    """The pending_day_final dependency already belongs to the scoped profile."""
    functions={f['name']:f for f in catalogue['functions']}
    source=functions.get(CATALOGUE_NAMES[0])
    reference = import_module('mta.runtime.migrations.0255_postbtr_rationing_reference')
    if source is None or source['body'] not in (*bodies(), reference.SOURCE):
        return set()
    if (source.get('security_definer') is not False or source.get('returns') != 'boolean'
            or source.get('language') != 14 or source.get('configuration') != ['search_path=pg_catalog, mta']):
        raise ValueError('Exact placement consumer predicate required')
    return set(CATALOGUE_NAMES)


def migration_pins():
    return [[name,hashlib.sha256((Path(__file__).parent/'migrations'/(name+'.py')).read_bytes()).hexdigest()] for name in NAMES]


def require_preserved_acl(before,after,*,owner_oid,consumer_oid):
    """Preserve every old ACL row and permit exactly this new invoker grant."""
    source=[row for row in before if row['scope']=='function'
            and row['name']==CATALOGUE_NAMES[0] and row['grantee']==owner_oid]
    if len(source)!=1 or owner_oid==consumer_oid:
        raise ValueError('Consumer ACL baseline owner differs')
    owner=source[0]
    if (owner['owner']!=owner_oid or owner['grantor']!=owner_oid
            or owner['column'] is not None or owner['privilege']!='EXECUTE'
            or owner['grantable'] is not False):
        raise ValueError('Consumer ACL baseline grant differs')
    added=dict(owner,grantee=consumer_oid)
    if (added in before or after.count(added)!=1
            or [row for row in after if row!=added]!=before):
        raise ValueError('Consumer ACL transition changed an original or unrelated grant')


def require_specification(spec):
    if spec['migration_pins']!=migration_pins():raise ValueError('Exact consumer ACL migration bytes required')
    delta=spec['catalogue_delta']
    if not isinstance(delta,dict) or len(delta)!=1:raise ValueError('Only one consumer EXECUTE grant permitted')
    identities=set();names=set()
    for key,value in delta.items():
        after=value.get('after')
        if (value.get('before') is not None or type(after) is not dict
                or set(after)!={'scope','name','column','owner','grantor','grantee','privilege','grantable'}
                or after['scope']!='function' or after['name'] not in CATALOGUE_NAMES
                or after['column'] is not None or after['privilege']!='EXECUTE' or after['grantable'] is not False
                or after['owner']!=after['grantor'] or after['owner']==after['grantee']
                or any(not re.fullmatch(r'[a-z_][a-z0-9_]{0,62}',after[k]) for k in ('owner','grantee'))
                or key!='grants:'+after['name']+':None:'+after['grantor']+':'+after['grantee']+':EXECUTE'):
            raise ValueError('Consumer ACL delta differs from exact invoker read grants')
        identities.add((after['owner'],after['grantee']));names.add(after['name'])
    if len(identities)!=1 or names!=set(CATALOGUE_NAMES):raise ValueError('Consumer ACL owner/function roster differs')


def require_start(cursor):
    from mta.runtime.ingestion_ownership import migration_history_guard
    cursor.execute("SELECT max(name) FROM mta.django_migrations WHERE app='fresh_mta'")
    if cursor.fetchone()!=('0231_runtime_report_placement_guards',):
        raise ValueError('Consumer ACL transition requires exact0231 start')
    cursor.execute("SELECT to_regclass('fresh_control.ingestion_schema_compatibility')")
    if cursor.fetchone()==(None,):
        raise ValueError('Consumer ACL transition requires existing compatible-code authority')
    for name,body in zip(EXECUTE,bodies()):
        cursor.execute('SELECT prosrc,prosecdef,provolatile,proconfig FROM pg_proc WHERE oid=to_regprocedure(%s)',[name])
        if cursor.fetchone()!=(body,False,'s',['search_path=pg_catalog, mta']):
            raise ValueError('Consumer ACL predecessor predicate differs')
    if not migration_history_guard(cursor):raise ValueError('Consumer ACL migration history guard differs')


def approved_receipt(value):return value.get('migration_pins')==migration_pins()
