"""Native daily builders for the sealed prepared report occurrence bags.

These builders only materialize the joins already consumed by the prepared
readers.  They do not apply authorization, filters, hierarchy supplements, or
display defaults.  Source ordinals and typed values remain in source order.
"""
import hashlib

from django.db import connection, transaction

from mta.presentation.bpr_prepared_fields import (
    FIELDS as BPR_FIELDS, SOURCES as BPR_SOURCES,
    field_name as bpr_field_name, schema_digest as bpr_schema_digest,
)
from mta.presentation.guided_chronic_fields import (
    OUTPUTS as CHRONIC_OUTPUTS, SOURCES as CHRONIC_SOURCES,
    schema_digest as chronic_schema_digest,
)
from mta.presentation.guided_dbm_fields import (
    FIELDS as DBM_FIELDS, SOURCES as DBM_SOURCES,
    field_name as dbm_field_name, schema_digest as dbm_schema_digest,
)
from mta.presentation.guided_history_fields import (
    NATIVE_EXCESS_FIELDS, ROW_FIELDS as HISTORY_FIELDS,
    native_excess_schema_digest, schema_digest as history_schema_digest,
)
from mta.presentation.rrr_sql import equal, key
from mta.presentation.selective import image_field, image_metadata, image_query
from mta.runtime.models import (
    BprPreparedProjection, BprPreparedRow, CalculationRun, ExcessInventoryRow,
    GuidedAvailabilityHistoryRow, GuidedAvailabilitySnapshotReference,
    GuidedExcessHistoryRow, GuidedHistoryPreparedProjection,
    GuidedChronicPreparedProjection, GuidedChronicPreparedRow,
    GuidedDbmPreparedProjection, GuidedDbmPreparedRow,
)
from mta.runtime.relational_state import CATALOG, PG_TYPES, quote
from mta.serialization import canonical_parts, digest


BPR_ORDINALS = ('a_ordinal', 'v_ordinal', 's_ordinal', 'c_ordinal',
                'd_ordinal', 'b_ordinal')
BPR_ROW_FIELDS = ('ordinal', 'sku_key', 'location_key') + BPR_ORDINALS + tuple(
    bpr_field_name(owner, name)
    for owner, fields in BPR_FIELDS.items() for name in fields)
DBM_ORDINALS = ('a_ordinal', 's_ordinal', 'l_ordinal', 'p_ordinal', 'm_ordinal')
DBM_ROW_FIELDS = ('ordinal',) + DBM_ORDINALS + tuple(
    dbm_field_name(owner, name)
    for owner, fields in DBM_FIELDS.items() for name in fields)
CHRONIC_ORDINALS = ('a_ordinal', 'n_ordinal', 'l_ordinal', 's_ordinal', 'p_ordinal')
CHRONIC_ROW_FIELDS = ('ordinal',) + CHRONIC_ORDINALS + tuple(CHRONIC_OUTPUTS)


def production_recipe_digest(layer):
    """Stable identity of the native preparation recipe, separate from rows."""
    schemas = {
        'bpr': bpr_schema_digest(),
        'guided_history': dict(availability=history_schema_digest(), excess=native_excess_schema_digest()),
        'guided_dbm': dbm_schema_digest(),
        'guided_chronic': chronic_schema_digest(),
    }
    if layer not in schemas:
        raise ValueError('unknown_native_prepared_layer:' + str(layer))
    import inspect
    recipes = {
        'bpr': (_bpr_insert_query,),
        'guided_history': (_history_availability, _history_excess),
        'guided_dbm': (_dbm_insert_query,),
        'guided_chronic': (_chronic_insert_query,),
    }
    from mta.presentation import native_excess_history
    history_contract = inspect.getsource(native_excess_history) if layer == 'guided_history' else None
    return digest({'version': 1, 'layer': layer, 'history_contract': history_contract, 'schema_digest': schemas[layer],
                   'builder': inspect.getsource(__import__(__name__, fromlist=['prepare'])),
                   'queries': [inspect.getsource(function)
                               for function in recipes[layer]]})


def _fail(message):
    from mta.presentation.context import PublicationUnavailable
    raise PublicationUnavailable(message)


