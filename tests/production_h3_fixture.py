"""Declared finite H3 integration inputs, derived from the supplied H2 fixture.

Only test input construction lives here. Synthetic facts are external inputs;
no calculated norms, orders, histories or future daily outputs are seeded.
"""
from copy import deepcopy

from tests.production_daily_fixture import initialized_input, day_input, SKU, CHILD, ROOT

FORCE=SKU
PHASE='SUPPLIED-PHASE'
PHASE_IN='SUPPLIED-NEXT'
SEASON='SUPPLIED-SEASON'
SKUS=(FORCE,PHASE,PHASE_IN,SEASON)
DIST='OWN-DIST';VENDOR='OWN-VENDOR';DMS='OWN-DMS';PARENT='OWN-PARENT'


def supplied_input(*, moq_format='WithDestLoc'):
    value=initialized_input()
    # Restore the operator spelling and all selected report flags; prior reduced
    # proof-only identity/profile deltas are not acceptance substitutes.
    def restore(node):
        if isinstance(node,dict):return {k:restore(v) for k,v in node.items()}
        if isinstance(node,list):return [restore(v) for v in node]
        return 'SUPPLIED-Z9' if node==SKU else node
    value=restore(value)
    master=value['masters']['importer']
    for name in ('SkuAttributeData','SKUDescriptionTbl','MasterData','SkuLocAttributeData'):
        old=deepcopy(master[name])
        master[name]=[{**row,'SKUCode':sku} for sku in ('SUPPLIED-Z9',PHASE,PHASE_IN,SEASON)
                      for row in old if row.get('LocCode',CHILD)!=ROOT or sku=='SUPPLIED-Z9']
    for row in master['SkuAttributeData']:row['ElephantOrderCapping']=50
    base_pair=next(r for r in master['SkuLocAttributeData'] if r['LocCode']==CHILD)
    base_norm=master['MasterData'][0]
    for loc,kind in ((DIST,'Distributor'),(VENDOR,'Vendor'),(DMS,'Warehouse')):
        master['LocationAttributeData'].append(dict(master['LocationAttributeData'][0],WHCode=loc,LocationType=kind))
        master['SiteDescriptionTbl'].append(dict(WHCode=loc,WHDescription='Supplied '+loc))
        master['SkuLocAttributeData'].append(dict(base_pair,LocCode=loc))
        master['MasterData'].append(dict(base_norm,WhCode=loc))
    for row in master['MasterData']:
        if row['SKUCode']=='SUPPLIED-Z9':row['ParentWhCode']=PARENT
    master['LocationAttributeData'].append(dict(master['LocationAttributeData'][0],WHCode=PARENT))
    master['SiteDescriptionTbl'].append(dict(WHCode=PARENT,WHDescription='Supplied '+PARENT))
    master['SkuLocAttributeData'].append(dict(base_pair,LocCode=PARENT))
    master['MasterData'].append(dict(base_norm,WhCode=PARENT,ParentWhCode=ROOT,Norm=36))
    for row in master['SkuLocAttributeData']:row.update(SpikeThreshold=20,PSOThreshold=20)
    for owner in ('btr','dbm'):
        value['masters'][owner]={name:deepcopy(master[name]) for name in ('SkuAttributeData','SKUDescriptionTbl')}
    state=value['opening']['state']
    current_template=state['consumer_context']['NMSAllItems'][0]
    current=[]
    for row in master['MasterData']:
        pair=next(r for r in master['SkuLocAttributeData'] if (r['SKUCode'],r['LocCode'])==(row['SKUCode'],row['WhCode']))
        attr=next(r for r in master['LocationAttributeData'] if r['WHCode']==row['WhCode'])
        current.append(dict(current_template,**row,ElephantOrderCapping=50,
            SpikeThreshold=20,PSOThreshold=20,LocationType=attr['LocationType'],WHDescription='Supplied '+row['WhCode']))
    state['consumer_context']['NMSAllItems']=current
    state['bpr']['BPRMaster']=[dict(SKUCode=r['SKUCode'],WHCode=r['WhCode'],Norm=r['Norm'],
        ParentWhCode=r['ParentWhCode'],SKUIntroDate=r['SKUIntroDate']) for r in master['MasterData']]
    for owner,name in (('dbm','DBMMaster'),('controls','dbm_master'),('controls','importer_master')):
        state[owner][name]=deepcopy(master['MasterData'])
    for row in state['importer_settings']:
        if row['Parameter']=='NMSMOQInputDataFormat':row['Value']=moq_format
    state['controls']['importer_settings']=deepcopy(state['importer_settings'])
    state['complete']['SOBDataRaw']=[dict(SKUCode='SUPPLIED-Z9',WHCode=CHILD,
        SupplierCode=ROOT,SupplierDescription='Supplied '+ROOT,SOB=100.0)]
    state['complete']['MOQDataRaw1' if moq_format=='WithoutDestLoc' else 'MOQDataRaw2']=[dict(
        SKUCode='SUPPLIED-Z9',SupplierCode=ROOT,SupplierDescription='Supplied '+ROOT,MOQ=1,
        **({} if moq_format=='WithoutDestLoc' else {'WHCode':CHILD}))]
    state['complete']['SOBDataRaw'][0]['WHCode']=PARENT
    if moq_format=='WithDestLoc':state['complete']['MOQDataRaw2'][0]['WHCode']=PARENT
    config=value['configuration'];calc=config['calculation']
    calc['skus']=[dict(sku_code=r['SKUCode'],description='Supplied '+r['SKUCode']) for r in master['SkuAttributeData']]
    calc['locations']=[dict(location_code=r['WHCode'],description='Supplied '+r['WHCode'],
        location_type=r['LocationType']) for r in master['LocationAttributeData']]
    opening_template=calc['stock_openings'][0];policy_template=calc['policies'][0]
    calc['stock_openings']=[dict(opening_template,sku_code=r['SKUCode'],location_code=r['WhCode']) for r in master['MasterData']]
    calc['policies']=[dict(deepcopy(policy_template),sku_code=r['SKUCode'],location_code=r['WhCode']) for r in master['MasterData']]
    calc['logistics'].update(vehicles=[dict(vehicle_id=1,name='Supplied vehicle',weight_capacity='10',volume_capacity='10')],
        location_vehicles=[dict(location_code=location,vehicle_id=1) for location in (ROOT,PARENT)])
    config['daily'].update(shell_flags=dict.fromkeys(config['daily']['shell_flags'],1),
        distributor_codes=[DIST],vendor_codes=[VENDOR],vector_dms_codes=[DMS],
        module_sources=dict(distributor_norms=[dict(SKUCode='SUPPLIED-Z9',WhCode=DIST)],
                            vendor_master=[dict(SKUCode='SUPPLIED-Z9',WhCode=VENDOR)]))
    config['delivery']['batch'].update(AutoDBMActive=1,PhaseOutRecommendation30Days=1,
        PhaseOutRecommendation60Days=1,PhaseOutRecommendation90Days=1,
        PhaseOutRecommendationTolerance30Days=29,PhaseOutRecommendationTolerance60Days=59,
        PhaseOutRecommendationTolerance90Days=89,
        Norm1Increase_MultipleRLT=1,Norm2Decrease_MultipleRLT=1,
        ActivateNorm0Report60Days=1,ActivateNorm0Report90Days=1)
    config['delivery']['btr_settings'].update(CaptureDispatchExecutionEfficiency=1,RationingHistoryHorizonBTR=30)
    config['delivery']['btr_history']=dict(importer_vf_settings=[dict(Parameter='CaptureDispatchExecutionEfficiency',Value='1',Description='Declared test configuration')])
    state['dbm']['DBMSettingsTbl'].append(dict(Parameter='NormZeroOneRuleActive',Value='1'))
    config['delivery']['conditional_dbm']=dict(importer_vf_settings=[dict(Parameter=name,Value=value,Description='Declared test configuration')
            for name,value in (('Norm1IncreaseCountThreshold','0'),('Norm2DecreaseCountThreshold','0'),('Norm2DecreaseDataPointPercent','0'))])
    value['recipe']['version']='supplied-h3-positive-integration-v1'
    value['opening']['identity']='SUPPLIED-H3-POSITIVE-'+moq_format
    return value


