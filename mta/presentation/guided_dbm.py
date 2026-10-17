from mta.presentation.native_mode import removed_mode
"""Sealed SQL readers for the four daily Guided DBM projections."""
from django.conf import settings
from django.db import connection, transaction

from mta.presentation.bpr_sql import _values_cte
from mta.presentation.context import PublicationUnavailable, scope
from mta.presentation.guided_dbm_fields import FIELDS, field_name, schema_digest
from mta.presentation.insight_filters import InsightPredicate, unavailable
from mta.presentation.rrr_sql import Filters, equal
from mta.presentation.selective import image_query
from mta.runtime.models import GuidedDbmPreparedProjection, GuidedDbmPreparedRow
from mta.runtime.relational_state import quote


KINDS = frozenset(('loc', 'sku', 'pie', 'ageing'))
OWNER = {'_a': 'A', '_sku': 'S', '_location': 'L', '_pair': 'P', '_master': 'M'}


def column(owner, name):
    if owner == '_description':
        return 'D.' + quote(name)
    source = OWNER[owner]
    return 'R.' + quote(field_name(source, name))


def raw_equal(left, right):
    return ('(' + left + ' IS NULL)=(' + right + ' IS NULL) AND '
            "COALESCE(" + left + ",'')=COALESCE(" + right + ",'')")


class PreparedFilters(Filters):
    """Established filter compiler over the finite prepared wire fields."""
    def column(self, owner, name):
        if owner == '_description':
            return column(owner, name) + '::text', 'text'
        source = OWNER[owner]
        actual = next((field for field in FIELDS[source]
                       if field.casefold() == name.casefold()), None)
        if actual is None:
            raise PublicationUnavailable('Guided_DBM_prepared_filter_field_missing')
        wire = FIELDS[source][actual]
        return column(owner, actual) + ('::text' if wire == 'text' else ''), \
               ('text' if wire == 'text' else 'int')


def compile_terms(predicate):
    compiler = PreparedFilters({})
    def term(node):
        if node[0] == 'or':
            return '(' + ' OR '.join(term(child) for child in node[1]) + ')'
        if node[0] == 'in':
            expression, _ = compiler.column(*node[1])
            compiler.params.extend(node[2])
            return '(' + ' OR '.join(equal(expression, '%s') for _ in node[2]) + ')'
        return compiler.compare(*node[1], node[2], node[3])
    try:
        where = ' AND '.join(term(node) for node in predicate.sql_terms) or 'TRUE'
    except PublicationUnavailable as exc:
        unavailable(str(exc).partition(':')[2])
    return where, compiler.params


def _max(expression, *, text=True):
    return 'max(' + expression + (' COLLATE "C"' if text else '') + ')'


def _projection(kind):
    inc = "sum(CASE WHEN R.a_suggestion='Increase' THEN 1 ELSE 0 END)::bigint"
    dec = "sum(CASE WHEN R.a_suggestion='Decrease' THEN 1 ELSE 0 END)::bigint"
    if kind == 'loc':
        fields = [('whcode', 'R.a_whcode'), ('location', _max('D."WHDescription"')),
                  ('NormInc', inc), ('NormDec', dec),
                  ('LogisticsLocation', _max('R.l_logisticslocation'))]
        fields += [(f'LL{i}', _max('R.l_ll' + str(i))) for i in range(1, 6)]
        fields += [(('c1' if i == 1 else f'C{i}'), _max('R.l_c' + str(i)))
                   for i in range(1, 16)]
        return fields, 'R.a_whcode', '(' + inc + ')+(' + dec + ') DESC,first_ordinal'
    if kind == 'sku':
        fields = [('sku', 'R.a_skucode'), ('SKUDescription', _max('D."SKUDescription"')),
                  ('NormInc', inc), ('NormDec', dec),
                  ('elephantOrderCapping', _max('R.s_elephantordercapping', text=False)),
                  ('weight', _max('R.s_weight')),
                  ('volume', _max('R.s_volume'))]
        fields += [(f'SL{i}', _max('R.s_sl' + str(i))) for i in range(1, 6)]
        fields += [(('c1' if i == 1 else f'C{i}'), _max('R.s_c' + str(i)))
                   for i in range(1, 16)]
        return fields, 'R.a_skucode', 'first_ordinal'
    if kind == 'pie':
        return [('suggestion', 'R.a_suggestion'),
                ('count', 'count(R.a_suggestion)::bigint')], 'R.a_suggestion', 'first_ordinal'
    band = ("CASE WHEN R.a_suggestiongenerationage<2 THEN '0-1' "
            "WHEN R.a_suggestiongenerationage<4 THEN '2-3' "
            "WHEN R.a_suggestiongenerationage<7 THEN '3-6' ELSE '7+' END")
    return [('age', band), ('NormInc', inc), ('NormDec', dec)], band, \
           "CASE " + band + " WHEN '0-1' THEN 0 WHEN '2-3' THEN 1 WHEN '3-6' THEN 2 ELSE 3 END"