def _binding(run):
    from mta.presentation.daily_preparation import production_branch, source_digest
    if run is None or not production_branch(run):
        _fail('native_prepared_daily_publication_build_required')
    # This proves the completed day belongs to its initialized native chain;
    # report preparation alone must never turn an arbitrary calculation into a
    # production application source.
    from mta.presentation.native_publication import identity
    identity(run)
    return source_digest(run)


def _lock(run, source):
    CalculationRun.objects.select_for_update().get(pk=run.pk)
    from mta.presentation.daily_preparation import assert_unchanged
    assert_unchanged(run, source)


def _raw_equal(left, right):
    return ('(' + left + ' IS NULL)=(' + right + ' IS NULL) AND '
            "COALESCE(" + left + ",'')=COALESCE(" + right + ",'')")


def _exact(left, right):
    return left + ' = ' + right


def _stream_receipt(run, model, fields, *, order='ordinal', batch_size=1000,
                    require_dense=True):
    checksum = hashlib.sha256(b'[')
    count = 0
    columns = ','.join(quote(name) for name in fields)
    with connection.chunked_cursor() as cursor:
        cursor.execute('SELECT ' + columns + ' FROM ' + quote(model._meta.db_table) +
                       ' WHERE run_id=%s ORDER BY ' + order, [run.pk])
        while True:
            batch = cursor.fetchmany(batch_size)
            if not batch:
                break
            for row in batch:
                if require_dense and row[0] != count:
                    _fail(model._meta.label + '_ordinal_population_changed')
                if count:
                    checksum.update(b',')
                for part in canonical_parts(dict(zip(fields, row))):
                    checksum.update(part)
                count += 1
    checksum.update(b']')
    return count, checksum.hexdigest()


def _bpr_insert_query(run):
    ctes, params = [], []
    for owner, path in BPR_SOURCES.items():
        item = image_metadata(run, path)
        native = dict(CATALOG['tables'][item['table']])
        published = {name: PG_TYPES[native[column]]
                     for name, column, _ in item['fields']}
        for name, kind in BPR_FIELDS[owner].items():
            if published.get(name) != kind:
                _fail('BPR_prepared_source_field_type_changed:' + owner + '.' + name)
        sql, values = image_query(run, path)
        ctes.append(owner + ' AS NOT MATERIALIZED (' + sql + ')')
        params.extend(values)
    source_order = ','.join(owner + '.vf_ordinal' for owner in BPR_SOURCES)
    selected = ['%s', 'row_number() OVER (ORDER BY ' + source_order + ')-1',
                key('A."SKUCode"'), key('A."WhCode"')]
    selected += [owner + '.vf_ordinal' for owner in BPR_SOURCES]
    selected += [owner + '.' + quote(name)
                 for owner, fields in BPR_FIELDS.items() for name in fields]
    joins = ' FROM A'
    for owner, sku, location in (('V', 'SKUCode', 'WhCode'),
                                 ('S', 'SKUCode', 'WhCode'),
                                 ('C', 'SKUCode', None), ('D', None, 'WHCode'),
                                 ('B', 'SKUCode', 'LocCode')):
        conditions = []
        if sku:
            conditions.append(equal('A."SKUCode"', owner + '.' + quote(sku)))
        if location:
            conditions.append(equal('A."WhCode"', owner + '.' + quote(location)))
        joins += ' LEFT JOIN ' + owner + ' ON ' + ' AND '.join(conditions)
    columns = ','.join(quote(name) for name in ('run_id',) + BPR_ROW_FIELDS)
    return ('WITH ' + ','.join(ctes) + ' INSERT INTO ' +
            quote(BprPreparedRow._meta.db_table) + ' (' + columns + ') SELECT ' +
            ','.join(selected) + joins), params + [run.pk]


