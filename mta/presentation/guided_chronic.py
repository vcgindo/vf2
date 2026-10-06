"""Prepared occurrence reader for the fixture Chronic grid only."""
from django.conf import settings
from django.db import connection, transaction

from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation.guided_chronic_fields import OUTPUTS, SOURCES, schema_digest
from mta.presentation.insight_filters import InsightPredicate, unavailable
from mta.presentation.rrr_sql import Filters, equal
from mta.presentation.selective import image_metadata, image_query, image_rows
from mta.runtime.guided_chronic_schema import verify_guards
from mta.runtime.models import GuidedChronicPreparedProjection, GuidedChronicPreparedRow
from mta.runtime.relational_state import quote, wire_value


OWNERS = {'_a': ('A', 'a_ordinal'), '_description': ('N', 'n_ordinal'),
          '_location': ('L', 'l_ordinal'), '_sku': ('S', 's_ordinal'),
          '_pair': ('P', 'p_ordinal')}
STORED_A = {'SKUCode': 'skucode', 'WhCode': 'location', 'ParentWhCode': 'parentloc',
            'RLT': 'RLT', 'BRAge': 'BlackRedAgeing',
            'PhysicalInventoryPen': 'PhysicalInventoryPen', 'PhysicalInventoryColor': 'Techcolor',
            'PipelineInventoryPen': 'PipelineInventoryPen', 'PipelineInventoryColor': 'ecocolor',
            'RationedQty': 'RationedStockatparent'}


def raw_equal(left, right):
    return ('((' + left + ' IS NULL)=(' + right + ' IS NULL) AND COALESCE(' +
            left + ",'')=COALESCE(" + right + ",''))")


def referenced_owners(terms):
    result = set()
    def visit(node):
        if node[0] == 'or':
            for child in node[1]: visit(child)
        else: result.add(node[1][0])
    for term in terms: visit(term)
    return result


def _prepared_query(run):
    return ('SELECT * FROM ' + quote(GuidedChronicPreparedRow._meta.db_table) +
            ' WHERE run_id=%s'), [run.pk]


def build_query(run, payload, attributes):
    predicate = InsightPredicate(payload, attributes['LocationAttributeData'], kind='chronic-grid')
    products, locations = scope(payload, attributes=attributes)
    if not products or not locations: return None, [], []
    ctes, params, wires = [], [], {}
    query, values = _prepared_query(run)
    ctes.append('prepared AS NOT MATERIALIZED (' + query + ')'); params.extend(values)
    owners = referenced_owners(predicate.sql_terms)
    # A's normal grid filter fields are already stored. Only an unexpected but
    # validated non-output A field earns an ordinal source join.
    a_fields = set()
    def collect(node):
        if node[0] == 'or':
            for child in node[1]: collect(child)
        elif node[1][0] == '_a': a_fields.add(node[1][1])
    for term in predicate.sql_terms: collect(term)
    if all(any(field.casefold() == stored.casefold() for stored in STORED_A)
           for field in a_fields): owners.discard('_a')
    joins = ' FROM prepared R'
    for owner in ('_a', '_description', '_location', '_sku', '_pair'):
        if owner not in owners: continue
        source, ordinal = OWNERS[owner]; path = SOURCES[source]
        item = image_metadata(run, path); query, values = image_query(run, path)
        ctes.append(source + ' AS NOT MATERIALIZED (' + query + ')'); params.extend(values)
        wires[owner] = {name: wire for name, _, wire in item['fields']}
        joins += ' LEFT JOIN ' + source + ' ON ' + source + '.vf_ordinal=R.' + ordinal

    class Compiler(Filters):
        def column(self, owner, field):
            if owner == '_a':
                stored = next((value for name, value in STORED_A.items()
                               if name.casefold() == field.casefold()), None)
                if stored is not None:
                    wire = OUTPUTS[stored]
                    expression = 'R.' + quote(stored)
                    return expression + ('::text' if wire == 'text' else ''), \
                           ('text' if wire == 'text' else 'int')
            source, _ = OWNERS[owner]
            actual = next((name for name in wires[owner] if name.casefold() == field.casefold()), None)
            if actual is None: raise PublicationUnavailable('Guided_Chronic_prepared_filter_field_missing')
            wire = wires[owner][actual]; expression = source + '.' + quote(actual)
            return expression + ('::text' if wire == 'str' else ''), ('text' if wire == 'str' else wire)
    compiler = Compiler({})
    def compile_term(node):
        if node[0] == 'or': return '(' + ' OR '.join(compile_term(child) for child in node[1]) + ')'
        if node[0] == 'in':
            expression, _ = compiler.column(*node[1]); compiler.params.extend(node[2])
            return '(' + ' OR '.join(equal(expression, '%s') for _ in node[2]) + ')'
        return compiler.compare(*node[1], node[2], node[3])
    try: where = ' AND '.join(compile_term(term) for term in predicate.sql_terms) or 'TRUE'
    except PublicationUnavailable as exc: unavailable(str(exc).partition(':')[2])

    for alias, codes in (('AUTH_P', products), ('AUTH_L', locations)):
        ordered = sorted(codes, key=lambda value: (value is not None, str(value)))
        ctes.append(alias + '(code,weight) AS (VALUES ' + ','.join(['(%s::text,%s::bigint)'] * len(codes)) + ')')
        params.extend(value for code in ordered for value in (code, codes.multiplicities[code]))
    joins += (' JOIN AUTH_P ON ' + raw_equal('R.skucode', 'AUTH_P.code') +
              ' JOIN AUTH_L ON ' + raw_equal('R.location', 'AUTH_L.code'))
    if predicate.children:
        if 'L' not in {OWNERS[owner][0] for owner in owners}:
            item = image_metadata(run, SOURCES['L']); query, values = image_query(run, SOURCES['L'])
            ctes.append('L AS NOT MATERIALIZED (' + query + ')'); params.extend(values)
        joins += (' JOIN L parent ON ' + equal('R.parentloc', 'parent."WHCode"') + ' AND (' +
                  ' OR '.join(equal('parent."LocationType"', '%s') for _ in predicate.children) + ')')
        params.extend(predicate.children)
    params.extend(compiler.params)
    selected = ','.join('R.' + quote(name) + ' AS ' + quote(name) for name in OUTPUTS)
    selected += ',AUTH_P.weight*AUTH_L.weight AS _copies'
    sql = ('WITH ' + ','.join(ctes) + ' SELECT ' + selected + joins +
           ' WHERE ' + where + ' ORDER BY R.ordinal')
    return sql, params, [('skucode','str'),('skudesc','str'),('location','str'),('parentloc','str'),
        ('RLT','int'),('BlackRedAgeing','int'),('PhysicalInventoryPen','str'),('Techcolor','str'),
        ('PipelineInventoryPen','str'),('ecocolor','str'),('RationedStockatparent','int'),('_copies','int')]


