"""One approved late BPR effect, with immutable typed rows and exact reuse.

The accepted BPR receipt and calculation snapshot remain unchanged. This owner
records when their omitted history effect was actually completed.
"""
import inspect
from django.db import connection, transaction
from mta.application import operational_bor
from mta.runtime import production_report_storage as reports
from mta.runtime import relational_state as typed
from mta.serialization import digest, storage

NAMES = ('BOR_OrderAllocationHistory', 'RRR_OrderAllocationHistory')
TABLES = {name: 'bpr_history/' + name for name in NAMES}
REGISTRY = {TABLES[name]: reports.TABLES['production/' + name] for name in NAMES}
AUTHORITY = dict(
    schema='fresh-late-bpr-history-test-v1',
    decision='call_018484042fc542ebab4ab493e37e00cb/0',
    run='e0735ad3-b98d-45c5-9bad-38bc5b0e5df8',
    phase='486ffe8a-ae78-4de9-90e5-0f01eb6ede97',
    phase_digest='863bcc7fd80bd4089bee87142afddc5fe1d8d1da840f099819e5efe9f486006d',
    snapshot_digest='2a06bf63b58ed68f1833f2e30ba18b471266b4c30051db3cfcb07b427fcea3ed',
    predecessor='ee2c37c6-923f-47f8-adc2-992a65dbb8dd',
    predecessor_digest='aebfa2e10b0d7c6b9ae491f3a11bd21799d5d5647bd200e62bb2410cace1561c',
    input_digest='faae0afaf12f9796d81645df25b34531943581a2a7ef2a8a01a45cdeb2c1d9b2',
    sources={
        NAMES[0]: dict(opening_digest='ecb160e444eed60fbe8b246a76138cf55f4db8980851d006a36ee0e727e805fb',
            current_digest='eee626b5c6a3f076443522ca89aa49a3f900bc60fb43207056bba0c5064b0d21'),
        NAMES[1]: dict(opening_digest='56f63db93ef9f3ecf944f3146237ea720bc8b7cb386f0c7f035ed40895dcfec9',
            current_digest='8c74f5acc00acff4c08ecc30d6c068481fdd63b874d9ba4b936d262b5cfd5623')},
    policy={'bor_history_horizon': 90, 'rrr_history_horizon': 90},
    expected={
        NAMES[0]: {'count': 8, 'digest': '2fbd681a26d579d928a7d10471d0d9c1ba454df009f375ec3b1cd2f9043e69e7'},
        NAMES[1]: {'count': 10, 'digest': 'fe1c69b8fab1fb05b1b1fdac9ed2dbdb5a6fe6ef41e32e7f11956194af43cfc0'}})


def recipe_digest():
    return digest(dict(schema=AUTHORITY['schema'], registry=REGISTRY,
        adapter=inspect.getsource(inspect.getmodule(project)),
        canonical=inspect.getsource(operational_bor)))


def verify_guards():
    """Read/write admission rejects disabled or replaced completion guards."""
    from importlib import import_module
    migration = import_module('mta.runtime.migrations.0223_bpr_history_completion')
    with connection.cursor() as cursor:
        for name in ('guard_bpr_history_completion', 'guard_bpr_history_rows', 'require_bpr_history_complete', 'deny_bpr_history_truncate'):
            expected = migration.GUARD_SQL.split('FUNCTION mta.' + name + '()', 1)[1].split('$body$', 2)[1]
            cursor.execute("""SELECT P.prosrc,P.prosecdef,P.proconfig,L.lanname,
                P.proowner=T.relowner FROM pg_proc P JOIN pg_language L ON L.oid=P.prolang
                CROSS JOIN pg_class T WHERE P.oid=to_regprocedure(%s)
                AND T.oid='mta.fresh_mta_bprhistorycompletion'::regclass""", ['mta.' + name + '()'])
            if cursor.fetchone() != (expected, False, ['search_path=pg_catalog, mta'], 'plpgsql', True):
                raise ValueError('Late BPR history guard definition differs')
        required = {
            'mta.fresh_mta_bprhistorycompletion': {
                'bpr_history_owner': ('guard_bpr_history_completion', 31, False, False, b''),
                'bpr_history_complete': ('require_bpr_history_complete', 21, True, True, b''),
                'bpr_history_no_truncate': ('deny_bpr_history_truncate', 34, False, False, b'')},
        }
        for name in NAMES:
            required[typed.table_sql(TABLES[name])] = {
                'bpr_history_rows': ('guard_bpr_history_rows', 31, False, False, (reports.PATHS[name] + '\0').encode()),
                'bpr_history_no_truncate': ('deny_bpr_history_truncate', 34, False, False, b'')}
        for table, triggers in required.items():
            cursor.execute("""SELECT T.tgname,P.proname,T.tgtype,T.tgdeferrable,T.tginitdeferred,T.tgargs
                FROM pg_trigger T JOIN pg_proc P ON P.oid=T.tgfoid JOIN pg_namespace N ON N.oid=P.pronamespace
                WHERE T.tgrelid=to_regclass(%s) AND NOT T.tgisinternal AND T.tgenabled='O' AND N.nspname='mta'""", [table])
            actual = {name: (fn, kind, deferred, initial, bytes(args))
                      for name, fn, kind, deferred, initial, args in cursor.fetchall()}
            if any(actual.get(name) != expected for name, expected in triggers.items()):
                raise ValueError('Late BPR history guard coverage differs')


