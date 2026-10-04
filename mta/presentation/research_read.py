"""Selected Research history inputs, without reconstructing a publication."""
from django.db import connection

from mta.presentation import hierarchy, history_native
from mta.presentation.context import permission_catalogue, scope, PublicationUnavailable
from mta.presentation.rrr import sql_key
from mta.presentation.rrr_sql import key, equal
from mta.presentation.selective import image_metadata, image_query, image_rows
from mta.runtime.relational_state import quote, wire_value


def attributes(run):
    state = {name: image_rows(run, 'closing/btr/' + name)
             for name in ('SkuAttributeData', 'LocationAttributeData')}
    try:
        manifest = hierarchy.selected_manifest(run)
        return hierarchy.project_attributes(state, permission_catalogue(), manifest) if manifest else state
    except hierarchy.HierarchyUnavailable as exc:
        raise PublicationUnavailable(str(exc)) from exc


def selected_rows(run, path, pairs, *, children=False):
    """EXISTS restricts transfer without multiplying native source occurrences."""
    pairs = sorted(pair for pair in pairs if pair is not None)
    if not pairs:
        return []
    item = image_metadata(run, path)
    relation, params = image_query(run, path)
    selected = 'VALUES ' + ','.join(['(%s,%s)'] * len(pairs))
    terms = ['(' + key('A."WhCode"') + '=K.column2)']
    if children:
        terms.append('(' + key('A."ParentWhCode"') + '=K.column2)')
    fields = item['fields']
    sql = ('WITH K AS (' + selected + ') SELECT ' + ','.join('A.' + quote(column) for _, column, _ in fields) +
           ' FROM (' + relation + ') A WHERE EXISTS (SELECT 1 FROM K WHERE ' + key('A."SKUCode"') +
           '=K.column1 AND (' + ' OR '.join(terms) + ')) ORDER BY A.vf_ordinal')
    with connection.cursor() as cursor:
        cursor.execute(sql, [value for pair in pairs for value in pair] + params)
        return [{name: wire_value(value, kind) for (name, _, kind), value in zip(fields, row)}
                for row in cursor.fetchall()]


def read_research(run, payload):
    data = payload.get('data')
    if not isinstance(data, list) or not data:
        raise ValueError('Selected research data required')
    selected = {sql_key(row['SKUCode'], row['WhCode']) for row in data}
    state = attributes(run)
    products, locations = scope(payload, attributes=state)
    masters = selected_rows(run, 'reports/bpr/vf_RationedReqReport', selected)
    parents = {sql_key(row['SKUCode'], row['ParentWhCode']) for row in masters}
    for name in ('BufferTrendPhysicalInv', 'BufferTrendDispatch'):
        state[name] = selected_rows(run, 'closing/btr/' + name, selected | parents, children=True)
    return history_native.research_rows(state, masters, data, products=products, locations=locations)


def read_historical_availability(run, payload):
    """Three date bands use the source's no-pair-attribute join grain."""
    state = attributes(run)
    products, locations = scope(payload, attributes=state)
    if not products or not locations:
        return [dict(availability_01_30=0, availability_31_60=0, availability_61_90=0)]
    ctes, params = [], []
    for alias, name in (('A', 'BufferTrendPhysicalInv'), ('sa', 'SkuAttributeData'), ('la', 'LocationAttributeData')):
        query, values = image_query(run, 'closing/btr/' + name)
        ctes.append(alias + ' AS (' + query + ')'); params.extend(values)
    for alias, codes in (('P', products), ('L', locations)):
        ctes.append(alias + ' AS (VALUES ' + ','.join(['(%s,%s)'] * len(codes)) + ')')
        params.extend(value for code in sorted(codes) for value in (code, codes.multiplicities[code]))
    # colour_counts uses the canonical normalized dimension index, while its
    # permission membership uses the original source code and its multiplicity.
    joins = (' FROM A JOIN sa ON ' + equal('A."SKUCode"', 'sa."SKUCode"') +
             ' JOIN la ON ' + equal('A."WhCode"', 'la."WHCode"') +
             ' JOIN P ON A."SKUCode"=P.column1 JOIN L ON A."WhCode"=L.column1')
    expressions = []
    for first, last in ((1, 30), (31, 60), (61, 90)):
        cells = ['A.' + quote('D' + str(i)) for i in range(first, last + 1)]
        for colours in (("'Black'",), tuple("'" + colour + "'" for _, colour in history_native.COLOURS)):
            expressions.append('sum((' + '+'.join('CASE WHEN ' + c + ' IN (' + ','.join(colours) +
                ') THEN 1 ELSE 0 END' for c in cells) + ')*P.column2*L.column2)')
    with connection.cursor() as cursor:
        cursor.execute('WITH ' + ','.join(ctes) + ' SELECT ' + ','.join(expressions) + joins, params)
        totals = cursor.fetchone()
    result = {}
    for i, (first, last) in enumerate(((1, 30), (31, 60), (61, 90))):
        black, total = (value or 0 for value in totals[i * 2:i * 2 + 2])
        value = float(history_native.percentage(total - black, total))
        result[f'availability_{first:02d}_{last}'] = int(value) if value.is_integer() else value
    return [result]
