"""One supported Cohort2 materialization boundary over committed daily owners."""
from functools import partial
from pathlib import Path
from mta.application.operational_alerts import ALERT_SEEDS
from mta.application.operational_input_archive import archive_clock
from mta.application.operational_inputs import PHYSICAL_TABLES
from mta.application.operational_io import archive_files
from mta.application.operational_upload_logs import LOG_BINDINGS
from mta.application.operational_report_files import NORM_REPORTS
from mta.application.operational_sqlcmd import no_norm_parent_bytes
from mta.runtime.operational_alert_runner import ALERT_OPERATION, materialize_alert_operation
from mta.runtime.operational_alert_sources import install_alert_opening, read_alert_inputs
from mta.runtime.operational_attempts import configuration_value, operational_worker
from mta.runtime.operational_backup import BACKUP_OPERATION, materialize_backup, SOURCE_IMAGE, RESTORED_IMAGE, OWNERSHIP_FILE
from mta.runtime.operational_effects import operation
from mta.runtime.operational_native import read_population
from mta.runtime.operational_opening import install_opening
from mta.runtime.operational_reports import REPORT_OPERATIONS, materialize_report_operation
from mta.serialization import digest

RUNNER_POLICY = 'cohort2-integrated-materialization-v1'
_GROUPS = ('O3', 'O2', 'O1', 'O4', 'O5', 'O6', 'O7', 'O8', 'O9')
COMPLETION_OPERATION = dict(name='OperationalCompletion', stage='operational-completion',
    source_digest=digest(dict(policy=RUNNER_POLICY, reports=REPORT_OPERATIONS,
                             alerts=ALERT_OPERATION, backup=BACKUP_OPERATION)))
ROSTER = [dict(ordinal=i, group=group, **(REPORT_OPERATIONS[group] if group in REPORT_OPERATIONS
          else ALERT_OPERATION if group=='O7' else BACKUP_OPERATION if group=='O8'
          else COMPLETION_OPERATION)) for i,group in enumerate(_GROUPS)]


def validate_configuration(configuration):
    value = configuration_value(configuration)
    bindings = value['bindings']
    if bindings.get('runner_policy') != RUNNER_POLICY or bindings.get('operation_roster') != ROSTER:
        raise ValueError('Exact integrated Cohort2 runner and canonical operation roster required')
    tool = bindings.get('zip_tool')
    if not isinstance(tool, dict) or set(tool) != {'path', 'sha256'}:
        raise ValueError('Explicit pinned ZIP tool required')
    if not isinstance(tool['path'], str) or not Path(tool['path']).is_absolute() or len(tool['sha256']) != 64:
        raise ValueError('Invalid pinned ZIP tool identity')
    return value


def _expected_files(owner, config):
    result = {}
    def add(group, path, members=()):
        result.setdefault(group, {})[path] = sorted(members)
    for folder in ('output', 'download'):
        add('O1', folder+'/BOR_OrderAllocation.csv')
    if len(no_norm_parent_bytes(read_population(owner, 'NoNormAtParentReport'))):
        for folder in ('output', 'download'):
            add('O3', folder+'/NoNormParentReport.zip', ('NoNormParentReport.csv',))
    else:
        add('O3', 'output/NoNormParentReport.csv')
    if read_population(owner, 'BPRExceptions'):
        add('O2', 'output/BPRExceptionReport.csv')
        add('O2', 'download/BPRExceptionReport.zip', ('BPRExceptionReport.csv',))
    else:
        result['O2'] = {}
    database = config['bindings']['input_export_database']
    input_members = [name+'.csv' for name in (*PHYSICAL_TABLES, 'InTransitRaw')]
    input_members += [database+'_'+name+'.CSV' for name in PHYSICAL_TABLES]
    input_members.append(archive_clock(owner.business_date)['marker'])
    for folder in ('output', 'download'):
        add('O4', folder+'/InputData.zip', input_members)
        for _, name in LOG_BINDINGS:
            add('O5', folder+'/UIUploadLogs/'+name+'.zip', (name+'.csv',))
    for key, name in NORM_REPORTS.items():
        add('O6', 'download/'+name+'.zip', (name+'.csv',))
        if key == 'DBMNormChange':
            add('O6', 'output/'+name+'.zip', (name+'.csv',))
        else:
            add('O6', 'output/'+name+'.csv')
    client = config['bindings']['upload_log_client_folder']
    if client is not None:
        for _, name in LOG_BINDINGS:
            add('O5', client+'/'+name+'.zip', (name+'.csv',))
    sources = read_alert_inputs(owner)
    if sources['configuration']['attach_invalid_data_report_zip']:
        add('O7', 'output/InvalidDataReport.zip', ('InvalidDataReport.csv',))
    else:
        add('O7', 'output/InvalidDataReport.csv')
    add('O7', 'download/InvalidDataReport.zip', ('InvalidDataReport.csv',))
    add('O7', f'output/{owner.business_date.day:02d}-FailedForceNormChanges.csv')
    if sources['reports']['phase_exceptions']:
        for folder in ('output', 'download'):
            add('O7', folder+'/PhaseInPhaseOutExceptionReport.zip', ('PhaseInPhaseOutExceptionReport.csv',))
    result['O9'] = {}
    result['O8'] = {path: [] for path in ('backup/post.dump', SOURCE_IMAGE, RESTORED_IMAGE)}
    if config['bindings'].get('postgres_backup', {}).get('owned_restore') is not None:
        add('O8', OWNERSHIP_FILE)
    return result


