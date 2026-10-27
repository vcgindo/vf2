"""Finite 0232 -> 0237 upgrade of a certified, not-yet-used initialization.

Original certificates and producer identities remain immutable. Consumed
installations need their own complete preservation proof; this profile never
implicitly admits them. Existing-reference read compatibility is independent.
"""
import hashlib
import re
from pathlib import Path

NAMES = ('0233_report_definition_registration', '0234_report_definition_guards',
         '0235_registered_scope_read_attachment', '0236_intake_diagnostic_custody',
         '0237_intake_diagnostic_guards')
# Complete 514-entry native rollback observation, including bootstrap authority,
# columns, constraints, indexes, trigger bodies/bindings and exact read grants.
CATALOGUE_DELTA_DIGEST = '2583f7a6de79f0ea5961e689c1511fb0c48e49c7dd2ac658371d19b1ec65f8ad'


def catalogue_contract(delta):
    from mta.serialization import digest
    owner = delta['functions:mta.ingestion_watch()']['before']['owner']
    consumers = [item['after']['grantee'] for name, item in delta.items()
        if name.startswith('grants:mta.fresh_mta_reportdefinitionregistration:')
        and item['after']['privilege'] == 'SELECT'
        and item['after']['grantee'] not in (owner, 'fresh_operational_acceptor')]
    if (len(consumers) != 1 or owner == consumers[0]
            or any(not re.fullmatch(r'[a-z_][a-z0-9_]{0,62}', role)
                   for role in (owner, *consumers))):
        raise ValueError('Exact registered report owner and read-only consumer required')
    mapping = {owner: '<namespace-owner>', consumers[0]: '<namespace-consumer>'}
    def normalized(value):
        if isinstance(value, dict):
            return {normalized(k): normalized(v) for k, v in value.items()}
        if isinstance(value, list):
            return [normalized(v) for v in value]
        if isinstance(value, str):
            if value in mapping:
                return mapping[value]
            if value.startswith('grants:'):
                return ':'.join(mapping.get(part, part) for part in value.split(':'))
        return value
    return digest(normalized(delta))


def migration_pins():
    root = Path(__file__).parent / 'migrations'
    return [[name, hashlib.sha256((root / (name + '.py')).read_bytes()).hexdigest()]
            for name in NAMES]


def require_specification(spec):
    if spec['migration_pins'] != migration_pins():
        raise ValueError('Exact registered report migration bytes required')
    try:
        matches = (CATALOGUE_DELTA_DIGEST is not None
                   and catalogue_contract(spec['catalogue_delta']) == CATALOGUE_DELTA_DIGEST)
    except (KeyError, TypeError, ValueError):
        matches = False
    if not matches:
        raise ValueError('Exact reviewed registered report catalogue/guards/ACLs required')


def require_start(cursor):
    from importlib import import_module
    from mta.runtime.ingestion_ownership import migration_history_guard
    placement = import_module('mta.runtime.migrations.0231_runtime_report_placement_guards')
    publication = import_module('mta.runtime.migrations.0230_runtime_report_publication_guards')
    cursor.execute("SELECT max(name) FROM mta.django_migrations WHERE app='fresh_mta'")
    if cursor.fetchone() != ('0232_runtime_report_consumer_read',):
        raise ValueError('Registered report upgrade requires exact0232 start')
    cursor.execute("SELECT to_regclass('fresh_control.ingestion_schema_compatibility')")
    if cursor.fetchone() != (None,):
        raise ValueError('Registered report upgrade requires unextended0232 namespace')
    for name, body in (
            ('mta.ingestion_watch()', placement.NEW),
            ('mta.guard_scope_read_reference()', publication.READ_REFERENCE_BODY),
            ('mta.runtime_report_publication_source(mta.fresh_mta_runtimereportpublication)', placement.SOURCE)):
        cursor.execute('SELECT prosrc FROM pg_proc WHERE oid=to_regprocedure(%s)', [name])
        if cursor.fetchone() != (body,):
            raise ValueError('Registered report predecessor guard differs')
    if not migration_history_guard(cursor):
        raise ValueError('Registered report migration history guard differs')
    # Deliberately qualify only the released unused-initialization boundary.
    # The generic preservation helper's CSV-run filter cannot certify JSON runs.
    for table in ('fresh_mta_calculationrun', 'fresh_mta_dailyfeedattempt',
                  'fresh_mta_mdmdailyinputcapture'):
        cursor.execute('SELECT EXISTS(SELECT 1 FROM mta.' + table + ')')
        if cursor.fetchone() != (False,):
            raise ValueError('Registered report upgrade requires no prior run/attempt/capture')


def approved_receipt(value):
    return value.get('migration_pins') == migration_pins()