def _prepared_query(run):
    return ('SELECT * FROM ' + quote(GuidedDbmPreparedRow._meta.db_table) +
            ' WHERE run_id=%s'), [run.pk]


def build_query(run, payload, kind, attributes):
    if kind not in KINDS:
        raise ValueError('unknown_guided_dbm_kind')
    predicate = InsightPredicate(payload, attributes['LocationAttributeData'], kind=kind)
    where, filter_params = compile_terms(predicate)
    products, locations = scope(payload, attributes=attributes)
    if not products or not locations:
        return None, []
    ctes, params = [], []
    query, values = _prepared_query(run)
    ctes.append('prepared AS NOT MATERIALIZED (' + query + ')')
    params.extend(values)
    for alias, codes in (('AUTH_SKU', products), ('AUTH_LOC', locations)):
        rows = [{'code': code} for code in codes for _ in range(codes.multiplicities[code])]
        query, values = _values_cte(rows, ('code',), {'code': '::text'})
        ctes.append(alias + ' AS NOT MATERIALIZED (' + query + ')')
        params.extend(values)
    joins = (' JOIN AUTH_SKU ON ' + raw_equal('R.a_skucode', 'AUTH_SKU.code') +
             ' JOIN AUTH_LOC ON ' + raw_equal('R.a_whcode', 'AUTH_LOC.code'))
    if kind in ('loc', 'sku'):
        path = ('closing/btr/SiteDescriptionTbl' if kind == 'loc'
                else 'closing/btr/SKUDescriptionTbl')
        query, values = image_query(run, path)
        ctes.append('D AS NOT MATERIALIZED (' + query + ')')
        params.extend(values)
        key = '"WHCode"' if kind == 'loc' else '"SKUCode"'
        source = 'R.a_whcode' if kind == 'loc' else 'R.a_skucode'
        joins += ' JOIN D ON ' + raw_equal(source, 'D.' + key)
    if predicate.children:
        query, values = image_query(run, 'closing/btr/LocationAttributeData')
        ctes.append('PARENT AS NOT MATERIALIZED (' + query + ')')
        params.extend(values)
        joins += (' JOIN PARENT ON ' + equal('R.m_parentwhcode', 'PARENT."WHCode"') +
                  ' AND (' + ' OR '.join(equal('PARENT."LocationType"', '%s')
                                        for _ in predicate.children) + ')')
        params.extend(predicate.children)
    if kind == 'ageing':
        where += (" AND R.a_suggestion IS NOT NULL AND R.a_suggestion<>'No Suggestion'"
                  ' AND R.a_suggestiongenerationage IS NOT NULL')
    fields, grouping, ordering = _projection(kind)
    select = ','.join(expression + ' AS ' + quote(name) for name, expression in fields)
    select += ',min(R.ordinal) AS first_ordinal'
    params.extend(filter_params)
    sql = ('WITH ' + ','.join(ctes) + ' SELECT ' + select + ' FROM prepared R' + joins +
           ' WHERE ' + where + ' GROUP BY ' + grouping + ' ORDER BY ' + ordering)
    return sql, params


def read_guided_dbm(run, payload, kind, attributes):
    """Return the existing small raw projection contract from the sealed bag."""
    from mta.presentation.daily_preparation import production_branch
    daily = production_branch(run)
    if not daily:
        raise ValueError('Guided DBM prepared reader requires an admitted source run')
    if not daily and (not getattr(settings, 'VF_GUIDED_PREPARED', False)):
        raise PublicationUnavailable('Guided_prepared_trial_disabled')
    if daily:
        from mta.presentation.daily_preparation import source_digest as daily_source_digest
        source_digest = daily_source_digest(run)
        selected = run
    else:
        selected, source_digest = removed_mode('historical_fixture')
    receipt = GuidedDbmPreparedProjection.objects.filter(run_id=run.pk).first()
    if selected.pk != run.pk or receipt is None or receipt.source_digest != source_digest or (receipt.schema_digest != schema_digest()):
        raise PublicationUnavailable('Guided_DBM_prepared_receipt_missing_or_changed')
    from mta.runtime.guided_dbm_schema import verify_guards
    try:
        verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('Guided_DBM_prepared_guards_changed') from exc
    query, params = build_query(run, payload, kind, attributes)
    if query is None:
        return []
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('jit')")
        previous_jit = cursor.fetchone()[0]
        cursor.execute('SET LOCAL jit=off')
        cursor.execute(query, params)
        names = [item[0] for item in cursor.description]
        rows = [{name: value for name, value in zip(names, record) if name != 'first_ordinal' and value is not None} for record in cursor.fetchall()]
        cursor.execute("SELECT set_config('jit',%s,true)", [previous_jit])
        return rows
