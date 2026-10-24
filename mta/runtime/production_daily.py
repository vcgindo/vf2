"""Native supplied daily facts linked to one typed production initialization."""
from copy import deepcopy
from datetime import date
import hashlib
import json
import uuid
import logging
from time import perf_counter

from mta.serialization import digest, storage
from mta.runtime.opening_scope import opening_operation
from mta.mdm.initialization_contract import object_pairs, sha
from mta.mdm.initialization_rows import scalar
from mta.application.r1_daily_input import DAILY_COLUMNS, _typed_rows
from mta.application.r1_importer_master import RAW_COLUMNS, NO_NORM_COLUMNS
from mta.runtime.relational_state import STORAGE_TABLES

from mta.application.native_daily_contract import (
    SCHEMA, FEED_SCHEMA, SOURCE_SCHEMA, SUPPLIER_TABLES, DAY_TABLES, CONTROL_TABLES, DAY_FIELDS)
from mta.application.native_daily_contract import STOCK_FEED_SCHEMA, ACTIVE_STOCK_SCHEMA, STOCK_TABLE, day_tables, day_fields
logger = logging.getLogger(__name__)


def rows(value, table, label):
    fields = dict(STORAGE_TABLES[table])
    if label == 'order_feed':
        fields.pop('Type')
    if label in ('distributor_transactions', 'vendor_transactions'):
        fields['ReportDate'] = 'date'
    if not isinstance(value, list):
        raise ValueError('Explicit daily population required: '+label)
    for row in value:
        if not isinstance(row, dict) or set(row) != set(fields):
            raise ValueError('Daily field roster differs: '+label)
        for name, kind in fields.items():
            scalar(row[name], kind, label+'/'+name)
    return value


def input_table(fields, path, records):
    """Choose supplied native day families by path, with complete fields."""
    from mta.runtime.input_storage import choose_table
    from mta.application.production_source_inputs import RAW_TABLE, DIRECTORY_TABLE, CONSUMER_PATHS
    source_table = {'input/day/shipment_input/rows/values': RAW_TABLE,
                    'input/day/transporter_input/rows/values': DIRECTORY_TABLE, **CONSUMER_PATHS}.get(path)
    if source_table:
        if records and set(fields) != set(dict(STORAGE_TABLES[source_table])):
            raise ValueError('Native external source field roster differs: '+path)
        return source_table
    if path.startswith('input/day/') and path.endswith('/values'):
        name = path.removeprefix('input/day/').removesuffix('/values')
        table = DAY_TABLES.get(name) or CONTROL_TABLES.get(name.removeprefix('control_requests/'))
        if name == 'requirement_stock':
            table = STOCK_TABLE
        if name == 'raw_master':
            table = 'Importer/MasterDataRaw'
        if name.startswith('supplier_feeds/'):
            table = SUPPLIER_TABLES.get(name.removeprefix('supplier_feeds/'))
        if name == 'exclusions':
            table = 'Intermediate/ExclusionRecords'
        if table:
            expected = dict(STORAGE_TABLES[table])
            if name == 'order_feed':
                expected.pop('Type')
            if records and set(fields) != set(expected):
                raise ValueError('Native captured daily field roster differs: '+path)
            return table
    if path in ('input/opening/state/btr/RationingHistory/values',
                'input/predecessor/btr/RationingHistory/values',
                'input/profile/delivery/btr_history/importer_vf_settings/values',
                'input/profile/daily/module_sources/distributor_norms/values',
                'input/profile/daily/module_sources/vendor_master/values'):
        return choose_table(fields,path,records)
    if not records:
        from mta.runtime.complete_daily_state import input_table as complete_table
        return complete_table(path)
    return choose_table(fields, path, records)


