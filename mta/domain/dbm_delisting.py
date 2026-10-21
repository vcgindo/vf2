"""Selected Rule12, including report population and SQL join multiplicity.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal
from mta.domain.ordinal_lookup import OrderedIndex


def _exact(*values):return tuple(values)


def delisting_recommendation(today,state):
    today=date.fromisoformat(today) if isinstance(today,str) else today
    if state['LastBatchRunTbl'] != [{'LastRunDate':today.isoformat()+'T00:00:00'}]:
        raise ValueError('Rule12 requires singleton midnight run date')
    values=[r['Value'] for r in state['VFSettings'] if r['Parameter']=='DBMDelistingDataPointPercent']
    if len(values)!=1:raise ValueError('Rule12 requires selected data-point percentage')
    percentage=Decimal(int(values[0]))/100
    key=lambda r:(r['SKUCode'],r.get('WhCode',r.get('WHCode')))
    day=lambda v:date.fromisoformat(v) if isinstance(v,str) else v
    result=deepcopy(state)
    suggestions=[r for r in result['Suggestions'] if r['Type']<12]
    prior={key(r) for r in suggestions}
    images=[]
    with OrderedIndex(state['SKULocStandardAttributes'],key=key,key_contract=_exact) as attr_index:
        for master in state['DBMMaster']:
            if master['OCP'] is None or master['MinOrderCount'] is None or master['Norm']<=0 or key(master) in prior:continue
            for attr in attr_index.candidates(key(master)):
                if key(attr)==key(master):
                    images.append({**master,'OCP':int(attr['ExtendedOCP']) if attr['ExtendedOCP'] is not None else None})
    observations={}
    with OrderedIndex(state['DailyConsumption'],key=key,key_contract=_exact) as fact_index:
        for image in images:
            for fact in fact_index.candidates(key(image)):
                if (key(fact)==key(image) and image['OCP'] is not None
                        and today-timedelta(days=image['OCP'])<=day(fact['ReportDate'])<=today):
                    observations.setdefault(key(image),[]).append(fact)
    siblings={}
    for image in images:
        count,period=siblings.get(key(image),(0,None))
        value=image['OCP']
        siblings[key(image)]=(count+1,value if period is None else period if value is None else max(period,value))
    eligible=[]
    for image in images:
        count,period=siblings[key(image)]
        joined_count=count*max(1,len(observations.get(key(image),[])))
        if period is not None and joined_count<period*percentage:continue
        eligible.append(image)
    reports=[]
    sku_key=lambda r:(r['SKUCode'],)
    site_key=lambda r:(r['WHCode'],)
    positives={}
    with OrderedIndex(state['SKUDescriptionTbl'],key=sku_key,key_contract=_exact) as sku_index, \
         OrderedIndex(state['SiteDescriptionTbl'],key=site_key,key_contract=_exact) as site_index:
        for image in eligible:
            identity=key(image)
            if identity not in positives:
                positives[identity]=[r for r in observations.get(identity,[]) if r['Consumption'] is not None and r['Consumption']>0]
            positive=positives[identity]
            if len(positive)>=image['MinOrderCount']:continue
            sku_names=[r['SKUDescription'] for r in sku_index.candidates((image['SKUCode'],)) if r['SKUCode']==image['SKUCode']]
            site_names=[r['WHDescription'] for r in site_index.candidates((image['WhCode'],)) if r['WHCode']==image['WhCode']]
            if not sku_names or not site_names:continue
            strings=[f"[{day(r['ReportDate']).strftime('%d/%m/%Y')} - {r['Consumption']}]" for r in positive]
            if len(set(strings))>1:
                raise ValueError('SOURCE_ORDER_AMBIGUITY: Rule12 unordered STRING_AGG occurrence text')
            for sku in sku_names:
                for site in site_names:
                    reports.append({'SKUCode':image['SKUCode'],'SKUDescription':sku,'WhCode':image['WhCode'],
                        'WHDescription':site,'Norm':image['Norm'],'OCP':image['OCP'],
                        'MinOrderCount':image['MinOrderCount'],'ConsumptionCount':len(positive),
                        'TotalConsumption':sum(r['Consumption'] for r in positive),'ConsumptionOcurrences':', '.join(strings)})
    result['DBMDelistingOfNormsWithHits']=reports
    result['Suggestions']=suggestions+[{'SKUCode':r['SKUCode'],'WhCode':r['WhCode'],'Type':12,'NewNorm':0} for r in reports]
    result['IntermediateTables']=[{'table':r['table'],'rows':[]} for r in state['IntermediateTables']]
    return result
