"""Exact pinned RRROA SELECT/count over the admitted smoke source in temp tables."""
import argparse
import json
import os
from pathlib import Path
import re
from mta.serialization import storage
from parity.output_archive import file_sha
from parity.legacy_isolation import exclusive_replay, connection
from parity.verify_rrr_consumer import temp_rows, auth_ctes

SOURCE = Path('D:/freshvcf-build/evidence/f3-stage2-git-source-001/PlanningProcessor.decompiled.cs')
SOURCE_SHA = 'bf716c4f84e43920b5f2ab302e3d3c78ec685f5d714471c53047d377537d3486'


def selected_sql():
    if file_sha(SOURCE) != SOURCE_SHA:
        raise ValueError('Pinned RRROA consumer changed')
    body = SOURCE.read_text().split('private string getSelectQueryRRRColorBandWise(', 1)[1]
    literal = re.search(r'string text = ("(?:[^"\\]|\\.)*");', body).group(1)
    query = json.loads(literal)
    query += ' Inner Join cte_SKUs skucodes on A.SKUCode=skucodes.SKUCode'
    query += ' Inner Join cte_WhCodes whcodes on A.WHCode=whcodes.WHCode '
    count = ('select count(1) from [RRR_OrderAllocation] A '
             'Inner Join cte_SKUs skucodes on A.SKUCode=skucodes.SKUCode '
             'Inner Join cte_WhCodes whcodes on A.WHCode=whcodes.WHCode '
             'Left Join SkuAttributeData C on A.SKUCode=C.SKUCode '
             'Left Join LocationAttributeData D on A.WHCode=D.WHCode '
             'left join SkuLocAttributeData B on A.SKUCode=B.SKUCode and a.WhCode=B.LocCode ')
    for old, new in (('[RRR_OrderAllocation]', '#RRR'), ('[SKUDescriptionTbl]', '#SkuDesc'),
            ('[SiteDescriptionTbl]', '#LocDesc'), ('SkuLocAttributeData', '#Pair'),
            ('SkuAttributeData', '#Sku'), ('LocationAttributeData', '#Loc')):
        query, count = query.replace(old, new), count.replace(old, new)
    return query, count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    if args.receipt.exists():
        raise ValueError('Preserve prior proof')
    exported = json.loads(args.source.read_text())
    if exported['run'] != '17f0eb84-7b6d-40e9-a288-9441a4d7a860':
        raise ValueError('This proof selects the accepted positive smoke source')
    grid, count = selected_sql()
    results = []
    os.environ['VFTEST_PROFILE'] = 'fresh'
    with exclusive_replay(), connection('VFTEST_BPR') as db:
        temp_rows(db, '#RRR', 'RRR_OrderAllocation', exported['source'])
        for name, table in (('#Sku', 'SkuAttributeData'), ('#Loc', 'LocationAttributeData'),
                            ('#Pair', 'SkuLocAttributeData'), ('#SkuDesc', 'SKUDescriptionTbl'),
                            ('#LocDesc', 'SiteDescriptionTbl')):
            temp_rows(db, name, 'VFTEST_Importer.dbo.'+table, exported['attributes'][table])
        for case in exported['cases']:
            auth = auth_ctes(db, exported['catalogue'], case['payload'])
            where = ' WHERE '+case['where'] if case['where'] else ''
            expected_count = db.execute(auth+count+where).fetchval()
            sql = auth+grid+where+') A '
            paging = case['payload'].get('paginationParameter')
            if paging:
                low = (paging['pageNumber']-1)*paging['recordsPerPage']+1
                high = paging['pageNumber']*paging['recordsPerPage']
                sql += f' WHERE RN BETWEEN {low} AND {high}'
            sql += ' ORDER BY RN'
            cursor = db.execute(sql)
            fields = [column[0] for column in cursor.description]
            legacy = storage([dict(zip(fields, row)) for row in cursor.fetchall()])
            results.append(dict(actor=case['actor'], name=case['name'],
                status='PASS' if expected_count==case['count'] and legacy==case['rows'] else 'FAIL',
                legacy_count=expected_count, modern_count=case['count'],
                legacy=legacy, modern=case['rows']))
            db.execute('DROP TABLE #ProductPermissions; DROP TABLE #LocationPermissions')
    result = dict(status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL',
        run=exported['run'], output_digest=exported['output_digest'], seal=exported['seal'],
        source_sha256=file_sha(args.source), consumer_sha256=SOURCE_SHA,
        comparisons=results, permanent_sql_writes=False)
    with args.receipt.open('x') as stream:
        json.dump(result, stream, indent=2)
    print(result['status'], len(results), args.receipt)
    return int(result['status'] != 'PASS')


if __name__ == '__main__':
    raise SystemExit(main())