def decode(raw, expected_sha256):
    sha(expected_sha256, 'daily input')
    def nonfinite(value):
        raise ValueError('Nonfinite daily number: '+value)
    from mta.application.streamed_input import JsonInputFile
    from mta.application.streamed_input import StreamedInput
    from mta.runtime.daily_preparation import PreparedDaily
    if isinstance(raw, PreparedDaily):
        return raw.checked(expected_sha256)
    if isinstance(raw, StreamedInput):
        value = raw._checked(expected_sha256)
    elif isinstance(raw, JsonInputFile):
        value = raw.decode(expected_sha256, object_pairs_hook=object_pairs, parse_constant=nonfinite)
    else:
        if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != expected_sha256:
            raise ValueError('Daily operator input bytes differ')
        value = json.loads(raw, object_pairs_hook=object_pairs, parse_constant=nonfinite)
    value = decode_value(value)
    if isinstance(raw, StreamedInput):
        raw._value = None  # Successful validation transfers exclusive ownership.
    return value


def decode_value(value):
    """The authoritative native validator over an exclusively owned parse."""
    envelope = {'schema', 'day', 'consumer_opening'}
    if isinstance(value, dict) and value.get('schema') == SOURCE_SCHEMA:
        envelope |= {'intake_schema', 'producer_sources'}
    if not isinstance(value, dict) or set(value) != envelope or value['schema'] not in (SCHEMA, FEED_SCHEMA, SOURCE_SCHEMA):
        raise ValueError('Complete native daily envelope required')
    intake = value.get('intake_schema', value['schema'])
    if intake not in (SCHEMA, FEED_SCHEMA, STOCK_FEED_SCHEMA, ACTIVE_STOCK_SCHEMA):
        raise ValueError('Explicit active/inactive native intake schema required')
    day = value['day']
    fields = day_fields(intake)
    if not isinstance(day, dict) or set(day) != fields:
        raise ValueError('Native day population roster differs; outputs/master answers are forbidden')
    if intake in (FEED_SCHEMA, STOCK_FEED_SCHEMA):
        rows(day['raw_master'], 'Importer/MasterDataRaw', 'raw_master')
        if not isinstance(day['supplier_feeds'], dict) or set(day['supplier_feeds']) != set(SUPPLIER_TABLES):
            raise ValueError('Explicit supplier raw feed roster required')
        for name, table in SUPPLIER_TABLES.items():
            rows(day['supplier_feeds'][name], table, name)
    if not isinstance(day['business_date'], str) or date.fromisoformat(day['business_date']).isoformat() != day['business_date']:
        raise ValueError('ISO daily business date required')
    if value['schema'] == SOURCE_SCHEMA:
        from mta.application.production_source_inputs import validate
        validate(value['producer_sources'], day['business_date'])
    for name, table in day_tables(intake).items():
        rows(day[name], table, name)
    if intake in (STOCK_FEED_SCHEMA, ACTIVE_STOCK_SCHEMA):
        from mta.application.requirement_stock import validate
        validate(day['requirement_stock'],day['business_date'])
    _typed_rows(day['raw_daily'], DAILY_COLUMNS, DAILY_COLUMNS[:-1])
    if any(row['ReportDate'] != day['business_date'] for row in day['raw_daily']):
        raise ValueError('Daily facts must match their declared business date')
    if day['order_feed_status'] not in ('PRESENT', 'MISSING') or day['order_feed_status'] == 'MISSING' and day['order_feed']:
        raise ValueError('Explicit order feed availability differs')
    if set(day['control_requests']) != set(CONTROL_TABLES):
        raise ValueError('Control request population roster differs')
    for name, table in CONTROL_TABLES.items():
        rows(day['control_requests'][name], table, name)
    # Native installed owners capture these queues; a file cannot replace them.
    if day['new_force_requests'] or any(day['control_requests'].values()):
        raise ValueError('Native MDM command feeds belong to their owned approval queues')
    for name in ('phase_controls_input_validation', 'seasonality_input_validation'):
        if type(day[name]) is not bool:
            raise ValueError('Explicit daily validation boolean required: '+name)
    opening = value['consumer_opening']
    if opening is not None:
        if not isinstance(opening, dict) or set(opening) != {'requests', 'remarks'} or not isinstance(opening['remarks'], dict) or set(opening['remarks']) != {'bpr', 'bor', 'boroa'}:
            raise ValueError('Explicit native consumer opening roster required')
        from mta.presentation.daily_requests import _typed
        if not isinstance(opening['requests'], list):
            raise ValueError('Explicit initial request bag required')
        for row in opening['requests']:
            _typed(row)
        if value['schema'] == SOURCE_SCHEMA:
            from mta.application.production_source_inputs import validate_initial_remarks
            validate_initial_remarks(opening['remarks'], day['business_date'])
        elif any(value != [] for value in opening['remarks'].values()):
            raise ValueError('H3 requires explicitly empty initial remark bags')
    return value