def _dbm_insert_query(run):
    ctes, params = [], []
    for owner, path in DBM_SOURCES.items():
        item = image_metadata(run, path)
        published = {name: {'str': 'text', 'int': 'bigint'}[wire]
                     for name, _, wire in item['fields'] if wire in ('str', 'int')}
        for name, kind in DBM_FIELDS[owner].items():
            if (kind == 'bigint' and published.get(name) == 'text' and
                    dict(CATALOG['tables'][item['table']]).get(name) in ('int', 'bigint') and
                    all(value is None for value in image_field(run, path, name))):
                published[name] = kind
            if published.get(name) != kind:
                _fail('Guided_DBM_prepared_source_field_type_changed:' + owner + '.' + name)
        sql, values = image_query(run, path)
        ctes.append(owner + ' AS NOT MATERIALIZED (' + sql + ')')
        params.extend(values)
    selected = ['%s', 'row_number() OVER (ORDER BY A.vf_ordinal,S.vf_ordinal,'
                'L.vf_ordinal,P.vf_ordinal NULLS FIRST,M.vf_ordinal)-1']
    selected += [owner + '.vf_ordinal' for owner in DBM_SOURCES]
    selected += [owner + '.' + quote(name)
                 for owner, fields in DBM_FIELDS.items() for name in fields]
    joins = (' FROM A JOIN S ON ' + _raw_equal('A."SKUCode"', 'S."SKUCode"') +
             ' JOIN L ON ' + _raw_equal('A."WhCode"', 'L."WHCode"') +
             ' LEFT JOIN P ON ' + _raw_equal('A."SKUCode"', 'P."SKUCode"') +
             ' AND ' + _raw_equal('A."WhCode"', 'P."LocCode"') +
             ' JOIN M ON ' + _raw_equal('A."SKUCode"', 'M."SKUCode"') +
             ' AND ' + _raw_equal('A."WhCode"', 'M."WhCode"'))
    columns = ','.join(quote(name) for name in ('run_id',) + DBM_ROW_FIELDS)
    return ('WITH ' + ','.join(ctes) + ' INSERT INTO ' +
            quote(GuidedDbmPreparedRow._meta.db_table) + ' (' + columns +
            ') SELECT ' + ','.join(selected) + joins), params + [run.pk]


def _chronic_insert_query(run):
    required = {
        'A': {'SKUCode': 'str', 'WhCode': 'str', 'ParentWhCode': 'str', 'RLT': 'int',
              'BRAge': 'int', 'PhysicalInventoryPen': 'str',
              'PhysicalInventoryColor': 'str', 'PipelineInventoryPen': 'str',
              'PipelineInventoryColor': 'str', 'RationedQty': 'int'},
        'N': {'SKUCode': 'str', 'WhCode': 'str', 'SKUDescription': 'str'},
        'L': {'WHCode': 'str'}, 'S': {'SKUCode': 'str'},
        'P': {'SKUCode': 'str', 'LocCode': 'str'},
    }
    ctes, params = [], []
    for owner, path in CHRONIC_SOURCES.items():
        item = image_metadata(run, path)
        published = {name: wire for name, _, wire in item['fields']}
        if item['count'] == 0:
            native = dict(CATALOG['tables'][item['table']])
            allowed = {'int': {'int', 'bigint'},
                       'str': {'nvarchar', 'varchar', 'nchar', 'xml', 'decimal',
                               'numeric', 'float', 'real'}}
            if any(native.get(name) not in allowed[wire]
                   for name, wire in required[owner].items()):
                _fail('Guided_Chronic_empty_source_schema_changed:' + owner)
            published = required[owner]
        if any(published.get(name) != wire for name, wire in required[owner].items()):
            _fail('Guided_Chronic_source_field_wire_changed:' + owner)
        sql, values = image_query(run, path)
        ctes.append(owner + ' AS NOT MATERIALIZED (' + sql + ')')
        params.extend(values)
    selected = ['%s', 'row_number() OVER (ORDER BY A.vf_ordinal,'
                'N.vf_ordinal NULLS FIRST,L.vf_ordinal NULLS FIRST,'
                'S.vf_ordinal NULLS FIRST,P.vf_ordinal NULLS FIRST)-1']
    selected += [owner + '.vf_ordinal' for owner in CHRONIC_SOURCES]
    selected += ['A."SKUCode"', 'N."SKUDescription"', 'A."WhCode"',
                 'A."ParentWhCode"', 'A."RLT"', 'A."BRAge"',
                 'A."PhysicalInventoryPen"::text', 'A."PhysicalInventoryColor"',
                 'A."PipelineInventoryPen"::text', 'A."PipelineInventoryColor"',
                 'A."RationedQty"']
    joins = (' FROM A LEFT JOIN N ON ' + _raw_equal('A."SKUCode"', 'N."SKUCode"') +
             ' AND ' + _raw_equal('A."WhCode"', 'N."WhCode"') +
             ' LEFT JOIN L ON ' + _raw_equal('A."WhCode"', 'L."WHCode"') +
             ' LEFT JOIN S ON ' + _raw_equal('A."SKUCode"', 'S."SKUCode"') +
             ' LEFT JOIN P ON ' + _raw_equal('A."SKUCode"', 'P."SKUCode"') +
             ' AND ' + _raw_equal('A."WhCode"', 'P."LocCode"'))
    columns = ','.join(quote(name) for name in ('run_id',) + CHRONIC_ROW_FIELDS)
    return ('WITH ' + ','.join(ctes) + ' INSERT INTO ' +
            quote(GuidedChronicPreparedRow._meta.db_table) + ' (' + columns +
            ') SELECT ' + ','.join(selected) + joins), params + [run.pk]


