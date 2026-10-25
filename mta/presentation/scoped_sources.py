"""Named immutable BPR sources, before report preparation or serving selection.

Logical consumer names retain their existing vocabulary. Physical image names
and producer provenance remain those of the accepted phase, including inherited
PRE_BPR storage. No terminal output, DBM/BTR result, or missing source is made up.
"""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime

from mta.serialization import digest
from mta.presentation.context import PublicationUnavailable
from mta.presentation.request_scope import once_per_request
from mta.runtime import phase_state
from mta.runtime.relational_state import load_image,quote,table_sql

SCHEMA='fresh-bpr-read-sources-v1'
IMPORTER=('MasterData','SKUDescriptionTbl','SiteDescriptionTbl','SkuAttributeData',
          'LocationAttributeData','SkuLocAttributeData')
# These are consumer aliases, not claims that DBM or terminal publication ran.
SOURCES={
    **{'closing/importer/'+name:('state','importer',name) for name in IMPORTER},
    'closing/dbm/SKULocStandardAttributes':('state','standard_attributes'),
    'closing/bpr/BPRMaster':('state','bpr_master'),
    'reports/bpr/BPR_Table':('state','late','BPR_Table'),
    'reports/bpr/vf_RationedReqReport':('state','late','vf_RationedReqReport'),
    'closing/bpr/DailyConsumption':('state','late','BPRDailyConsumption'),
    'metadata/bpr/LastBatchRunTbl':('state','late','BPRLastBatchRunTbl'),
    'closing/orders/SpikeOrderData':('state','order_state','SpikeOrderData'),
    'closing/complete/LogisticPickList':('state','pick_state','LogisticPickList'),
    'closing/complete/PickListDataForTruckFormation':('state','pick_state','PickListDataForTruckFormation'),
    'sources/calculation/PickBands':('consumers','pick_bands'),
    'sources/calculation/OrderRoutes':('consumers','routes'),
}


def _image(manifest,node):
    for key in node:
        if not isinstance(manifest,dict) or key not in manifest:return None
        manifest=manifest[key]
    if not isinstance(manifest,dict) or set(manifest)!={'image'}:return None
    return manifest['image']


def _checked(item):
    if (type(item) is not dict or item.get('table') not in phase_state.REGISTRY
            or type(item.get('image')) is not str or not item['image'].startswith(('phase/BPR/','phase/PRE_BPR/'))
            or type(item.get('count')) is not int or item['count']<0
            or type(item.get('fields')) is not list or item['count'] and not item['fields']):
        raise PublicationUnavailable('bpr_phase_image_identity_differs')
    from mta.runtime.ingestion_context import sha
    try:sha(item.get('digest'))
    except ValueError as error:raise PublicationUnavailable('bpr_phase_image_digest_differs') from error
    columns=dict(phase_state.REGISTRY[item['table']])
    seen=set()
    for field in item['fields']:
        if (not isinstance(field,(list,tuple)) or len(field)!=3 or type(field[0]) is not str
                or field[0] in seen or field[1] not in columns or field[2] not in ('str','int','float','bool')):
            raise PublicationUnavailable('bpr_phase_image_fields_differ')
        seen.add(field[0])
    return item


@dataclass(frozen=True)
class BprSources:
    run: object
    acceptance_id: object
    acceptance_digest: str
    snapshot_digest: str
    action_revision: int
    display_date: object
    source_digest: str
    _images: dict
    inherited_btr: object = None

    def metadata(self,path):
        from mta.presentation.scoped_inherited_btr import PATH
        if path==PATH and self.inherited_btr is not None:return self.inherited_btr.metadata()
        item=self._images.get(path)
        if item is None:raise PublicationUnavailable('bpr_phase_source_unavailable:'+path)
        return deepcopy(_checked(item))

    def rows(self,path):
        from mta.presentation.scoped_inherited_btr import PATH
        if path==PATH and self.inherited_btr is not None:return self.inherited_btr.rows()
        item=self.metadata(path)
        try:return load_image(self.run,item,table_registry=phase_state.REGISTRY)
        except ValueError as error:raise PublicationUnavailable('bpr_phase_source_rows_differ:'+path) from error

    def query(self,path):
        from mta.presentation.scoped_inherited_btr import PATH
        if path==PATH and self.inherited_btr is not None:return self.inherited_btr.query()
        item=self.metadata(path)
        fields=item['fields']
        # An explicitly empty typed population owns its declared relation, even
        # though the storage manifest has no observed row fields. No NULL cells
        # or rows are substituted for absent/nonempty fields.
        selected=(','.join(quote(column)+' AS '+quote(name) for name,column,_ in fields)
            if fields else ','.join(quote(name) for name,_ in phase_state.REGISTRY[item['table']]))
        return ('SELECT vf_ordinal'+(','+selected if selected else '')+' FROM '+table_sql(item['table'])+
            ' WHERE vf_run_id=%s AND vf_image=%s',[self.run.pk,item['image']])

    def provenance(self,path):
        from mta.presentation.scoped_inherited_btr import PATH
        if path==PATH and self.inherited_btr is not None:return self.inherited_btr.provenance()
        item=self.metadata(path)
        return dict(owner='accepted_BPR',run_id=str(self.run.pk),acceptance_id=str(self.acceptance_id),
            acceptance_digest=self.acceptance_digest,snapshot_digest=self.snapshot_digest,
            action_revision=self.action_revision,accepted_business_date=self.run.business_date.isoformat(),
            physical_image=item['image'],table=item['table'],rows_digest=item['digest'],row_count=item['count'])


