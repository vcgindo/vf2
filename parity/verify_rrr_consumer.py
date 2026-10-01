"""Independent deployed RRR SELECT over its accepted legacy terminal facts.

Only session-temp tables are written. No engine replay, serving request, modern
seed or permanent SQL update. This compares the unfiltered full-page HTTP
response; authenticated gateway/filter variants remain separate F3 obligations.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
from decimal import Decimal

from parity.legacy_isolation import exclusive_replay, connection
from parity.output_archive import file_sha, iter_rows, write_rows
from parity.retained_consumer_input import terminal_inputs
from parity.temporal import differences

EVIDENCE = Path('D:/freshvcf-build/evidence')
RRR = Path('F:/vflow_integrated/.local-stage7/deployed-planning/VectorFlowAPIs.VectorFlow.Processors.RRRProcessor.decompiled.cs')
RRR_SHA = 'd59a23788cb992f0413fb39fe43744043acea57804432d4eda8e09a1ac8dda82'
PICK_RECEIPT_SHA = 'd06e30cc8d203d78ec7ade158ddc2402b0134e30e268217ade1be2fb84beb19a'
PERMISSION_SHA = '18df4d8e84633848062c45e1896615a7a46d350d0c0cd8657f38cb7b0948c356'
TYPE_SHA = '51883c78e5effbb55b303f07b99df9c84a3a336b0525d19b0540a9b95df02a19'
AUTH_SOURCE = RRR.with_name('VectorFlowAPIs.Filters.GenericFunction.decompiled.cs')
AUTH_SHA = '6850a0bf2eadb4a38a2998e96ef70a264a2bc529d0de5c433c066d76c1933420'


def selected_sql(sql_filter='', sql_join_filter=''):
    if file_sha(RRR) != RRR_SHA:
        raise ValueError('Canonical deployed consumer source changed')
    method = RRR.read_text().split('private string getSelectQueryRRR(',1)[1]
    source = method.split('string.Concat(new string[6]',1)[1].split('if (sqlFilter',1)[0]
    literals = re.findall(r'"(?:[^"\\]|\\.)*"',source)
    query = ''.join(json.loads(s) for s in literals)
    if sql_join_filter:
        query = query.replace('from vf_PickListReport A ', 'from vf_PickListReport A '+sql_join_filter)
    if sql_filter:
        query += ' where '+sql_filter
    # Only table bindings and the omitted empty sqlJoinFilter/DB-name operands.
    for old,new in (('.dbo.SKULocStandardAttributes','#Standard'),('vf_PickListReport','#Pick'),
                    ('SkuLocAttributeData','#Pair'),('SkuAttributeData','#Sku'),('LocationAttributeData','#Loc')):
        query = query.replace(old,new)
    if 'SELECT DispatchColorSequence' not in query or 'Startup' in query:
        raise ValueError('Unexpected consumer extraction')
    return query


def temp_rows(db, name, table, rows):
    quote = lambda n:'['+n.replace(']',']]')+']'
    db.execute(f'SELECT TOP 0 a.* INTO {name} FROM {table} a CROSS JOIN (SELECT 1 x) b')
    if rows:
        fields = list(rows[0])
        if any(set(row)!=set(fields) for row in rows):
            raise ValueError('Mixed retained source row shapes')
        db.cursor().executemany(f'INSERT INTO {name} ('+','.join(map(quote,fields))+') VALUES ('+
            ','.join('?' for _ in fields)+')',[tuple(r[f] for f in fields) for r in rows])


def auth_ctes(db, catalogue, payload):
    """Selected GenericFunction hierarchy expansion and lower(trim) joins.

    Table/column bindings only; preserve DISTINCT expanded IDs, then membership
    multiplicity. SQL NULL equality is retained by executing these predicates.
    """
    if file_sha(AUTH_SOURCE)!=AUTH_SHA:
        raise ValueError('Selected permission source changed')
    ctes = []
    for kind,prefix,table,code,level,scope in (
        ('products','Product','#Sku','SKUCode','SL','product_permissions'),
        ('locations','Location','#Loc','WHCode','LL','location_permissions')):
        name = '#'+prefix+'Permissions'
        db.execute(f'CREATE TABLE {name} (id int,l1 nvarchar(255),l2 nvarchar(255),l3 nvarchar(255))')
        db.cursor().executemany(f'INSERT INTO {name} VALUES (?,?,?,?)',
            [(r['id'],r['level_1'],r['level_2'],r['level_3']) for r in catalogue[kind]['records']])
        assigned = payload[scope]
        if not assigned or any(type(v) is not int for v in assigned):
            raise ValueError('This receipt requires explicit selected permission IDs')
        ids = ','.join(map(str,assigned))
        expanded = f'''SELECT DISTINCT t2.id FROM {name} t1 JOIN {name} t2
            ON t2.l1=t1.l1 AND (t1.l2 IS NULL OR t2.l2=t1.l2)
            AND (t1.l3 IS NULL OR t2.l3=t1.l3) WHERE t1.id IN ({ids})'''
        cte = 'cte_SKUs' if kind=='products' else 'cte_WhCodes'
        ctes.append(f'''{cte} AS (SELECT a.{code} FROM {table} a JOIN {name} b
            ON lower(trim(a.{level}1))=lower(trim(b.l1))
            AND lower(trim(a.{level}2))=lower(trim(b.l2))
            AND lower(trim(a.{level}3))=lower(trim(b.l3))
            WHERE b.id IN ({expanded}))''')
    return ';WITH '+','.join(ctes)+' '


def supplement_temp_hierarchy(db, catalogue):
    """Independent SQL-only projection of approved retained six-field metadata.

    Session-local tables only. Deliberately do not import the modern adapter.
    SQL joins retain every original occurrence; reject missing/conflicting rows.
    """
    for kind, table, code, prefix in (('products','#Sku','SKUCode','SL'),
                                     ('locations','#Loc','WHCode','LL')):
        name = '#Retained'+prefix
        db.execute(f'CREATE TABLE {name} (code nvarchar(255) PRIMARY KEY,l1 nvarchar(255),l2 nvarchar(255),l3 nvarchar(255))')
        db.cursor().executemany(f'INSERT INTO {name} VALUES (?,?,?,?)',
            [(r['code'],r['level_1'],r['level_2'],r['level_3']) for r in catalogue[kind]['attributes']])
        conflicts = ' OR '.join(f'(a.{prefix}{i} IS NOT NULL AND a.{prefix}{i}<>r.l{i})' for i in (1,2,3))
        bad = db.execute(f'SELECT COUNT(*) FROM {table} a LEFT JOIN {name} r ON a.{code}=r.code WHERE r.code IS NULL OR '+conflicts).fetchone()[0]
        if bad: raise ValueError('Retained hierarchy has missing/conflicting native identities')
        db.execute(f'UPDATE a SET '+','.join(f'{prefix}{i}=r.l{i}' for i in (1,2,3))+
                   f' FROM {table} a JOIN {name} r ON a.{code}=r.code')


def wire_rows(rows, types):
    # Independent oracle transcription of the deployed reader, using canonical
    # SQL configuration rather than importing the modern serializer/type list.
    result = []
    for row in rows:
        values = {}
        for key,value in row.items():
            if types.get(key.casefold()) == 'Number':
                if isinstance(value,Decimal):
                    value = int(value) if value==value.to_integral_value() else float(value)
                values[key] = value
            else:
                values[key] = '' if value is None else str(value)
        result.append(values)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('modern',type=Path)
    parser.add_argument('evidence',type=Path)
    parser.add_argument('--unscoped-read-model',action='store_true')
    parser.add_argument('--scope-denial-only',action='store_true')
    parser.add_argument('--hierarchy-supplement',type=Path)
    args = parser.parse_args()
    if args.evidence.exists():
        raise ValueError('Preserve earlier receipts; select a new directory')
    args.evidence.mkdir(parents=True)
    result = dict(status='FAILED',persistent_database_writes=False,engine_replays=0)
    try:
        if args.unscoped_read_model and args.scope_denial_only:
            raise ValueError('Select one proof boundary')
        receipt = json.loads((args.modern/'receipt.json').read_text())
        supplement = receipt.get('hierarchy_supplement')
        if bool(args.hierarchy_supplement) != bool(supplement):
            raise ValueError('Modern/legacy presentation supplement must be explicit and identical')
        if supplement:
            manifest = json.loads(args.hierarchy_supplement.read_text())
            binding = dict(run_id=receipt['run']['id'],business_date='2026-06-17',output_digest=receipt['run']['output_digest'])
            if (file_sha(args.hierarchy_supplement)!=supplement['sha256'] or
                    manifest['catalogue_sha256']!=PERMISSION_SHA or
                    binding not in manifest['publications'] or
                    manifest['allowed_fields']!={'products':['SL1','SL2','SL3'],'locations':['LL1','LL2','LL3']}):
                raise ValueError('Unapproved or mismatched consumer hierarchy supplement')
            if args.unscoped_read_model or args.scope_denial_only:
                raise ValueError('Supplement proof must exercise actual selected hierarchy permissions')
        root = Path(__file__).resolve().parents[1]
        sources = receipt['sources'] if args.unscoped_read_model else json.loads((args.modern/'source.json').read_text())
        if not args.unscoped_read_model and file_sha(args.modern/'source.json') != receipt['sources_sha256']:
            raise ValueError('Modern source receipt changed')
        for name,sha in sources.items():
            if file_sha(root/name) != sha:
                raise ValueError('Modern readback source changed: '+name)
        responses = {}
        for obs in receipt.get('observations',[]):
            path = args.modern/obs['payload']
            if file_sha(path) != obs['sha256']:
                raise ValueError('Modern response changed')
            with gzip.open(path,'rt') as stream:
                responses[obs['path']] = json.load(stream)
        if args.unscoped_read_model:
            if receipt['boundary']!='UNSCOPED_RRR_READ_MODEL':
                raise ValueError('Wrong exported proof boundary')
            actual = list(iter_rows(args.modern/receipt['file'],receipt))
            grid = dict(status=200,response={'data':actual})
            payload = dict(paginationParameter=dict(pageNumber=1,recordsPerPage=5000))
        else:
            grid = responses['RRRData']
            payload = grid['request']
        if payload.get('filters') or payload['paginationParameter'] != dict(pageNumber=1,recordsPerPage=5000):
            raise ValueError('Expected selected unfiltered full-page contract')
        if grid['status']!=200 or (not args.scope_denial_only and not grid['response']['data']):
            raise ValueError('Expected nonempty successful modern response')
        values,provenance = terminal_inputs()
        if provenance['modern_run'] != receipt['run']['id'] or provenance['modern_output_digest'] != receipt['run']['output_digest']:
            raise ValueError('Modern/legacy terminal pair changed')
        pick_dir = EVIDENCE/'f3-pick-native-comparison-003'
        if file_sha(pick_dir/'receipt.json') != PICK_RECEIPT_SHA:
            raise ValueError('Accepted Pick handoff receipt changed')
        pick = json.loads((pick_dir/'receipt.json').read_text())
        if pick['retained_source'] != provenance:
            raise ValueError('Pick legacy source identity differs')
        rows = list(iter_rows(pick_dir/'legacy-pick.jsonl.gz',pick['legacy']))
        permission = Path('D:/freshvcf-build/inputs/permission-input-v1.json')
        if file_sha(permission) != PERMISSION_SHA:
            raise ValueError('Permission artifact changed')
        catalogue = json.loads(permission.read_text())
        sql = selected_sql()
        type_source = Path('F:/VFlow_Local/local-runtime/mta-engine/Scripts/DBCreation/UI_ReportColumnTypes_2.0.sql')
        if file_sha(type_source)!=TYPE_SHA:
            raise ValueError('Selected type configuration source changed')
        types = {name.casefold():kind for name,kind in re.findall(
            r"VALUES \(N'RationRequirementReport', N'([^']+)', N'([^']+)'\)",type_source.read_text())}
        if len(types)!=118:
            raise ValueError('Selected type configuration roster changed')
        os.environ['VFTEST_PROFILE']='fresh'
        with exclusive_replay():
            with connection('VFTEST_BPR') as db:
                temp_rows(db,'#Pick','dbo.vf_PickListReport',rows)
                closing = values['closing']
                temp_rows(db,'#Standard','VFTEST_Importer.dbo.SKULocStandardAttributes',closing['dbm']['SKULocStandardAttributes'])
                for name,table in (('#Sku','SkuAttributeData'),('#Loc','LocationAttributeData'),('#Pair','SkuLocAttributeData')):
                    temp_rows(db,name,'dbo.'+table,closing['importer'][table])
                if supplement:
                    supplement_temp_hierarchy(db,catalogue)
                cte = (';WITH cte_SKUs AS (SELECT DISTINCT SKUCode FROM #Sku), '
                       'cte_WhCodes AS (SELECT DISTINCT WHCode FROM #Loc) '
                       if args.unscoped_read_model else auth_ctes(db,catalogue,payload))
                count = db.execute(cte+', cte_finaldata AS ('+sql+') SELECT COUNT(1) FROM cte_finaldata').fetchone()[0]
                query = cte+sql+' ORDER BY DispatchColorSequence, DispatchPen DESC, WhCode, SKUCode OFFSET 0 ROWS FETCH NEXT 5000 ROWS ONLY'
                cursor = db.execute(query)
                columns = [c[0] for c in cursor.description]
                expected = wire_rows([dict(zip(columns,r)) for r in cursor.fetchall()],types)
        delta = differences(expected,grid['response']['data'],'/RRRData')
        if not args.unscoped_read_model:
            delta += differences(str(count),responses['RRRDataCount']['response']['recordCount'],'/RRRDataCount')
        order_fields = ('DispatchColorSequence','DispatchPen','WhCode','SKUCode')
        delta += differences([tuple(r[f] for f in order_fields) for r in expected],
            [tuple(r[f] for f in order_fields) for r in grid['response']['data']],'/ordered_keys')
        # Bag comparison covers all values/types/duplicates; order must match as
        # a sequence of declared keys, without inventing a tied-row priority.
        order_match = [[r[f] for f in order_fields] for r in expected] == [[r[f] for f in order_fields] for r in grid['response']['data']]
        if args.scope_denial_only and (count or grid['response']['data']):
            raise ValueError('Scope-denial proof requires both independently empty populations')
        passed = ('PASS_UNSCOPED_RRR_READ_MODEL_NOT_AUTH_ACCEPTANCE' if args.unscoped_read_model else
                  'PASS_SCOPE_DENIAL_NONEMPTY_ACCEPTANCE_OPEN' if args.scope_denial_only else
                  'PASS_SELECTED_RRR_RESPONSE')
        result.update(status=passed if not delta and order_match else 'FAIL',
            hierarchy_supplement=supplement,
            legacy_source=provenance,legacy_rows=write_rows(args.evidence/'legacy-rrr.jsonl.gz',expected),
            rows=len(expected),fields=len(columns),count=count,differences=delta,declared_order_matches=order_match,
            modern_receipt_sha256=file_sha(args.modern/'receipt.json'),consumer_source_sha256=RRR_SHA,
            type_source_sha256=file_sha(type_source),permission_source_sha256=AUTH_SHA,query=query,
            qualification=('Unscoped projection/types only; no authorization or filter acceptance' if args.unscoped_read_model else
                'Scope-denial only; zero rows cannot close nonempty consumer acceptance' if args.scope_denial_only else
                'Unfiltered selected root-scope grid/count/typing only; authenticated gateway and filter variants remain pending'))
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc))
        raise
    finally:
        (args.evidence/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('status','rows','fields','count','declared_order_matches')}))
    if result['status']=='FAIL':
        raise SystemExit(1)


if __name__=='__main__':
    main()