def _single_prepare(run, *, layer, row_model, receipt_model, fields, insert_query,
                    schema, guard, verify_only):
    if connection.vendor != 'postgresql':
        _fail(layer + '_native_preparation_requires_PostgreSQL')
    source = _binding(run)
    from mta.presentation.daily_preparation import assert_unchanged
    with transaction.atomic():
        guard(connection)
        if verify_only:
            assert_unchanged(run, source)
        else:
            _lock(run, source)
        receipt = receipt_model.objects.filter(run=run).first()
        if receipt is not None:
            if (receipt.source_digest, receipt.schema_digest) != (source, schema):
                _fail(layer + '_existing_binding_or_schema_changed')
            count, rows_digest = _stream_receipt(run, row_model, fields)
            if (receipt.row_count, receipt.rows_digest) != (count, rows_digest):
                _fail(layer + '_existing_complete_row_receipt_changed')
            created = False
        else:
            if verify_only:
                _fail(layer + '_prepared_receipt_missing')
            if row_model.objects.filter(run=run).exists():
                _fail(layer + '_unsealed_rows_exist')
            query, params = insert_query(run)
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                inserted = cursor.rowcount
            count, rows_digest = _stream_receipt(run, row_model, fields)
            if inserted != count:
                _fail(layer + '_insert_readback_population_changed')
            receipt = receipt_model.objects.create(
                run=run, source_digest=source, schema_digest=schema,
                rows_digest=rows_digest, row_count=count)
            created = True
        assert_unchanged(run, source)
        guard(connection)
    return {'status': 'PASS', 'source_digest': source,
            'recipe_digest': production_recipe_digest(layer),
            'rows_digest': receipt.rows_digest, 'row_count': receipt.row_count,
            'created': created}


def build_bpr(run):
    from mta.runtime.bpr_prepared_schema import verify_guards
    return _single_prepare(run, layer='bpr', row_model=BprPreparedRow,
        receipt_model=BprPreparedProjection, fields=BPR_ROW_FIELDS,
        insert_query=_bpr_insert_query, schema=bpr_schema_digest(),
        guard=verify_guards, verify_only=False)


def verify_bpr(run):
    from mta.runtime.bpr_prepared_schema import verify_guards
    return _single_prepare(run, layer='bpr', row_model=BprPreparedRow,
        receipt_model=BprPreparedProjection, fields=BPR_ROW_FIELDS,
        insert_query=_bpr_insert_query, schema=bpr_schema_digest(),
        guard=verify_guards, verify_only=True)


def build_guided_dbm(run):
    from mta.runtime.guided_dbm_schema import verify_guards
    return _single_prepare(run, layer='guided_dbm', row_model=GuidedDbmPreparedRow,
        receipt_model=GuidedDbmPreparedProjection, fields=DBM_ROW_FIELDS,
        insert_query=_dbm_insert_query, schema=dbm_schema_digest(),
        guard=verify_guards, verify_only=False)


