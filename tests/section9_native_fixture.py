"""Bounded raw facts for positive native Section9 SQL acceptance.

These are separate small test facts, never changes to the accepted large day.
DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import json
from pathlib import Path
import zipfile


def source_archive(original, destination):
    with zipfile.ZipFile(original) as source:
        bodies={name:source.read(name) for name in source.namelist()}
    opening=json.loads(bodies['initialization.json'])
    # Previously absent physical dimensions/vehicles excluded all Pick rows.
    # Supply small exact physical facts and retain all daily quantities/orders.
    for owner in opening['masters'].values():
        for row in owner.get('SkuAttributeData',[]):row.update(Weight='1.000',Volume='1.000')
    for row in opening['opening']['state']['consumer_context']['NMSAllItems']:
        row.update(Weight='1.000',Volume='1.000')
    locations=opening['configuration']['calculation']['locations']
    opening['configuration']['calculation']['logistics'].update(
        vehicles=[dict(vehicle_id=1,name='Section9 small vehicle',weight_capacity='10.000',volume_capacity='10.000')],
        location_vehicles=[dict(location_code=row['location_code'],vehicle_id=1) for row in locations])
    bodies['initialization.json']=json.dumps(opening).encode()
    with zipfile.ZipFile(destination,'x') as target:
        for name,body in bodies.items():target.writestr(name,body)
    return Path(destination)


def enqueue_control(owner):
    from django.db import transaction
    from mta.mdm.supplier_revisions import source_lock
    from mta.runtime.mdm_force_models import MdmForceQueue
    with transaction.atomic(),source_lock(owner.source_id,deciding=True):
        return MdmForceQueue.objects.create(source=owner.source,SKUCode='5708',WhCode='DP010290',
            NewNorm=40,Approved=True,RequestedBy='section9-isolated-control-fact')


def verify_positive(test,run):
    from mta.runtime.services import read_outputs
    from mta.runtime.receipt_integrity import audit_input,audit_output,verify
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    value=read_outputs(run);closing=value['ClosingState'][0]
    test.assertTrue(closing['complete']['LogisticPickList'],'native positive Pick required')
    from mta.runtime.production_report_storage import read
    orders=read(run,'AllocatedOrders')
    test.assertTrue(any(row['OrderWiseAllocatedQty']>0 for row in orders),'native positive order allocation required')
    test.assertTrue(closing['dbm']['SuspendHistory'])
    test.assertTrue(closing['dbm']['NormChangeLogTbl'])
    test.assertTrue(closing['btr']['BPR']);test.assertTrue(closing['btr']['BTRSnapshotForUI'])
    test.assertEqual(MdmDailyInputCapture.objects.get(run=run).status,'CONSUMED')
    audit_input(run);audit_output(run);verify(run)
    print('SECTION9_POSITIVE_NATIVE_PASS native-orders='+str(len(orders))+
        ' pick='+str(len(closing['complete']['LogisticPickList']))+
        ' controls/history+BTR full typed readback/capture-consumption')