def project(opening, current, business_date, policy):
    """Canonical retention and append; preserves types, NULLs and occurrences."""
    return {
        NAMES[0]: operational_bor.collect_bor_order_allocation_history(
            opening_history=opening[NAMES[0]], current_bor=current['BORWithOrderAllocation'],
            business_date=business_date, horizon=policy['bor_history_horizon']),
        NAMES[1]: operational_bor.collect_rrr_order_allocation_history(
            opening_history=opening[NAMES[1]], current_rrr=current['RRR_OrderAllocation'],
            business_date=business_date, horizon=policy['rrr_history_horizon'])}


def _save(run, name, rows):
    table = TABLES[name]
    expected = [column['name'] for column in operational_bor.NATIVE_SCHEMAS[name]]
    if any(list(row) != expected for row in rows):
        raise ValueError('Late BPR history field order differs')
    rows = storage(rows)
    columns = {key.casefold(): (key, kind) for key, kind in REGISTRY[table]}
    meta, fields, native = typed.describe_rows(rows, columns, reports.PATHS[name])
    meta['table'] = table
    if rows:
        sql = ('INSERT INTO ' + typed.table_sql(table) +
            ' (vf_run_id,vf_image,vf_ordinal,' + ','.join(typed.quote(n) for n, _ in native) +
            ') VALUES (' + ','.join(['%s'] * (len(native) + 3)) + ')')
        typed.bulk(sql, ((run.pk, meta['image'], ordinal,
            *[typed.db_value(row[field], kind) for field, (_, kind) in zip(fields, native)])
            for ordinal, row in enumerate(rows)))
    if typed.load_image(run, meta, table_registry=REGISTRY) != rows:
        raise ValueError('Late BPR history typed readback differs')
    return meta


def _digest(receipt):
    return digest(dict(run=str(receipt.run_id), phase=str(receipt.phase_id),
        predecessor=str(receipt.predecessor_id), input_digest=receipt.input_digest,
        phase_digest=receipt.phase_digest, snapshot_digest=receipt.snapshot_digest,
        predecessor_digest=receipt.predecessor_digest, recipe_digest=receipt.recipe_digest,
        authority=receipt.authority, images=receipt.images))


def _identity(run, phase):
    from mta.runtime.scope_execution import receipt_digest
    if (str(run.pk) != AUTHORITY['run'] or run.input_digest != AUTHORITY['input_digest']
            or str(phase.pk) != AUTHORITY['phase']
            or phase.run_id != run.pk or phase.phase != 'BPR' or not phase.state_sealed
            or phase.digest != AUTHORITY['phase_digest'] or phase.digest != receipt_digest(phase)
            or phase.input_digest != run.input_digest
            or phase.snapshot.state_digest != AUTHORITY['snapshot_digest']
            or phase.snapshot.state_digest != digest(phase.snapshot.manifest)
            or phase.snapshot.run_id != run.pk or phase.snapshot.acceptance_id != phase.pk
            or str(run.predecessor_id) != AUTHORITY['predecessor']
            or run.predecessor.output_digest != AUTHORITY['predecessor_digest']
            or run.predecessor.status != 'SUCCEEDED'
            or run.predecessor.business_date >= run.business_date):
        raise ValueError('Late BPR history approved owner differs')