def working_day(value, profile):
    """Inactive input files are facts, never reconstructed calculated answers."""
    from mta.runtime.daily_preparation import PreparedDaily
    validated = isinstance(value, PreparedDaily)
    if validated:
        value = value.checked(value.sha256)
    from mta.application.daily_finalization import ACTIVE_POLICY, POLICY
    policy = profile.get('complete_daily', {}).get('policy')
    day = deepcopy(value['day'])
    intake = value.get('intake_schema', value['schema'])
    if policy == POLICY:
        if intake not in (FEED_SCHEMA,STOCK_FEED_SCHEMA):
            raise ValueError('Inactive NMS requires explicit v2 master and supplier raw feeds')
    elif policy == ACTIVE_POLICY:
        if intake not in (SCHEMA, ACTIVE_STOCK_SCHEMA):
            raise ValueError('Active NMS requires v1 intake from its captured owners')
    else:
        raise ValueError('Native daily execution requires a supported finalization policy')
    day.setdefault('raw_master', [])
    day.setdefault('supplier_feeds', {name: [] for name in SUPPLIER_TABLES})
    day['exclusions'] = []
    if value['schema'] == SOURCE_SCHEMA:
        from mta.application.production_source_inputs import validate
        sources = value['producer_sources'] if validated else validate(value['producer_sources'], day['business_date'])
        day['shipment_input'] = deepcopy(sources['shipments'])
        day['transporter_input'] = deepcopy(sources['transporters'])
        day['production_report_policy'] = deepcopy(sources['report_policy'])
        day['production_report_opening'] = deepcopy(sources['report_opening'])
        day['production_report_schema'] = sources['schema']
        if (value['consumer_opening'] is None) != (sources['report_opening'] is None):
            raise ValueError('Native report opening must match root or own-successor ownership')
    return day


def initialize_consumers(owner, value, input_sha256):
    """Explicit initial fact owners, inside execute_day's capture transaction."""
    from mta.runtime.daily_request_models import DailyRequestOwner
    from mta.runtime.ancillary_models import RemarkOwner
    from mta.presentation import daily_requests, ancillary_live
    if (not isinstance(value, dict) or set(value) != {'requests', 'remarks'}
            or not isinstance(value['remarks'], dict)
            or set(value['remarks']) != {'bpr', 'bor', 'boroa'}):
        raise ValueError('Explicit native request/remark opening required')
    families = (ancillary_live.BPR, ancillary_live.BOR, ancillary_live.BOROA)
    provenance = dict(schema='fresh-production-consumer-opening-v1', initialization_id=str(owner.pk),
        initialization_digest=owner.input_digest, source_digest=owner.source.digest,
        input_sha256=input_sha256, population_digest=digest(value))
    existing = DailyRequestOwner.objects.filter(pk=daily_requests.OWNER).first()
    if existing:
        if existing.provenance != provenance:
            raise ValueError('Consumer opening cannot replace an existing owner')
    else:
        if RemarkOwner.objects.exists():
            raise ValueError('Partial consumer ownership prevents initialization')
        daily_requests.initialize(value['requests'], provenance=provenance)
        for name, family in zip(('bpr', 'bor', 'boroa'), families):
            ancillary_live.initialize_owner(family, provenance_digest=digest(provenance), provenance_receipt=provenance)
            for row in value['remarks'][name]:
                from datetime import datetime
                ancillary_live.append(family, [{key: item for key, item in row.items() if key != 'RemarkDate'}],
                    actor_id='initialization:'+str(owner.pk), timestamp=datetime.fromisoformat(row['RemarkDate']))
    if {row.family for row in RemarkOwner.objects.all()} != set(families):
        raise ValueError('Complete native remark owner roster required')
    if any(row.provenance_receipt != provenance for row in RemarkOwner.objects.all()):
        raise ValueError('Native remark owner provenance differs')


