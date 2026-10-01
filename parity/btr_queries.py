"""Extract selected deployed BTR SQL; only parameter/table bindings change."""
import json
from pathlib import Path
import re
from parity.output_archive import file_sha
from parity.verify_excess_readmodel import literals

SOURCE=Path('D:/freshvcf-build/evidence/f3-daily-history-source-001/VectorFlowAPIs.VectorFlow.Processors.BORProcessor.decompiled.cs')
SOURCE_SHA='80ceb4916ca4cd8567384a4598858cef55f8574007662b025aee237f20ab9298'
REQ_FIELDS=('SKUCode','WhCode','ParentWhCode','Norm','VirtualNorm')
CTE=';WITH cte_SKUs AS (SELECT DISTINCT SKUCode FROM #SkuAttributeData),cte_WhCodes AS (SELECT DISTINCT WHCode FROM #LocationAttributeData) '


def source():
    if file_sha(SOURCE)!=SOURCE_SHA: raise ValueError('Fresh deployed BTR source changed')
    return SOURCE.read_text()


def bindings(query):
    for old,new in (('{Startup.BPRServerName}.dbo.vf_ReqCalculation','#Req'),
        ('{Startup.ImporterServerName}.dbo.SKULocStandardAttributes','#Standard'),
        ('{Startup.ImporterServerName}.dbo.SKuDescriptionTbl','#SKUDescriptionTbl'),
        ('{Startup.ImporterServerName}.dbo.SiteDescriptionTbl','#SiteDescriptionTbl'),
        ('.dbo.vf_RationedReqReport','#Rationed'),('.dbo.SKULocStandardAttributes','#Standard')):
        query=query.replace(old,new)
    for table in ('BPPTrendDispatch','BPPTrendPhysicalInv','BufferTrendDispatch','BufferTrendPhysicalInv',
        'SkuLocAttributeData','SKUAttributeData','LocationAttributeData','CategoryColDescription'):
        query=re.sub(r'(?<![#\w])'+table+r'\b','#'+('SkuAttributeData' if table=='SKUAttributeData' else table),query,flags=re.I)
    return query


def grid_query(name,*,page=1,size=5000,start=1,end=90,sql_filter='',sql_join_filter='',auth_cte=None):
    if name not in ('tech','eco','both'): raise ValueError('Invalid branch')
    body=source().split('public async System.Threading.Tasks.Task<responseMessage> GetBTRDataAsync(',1)[1]
    lines=body.splitlines()
    category=next(line for line in lines if line.strip().startswith('authQueryForReports = authQueryForReports +'))
    auth=(auth_cte or CTE)+bindings(literals(category))
    selections=[json.loads(re.search(r'val7.Add\(\$(.*)\);',line).group(1)) for line in lines if 'val7.Add($' in line]
    if len(selections)!=2: raise ValueError('Unexpected BTR result branches')
    outer=next(line.strip()[len('string finalSql = $'):-1] for line in lines if line.strip().startswith('string finalSql = $'))
    outer=outer.replace('{(string.IsNullOrWhiteSpace(sqlFilter) ? "" : ("WHERE " + sqlFilter))}',
                        'WHERE '+sql_filter if sql_filter else '')
    outer=outer.replace('{string.Join(" UNION ALL ", (System.Collections.Generic.IEnumerable<string>)val7)}','__SELECTS__')
    query=json.loads(outer).replace('__SELECTS__',' UNION ALL '.join(selections if name=='both' else [selections[0 if name=='eco' else 1]]))
    values={'{authQueryForReports}':auth,'{text2}':', '.join(f'a.D{i}' for i in range(start,end+1)),
        '{text3}':', '.join(f'btd.D{i} as CD{i}' for i in range(start,end+1)),
        '{masterRoot.paginationParameter.RecordsPerPage}':str(size),
        '{(masterRoot.paginationParameter.PageNumber - 1) * masterRoot.paginationParameter.RecordsPerPage}':str((page-1)*size),
        '{sqlJoinFilter}':sql_join_filter}
    for old,new in values.items(): query=query.replace(old,new)
    query=bindings(query)
    if '{' in query or 'Startup.' in query: raise ValueError('Unbound selected BTR interpolation')
    return query


def count_queries(sql_filter='',sql_join_filter='',auth_cte=None):
    body=source().split('public responseMessage GetBTRDataCount(',1)[1].split('string vectorFlow_BufferTrend',1)[0]
    halves=body.split('text += authQueryForReports;')
    if len(halves)!=2: raise ValueError('Unexpected BTR count branches')
    result={}
    for name,half in zip(('eco','tech'),halves):
        parts=[]
        for line in half.splitlines():
            if not line.strip().startswith('text '): continue
            if '" and  " + sqlFilter' in line:
                if sql_filter: parts.append(' and '+sql_filter)
                continue
            parts.append(literals(line)+(sql_join_filter if 'sqlJoinFilter' in line else ''))
        result[name]=(auth_cte or CTE)+bindings(''.join(parts))
    return result
