"""Extract exact deployed BPR count/key-page/grid SQL, changing table bindings only."""
import json
from pathlib import Path
import re
from parity.output_archive import file_sha
from parity.verify_excess_readmodel import literals

SOURCE = Path('D:/freshvcf-build/evidence/f3-canonical-api-001/VectorFlowAPIs.VectorFlow.Processors.Replenishment.SCIH.BPRProcessor.decompiled.cs')
SOURCE_SHA = '68b9680373d7edf530fe5985f89d88d67b6fc4f7f1870112230cba9c7bb6b03b'


def source():
    if file_sha(SOURCE) != SOURCE_SHA:
        raise ValueError('Selected deployed BPR source changed')
    return SOURCE.read_text()


def bindings(query):
    query = query.replace('{((DbConnection)sqlConnection).Database}.dbo.SKULocStandardAttributes', '#Standard')
    query = query.replace('{Startup.BTRServerName}.dbo.BufferTrendPhysicalInv', '#Trend')
    query = query.replace('.dbo.InTransitData', '#Transit').replace('.dbo.SKULocStandardAttributes', '#Standard')
    for old, new in (('BPR_Table','#Bpr'), ('vf_RationedReqReport','#Rationed'),
                     ('SkuAttributeData','#Sku'), ('LocationAttributeData','#Loc'),
                     ('SkuLocAttributeData','#Pair'), ('BPRReport_RemarkDetails','#Remarks')):
        query = re.sub(r'(?<![#\w])' + old + r'\b', new, query, flags=re.I)
    if '{' in query or 'Startup.' in query:
        raise ValueError('Unbound deployed SQL interpolation')
    return query


def queries(auth, page=1, size=5000):
    text = source()
    selector = text.split('private string getBPRSelectQuery(',1)[1].split('if (flag == 1)',1)[0]
    select_line = next(line for line in selector.splitlines() if line.strip().startswith('text = "Select tags,'))
    selected = literals(select_line)
    body = text.split('public async System.Threading.Tasks.Task<responseMessage> GetBPRDataAsync(',1)[1]
    lines = body.splitlines()
    prefix = next(line.strip()[len('strSql5 += $'):-1] for line in lines if line.strip().startswith('strSql5 += $", cte_Top5000'))
    ordering = next(line for line in lines if line.strip().startswith('strSql5 += "ORDER BY'))
    suffix = next(line.strip()[len('strSql5 += $'):-1] for line in lines if line.strip().startswith('strSql5 += $" FROM cte_Top5000'))
    # Positive pagination is the selected deployed contract; null pagination is not repaired.
    paging = next(line.strip()[len('strSql5 += $'):-1] for line in lines if line.strip().startswith('strSql5 += $" OFFSET'))
    paging = json.loads(paging).replace('{(masterRoot.paginationParameter.PageNumber - 1) * masterRoot.paginationParameter.RecordsPerPage}', str((page-1)*size))
    paging = paging.replace('{masterRoot.paginationParameter.RecordsPerPage}', str(size))
    grid = auth + json.loads(prefix).replace('{sqlJoinFilter}', '') + literals(ordering) + paging + selected + json.loads(suffix)
    count_body = text.split('public responseMessage GetBPRDataCount(',1)[1].split('if (sqlFilter',1)[0]
    count_concat = count_body.split('string.Concat(new string[6]',1)[1]
    count = auth + literals(count_concat)
    return dict(count=bindings(count), grid=bindings(grid))
