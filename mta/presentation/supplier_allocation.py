"""Canonical supplier-name allocation reads over the existing prepared BOROA.

PlanningProcessor.SupplierWiseAllocationReportData[Count], deployed DLL
0222eb96677a8f06250c4bba9eb0d477ac2dab6c88d35b214a33e7a9248bb346.
The authenticated gateway name is the supplier key; browser user data is not.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from collections import defaultdict

from django.db import connection

from mta.presentation.boroa_contract import PREPARED_FIELDS, field_name
from mta.presentation.boroa_filters import BorOaFilters, BorOaQueryError
from mta.presentation.boroa_sql import col, projection, remark_query
from mta.presentation.context import PublicationUnavailable
from mta.presentation.rrr_filters import OPERATORS
from mta.presentation.rrr_sql import equal, key
from mta.runtime.relational_state import quote


class SupplierFilters(BorOaFilters):
    """Commons.filterQuery, rather than BOROA's filterQueryForReports.

    The supplier caller never concatenates sqlJoinFilter, so forchildren is
    ignored. Its explicit parent-code replacement instead addresses B's
    nonexistent ParentWhCode. Retain those source behaviors and missing-column
    errors; do not redirect them to the conveniently available F parent.
    """

    def __init__(self, payload, *, count=False):
        super().__init__(payload)
        self.supplier_count = count

    def build(self):
        if not isinstance(self.groups, dict):
            raise BorOaQueryError('native supplier filter object required')
        # This is the deployed caller's condition, including its omission of
        # customAttributeFilter when every one of the six groups is NULL.
        if not any(self.groups.get(g) is not None for g in (
                'availabilityFilter', 'supplyChainFilter', 'coverageFilter',
                'productFilter', 'locationFilter', 'colorFilter')):
            return
        supply = defaultdict(list)
        for item in self.items('supplyChainFilter'):
            name = item['attributeName'].lower()
            if name in ('forlocation', 'forlocationlocationcode', 'forchildrenlocationcode'):
                supply[name].append(self.value(item))
        for name, owner, field in (('forlocation', 'D', 'LocationType'),
                ('forlocationlocationcode', 'A', 'WhCode'),
                ('forchildrenlocationcode', 'B', 'ParentWhCode')):
            self.in_list(owner, field, supply[name])
        for group, special, code in (('locationFilter', 'location', 'WhCode'),
                                     ('productFilter', 'sku', 'SKUCode')):
            items = [{**i, 'value': self.value(i)} for i in self.items(group)]
            self.in_list('A', code, [i['value'] for i in items if i['attributeName'].lower() == special])
            self.grouped([i for i in items if i['attributeName'].lower() != special],
                lambda name, group=group: ('C', name.replace('p', 'sl'))
                if group == 'productFilter' else ('D', 'l' + name))
        for item in self.items('availabilityFilter'):
            name = item['attributeName'].lower()
            if name in ('category', 'pic', 'ohic', 'pipo,seasonality', 'availability'):
                # These native unqualified/qualified columns are absent from
                # the supplier query, rather than aliases for another color.
                raise BorOaQueryError('native supplier filter column missing')
            if name in ('norm', 'stock', 'git', 'virtualnorm'):
                self.value(item)
                if item.get('operator') not in OPERATORS:
                    if self.where:
                        raise BorOaQueryError('native supplier empty filter operator')
                    continue
                if not self.supplier_count:
                    # Data joins vf_ReqCalculation F as well as A. Its native
                    # unqualified numeric predicates are ambiguous; count
                    # omits F and therefore has a different valid boundary.
                    raise BorOaQueryError('native supplier data filter column ambiguous')
                self.where.append(self.compare('A', name, item.get('operator'), self.value(item)))
        for item in self.items('colorFilter'):
            if self.where or item.get('type') in ('colorage', 'colorcount'):
                raise BorOaQueryError('native supplier color owner missing or dangling conjunction')
        if any(i['attributeName'].lower() == 'coverage' for i in self.items('coverageFilter')):
            raise BorOaQueryError('native supplier coverage column missing')
        def custom(name):
            for prefix, owner in (('skulocattr', 'B'), ('skuattr', 'C'), ('locattr', 'D')):
                if prefix in name.lower():
                    return owner, name.lower().replace(prefix, 'c')
        items = [i for i in self.items('customAttributeFilter') if any(
            p in i['attributeName'].lower() for p in ('skulocattr', 'skuattr', 'locattr'))]
        self.grouped([{**i, 'value': self.value(i)} for i in items], custom)


def query(run, payload, supplier_name, *, count=False):
    if not isinstance(supplier_name, str):
        raise ValueError('Authenticated supplier name required')
    from mta.runtime.boroa_models import BorOaPreparedRow
    filters = SupplierFilters(payload, count=count)
    where = filters.compile()
    prepared = 'SELECT * FROM mta.' + quote(BorOaPreparedRow._meta.db_table) + ' WHERE run_id=%s'
    ctes = ['prepared AS (' + prepared + ')']
    params = [run.pk]
    if count:
        # Collapse only joins absent from native count: F, descriptions and
        # remark ties. A/B/C/D/E ordinals preserve their duplicate occurrences.
        fields = []
        for owner in ('A', 'B', 'C', 'D', 'E'):
            fields += [owner.lower() + '_ordinal', *[field_name(owner, n) for n in PREPARED_FIELDS[owner]]]
        ctes.append('R AS (SELECT DISTINCT ' + ','.join(map(quote, fields)) + ' FROM prepared)')
    else:
        ctes.append('R AS (SELECT * FROM prepared)')
    joins = ' FROM R'
    if not count:
        remarks, values = remark_query(run)
        ctes.append('remarks AS (' + remarks + ')'); params += values
        ctes.append('latest AS (SELECT ' + key('"SKUCode"') + ' sk,' + key('"WhCode"') + ' lk,' +
            key('"SupplierCode"') + ' sp,max("RemarkDate") d FROM remarks GROUP BY 1,2,3)')
        ctes.append('RM AS (SELECT M.* FROM remarks M JOIN latest T ON ' + key('M."SKUCode"') +
            '=T.sk AND ' + key('M."WhCode"') + '=T.lk AND ' + key('M."SupplierCode"') +
            '=T.sp AND M."RemarkDate"=T.d)')
        joins += (' LEFT JOIN RM ON R.sku_key=' + key('RM."SKUCode"') + ' AND R.location_key=' +
                  key('RM."WhCode"') + ' AND R.supplier_key=' + key('RM."SupplierCode"'))
    where = col('A', 'DispatchQty') + '>0 AND ' + equal(col('A', 'SupplierCode'), '%s') + ' AND (' + where + ')'
    params += [supplier_name, *filters.params]
    order = col('E', 'SequenceNo') + ' ASC NULLS FIRST,' + ','.join(col('A', n) + ' DESC NULLS LAST'
        for n in ('OrderBlackUnsatisfiedPercentage', 'OrderRedUnsatisfiedPercentage',
                  'OrderYellowUnsatisfiedPercentage', 'OrderGreenUnsatisfiedPercentage', 'DispatchPen'))
    select = 'count(*)' if count else 'row_number() OVER (ORDER BY ' + order + ')::integer AS "RN",' + \
        ','.join(v + ' AS ' + quote(n) for n, v in projection())
    sql = 'WITH ' + ','.join(ctes) + ' SELECT ' + select + joins + ' WHERE ' + where
    if not count:
        sql = 'SELECT * FROM (' + sql + ') ranked'
        paging = payload.get('paginationParameter')
        if paging is not None:
            if not isinstance(paging, dict) or any(type(paging.get(k)) is not int for k in ('pageNumber', 'recordsPerPage')):
                raise BorOaQueryError('native supplier pagination invalid')
            sql += ' WHERE "RN" BETWEEN %s AND %s'
            params += [(paging['pageNumber'] - 1) * paging['recordsPerPage'] + 1,
                       paging['pageNumber'] * paging['recordsPerPage']]
        sql += ' ORDER BY "RN"'
    return sql, params


def read(payload, supplier_name, *, count=False):
    from mta.presentation.boroa_sources import admitted_sources
    from mta.presentation.boroa_contract import production_prepared_recipe
    from mta.presentation import native_publication
    from mta.runtime.boroa_models import BorOaPreparedReceipt
    from mta.runtime.boroa_prepared_schema import verify_guards
    run, source = admitted_sources()
    native_publication.require_mode()
    receipt = BorOaPreparedReceipt.objects.filter(run=run).first()
    recipe = production_prepared_recipe()
    if receipt is None or receipt.source_digest != source.source_digest or receipt.recipe_digest != recipe:
        raise PublicationUnavailable('BOROA_prepared_receipt_missing_or_changed')
    try:
        verify_guards(connection)
    except ValueError as exc:
        raise PublicationUnavailable('BOROA_prepared_guards_changed') from exc
    sql, params = query(run, payload, supplier_name, count=count)
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        if count:
            return cursor.fetchone()[0]
        names = [d[0] for d in cursor.description]
        return [dict(zip(names, row)) for row in cursor.fetchall()]