def complete(run_id):
    """Installer-only, one atomic late effect. Repeated calls verify and reuse."""
    from mta.runtime.production_scope import authorize
    from mta.runtime.scope_runtime_reports import require_test_database
    from mta.runtime.models import CalculationRun, RunPhaseAcceptance, BprHistoryCompletion
    from mta.runtime.scope_execution import head
    from mta.runtime.input_reader import read_input
    from mta.runtime import phase_state
    authorize()
    require_test_database()
    verify_guards()
    with transaction.atomic():
        run = CalculationRun.objects.select_for_update(of=('self',)).select_related('predecessor').get(pk=run_id)
        phase = RunPhaseAcceptance.objects.select_related('snapshot').get(run=run, phase='BPR')
        _identity(run, phase)
        if BprHistoryCompletion.objects.filter(run=run).exists():
            return verified(run)
        if (run.status != 'RUNNING' or run.output_digest or head(run.pk) != ('BPR', phase.digest)
                or run.scope_attempts.filter(status='ACTIVE').exists()):
            raise ValueError('Late BPR history requires an idle accepted BPR head')
        day = read_input(run, components=('day',))['day']
        if (day['production_report_policy'] != AUTHORITY['policy']
                or day['production_report_opening'] is not None
                or day['production_report_schema'] != 'fresh-production-source-inputs-v1'):
            raise ValueError('Late BPR history captured policy differs')
        current = {}
        for name in ('BORWithOrderAllocation', 'RRR_OrderAllocation'):
            image = phase.snapshot.manifest['consumers']['production_reports'][name]['image']
            current[name] = typed.load_image(run, phase.snapshot.manifest['images'][image],
                                             table_registry=phase_state.REGISTRY)
        opening = {name: reports.read(run.predecessor, name) for name in NAMES}
        for name, current_name in zip(NAMES, ('BORWithOrderAllocation', 'RRR_OrderAllocation')):
            if dict(opening_digest=digest(opening[name]), current_digest=digest(current[current_name])) != AUTHORITY['sources'][name]:
                raise ValueError('Late BPR history source identity differs')
        values = project(opening, current, run.business_date.isoformat(), day['production_report_policy'])
        if {name: dict(count=len(rows), digest=digest(rows)) for name, rows in values.items()} != AUTHORITY['expected']:
            raise ValueError('Late BPR history differs from approved canonical projection')
        receipt = BprHistoryCompletion.objects.create(run=run, phase=phase,
            predecessor=run.predecessor, input_digest=run.input_digest, phase_digest=phase.digest,
            snapshot_digest=phase.snapshot.state_digest, predecessor_digest=run.predecessor.output_digest,
            recipe_digest=recipe_digest(), authority=AUTHORITY)
        receipt.images = {reports.PATHS[name]: _save(run, name, values[name]) for name in NAMES}
        receipt.digest = _digest(receipt)
        receipt.state_sealed = True
        receipt.save(update_fields=('images', 'digest', 'state_sealed'))
        return verified(run)


def verified(run):
    from mta.runtime.models import BprHistoryCompletion
    verify_guards()
    receipt = BprHistoryCompletion.objects.select_related('phase__snapshot').get(run=run)
    _identity(run, receipt.phase)
    if (not receipt.state_sealed or receipt.input_digest != run.input_digest
            or receipt.phase_digest != receipt.phase.digest
            or receipt.snapshot_digest != receipt.phase.snapshot.state_digest
            or receipt.predecessor_id != run.predecessor_id
            or receipt.predecessor_digest != run.predecessor.output_digest
            or receipt.authority != AUTHORITY or receipt.recipe_digest != recipe_digest()
            or receipt.digest != _digest(receipt)
            or set(receipt.images) != {reports.PATHS[name] for name in NAMES}):
        raise ValueError('Late BPR history completion identity differs')
    for name in NAMES:
        item = receipt.images[reports.PATHS[name]]
        if (item['table'] != TABLES[name] or item['image'] != reports.PATHS[name]
                or {key: item[key] for key in ('count', 'digest')} != AUTHORITY['expected'][name]):
            raise ValueError('Late BPR history image identity differs')
        typed.load_image(run, item, table_registry=REGISTRY)
    return receipt


def terminal_completion(run):
    """This approved run must never silently use the ordinary terminal append."""
    from mta.runtime.models import BprHistoryCompletion
    if str(run.pk) == AUTHORITY['run'] or BprHistoryCompletion.objects.filter(run=run).exists():
        return verified(run)
    return None


def published_images(receipt):
    return {path: dict(item, completion=dict(run=str(receipt.run_id), digest=receipt.digest))
            for path, item in receipt.images.items()}


def publish(run, values, opening, completion):
    """Save current populations; reference history already completed before DBM."""
    from mta.presentation.production_reports import recipe_digest as report_recipe
    from mta.runtime.scoped_final import require_pending_final
    require_pending_final(run)
    receipt = verified(run)
    if receipt.pk != completion.pk or receipt.digest != completion.digest:
        raise ValueError('Terminal BPR history completion differs')
    if (opening['production_report_policy'] != AUTHORITY['policy']
            or opening['production_report_opening'] is not None
            or opening['production_report_schema'] != 'fresh-production-source-inputs-v1'
            or set(values) != {'BORWithOrderAllocation', 'RRR_OrderAllocation', 'AllocatedOrders', 'BOROARequirement'}):
        raise ValueError('Terminal BPR history sources differ')
    # The original BPR populations, not later DBM data, own these histories.
    manifest = receipt.phase.snapshot.manifest
    for name, rows in values.items():
        item = manifest['images'][manifest['consumers']['production_reports'][name]['image']]
        if len(rows) != item['count'] or digest(rows) != item['digest']:
            raise ValueError('Terminal allocation rows differ from accepted BPR')
    images = published_images(receipt)
    for name, rows in values.items():
        item = reports.save(run, name, rows, expanded=False)
        item['producer'] = dict(recipe_digest=report_recipe(), policy=opening['production_report_policy'],
            input_digest=run.input_digest, business_date=run.business_date.isoformat(),
            predecessor_id=str(run.predecessor_id), predecessor_output_digest=run.predecessor.output_digest,
            supplier_opening_digest=digest(opening['supplier']))
        images[reports.PATHS[name]] = item
    return images


def read_published(run, path, item):
    receipt = verified(run)
    if published_images(receipt).get(path) != item:
        raise ValueError('Published BPR history differs from its completion')
    return typed.load_image(run, item, table_registry=REGISTRY)
