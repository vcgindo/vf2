"""Selected no-filter SQL extracted from the pinned deployed insight methods."""
from pathlib import Path
import re
from parity.output_archive import file_sha
from parity.verify_excess_readmodel import literals

SOURCE=Path('D:/freshvcf-build/evidence/f3-insights-source-001/VectorFlowAPIs.VectorFlow.Processors.Replenishment.InsightsAndTrends.GuidedInsightsProcessor.decompiled.cs')
SOURCE_SHA='d2f578a2beda0b67226b3c85ae65d3a39fe732496237ee41f7c0a9b067f29249'
METHODS={'loc':'GetDBMNormSuggestionLoc','sku':'GetDBMNormSuggestionSKUs','pie':'GetDBMNormSuggestionPie',
    'ageing':'GetDBMNormSuggestionAgeing','chronic-loc':'GetChronicUnavailabilityLoc',
    'chronic-sku':'GetChronicUnavailabilitySku','chronic-grid':'ChronicUnavailabilityGridViewData',
    'availability-trend':'GetAvailabilityTrend','availability-ageing':'GetAvailabilityAgeing'}
TABLES=('ChronicUnavalabilityData','DBMNormSuggestionsData','LocationAttributeData','SkuAttributeData',
    'SkuLocAttributeData','SKUDescriptionTbl','SiteDescriptionTbl','BTRSnapshotForUI','LastBatchRunTbl','BPR')
CTE=';WITH cte_SKUs AS (SELECT DISTINCT SKUCode FROM #SkuAttributeData),cte_WhCodes AS (SELECT DISTINCT WHCode FROM #LocationAttributeData) '


def query(kind,*,horizon=90,ageing=1):
    if file_sha(SOURCE)!=SOURCE_SHA: raise ValueError('Canonical insight source changed')
    body=SOURCE.read_text().split('public responseMessage '+METHODS[kind]+'(',1)[1].split('\n\tpublic ',1)[0]
    variable='text3' if kind=='chronic-grid' else 'text'
    # C# assignments end at a semicolon OUTSIDE a quoted string. Selected
    # method bodies use only concatenated literals, known date parameters,
    # empty selected filters and approved database/auth operands here.
    pattern=r'(?m)^\s*(?:string )?'+variable+r'\s*(?:\+=|=)\s*((?:"(?:[^"\\]|\\.)*"|[^";])*);'
    parts=[]
    for match in re.finditer(pattern,body):
        expression=match.group(1)
        if re.search(r'\+\s*sqlFilter\b',expression): continue
        expression=re.sub(r'\bhorison(?:\.ToString\(\))?',f'"{int(horizon)}"',expression)
        expression=re.sub(r'\bageing\.ToString\(\)',f'"{int(ageing)}"',expression)
        parts.append(literals(expression))
    sql=CTE+''.join(parts)
    for old,new in (('.dbo.DBMMaster','#DBMMaster'),('.dbo.NMSAllItems','#NMSAllItems'),
                    ('.[dbo].[ChronicUnavalabilityData]','#ChronicUnavalabilityData')):
        sql=sql.replace(old,new)
    for table in sorted(TABLES,key=len,reverse=True):
        sql=re.sub(r'\['+table+r'\]|(?<![\w#])'+table+r'(?!\w)', ' #'+table+' ',sql,flags=re.I)
    if 'for json path' not in sql.lower() or 'Startup' in sql or 'sqlFilter' in sql:
        raise ValueError('Unexpected insight extraction')
    return sql
