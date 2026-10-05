"""Pinned BOR order-allocation filter compilation over prepared columns."""
from collections import defaultdict

from mta.presentation.boroa_contract import PREPARED_FIELDS
from mta.presentation.rrr_filters import OPERATORS
from mta.presentation.rrr_sql import Filters
from mta.runtime.relational_state import quote


class BorOaQueryError(ValueError):
    pass


class _FilterBuildAbort(Exception):
    pass


class BorOaFilters(Filters):
    """Compile CommonsProcessor.filterQueryForReports aliases for ``BOROA``.

    The deployed call supplies aliases ``a,a,F,c,d,b``.  Prepared rows retain
    those owners in lower-case column prefixes so unsupported native columns
    still fail instead of being redirected to a convenient joined source.
    """

    def __init__(self, payload, *, count=False):
        super().__init__(payload)
        self.count = count

    def column(self, owner, name):
        # BOROrderAllocationReportDataCount joins ColorSequence as C and joins
        # SkuAttributeData as s. Product hierarchy predicates are unqualified
        # and bind successfully to s.SL*, represented by prepared C columns.
        # SKU custom-attribute predicates are qualified as c.c* and therefore
        # retain their native missing-column failure in count mode.
        prepared_owner = 'C' if self.count and owner == 'S' else owner
        if self.count and owner == 'C':
            raise BorOaQueryError('native BOROA count filter column missing')
        try:
            owner_fields = PREPARED_FIELDS[prepared_owner]
        except KeyError as exc:
            raise BorOaQueryError('native BOROA filter owner missing') from exc
        fields = {field.casefold(): (field, kind) for field, kind in owner_fields.items()}
        try:
            actual, kind = fields[name.casefold()]
        except KeyError as exc:
            raise BorOaQueryError('native BOROA filter column missing') from exc
        sql_kind = {
            'bigint': 'int', 'integer': 'int', 'int': 'int',
            'numeric': 'decimal', 'decimal': 'decimal',
            'text': 'nvarchar', 'nvarchar': 'nvarchar',
            'float': 'float', 'real': 'real',
        }.get(kind)
        if sql_kind is None:
            raise BorOaQueryError('native BOROA filter column type missing')
        return 'R.' + quote(prepared_owner.lower() + '_' + actual.lower()), sql_kind

    def items(self, group):
        group_name = group
        group = self.groups.get(group)
        if group is None:
            return
        rows = group.get('filters')
        if rows is None:
            raise _FilterBuildAbort()
        for item in rows:
            if item is None or (item.get('attributeName') is None and group_name != 'colorFilter'):
                raise _FilterBuildAbort()
            if item.get('attributeName') != '':
                yield item

    @staticmethod
    def value(item, *, nullable=False):
        value = item.get('value')
        if value is None:
            if nullable:
                return ''
            raise _FilterBuildAbort()
        return str(value)

    def compile(self):
        # ApplyFiltersForReports catches builder NULL failures after preserving
        # predicates already appended. Provider/column failures remain errors.
        self.unfinished_join = False
        try:
            self.build()
        except _FilterBuildAbort:
            if self.unfinished_join:
                raise BorOaQueryError('native incomplete filter join')
        return ' AND '.join(self.where) or 'TRUE'

    def build(self):
        supply = defaultdict(list)
        for item in self.items('supplyChainFilter'):
            name = item['attributeName'].lower()
            if name in ('forlocation', 'forlocationlocationcode',
                        'forchildrenlocationcode', 'forchildren'):
                supply[name].append(self.value(item))
                if name == 'forchildren':
                    self.unfinished_join = True
        for name, owner, field in (
                ('forlocation', 'D', 'LocationType'),
                ('forlocationlocationcode', 'A', 'WhCode'),
                ('forchildrenlocationcode', 'F', 'ParentWhCode')):
            self.in_list(owner, field, supply[name])
        self.children = supply['forchildren']
        self.unfinished_join = False

        for group, special, code in (
                ('locationFilter', 'location', 'WhCode'),
                ('productFilter', 'sku', 'SKUCode')):
            items = [{**item, 'value': self.value(item)} for item in self.items(group)]
            mapped = [item for item in items if item['attributeName'].lower() != special]
            if group == 'locationFilter':
                self.in_list('A', code, [item['value'] for item in items
                                         if item['attributeName'].lower() == special])
            self.grouped(
                mapped,
                lambda name, group=group: (
                    'S' if self.count else 'C', name.replace('p', 'sl')
                )
                if group == 'productFilter' else ('D', 'l' + name),
            )
            if group == 'productFilter':
                self.in_list('A', code, [item['value'] for item in items
                                         if item['attributeName'].lower() == special])

        accumulated = defaultdict(list)
        for item in self.items('availabilityFilter'):
            name = item['attributeName'].lower()
            if name in ('category', 'pic', 'ohic', 'pipo,seasonality'):
                accumulated[name].append(self.value(item, nullable=True))
            if name in ('norm', 'stock', 'git', 'availability', 'virtualnorm'):
                if item.get('value') is None:
                    if self.where:
                        raise BorOaQueryError('native dangling filter conjunction')
                    raise _FilterBuildAbort()
                if item.get('operator') not in OPERATORS:
                    if self.where:
                        raise BorOaQueryError('native empty filter operator')
                    continue
                self.where.append(self.compare('A', name, item.get('operator'), self.value(item)))
        if accumulated['category']:
            # Native SQL addresses b.Category; BOR-OA b is SkuLocAttributeData.
            raise BorOaQueryError('native BOROA category column missing')
        for name, owner, field in (
                ('pic', 'A', 'DispatchColor'),
                ('ohic', 'A', 'PhysicalInventoryColor'),
                ('pipo,seasonality', 'A', 'Tags')):
            self.in_list(owner, field, accumulated[name])

        for item in self.items('colorFilter'):
            kind = item.get('type')
            if kind == 'colorage' and item.get('value') is None and not self.where:
                raise _FilterBuildAbort()
            if self.where or kind in ('colorage', 'colorcount'):
                raise BorOaQueryError('native BOROA color owner absent or dangling conjunction')

        coverage = list(self.items('coverageFilter'))
        if any(item['attributeName'].lower() == 'coverage' for item in coverage):
            raise BorOaQueryError('native BOROA coverage owner absent')

        def custom(name):
            for prefix, owner in (('skulocattr', 'B'), ('skuattr', 'C'), ('locattr', 'D')):
                if prefix in name.lower():
                    return owner, name.lower().replace(prefix, 'c')

        custom_items = [
            {**item, 'value': self.value(item)}
            for item in self.items('customAttributeFilter')
            if any(prefix in item['attributeName'].lower()
                   for prefix in ('skulocattr', 'skuattr', 'locattr'))
        ]
        self.grouped(custom_items, custom)