def _inspection_frame(owner, predecessor_id, retry_capture_id):
    """Install fresh private readiness before selecting the bounded daily frame."""
    from mta.mdm.production_families import certified_state_handle, frame_for_daily
    if retry_capture_id is None:
        from mta.runtime.ingestion_admission import preparation_source
        admitted = preparation_source(owner.source.digest)
        if admitted is not None:
            certified_state_handle(owner, admitted)
    return frame_for_daily(owner, predecessor_id)


@opening_operation
def inspect_execution(raw, expected_sha256, *, initialization_id, source_digest, configuration_digest,
            pick_output_root, execution_revision=None, retry_capture_id=None,
            predecessor_id=None, predecessor_output_digest=None, report_disposition=None,
            scope_request=None):
    """Read persisted identities only; return every known input/capability issue."""
    from django.core.exceptions import ObjectDoesNotExist
    from mta.runtime.models import ProductionInitialization, CalculationRun
    from mta.mdm.production_families import require_initialization, require_binding
    from mta.runtime.production_preflight import daily
    from mta.runtime.input_reader import read_input
    from mta.runtime.services import read_outputs
    issues=[];owner=None;parent=None;frame=None;parent_context=None
    def problem(path,owner_name,error):
        issues.append(dict(path=path,owner=owner_name,code='CONTEXT_INVALID',message=str(error)))
    if scope_request is not None:
        from mta.runtime.production_scope import validate_request
        validate_request(scope_request)
        if retry_capture_id is not None or report_disposition is not None:
            raise ValueError('UptoBPR recovery uses its scope attempt, never a new daily capture')
    try:
        owner=ProductionInitialization.objects.select_related('source').get(pk=uuid.UUID(str(initialization_id)))
        frame=_inspection_frame(owner, predecessor_id, retry_capture_id)
        try:
            require_initialization(owner.source)
        except (ValueError,ObjectDoesNotExist) as error:
            problem('/initialization','native initialization seal',error)
        if owner.source.digest != source_digest:
            problem('/source_digest','native source','Native source identity differs')
        if owner.configuration_digest != configuration_digest:
            problem('/configuration_digest','native configuration','Native configuration identity differs')
        if scope_request is not None and type(frame['profile'].get('daily_publication')) is not bool:
            problem('/profile/daily_publication','captured scope configuration',
                'Scoped publication mode must be explicit')
    except (ValueError,TypeError,ObjectDoesNotExist) as error:
        problem('/initialization_id','ProductionInitialization',error)
    if predecessor_id is not None:
        try:
            parent=CalculationRun.objects.get(pk=uuid.UUID(str(predecessor_id)))
            captured=parent.mdm_input_capture
            binding=read_input(parent,components=('initialization_binding',)).get('initialization_binding')
            if owner is not None:
                expected_binding=dict(id=str(owner.pk),source_digest=owner.source.digest,
                    input_sha256=owner.input_sha256,content_digest=owner.input_digest,
                    configuration_digest=owner.configuration_digest)
                if binding!=expected_binding:
                    problem('/predecessor/initialization_binding','own persisted predecessor','Full native initialization binding differs')
            parent_context=dict(run_id=str(parent.pk),business_date=parent.business_date.isoformat(),kind=parent.kind,
                status=parent.status,output_digest=parent.output_digest,
                initialization_id=binding.get('id') if isinstance(binding,dict) else None,
                source_digest=captured.source.digest,capture_status=captured.status)
            if parent.status=='SUCCEEDED':
                previous=read_outputs(parent,include_reports=False)
                parent_context['closing_state']=previous['ClosingState'][0]
                parent_context['output_version']=parent.production_manifest.get('version',2)
                parent_profile=read_input(parent,components=('profile',))['profile']
                if frame is not None and digest(parent_profile)!=digest(frame['profile']):
                    problem('/predecessor/profile','own persisted predecessor','Persisted predecessor configuration differs')
                from mta.application.daily_finalization import verify_successor
                try:
                    verify_successor(previous,parent_profile,parent.business_date.isoformat())
                except (ValueError,TypeError,KeyError) as error:
                    problem('/predecessor/finalization','own persisted predecessor',error)
        except (ValueError,TypeError,KeyError,IndexError,ObjectDoesNotExist) as error:
            problem('/predecessor','own persisted predecessor',error)
            parent_context={}  # An invalid context, never a substitute state.
    elif predecessor_output_digest is not None:
        problem('/predecessor_output_digest','own persisted predecessor','Root must not provide a predecessor digest')
    from mta.runtime.mdm_integration_models import MdmSourceIntegration
    sealed_root = (owner is not None and predecessor_id is None and retry_capture_id is None
        and MdmSourceIntegration.objects.filter(source=owner.source).exists())
    if owner is not None and (predecessor_id is not None or retry_capture_id is not None or sealed_root):
        try:
            require_binding(owner.source)
        except (ValueError,ObjectDoesNotExist) as error:
            problem('/initialization/integration_seal','native MDM integration',error)
        if retry_capture_id is None and (parent is not None or sealed_root):
            from mta.mdm.integration_source import verify_predecessor
            try:
                repeated=inspect_completed_request(raw,expected_sha256,owner,frame,parent,parent_context,
                    execution_revision,pick_output_root,**({'scope_request':scope_request} if scope_request is not None else {}))
                if not repeated:verify_predecessor(owner.source,parent)
            except (ValueError,TypeError,KeyError,OSError,ObjectDoesNotExist) as error:
                problem('/predecessor/current_ownership' if parent is not None else '/initialization/current_ownership',
                    'native MDM integration',error)
    if report_disposition is not None and retry_capture_id is None:
        problem('/report_disposition','native report disposition','Disposition requires an exact frozen retry')
    if retry_capture_id is not None:
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        try:
            frozen=MdmDailyInputCapture.objects.select_related('run','source').get(run_id=uuid.UUID(str(retry_capture_id)))
            if frozen.run.status!='FAILED' or frozen.status!='CAPTURED' or frozen.source.digest!=source_digest:
                problem('/retry_capture_id','frozen MDM capture','Retry requires its own FAILED/CAPTURED source')
            if frozen.run.predecessor_id != (parent.pk if parent else None):
                problem('/retry_capture_id','frozen MDM capture','Frozen retry predecessor differs')
            origin=read_input(frozen.run,components=('daily_input_sha256',))
            if origin.get('daily_input_sha256') != expected_sha256:
                problem('/retry_capture_id','frozen MDM capture','Frozen retry daily input identity differs')
            if owner is not None and frame is not None and (predecessor_id is None or parent_context and 'closing_state' in parent_context):
                inspect_retry(raw,expected_sha256,owner,frame,parent,parent_context,frozen,
                    execution_revision,pick_output_root,problem,report_disposition=report_disposition)
        except (ValueError,TypeError,ObjectDoesNotExist) as error:
            problem('/retry_capture_id','frozen MDM capture',error)
    report=daily(raw,expected_sha256,frame=frame,predecessor=parent_context,
        initialization_id=initialization_id,source_digest=source_digest,configuration_digest=configuration_digest,
        predecessor_output_digest=predecessor_output_digest,pick_output_root=pick_output_root,
        execution_revision=execution_revision,retry_capture_id=retry_capture_id,context_issues=issues)
    return report,owner,parent,frame