def verify_guided_dbm(run):
    from mta.runtime.guided_dbm_schema import verify_guards
    return _single_prepare(run, layer='guided_dbm', row_model=GuidedDbmPreparedRow,
        receipt_model=GuidedDbmPreparedProjection, fields=DBM_ROW_FIELDS,
        insert_query=_dbm_insert_query, schema=dbm_schema_digest(),
        guard=verify_guards, verify_only=True)


def build_guided_chronic(run):
    from mta.runtime.guided_chronic_schema import verify_guards
    return _single_prepare(run, layer='guided_chronic', row_model=GuidedChronicPreparedRow,
        receipt_model=GuidedChronicPreparedProjection, fields=CHRONIC_ROW_FIELDS,
        insert_query=_chronic_insert_query, schema=chronic_schema_digest(),
        guard=verify_guards, verify_only=False)


def verify_guided_chronic(run):
    from mta.runtime.guided_chronic_schema import verify_guards
    return _single_prepare(run, layer='guided_chronic', row_model=GuidedChronicPreparedRow,
        receipt_model=GuidedChronicPreparedProjection, fields=CHRONIC_ROW_FIELDS,
        insert_query=_chronic_insert_query, schema=chronic_schema_digest(),
        guard=verify_guards, verify_only=True)



def _history_receipt(run, family, *, native_excess=False):
    if (native_excess and GuidedExcessHistoryRow.objects.filter(
            run=run, fact_run__isnull=True).exists()):
        _fail('guided_excess_history_fact_owner_missing')
    models = ((GuidedAvailabilityHistoryRow, HISTORY_FIELDS['availability']),
              (GuidedAvailabilitySnapshotReference, HISTORY_FIELDS['snapshot'])) \
             if family == 'availability' else \
             ((GuidedExcessHistoryRow,
               NATIVE_EXCESS_FIELDS if native_excess else HISTORY_FIELDS['excess']),)
    checksum = hashlib.sha256(b'[')
    rows = references = total = 0
    for model, fields in models:
        order = ('snapshot_anchor_ordinal,snapshot_ordinal'
                 if model is GuidedAvailabilitySnapshotReference else 'ordinal')
        with connection.chunked_cursor() as cursor:
            columns = [quote(field) + ('::text' if field == 'fact_run_id' else '')
                       for field in fields]
            cursor.execute('SELECT '+','.join(columns)+
                           ' FROM '+quote(model._meta.db_table)+
                           ' WHERE run_id=%s ORDER BY '+order, [run.pk])
            while True:
                batch = cursor.fetchmany(2000)
                if not batch:
                    break
                for row in batch:
                    if total:
                        checksum.update(b',')
                    for part in canonical_parts(dict(zip(fields, row))):
                        checksum.update(part)
                    total += 1
                    if model is GuidedAvailabilitySnapshotReference:
                        references += 1
                    else:
                        rows += 1
    checksum.update(b']')
    return rows, references, checksum.hexdigest()