@once_per_request
def _accepted_phase(phase_id, expected_digest):
    from mta.runtime.scoped_pick_files import _accepted
    return _accepted(phase_id, expected_digest)


@once_per_request
def _input_manifest_digest(run):
    return digest(run.input_payload)


@once_per_request
def bind(phase_id,*,expected_digest,action_revision,include_inherited_btr=False,include_nms=False,
         read_reference=None):
    """Bind real accepted sources; this alone grants no native/UI admission."""
    from mta.runtime.scoped_actions import revision
    from mta.runtime.calculation_effects import SCHEMA as EFFECTS
    from django.core.exceptions import ObjectDoesNotExist
    try:phase=_accepted_phase(phase_id,expected_digest)
    except (ValueError,ObjectDoesNotExist) as error:
        raise PublicationUnavailable('bpr_phase_read_owner_differs') from error
    run=phase.run
    if (phase.phase!='BPR' or phase.metadata.get('effects',{}).get('schema')!=EFFECTS
            or _input_manifest_digest(run)!=run.input_manifest_digest
            or run.input_payload.get('content_digest')!=run.input_digest):
        raise PublicationUnavailable('bpr_phase_read_owner_differs')
    current_revision=revision(run)
    if read_reference is None:
        if type(action_revision) is not int or action_revision<0 or action_revision!=current_revision:
            raise PublicationUnavailable('bpr_phase_action_revision_changed')
    else:
        from mta.presentation.scoped_read_cut import require
        require(read_reference,phase,build_revision=action_revision,current_revision=current_revision)
    images={}
    for path,node in SOURCES.items():
        name=_image(phase.snapshot.manifest,node)
        if name is not None:
            item=phase.snapshot.manifest['images'].get(name)
            images[path]=deepcopy(_checked(item))
    marker='metadata/bpr/LastBatchRunTbl'
    if marker not in images:raise PublicationUnavailable('bpr_phase_date_marker_unavailable')
    rows=load_image(run,images[marker],table_registry=phase_state.REGISTRY)
    if len(rows)!=1 or set(rows[0])!={'LastRunDate'} or not isinstance(rows[0]['LastRunDate'],str):
        raise PublicationUnavailable('bpr_phase_date_marker_differs')
    try:display_date=datetime.fromisoformat(rows[0]['LastRunDate']).date()
    except ValueError as error:raise PublicationUnavailable('bpr_phase_date_marker_differs') from error
    if display_date!=run.business_date:raise PublicationUnavailable('bpr_phase_date_marker_differs')
    if type(include_inherited_btr) is not bool:raise PublicationUnavailable('bpr_inherited_btr_read_contract_differs')
    inherited=None
    if include_inherited_btr:
        from mta.presentation import scoped_inherited_btr
        inherited=scoped_inherited_btr.bind(phase)
    identity=dict(schema=SCHEMA,run_id=str(run.pk),input_digest=run.input_digest,
        input_manifest_digest=run.input_manifest_digest,phase_id=str(phase.pk),phase_digest=phase.digest,
        snapshot_digest=phase.snapshot.state_digest,capture_digest=phase.capture_digest,
        source_id=phase.source_id,action_revision=action_revision,images=images,display_date=display_date.isoformat())
    common_digest=digest(identity)
    # Custom Planning alone consumes this accepted image. Keep its discovery
    # outside the independent five-fact/three-source identity and opt in only
    # when preparing/binding those consumers. Their receipt pins provenance.
    if type(include_nms) is not bool:raise PublicationUnavailable('bpr_nms_read_contract_differs')
    if include_nms:
        name=_image(phase.snapshot.manifest,('state','nms','NMSAllItems'))
        if name is not None:
            images['closing/consumer_context/NMSAllItems']=deepcopy(_checked(phase.snapshot.manifest['images'].get(name)))
    return BprSources(run,phase.pk,phase.digest,phase.snapshot.state_digest,action_revision,
        display_date,common_digest,images,inherited)