def supplied_day(day,*,root=False):
    value=day_input(day,root=root)
    value['day']['raw_daily']=[dict(SKUCode=sku,WhCode=loc,Stock=10,
        # Stopped PhaseOut/PhaseIn becomes Norm0. Zero external sales retain the unchanged
        # 30-day unordered-occurrence restriction across consecutive inputs.
        Consumption=0 if sku in (PHASE,PHASE_IN) else 2,GIT=4,Receipts=1,PSO=0,ReportDate=day) for sku in ('SUPPLIED-Z9',PHASE,PHASE_IN,SEASON)
        for loc in (CHILD,)]
    value['day']['raw_daily'] += [dict(SKUCode='SUPPLIED-Z9',WhCode=loc,Stock=5,
        Consumption=2,GIT=4,Receipts=1,PSO=0,ReportDate=day) for loc in (DIST,VENDOR,DMS)]
    value['day']['raw_daily'].append(dict(SKUCode='SUPPLIED-Z9',WhCode=PARENT,Stock=40,
        Consumption=0,GIT=0,Receipts=0,PSO=0,ReportDate=day))
    value['day']['raw_daily'] += [dict(SKUCode=sku,WhCode=ROOT,Stock=40,
        Consumption=0,GIT=0,Receipts=0,PSO=0,ReportDate=day) for sku in ('SUPPLIED-Z9',PHASE,PHASE_IN,SEASON)]
    value['day']['order_feed']=[dict(OrderID=oid,SKUCode='SUPPLIED-Z9',WhCode=CHILD,Qty=qty,CustomerExpDate=None)
        for oid,qty in (('ELEPHANT-Z',60),('ELEPHANT-A',65),('ORDINARY',1),('SPIKE',15))]
    return value