def inspection_request(raw,sha256,owner,frame,parent,parent_context,pick_root,*,scope_request=None):
    """Reconstruct the same pre-capture request used by locked execute_day."""
    from mta.runtime.temporal import request_input,command_states,resolved_pick_root
    value=decode(raw,sha256)
    from mta.runtime.daily_preparation import PreparedDaily
    day=working_day(raw if isinstance(raw,PreparedDaily) else value,frame['profile'])
    initial=frame['opening'] if parent is None else None
    prior=deepcopy(initial['state'] if parent is None else parent_context['closing_state'])
    if parent is None:
        lineage=dict(opening_identity=initial['identity'],opening_digest=digest(initial))
    else:
        prior,commands=command_states(parent,prior,through_date=date.fromisoformat(day['business_date']))
        lineage=dict(run_id=str(parent.pk),output_digest=parent.output_digest,commands=commands)
    lineage['initialization_id']=str(owner.pk)
    binding=dict(id=str(owner.pk),source_digest=owner.source.digest,input_sha256=owner.input_sha256,
        content_digest=owner.input_digest,configuration_digest=owner.configuration_digest)
    request=digest(request_input(day=day,profile=frame['profile'],initial=initial,lineage=lineage,
        initialization_binding=binding,daily_input_sha256=sha256,complete_pick=True,
        pick_output_root=resolved_pick_root(pick_root),scope_request=scope_request))
    return day,prior,request,binding