def _history_availability(cursor, run):
    relations, params = {}, []
    for alias, path in (('a', 'closing/btr/BPR'),
                        ('s', 'closing/btr/SkuAttributeData'),
                        ('l', 'closing/btr/LocationAttributeData'),
                        ('p', 'closing/btr/SkuLocAttributeData'),
                        ('n', 'closing/btr/BTRSnapshotForUI')):
        query, values = image_query(run, path)
        relations[alias] = query
        params.extend(values)
    cursor.execute(
        'WITH a AS ('+relations['a']+'),s AS ('+relations['s']+'),l AS ('+relations['l']+
        '),p AS ('+relations['p']+'),n AS ('+relations['n']+'), anchors AS ('
        'SELECT n.*,min(n.vf_ordinal) OVER (PARTITION BY n."SKUCode",n."WhCode") anchor FROM n) '
        'INSERT INTO '+quote(GuidedAvailabilitySnapshotReference._meta.db_table)+
        ' (run_id,snapshot_anchor_ordinal,snapshot_ordinal,age_physical_inventory) '
        'SELECT %s,anchor,vf_ordinal,"AgePhysicalInv" FROM anchors', params + [run.pk])
    cursor.execute(
        'WITH a AS ('+relations['a']+'),s AS ('+relations['s']+'),l AS ('+relations['l']+
        '),p AS ('+relations['p']+'),n AS ('+relations['n']+'), anchors AS ('
        'SELECT "SKUCode","WhCode",min(vf_ordinal) anchor FROM n GROUP BY "SKUCode","WhCode"), joined AS ('
        'SELECT a.vf_ordinal fact_ordinal,s.vf_ordinal sku_ordinal,l.vf_ordinal location_ordinal,'
        'p.vf_ordinal pair_ordinal,anchors.anchor snapshot_anchor_ordinal,a."ReportDate" report_date,'
        'a."SKUCode" sku_code,a."WHCode" location_code,a."ParentWhCode" parent_location_code,'
        'l."LocationType" location_type,a."PhysicalInventoryColor" physical_inventory_color '
        'FROM a JOIN s ON '+_exact('a."SKUCode"','s."SKUCode"')+
        ' JOIN l ON '+_exact('a."WHCode"','l."WHCode"')+
        ' LEFT JOIN p ON '+_exact('a."SKUCode"','p."SKUCode"')+' AND '+_exact('a."WHCode"','p."LocCode"')+
        ' LEFT JOIN anchors ON '+_exact('a."SKUCode"','anchors."SKUCode"')+' AND '+_exact('a."WHCode"','anchors."WhCode"')+') '
        'INSERT INTO '+quote(GuidedAvailabilityHistoryRow._meta.db_table)+
        ' (run_id,ordinal,fact_ordinal,sku_ordinal,location_ordinal,pair_ordinal,snapshot_anchor_ordinal,'
        'report_date,sku_code,location_code,parent_location_code,location_type,physical_inventory_color) '
        'SELECT %s,row_number() OVER (ORDER BY fact_ordinal,sku_ordinal,location_ordinal,pair_ordinal NULLS FIRST)-1,* FROM joined',
        params + [run.pk])


def _history_excess(cursor, run, history):
    relations, params = {}, []
    for alias, path in (('s', 'closing/importer/SkuAttributeData'),
                        ('l', 'closing/importer/LocationAttributeData'),
                        ('p', 'closing/importer/SkuLocAttributeData')):
        query, values = image_query(run, path)
        relations[alias] = query
        params.extend(values)
    owners = [(item['run_id'], item['ordinal']) for item in history['lineage']]
    if not owners:
        return
    owner_values = ','.join(['(%s::uuid,%s::bigint)'] * len(owners))
    cursor.execute(
        'WITH s AS ('+relations['s']+'),l AS ('+relations['l']+'),p AS ('+relations['p']+
        '),owners(run_id,source_ordinal) AS (VALUES '+owner_values+'), joined AS ('
        'SELECT a.run_id fact_run_id,a.ordinal fact_ordinal,s.vf_ordinal sku_ordinal,l.vf_ordinal location_ordinal,'
        'p.vf_ordinal pair_ordinal,a."ReportDate" report_date,a."SKUCode" sku_code,a."WhCode" location_code,'
        'a."ParentWhCode" parent_location_code,l."LocationType" location_type,'
        'a."PhysicalInventoryColor" physical_inventory_color,a."Amount" amount,owners.source_ordinal FROM owners JOIN '+
        quote(ExcessInventoryRow._meta.db_table)+' a ON a.run_id=owners.run_id JOIN s ON '+_exact('a."SKUCode"','s."SKUCode"')+
        ' JOIN l ON '+_exact('a."WhCode"','l."WHCode"')+
        ' LEFT JOIN p ON '+_exact('a."SKUCode"','p."SKUCode"')+' AND '+_exact('a."WhCode"','p."LocCode"')+
        ' WHERE a."ReportDate">%s) INSERT INTO '+quote(GuidedExcessHistoryRow._meta.db_table)+
        ' (run_id,ordinal,fact_run_id,fact_ordinal,sku_ordinal,location_ordinal,pair_ordinal,report_date,sku_code,'
        'location_code,parent_location_code,location_type,physical_inventory_color,amount) '
        'SELECT %s,row_number() OVER (ORDER BY report_date,source_ordinal DESC,fact_ordinal,sku_ordinal,'
        'location_ordinal,pair_ordinal NULLS FIRST)-1,fact_run_id,fact_ordinal,sku_ordinal,location_ordinal,'
        'pair_ordinal,report_date,sku_code,location_code,parent_location_code,location_type,'
        'physical_inventory_color,amount FROM joined',
        params + [value for owner in owners for value in owner] +
        [history['storage_cutoff'], run.pk])


