"""Extract the ten actual deployed overview queries with binding-only changes."""
import re
from pathlib import Path
from parity.output_archive import file_sha
from parity.verify_excess_readmodel import literals

SOURCE = Path('D:/freshvcf-build/evidence/f3-dbmhist-source-001/VectorFlowAPIs.VectorFlow.Processors.Replenishment.SCIH.SCIHProcessor.decompiled.cs')
SOURCE_SHA = 'f709a448c1bb6f6af6583975a13a88cf3cb009caee516bc2fe867af21eb624e5'


def queries(auth):
    if file_sha(SOURCE) != SOURCE_SHA:
        raise ValueError('Selected deployed SCIH source changed')
    method = SOURCE.read_text().split('private static string GetQuadrantDetailsQuery(',1)[1].split('public static responseMessage GetInTransitWhereAbouts(',1)[0]
    statements, pending = [], []
    for line in method.splitlines():
        if not pending and not line.strip().startswith('strSql '):
            continue
        pending.append(line)
        if line.rstrip().endswith(';'):
            statement = '\n'.join(pending)
            if not re.search(r'\bsqlFilter\b',statement):
                statements.append(literals(statement))
            pending = []
    if pending:
        raise ValueError('Incomplete deployed SQL extraction')
    sql = ''.join(statements)
    for old,new in (('.dbo.[SKULocStandardAttributes]','#Standard '),('.dbo.InTransitData','#Transit'),
                    ('.[dbo].[ExpediteDispatches]','#Expedite '),('.[dbo].[ExcessInventoryDetails]','#Excess '),
                    ('[GoodsInTransitMaster]',' #Git '),('GoodsInTransitTransporterMaster','#Transporter'),
                    ('[OrderFulfillmentData]','#Fulfillment'),('OrderFulfillmentData','#Fulfillment'),
                    ('ExpediteDispatches','#Expedite'),('ExcessInventoryDetails','#Excess'),
                    ('SKUDescriptionTbl','#SkuDesc'),('SiteDescriptionTbl','#LocDesc'),
                    ('SkuLocAttributeData','#Pair'),('SkuAttributeData','#Sku'),
                    ('LocationAttributeData','#Loc'),('LastBatchRunTbl','#LastDate')):
        sql = sql.replace(old,new)
    selected = [q.strip() for q in sql.split(';') if q.strip()]
    if len(selected) != 10 or any(not re.match(r'select\s+count\(1\)',q,re.I) for q in selected):
        raise ValueError('Expected exactly ten deployed count statements')
    if '.dbo.' in sql or 'sqlFilter' in sql:
        raise ValueError('Unresolved source binding')
    return [auth + q for q in selected]


def response(values):
    if len(values) != 10:
        raise ValueError('Deployed result roster differs')
    return [dict(category='git/wip',parentCount=str(values[0]),childCount=str(values[1]),custom=str(values[2])),
        dict(category='expedite',parentCount=str(values[3]),childCount=str(values[4]),custom=str(values[5])),
        dict(category='excessInventory',reviewCount=str(values[6]),custom=str(values[7])),
        dict(category='orderFulfillment',reviewCount=str(values[8]),custom=str(values[9]))]