def inspect_completed_request(raw,sha256,owner,frame,parent,parent_context,revision,pick_root,*,scope_request=None):
    """Verify an exact completed normal request without restoring files/writing."""
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.input_reader import read_input
    from mta.runtime.services import read_outputs
    day,_,request,binding=inspection_request(raw,sha256,owner,frame,parent,parent_context,pick_root,
        scope_request=scope_request)
    repeated=MdmDailyInputCapture.objects.select_related('run').filter(source=owner.source,
        request_digest=request,run__execution_revision=revision).first()
    if repeated is None:return False
    run=repeated.run
    if scope_request is not None:
        from mta.runtime.production_scope import captured_run
        captured_run(run,scope_request)
        captured=read_input(run,components=('initialization_binding','daily_input_sha256'))
        if (repeated.origin_id is not None or run.predecessor_id!=(parent.pk if parent else None)
                or run.business_date!=date.fromisoformat(day['business_date'])
                or captured!={'initialization_binding':binding,'daily_input_sha256':sha256}):
            raise ValueError('Repeated native scoped request differs')
        return True
    if (repeated.status!='CONSUMED' or repeated.origin_id is not None or run.status!='SUCCEEDED'
            or run.kind!='DAILY_CHAIN' or run.evidence_mode!='production'
            or run.predecessor_id!=(parent.pk if parent else None)
            or run.business_date!=date.fromisoformat(day['business_date'])):
        raise ValueError('Repeated native daily request identity/status differs')
    captured=read_input(run,components=('initialization_binding','daily_input_sha256'))
    if captured!={'initialization_binding':binding,'daily_input_sha256':sha256}:
        raise ValueError('Repeated native daily input/initialization differs')
    read_outputs(run,include_reports=False)  # Full input/output integrity; file recovery stays in execute_day.
    return True