def verify_required_outputs(owner):
    """Require mapped files, typed populations and all 14 intents, not empty receipts."""
    config = validate_configuration(owner.configuration)
    expected = _expected_files(owner, config)
    for effect in owner.operations.order_by('ordinal'):
        actual = {file.relative_path: sorted(file.members.values_list('name', flat=True))
                  for file in effect.files.all()}
        if actual != expected[effect.group]:
            raise ValueError('Required operational artifact/member roster differs: '+effect.group)
        if effect.group != 'O8' and any(file.role != file.relative_path.split('/')[0] for file in effect.files.all()):
            raise ValueError('Operational file role differs from its mapped path')
    for name in ('BORWithOrderAllocation', 'closing/BOR_OrderAllocationHistory',
                 'closing/RRR_OrderAllocation', 'closing/RRR_OrderAllocationHistory',
                 'NoNormAtParentReport', 'BPRExceptions', 'closing/UIUploadLogActionType',
                 'closing/RunAbortReasons', *('closing/'+name for name,_ in LOG_BINDINGS)):
        read_population(owner, name)
    intents = list(owner.operations.get(group='O7').operationalintentevaluation_set.select_related('intent'))
    if len(intents) != 14 or {row.intent.alert_name for row in intents} != {seed['name'] for seed in ALERT_SEEDS}:
        raise ValueError('Fourteen complete mapped alert evaluations required')
    if any(effect.operationalintentevaluation_set.exists() for effect in owner.operations.exclude(group='O7')):
        raise ValueError('Unexpected alert evaluation owner')
    if (Path(owner.root)/'output/InputData').exists():
        raise ValueError('Input archive staging was not cleared')


def materialize(*, openings=None, abort_opening=None, **arguments):
    """No execute_day call: consume exactly its committed owner and own predecessor."""
    with operational_worker(**arguments) as owner:
        if owner.status == 'SUCCEEDED':
            return owner
        config = validate_configuration(owner.configuration)
        if owner.repair_of_id is not None:
            raise ValueError('Use the explicit repair command for historical missing files')
        if owner.predecessor_id is None:
            install_opening(owner.pk, populations=openings)
            install_alert_opening(owner.pk, abort_reasons=abort_opening)
        elif openings is not None or abort_opening is not None:
            raise ValueError('Successor must consume its own operational predecessor, not supplied openings')
        client = config['bindings']['upload_log_client_folder']
        if client is not None:
            from mta.application.operational_io import owned_path
            owned_path(owner.root, client).mkdir(parents=True, exist_ok=False)
        from mta.runtime.operational_retry import retry_archive_writer
        writer = retry_archive_writer(owner, executable=config['bindings']['zip_tool']['path'],
                                      tool_sha256=config['bindings']['zip_tool']['sha256'])
        for group in _GROUPS:
            if group in REPORT_OPERATIONS:
                materialize_report_operation(owner.pk, group=group, archive_writer=writer)
            elif group == 'O7':
                materialize_alert_operation(owner.pk, archive_writer=writer)
            elif group == 'O8':
                materialize_backup(owner.pk)
            else:
                with operation(owner, **ROSTER[-1]):
                    verify_required_outputs(owner)
    owner.refresh_from_db()
    return owner
