"""Read mapped alert inputs from exact persisted owners, without calculation."""
from django.db import transaction
from mta.application.operational_alerts import seed_settings
from mta.domain.complete_daily_fullkit import unavailable_file_reasons
from mta.domain.complete_daily_scalars import ascii_equal
from mta.runtime.operational_attempts import configuration_value
from mta.runtime.operational_force_source import read_force_source
from mta.runtime.operational_models import OperationalAttempt
from mta.runtime.operational_native import save_population, read_population
from mta.runtime.services import read_outputs
from mta.runtime.validation_storage import read_input
from mta.serialization import digest

ABORT_OPENING_POLICY = 'cohort2-explicit-abort-opening-v1'


@transaction.atomic
def install_alert_opening(attempt_id, *, abort_reasons):
    owner = OperationalAttempt.objects.select_for_update().select_related('run', 'configuration').get(pk=attempt_id)
    bindings = configuration_value(owner.configuration)['bindings']
    if (owner.predecessor_id is not None or owner.run.predecessor_id is not None
            or bindings.get('abort_opening_policy') != ABORT_OPENING_POLICY
            or bindings.get('opening_input_digest') != owner.run.input_digest
            or bindings.get('abort_opening_digest') != digest(abort_reasons)):
        raise ValueError('Exact explicit first-run abort opening binding required')
    if abort_reasons != []:
        raise ValueError('Only declared empty first-run abort history is supported')
    return save_population(owner, 'opening/RunAbortReasons', 'Importer/RunAbortReasons', abort_reasons)


def _rows(owner, key):
    if not isinstance(owner, dict) or not isinstance(owner.get(key), list):
        raise ValueError('Required mapped alert source absent: '+key)
    return owner[key]


def read_alert_inputs(owner):
    config = configuration_value(owner.configuration)
    settings = {row['name']: str(int(row['active'])) for row in config['alerts']}
    if settings != seed_settings() or len(config['alerts']) != 14:
        raise ValueError('All fourteen exact seeded alert flags required')
    bindings = config['bindings']
    # Bound transport suppression is explicit; no SMTP/mail operation exists.
    alert_config = bindings.get('alert_configuration')
    required = {'recipient', 'cc_recipient', 'profile', 'site',
                'attach_invalid_data_report_zip', 'auto_dbm_active',
                'distributor_system_active', 'fnc_match_master_norm', 'nms_active'}
    if not isinstance(alert_config, dict) or set(alert_config) != required:
        raise ValueError('Complete explicit generic alert configuration required')
    if (alert_config['recipient'] != 'Not-Defined' or alert_config['profile'] != 'Not-Defined'
            or alert_config['auto_dbm_active'] is not False
            or alert_config['distributor_system_active'] is not False
            or alert_config['nms_active'] is not False):
        raise ValueError('Alert configuration exceeds approved local generic domain')
    source = read_input(owner.run, components=('profile',))['profile']
    if source.get('delivery', {}).get('site_code') != alert_config['site']:
        raise ValueError('Alert site differs from its calculated owner')
    flags = source.get('force_flags', {})
    if (flags.get('nms_active') is not alert_config['nms_active']
            or type(flags.get('ignore_master_norm')) is not bool
            or (not flags['ignore_master_norm']) is not alert_config['fnc_match_master_norm']):
        raise ValueError('Force-alert setting differs from its calculated owner')
    output = read_outputs(owner.run)
    closing = output['ClosingState'][0]
    complete = closing.get('complete')
    critical = _rows(complete, 'CriticalFiles')
    # C1 explicitly binds no generic CriticalFiles. Nonempty closing rows cannot
    # certify that a pre-run filesystem resolver or client hook actually ran.
    if critical != []:
        raise ValueError('Populated critical files need source-positioned resolver evidence')
    sanitation = _rows(complete, 'DataSanitizationResult')
    if owner.predecessor_id is None:
        abort_opening = read_population(owner, 'opening/RunAbortReasons')
    else:
        from mta.runtime.operational_attempts import verify_attempt
        previous = OperationalAttempt.objects.select_related('configuration', 'run').get(pk=owner.predecessor_id)
        if (previous.run_id != owner.run.predecessor_id or previous.status != 'SUCCEEDED'
                or previous.configuration_id != owner.configuration_id):
            raise ValueError('Abort history requires its own completed operational predecessor')
        verify_attempt(previous)
        abort_opening = read_population(previous, 'closing/RunAbortReasons')
    clock = owner.business_date.isoformat()+'T00:00:00'
    abort = abort_opening
    for file_type in ('GoAheadFiles', 'DataFiles'):
        abort = unavailable_file_reasons(abort, critical, file_type, clock, equal=ascii_equal)
    force = read_force_source(owner.run)
    # Native DBMMaster uses WHCode; capture preserves the producer's original
    # wire spelling. Normalize only these labels, not values or row order.
    masters = [{key.casefold(): value for key, value in row.items()} for row in force['DBMMaster']]
    controls = _rows(output, 'Reports')
    control_reports = [row for row in controls if row.get('stage') == 'controls']
    if len(control_reports) != 1:
        raise ValueError('One persisted control-report source required')
    reports = control_reports[0]['tables']
    populations = dict(RejectedMaster=_rows(closing.get('importer'), 'RejectedMaster'),
        RunAbortReasons=abort, DataSanitizationResult=sanitation,
        PhaseOut=_rows(closing.get('control_aux'), 'phase_requests'),
        PhaseInNorms=_rows(closing.get('control_aux'), 'phase_in_requests'),
        PhaseInPhaseOutExceptionLog=_rows(closing.get('control_aux'), 'phase_exceptions'),
        ForceNormChange=force['ForceNormChange'], MasterDataRaw=force['MasterDataRaw'],
        DBMMaster=[dict(SKUCode=row['skucode'], WHCode=row['whcode'], Norm=row['norm']) for row in masters],
        FailedForceNormChange=_rows(reports, 'failed_force'),
        BPRExceptions=read_population(owner, 'BPRExceptions'))
    return dict(settings=settings, configuration=dict(alert_config,
        business_date=owner.business_date.isoformat(), run_datetime=clock,
        critical_data_available=True), populations=populations, reports=reports)
