"""Explicit approved operational openings and own-predecessor carry-forward."""
from django.db import transaction
from mta.application.operational_upload_logs import LOG_BINDINGS
from mta.runtime.operational_models import OperationalAttempt
from mta.runtime.operational_native import OperationalPopulation, save_population, read_population
from mta.serialization import digest

OPENING_POLICY = 'cohort2-explicit-empty-opening-20261008'
ACTION_TYPES = [dict(ActionId=i, ActionDesc=text) for i, text in enumerate((
    'Request uploaded', 'Request reverted', 'Request approved',
    'Request approval reverted/ Rejected', 'Add/Modify request uploaded', 'Request deleted'), 1)]
OPENING_TABLES = {name: 'Importer/' + name for name, _ in LOG_BINDINGS}
OPENING_TABLES.update(UIUploadLogActionType='Importer/UIUploadLogActionType',
    BOR_OrderAllocationHistory='BPR/BOR_OrderAllocationHistory',
    RRR_OrderAllocation='BPR/RRR_OrderAllocation',
    RRR_OrderAllocationHistory='BPR/RRR_OrderAllocationHistory')


@transaction.atomic
def install_opening(attempt_id, *, populations):
    """Require every population explicitly; never turn absence into empty rows."""
    from mta.runtime.operational_attempts import configuration_value
    owner = OperationalAttempt.objects.select_for_update().select_related('run', 'configuration').get(pk=attempt_id)
    bindings = configuration_value(owner.configuration)['bindings']
    if (owner.status != 'RUNNING' or owner.predecessor_id is not None or owner.run.predecessor_id is not None
            or bindings.get('opening_policy') != OPENING_POLICY
            or bindings.get('opening_input_digest') != owner.run.input_digest):
        raise ValueError('Explicit first-run operational opening binding required')
    if not isinstance(populations, dict) or set(populations) != set(OPENING_TABLES):
        raise ValueError('Complete explicit operational opening roster required')
    if populations['UIUploadLogActionType'] != ACTION_TYPES:
        raise ValueError('Six exact native upload action seeds required')
    if any(populations[name] != [] for name in OPENING_TABLES if name != 'UIUploadLogActionType'):
        raise ValueError('Only the approved explicit empty opening domain is supported')
    if bindings.get('opening_digest') != digest(populations):
        raise ValueError('Operational opening content differs from declared configuration')
    if OperationalPopulation.objects.filter(attempt=owner, image__startswith='opening/').exists():
        raise ValueError('Operational opening already installed')
    for name, table in OPENING_TABLES.items():
        save_population(owner, 'opening/' + name, table, populations[name])


def opening_rows(owner, name):
    if name not in OPENING_TABLES:
        raise ValueError('Unknown operational opening population')
    if owner.predecessor_id is None:
        return read_population(owner, 'opening/' + name)
    from mta.runtime.operational_attempts import verify_attempt
    predecessor = OperationalAttempt.objects.select_related('run','configuration').get(pk=owner.predecessor_id)
    if (predecessor.status != 'SUCCEEDED' or predecessor.run_id != owner.run.predecessor_id
            or predecessor.configuration_id != owner.configuration_id):
        raise ValueError('Operational opening is not the own accepted predecessor')
    verify_attempt(predecessor)
    return read_population(predecessor, 'closing/' + name)


def upload_inputs(owner):
    """Bounded carry-forward: populated application log producers stay unsupported."""
    from mta.runtime.validation_storage import read_input
    from mta.runtime.services import read_outputs
    from mta.runtime.operational_attempts import configuration_value
    if owner.run.input_payload.get('schema') != 'fresh-daily-input-manifest-v2':
        raise ValueError('Typed daily upload-log sources required')
    source = read_input(owner.run, components=('profile', 'day'))
    if (source['profile'].get('force_flags', {}).get('nms_active') is not False
            or source['day'].get('new_force_requests') != []):
        raise ValueError('Populated/enabled upload-log producer requires its own supported binding')
    closing = read_outputs(owner.run)['ClosingState'][0]
    if closing.get('controls', {}).get('upload_log') != []:
        raise ValueError('Missing or populated current upload-log producer is unsupported')
    config = configuration_value(owner.configuration)
    horizons = [row['value'] for row in config['settings'] if row['name'] == 'UIUploadLogHorizon']
    if horizons != ['7'] or 'upload_log_client_folder' not in config['bindings']:
        raise ValueError('Explicit upload horizon and client-folder binding required')
    return dict(logs={name: opening_rows(owner, name) for name, _ in LOG_BINDINGS},
                actions=opening_rows(owner, 'UIUploadLogActionType'), horizon=7,
                client_folder=config['bindings']['upload_log_client_folder'])