def read_guided_chronic(run, payload):
    from mta.presentation.daily_preparation import production_branch
    daily = production_branch(run)
    if getattr(run, 'kind', None) != 'LEGACY_UI_FIXTURE' and not daily: raise ValueError('guided_chronic_admitted_run_required')
    if not daily and not getattr(settings, 'VF_GUIDED_PREPARED', False):
        raise PublicationUnavailable('Guided_prepared_trial_disabled')
    from mta.presentation import fixture, hierarchy
    try: manifest = hierarchy.selected_manifest(run)
    except hierarchy.HierarchyUnavailable as exc: raise PublicationUnavailable(str(exc)) from exc
    if manifest:
        raise PublicationUnavailable('chronic_SQL_hierarchy_supplement_not_bound')
    if daily:
        from mta.presentation.daily_preparation import source_digest
        selected, source = run, source_digest(run)
    else:
        selected, source = fixture.binding()
    receipt = GuidedChronicPreparedProjection.objects.filter(run_id=run.pk).first()
    if selected.pk != run.pk or receipt is None or receipt.source_digest != source or receipt.schema_digest != schema_digest():
        raise PublicationUnavailable('Guided_Chronic_prepared_receipt_missing_or_changed')
    try: verify_guards(connection)
    except ValueError as exc: raise PublicationUnavailable('Guided_Chronic_prepared_guards_changed') from exc
    attributes = {name: image_rows(run, 'closing/btr/' + name)
                  for name in ('SkuAttributeData', 'LocationAttributeData')}
    query, params, outputs = build_query(run, payload, attributes)
    if query is None: return []
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('jit')"); previous_jit = cursor.fetchone()[0]
        cursor.execute('SET LOCAL jit=off'); cursor.execute(query, params); records = cursor.fetchall()
        cursor.execute("SELECT set_config('jit',%s,true)", [previous_jit])
    result = []
    for record in records:
        item = {name: wire_value(value, wire) for (name, wire), value in zip(outputs, record)
                if value is not None}
        for field in ('PhysicalInventoryPen', 'PipelineInventoryPen'):
            if field in item: item[field] = float(item[field])
        copies = item.pop('_copies', 1)
        result.extend(dict(item) for _ in range(copies))
    return result