def inspect_retry(raw,sha256,owner,frame,parent,parent_context,frozen,revision,pick_root,problem,report_disposition=None):
    """Read-only mirror of frozen retry checks; locked execution gates remain."""
    from mta.runtime.input_reader import read_input
    from mta.runtime.services import read_outputs
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.runtime.mdm_configuration import capture_configuration_for_day
    from mta.mdm.integration_source import verify_predecessor, verify_capture
    from mta.runtime.production_preflight import frozen_retry
    try:
        day,prior,request,_=inspection_request(raw,sha256,owner,frame,parent,parent_context,pick_root)
        from mta.application.native_report_disposition import admit, verify_replay, RETRIES
        if report_disposition is not None or revision in RETRIES.values():
            admit(requested=report_disposition,native=True,origin=frozen,parent=parent,
                initialization=owner,raw=read_input(frozen.run),request_digest=request,execution_revision=revision)
        repeated=MdmDailyInputCapture.objects.select_related('run').filter(source_id=frozen.source_id,
            request_digest=request,run__execution_revision=revision).first()
        if repeated is not None:
            if repeated.origin_id!=frozen.pk or repeated.run.evidence_mode!='production':
                problem('/retry_capture_id/repeated','frozen MDM capture','Repeated retry identity/evidence policy differs')
            try:
                verify_replay(repeated.run,repeated.run.production_manifest.get('lineage'),report_disposition)
                read_outputs(repeated.run,include_reports=False)  # Verify only; never restore Pick files.
            except (ValueError,KeyError,TypeError) as error:
                problem('/retry_capture_id/repeated/output','frozen MDM capture',error)
            return
        leaves=list(MdmDailyInputCapture.objects.filter(source_id=frozen.source_id,status='CAPTURED',
            retries__isnull=True).values_list('run_id',flat=True))
        snapshot=read_input(frozen.run,components=('mdm_input','request_inputs','remark_inputs')).get('mdm_input')
        nms,horizon=capture_configuration_for_day(prior['importer_settings'],predecessor=parent,source=owner.source)
        for path,message in frozen_retry(frozen,leaves,request,parent,day['business_date'],revision,snapshot,nms,horizon):
            problem(path,'frozen MDM capture',message)
        for path,verify in (('/retry_capture_id/predecessor',lambda:verify_predecessor(owner.source,parent,retry_capture=frozen)),
                            ('/retry_capture_id/snapshot',lambda:verify_capture(owner.source,snapshot))):
            try:
                verify()
            except (ValueError,KeyError,TypeError) as error:
                problem(path,'frozen MDM capture',error)
    except (ValueError,KeyError,TypeError,OSError) as error:
        problem('/retry_capture_id/request','frozen MDM capture',error)


def _daily_initialization(owner, parent, retry_capture_id, handle):
    """Select the exact opening read boundary after admission has completed."""
    from mta.mdm.initialization import read_initialized_input
    from mta.mdm.production_families import (bootstrap_native_families, require_binding,
        require_certified_binding, frame_for_daily)
    from mta.runtime.opening_scope import current_certified_opening
    active = handle if handle is not None else current_certified_opening(owner)
    if active is not None:
        require_certified_binding(owner.source, owner, active)
        return frame_for_daily(owner, parent)
    if parent is None and retry_capture_id is None:
        bootstrap_native_families(owner)
    else:
        require_binding(owner.source)
    return read_initialized_input(owner)


