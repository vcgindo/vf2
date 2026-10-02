"""Pinned deployed parent Expedite SQL; only owned table bindings vary."""
from parity.git_queries import method, blocks, parts, bound


def count_query(auth, kind, *, sql_filter='', sql_join_filter=''):
    from parity.verify_expedite_consumer import selected_queries
    _, selected = selected_queries()
    queries = []
    for query in selected[kind].values():
        assert query.count('#Expedite a ') == 1
        query = query.replace('#Expedite a ', '#Expedite a '+sql_join_filter+' ')
        if sql_filter:
            position = query.rindex(')) ')
            query = query[:position]+' and '+sql_filter+query[position:]
        queries.append(auth+bound(query))
    return ';'.join(queries)


def custom_query(auth, *, page=1, size=5000):
    body = method('GetCustomGridData')
    p = parts(next(b for b in blocks(body) if 'rq=B.RationedQty' in b and 'ExpediteDispatches B' in b))
    assert len(p) == 3
    query = auth + p[0] + p[1] + '[VFTEST_Importer]' + p[2]
    if page is not None:
        query += f' where RN between ({page}-1)*{size}+1 and ({page}*{size})'
    query += ' for json path) data'
    return bound(query.replace('ExpediteDispatches B', '#Expedite B').replace('BPR_Table D', '#Bpr D'))


def parent_query(auth, *, page=1, size=5000, sql_filter=''):
    body = method('ExpediteFromParent')
    fragments = [parts(b) for b in blocks(body) if 'cte_' in b]
    assert len(fragments) == 4 and all(len(p) == 3 for p in fragments)
    query = auth
    for i, p in enumerate(fragments):
        # The database operands differ by fragment. Bind only the names;
        # preserve source comments, joins and WHERE clauses verbatim.
        first, second = ('[VFTEST_BPR]', '[VFTEST_Importer]') if i in (0, 2) else ('[VFTEST_Importer]', '[VFTEST_BPR]')
        query += p[0]+first+p[1]+second+p[2]
        if i in (0, 2):
            if sql_filter: query += ' and '+sql_filter
            query += ' )'
    query += 'Select ((Select * from cte_intransit for json path)) intransit, (Select * from cte_avilatparentintransit for json path) atparentintransit,'
    for table, alias in (('cte_expediteDispatches', 'expedite'), ('cte_avilatparent', 'Availabilityatparent')):
        query += '(Select * from '+table
        # Retain the source unpaged missing separator; do not silently repair.
        query += 'order by RN for json path)' if page is None else f' where RN between ({page}-1)*{size}+1 and ({page}*{size}) order by RN for json path)'
        query += ' '+alias+(',' if alias == 'expedite' else '')
    for old,new in (('[VFTEST_BPR].[dbo].[ExpediteDispatches]','#Expedite '),
                    ('[VFTEST_Importer].dbo.[SKULocStandardAttributes]','#Standard'),
                    ('[VFTEST_BPR].dbo.vf_PickListReport','#Pick'),
                    ('BPRReport_RemarkDetails','#Remarks'),('BPRMaster','#Master')):
        query = query.replace(old,new)
    return bound(query)