def _prepare_guided_history(run, *, verify_only):
    if connection.vendor != 'postgresql':
        _fail('guided_history_native_preparation_requires_PostgreSQL')
    daily_source = _binding(run)
    from mta.presentation import native_excess_history
    history = native_excess_history.identity(run, verify_rows=True)
    source = native_excess_history.source_digest(daily_source, history)
    from mta.runtime.guided_history_schema import verify_guards
    from mta.presentation.daily_preparation import assert_unchanged
    with transaction.atomic():
        verify_guards(connection)
        if verify_only:
            assert_unchanged(run, daily_source)
        else:
            _lock(run, daily_source)
        receipts = {item.family: item
                    for item in GuidedHistoryPreparedProjection.objects.filter(run=run)}
        if receipts:
            if set(receipts) != {'availability', 'excess'}:
                _fail('guided_history_incomplete_receipt_set')
            created = False
        else:
            if verify_only:
                _fail('guided_history_prepared_receipts_missing')
            if (GuidedAvailabilityHistoryRow.objects.filter(run=run).exists() or
                    GuidedAvailabilitySnapshotReference.objects.filter(run=run).exists() or
                    GuidedExcessHistoryRow.objects.filter(run=run).exists()):
                _fail('guided_history_unsealed_rows_exist')
            with connection.cursor() as cursor:
                cursor.execute("SELECT set_config('fresh.guided_history_build',%s,true)",
                               [str(run.pk)])
                _history_availability(cursor, run)
                _history_excess(cursor, run, history)
            receipts = {}
            for family in ('availability', 'excess'):
                count, references, rows_digest = _history_receipt(
                    run, family, native_excess=(family == 'excess'))
                receipts[family] = GuidedHistoryPreparedProjection.objects.create(
                    run=run, family=family,
                    source_digest=(source if family == 'excess' else daily_source),
                    schema_digest=(native_excess_schema_digest()
                                   if family == 'excess' else history_schema_digest()),
                    rows_digest=rows_digest,
                    row_count=count, reference_count=references)
            created = True
        families = {}
        for family, receipt in receipts.items():
            count, references, rows_digest = _history_receipt(
                run, family, native_excess=(family == 'excess'))
            actual = (receipt.source_digest, receipt.schema_digest,
                      receipt.row_count, receipt.reference_count, receipt.rows_digest)
            expected = ((source if family == 'excess' else daily_source),
                        (native_excess_schema_digest() if family == 'excess'
                         else history_schema_digest()), count, references, rows_digest)
            if actual != expected:
                _fail('guided_history_existing_receipt_changed:' + family)
            families[family] = {'row_count': count, 'reference_count': references,
                                'rows_digest': rows_digest}
        assert_unchanged(run, daily_source)
        verify_guards(connection)
    return {'status': 'PASS', 'source_digest': daily_source,
            'recipe_digest': production_recipe_digest('guided_history'),
            'rows_digest': digest(families),
            'row_count': sum(item['row_count'] for item in families.values()),
            'families': families, 'created': created}


def build_guided_history(run):
    return _prepare_guided_history(run, verify_only=False)


def verify_guided_history(run):
    return _prepare_guided_history(run, verify_only=True)


BUILDERS = {
    'bpr': (build_bpr, verify_bpr),
    'guided_history': (build_guided_history, verify_guided_history),
    'guided_dbm': (build_guided_dbm, verify_guided_dbm),
    'guided_chronic': (build_guided_chronic, verify_guided_chronic),
}


def prepare(run, name, *, verify_only=False):
    """Build or verify one named native prepared layer."""
    try:
        functions = BUILDERS[name]
    except KeyError as exc:
        raise ValueError('unknown_native_prepared_layer:' + str(name)) from exc
    return functions[1 if verify_only else 0](run)