@opening_operation
def execute(raw, expected_sha256, *, initialization_id, source_digest, configuration_digest,
            execution_revision, pick_output_root, predecessor_id=None, predecessor_output_digest=None,
            retry_capture_id=None, report_disposition=None, feed_attempt=None, scope_request=None):
    started = perf_counter()
    from mta.runtime.models import ProductionInitialization, CalculationRun
    from mta.mdm.production_families import require_initialization, certified_handle
    from mta.runtime.temporal import execute_day
    from mta.runtime.production_preflight import require
    from mta.runtime.daily_preparation import prepare
    try:
        raw = prepare(raw, expected_sha256)
    except (ValueError, TypeError, KeyError, OverflowError):
        # Preserve aggregated preflight diagnostics and the no-writer barrier
        # for invalid native envelopes.
        pass
    prepared_arguments = None
    prepared_attempt = None
    prepared_admission = None
    if scope_request is not None and (feed_attempt is not None or getattr(raw,'admission',None) is not None):
        raise ValueError('UptoBPR currently requires the supplied native JSON command')
    if getattr(raw, 'admission', None) is not None:
        if feed_attempt is None or retry_capture_id is not None or report_disposition is not None:
            raise ValueError('Accepted preparation requires its original unexecuted CSV attempt')
        from mta.runtime.daily_feed_models import DailyFeedAttempt
        from mta.runtime.accepted_daily import check
        prepared_arguments = dict(initialization_id=initialization_id, source_digest=source_digest,
            configuration_digest=configuration_digest, execution_revision=execution_revision,
            pick_output_root=pick_output_root, predecessor_id=predecessor_id,
            predecessor_output_digest=predecessor_output_digest)
        prepared_attempt = DailyFeedAttempt.objects.select_related('initialization__source',
            'certification','master_revision').get(pk=feed_attempt)
        prepared_admission = check(prepared_attempt, prepared_arguments)
        if prepared_admission != raw.admission:
            raise ValueError('Accepted preparation differs from its durable receipt')
    else:
        report,owner,parent,frame=inspect_execution(raw,expected_sha256,initialization_id=initialization_id,
            source_digest=source_digest,configuration_digest=configuration_digest,pick_output_root=pick_output_root,
            predecessor_id=predecessor_id,predecessor_output_digest=predecessor_output_digest,
            execution_revision=execution_revision,retry_capture_id=retry_capture_id,report_disposition=report_disposition,
            scope_request=scope_request)
        require(report,'day')
    value = decode(raw, expected_sha256)
    owner = ProductionInitialization.objects.select_related('source').get(pk=uuid.UUID(str(initialization_id)))
    handle = (certified_handle(owner, prepared_attempt, prepared_admission)
              if prepared_attempt is not None else None)
    if handle is None:
        require_initialization(owner.source)
    if owner.source.digest != sha(source_digest, 'native source') or owner.configuration_digest != sha(configuration_digest, 'native configuration'):
        raise ValueError('Native daily source/configuration identity differs')
    parent = None
    if predecessor_id is not None:
        parent = CalculationRun.objects.get(pk=uuid.UUID(str(predecessor_id)))
        if parent.output_digest != sha(predecessor_output_digest, 'predecessor output'):
            raise ValueError('Native predecessor output identity differs')
        if value['consumer_opening'] is not None:
            raise ValueError('Successor must use its persisted consumer ownership')
    elif predecessor_output_digest is not None or value['consumer_opening'] is None:
        raise ValueError('Initial native day requires explicit consumer opening and no predecessor digest')
    frame = _daily_initialization(owner, parent, retry_capture_id, handle)
    day = working_day(raw, frame['profile'])
    if day['raw_non_nms'] and not frame['profile']['import_non_nms']:
        raise ValueError('Non-NMS feed requires its initialized active configuration')
    from mta.mdm.location_transition import admit
    admit(owner.source, day['business_date'], parent)
    logger.warning('daily_phase initialization=%s phase=native_preflight_and_bootstrap seconds=%.6f',
                   owner.pk, perf_counter()-started)
    from mta.runtime.ingestion_admission import preparation_source
    prepared_state = preparation_source(owner.source.digest) if retry_capture_id is None else None
    return execute_day(day=day, profile=frame['profile'], execution_revision=execution_revision,
        predecessor=parent, opening=frame['opening'] if parent is None else None,
        mdm_source=owner.source if retry_capture_id is None else None,
        mdm_retry=retry_capture_id, pick_output_root=pick_output_root,
        production_initialization=owner, daily_input_sha256=expected_sha256,
        consumer_opening=value['consumer_opening'], report_disposition=report_disposition,
        feed_attempt=feed_attempt, prepared_arguments=prepared_arguments, prepared_state=prepared_state,
        scope_request=scope_request)
