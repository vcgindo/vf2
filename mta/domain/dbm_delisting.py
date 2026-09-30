"""Selected Rule12, including report population and SQL join multiplicity."""
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal


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
    for master in state['DBMMaster']:
        if master['OCP'] is None or master['MinOrderCount'] is None or master['Norm']<=0 or key(master) in prior:continue
        for attr in state['SKULocStandardAttributes']:
            if key(attr)==key(master):
                images.append({**master,'OCP':int(attr['ExtendedOCP']) if attr['ExtendedOCP'] is not None else None})
    observations={}
    for image in images:
        for fact in state['DailyConsumption']:
            if (key(fact)==key(image) and image['OCP'] is not None
                    and today-timedelta(days=image['OCP'])<=day(fact['ReportDate'])<=today):
                observations.setdefault(key(image),[]).append(fact)
    eligible=[]
    for image in images:
        siblings=[r for r in images if key(r)==key(image)]
        periods=[r['OCP'] for r in siblings if r['OCP'] is not None]
        joined_count=len(siblings)*max(1,len(observations.get(key(image),[])))
        if periods and joined_count<max(periods)*percentage:continue
        eligible.append(image)
    reports=[]
    for image in eligible:
        positive=[r for r in observations.get(key(image),[]) if r['Consumption'] is not None and r['Consumption']>0]
        if len(positive)>=image['MinOrderCount']:continue
        sku_names=[r['SKUDescription'] for r in state['SKUDescriptionTbl'] if r['SKUCode']==image['SKUCode']]
        site_names=[r['WHDescription'] for r in state['SiteDescriptionTbl'] if r['WHCode']==image['WhCode']]
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
