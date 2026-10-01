"""Extract selected deployed history/DBM query builders without SQL repair."""
import json
from pathlib import Path
import re
from parity.output_archive import file_sha

BASE=Path('D:/freshvcf-build/evidence')
SOURCES={
 'scih':(BASE/'f3-dbmhist-source-001/VectorFlowAPIs.VectorFlow.Processors.Replenishment.SCIH.SCIHProcessor.decompiled.cs','f709a448c1bb6f6af6583975a13a88cf3cb009caee516bc2fe867af21eb624e5'),
 'dbm':(BASE/'f3-dbmhist-source-001/VectorFlowAPIs.VectorFlow.Processors.DBMProcessor.decompiled.cs','7339a2e04aab1b2c4108bb182721dfb057ab65267fcee027c88480e6c449aea5'),
 'bpr':(BASE/'f3-dbmhist-source-002/VectorFlowAPIs.VectorFlow.Processors.Replenishment.SCIH.BPRProcessor.decompiled.cs','68b9680373d7edf530fe5985f89d88d67b6fc4f7f1870112230cba9c7bb6b03b')}
TABLES=('BufferTrendPhysicalInv','BufferTrendDispatch','BufferTrendDates','SkuAttributeData',
    'LocationAttributeData','SkuLocAttributeData','DBMMaster','Suggestions','NormAcceptanceTbl',
    'SKUDescriptionTbl','SiteDescriptionTbl','ReasonCodes')
CTE=';WITH cte_SKUs AS (SELECT DISTINCT SKUCode FROM #SkuAttributeData),cte_WhCodes AS (SELECT DISTINCT WHCode FROM #LocationAttributeData) '


def method(source,name):
    path,sha=SOURCES[source]
    if file_sha(path)!=sha: raise ValueError('Canonical consumer source changed')
    return path.read_text().split(' '+name+'(',1)[1].split('\n\tpublic ',1)[0]


def concat(expression,parameters):
    # Consume whole quoted literals before considering identifiers; never
    # rewrite a word inside an SQL literal as a C# parameter.
    return ''.join(json.loads(t) if t.startswith('"') else parameters.get(t,'')
        for t in re.findall(r'"(?:[^"\\]|\\.)*"|\b[A-Za-z_]\w*\b',expression))


def assignments(body,variable,parameters,*,sql_filter=''):
    pattern=r'(?m)^\s*(?:string )?'+variable+r'\s*(?:\+=|=)\s*((?:"(?:[^"\\]|\\.)*"|[^";])*);'
    parts=[]
    for match in re.finditer(pattern,body):
        expression=match.group(1)
        if re.search(r'\+\s*(?:sqlFilter|text3)\b',expression):
            if sql_filter and re.search(r'\+\s*sqlFilter\b',expression): parts.append(' and '+sql_filter)
            continue
        if 'masterRoot.paginationParameter ==' in expression: continue
        parts.append(concat(expression,parameters))
    return ''.join(parts)


def bind(query):
    query=query.replace('.DBO.BPRMaster','#BPRMaster')
    for name in sorted(TABLES,key=len,reverse=True):
        query=re.sub(r'\['+name+r'\]|(?<![\w#])'+name+r'(?!\w)',' #'+name+' ',query,flags=re.I)
    return query


def buffer_query(kind,days):
    body=method('scih','GetBufferGraphData').split('strSql = authQueryForReports;',1)[1].split('ErrorLog.Logger(',1)[0]
    cols=range(91-days,91)
    parameters=dict(text='BufferTrendDispatch' if kind=='eco' else 'BufferTrendPhysicalInv',
        text4=','.join(f"({i}, 'D{i}')" for i in cols),text5=','.join(f'( {i}, D{i})' for i in cols),
        text6=' ; Select '+','.join(f'D{i}' for i in cols)+' from BufferTrendDates ;')
    return bind(CTE+assignments(body,'strSql',parameters))


def availability_query():
    body=method('bpr','GetHistroricalAvailabilityBPRData').split('for (int i = 1; i <= 30; i++)',1)[1].split('string text5',1)[0]
    branches=[]
    for i in range(1,91):
        sql=assignments(body,'text4',dict(i=str(i),text='BufferTrendPhysicalInv'))
        if not sql.endswith(' union all '): raise ValueError('Historical loop extraction changed')
        branches.append(sql[:-len(' union all ')])
    return bind(CTE+' union all '.join(branches))


def dbm_query(*,count=False,page=1,size=5000,sql_filter='',sql_join_filter='',auth_cte=None):
    body=method('dbm','GetDBMDataCount' if count else 'GetDBMData').split('string vectorPULLFG_DBM',1)[0]
    sql=(auth_cte or CTE)+assignments(body,'text2',dict(sqlJoinFilter=sql_join_filter),sql_filter=sql_filter)
    if not count: sql+=f' where RN between ({page}-1)*{size}+1 and ({page}*{size}) for json path) dbm'
    return bind(sql)
