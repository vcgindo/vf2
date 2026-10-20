"""Accepted active-NMS master reuse with an exact compatibility row view.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.

The view projects the existing NMSCreateSnapshot output. It is qualified only
after comparison with a complete canonical producer result at a committed
master generation. Neither an empty queue nor an arbitrary prior qualifies it.
"""
from copy import deepcopy
from functools import cached_property
import json
from mta.row_sequences import RecordRows, CanonicalWireRows
from mta.serialization import digest, storage
from mta.application.r1_importer_master import RAW_COLUMNS, PRIOR_TABLES, DESCRIPTIONS

CONTRACT = 'native-persistent-master-v1'


def _row(item):
    return {name: None if name == 'MOQ' else item[name] for name in RAW_COLUMNS}


class NmsMasterRows(RecordRows,CanonicalWireRows):
    """Immutable engine/compatibility projection; no second population owner."""
    def __init__(self, rows, *, canonical=False, reference=None, snapshot=None, business_date=None, plan=None):
        self.reference = reference
        self.canonical = canonical
        if plan is None and snapshot is not None:
            from mta.application.master_compatibility import unchanged_plan
            plan=unchanged_plan(snapshot,rows,business_date)
        if plan is not None:
            view=plan.view(canonical=canonical)
            super().__init__(len(view),lambda: iter(view),getitem=lambda i:view[i])
        else:
            # Pure legacy view retained for non-native readers and old manifests.
            ordinals=(sorted(range(len(rows)),key=lambda i:json.dumps(_row(rows[i]),sort_keys=True))
                      if canonical else range(len(rows)))
            super().__init__(len(rows),lambda:(_row(rows[i]) for i in ordinals))



def settings(prior):
    return [{'Parameter': row['Parameter'],'Value':int(row['Value'])}
        for row in prior['importer_settings']
        if row['Parameter'] in ('NMSActive','DBMActive','UpdatePWh_RLT_RCP_GCP')]


def static_tables(prior):
    result=deepcopy(prior['importer'])
    for rows in result.values():
        for row in rows:
            for name,value in row.items():
                if type(value) is bool:
                    row[name]=int(value)
        rows.sort(key=lambda row:json.dumps(row,sort_keys=True))
    return result


class MasterReuse:
    def __init__(self, prior, snapshot, business_date):
        self.prior=prior
        from mta.application.master_compatibility import unchanged_plan
        self.plan=unchanged_plan(snapshot,prior['consumer_context']['NMSAllItems'],business_date)

    @cached_property
    def result(self):
        return reused(self.prior,self.plan)


def select(prior, profile, day, snapshot, previous, cut):
    if not eligible(profile,day,snapshot,previous,cut):
        return None
    # Qualification excludes the operational Norm. A later NULL must still go
    # through the canonical producer, which owns its original rejection.
    if any(row['SKUCode'] is not None and row['WhCode'] is not None
           and row['Norm'] is None for row in prior['consumer_context']['NMSAllItems']):
        return None
    return MasterReuse(prior,snapshot,day['business_date'])


def eligible(profile, day, snapshot, previous, cut):
    if (not isinstance(previous,dict) or previous.get('contract') != CONTRACT
            or previous.get('qualified') is not True
            or previous.get('configuration_digest') != digest(profile)
            or previous.get('master_cut') != list(cut[:2])
            or profile['import_non_nms'] or day['raw_non_nms'] or day['raw_no_norm']
            or snapshot.get('nms_active') is not True):
        return False
    for family, names in (('sku',('approved',)),('location',('approved',)),
                          ('skuloc',('additions','modifications','removals'))):
        if any(row['Approved'] for name in names for row in snapshot['rows'][family][name]):
            return False
    return True


def reused(prior,plan):
    tables=static_tables(prior)
    tables.update(MasterDataRaw=NmsMasterRows(prior['consumer_context']['NMSAllItems'],canonical=True,plan=plan),
                  MasterDataRawNonNMS=[],NoNormMasterRaw=[])
    return dict(outcome='APPLIED',tables=tables,rejects_added=[],retired_events_added=[])


def qualify(master, profile, day, closing, snapshot=None):
    """Root/changed generations qualify only by complete canonical compatibility."""
    flags=settings(closing)
    active=lambda name: sum(row['Parameter']==name and row['Value']==1 for row in flags)==1
    if (master['outcome']!='APPLIED' or profile['import_non_nms'] or snapshot is None
            or day['raw_non_nms'] or day['raw_no_norm'] or not active('NMSActive')
            or not active('DBMActive')):
        return False
    try:
        from mta.application.master_compatibility import unchanged_plan
        plan=unchanged_plan(snapshot,closing['consumer_context']['NMSAllItems'],day['business_date'])
    except ValueError:
        return False
    # Operational Norm and date-sensitive standalone introductions are projected
    # from the next day's own NMS/date, never frozen into the accepted masters.
    project=lambda row: {k:v for k,v in row.items() if k not in ('Norm','SKUIntroDate')}
    ordered=lambda rows: sorted((project(row) for row in rows),key=lambda row:json.dumps(row,sort_keys=True))
    return storage(ordered(master['tables']['MasterDataRaw']))==storage(ordered(plan.canonical))


class MasterChange:
    """A changed-only dependency closure; canonical producer owns every rule."""
    def __init__(self,parent,snapshot):
        self.parent=parent
        rows=snapshot['rows']
        self.changed=dict(sku=[r['SKUCode'] for r in rows['sku']['approved'] if r['Approved']],
            location=[r['WHCode'] for r in rows['location']['approved'] if r['Approved']],
            pair=[dict(SKUCode=r['SKUCode'],WhCode=r['WhCode'])
                  for name in ('additions','modifications') for r in rows['skuloc'][name] if r['Approved']],
            retirement=[dict(SKUCode=r['SKUCode'],WhCode=r['WhCode'])
                  for r in rows['skuloc']['removals'] if r['Approved']],**{'global':False})
        self.work=None

    def prepare(self,payload):
        from mta.runtime.input_reader import read_input
        from mta.application.master_preparation import prepare_changed,_canonical_raw
        prior=read_input(self.parent,components=('input/day/raw_master',))['day']['raw_master']
        canonical=_canonical_raw(prior,self.parent.business_date.isoformat())
        outcome=prepare_changed(payload,canonical,self.changed)
        self.work=outcome['work']
        return outcome['result']


def changed(prior_run,profile,snapshot,base_revision_id):
    previous=prior_run.production_manifest.get('master_preparation',{})
    if (previous.get('qualified') is not True or previous.get('configuration_digest')!=digest(profile)
            or snapshot.get('nms_active') is not True):
        return None
    from mta.runtime.ingestion_models import MasterInputRevision
    base=MasterInputRevision.objects.get(pk=base_revision_id,status='ACCEPTED')
    if [base.master_epoch,base.configuration_epoch]!=previous.get('master_cut'):
        return None
    rows=snapshot['rows']
    if not any(r['Approved'] for family,names in (('sku',('approved',)),('location',('approved',)),
            ('skuloc',('additions','modifications','removals')))
            for name in names for r in rows[family][name]):
        return None
    return MasterChange(prior_run,snapshot)
