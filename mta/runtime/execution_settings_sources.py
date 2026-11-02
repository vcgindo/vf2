"""Bounded current control owners for one-time central adoption.

Only the declared small control bags are decoded. Masters, fact populations and
histories are neither reconstructed nor copied to obtain global settings.
Admission and the source lock are held by the management caller.
"""
from mta.runtime.execution_setting_owners import DESCRIPTORS


def current_state(owner):
    from mta.runtime.models import CalculationRun
    run = CalculationRun.objects.filter(mdm_input_capture__source_id=owner.source_id,
        kind='DAILY_CHAIN', status='SUCCEEDED').order_by('-business_date', '-created_at').first()
    if run is None:
        from mta.runtime.input_storage import read_input
        from mta.runtime.opening_storage import load_image
        paths = tuple('opening/state/' + '/'.join(item.source) for item in DESCRIPTORS)
        value = read_input(owner, components=paths, image_reader=load_image)
        return value.get('opening', {}).get('state', {})
    from mta.presentation.selective import image_rows
    state = {}
    for descriptor in DESCRIPTORS:
        image = 'closing/' + '/'.join(descriptor.source)
        if image not in run.production_manifest.get('images', {}):
            # A source absent from this accepted closing remains absent. In
            # particular, finalization may omit the original MDM task horizon;
            # its existing frozen capture remains its separate readable owner.
            continue
        current = state
        for key in descriptor.source[:-1]:
            current = current.setdefault(key, {})
        current[descriptor.source[-1]] = list(image_rows(run, image))
    return state


def reference_rows(owner):
    """Inspect existing immutable owners without making editable duplicates."""
    from mta.runtime.execution_setting_values import encode_scalar
    from mta.runtime.models import CalculationRun
    rows = []

    def append(module, parameter, ordinal, value, source, identity):
        kind, text = encode_scalar(value)
        rows.append(dict(module=module, parameter=parameter, ordinal=ordinal,
            value_kind=kind, value_text=text, value_state='NULL' if value is None else 'VALUE',
            activation='IMMUTABLE_OWNER_REFERENCE', source_owner=source, reference=identity))

    run = CalculationRun.objects.filter(mdm_input_capture__source_id=owner.source_id,
        status='SUCCEEDED', kind='DAILY_CHAIN').order_by('-business_date', '-created_at').first()
    if run is not None:
        from mta.runtime.input_reader import read_input
        frozen = read_input(run, components=('mdm_input/configuration',))
        configuration = frozen.get('mdm_input', {}).get('configuration', {})
        if 'task_status_log_horizon' in configuration:
            append('MDM', 'TaskStatusLogHorizon', 0, configuration['task_status_log_horizon'],
                'MDM daily capture/configuration (derived parser value)', str(run.pk))
    from mta.runtime.operational_models import OperationalAttempt
    from mta.runtime.operational_attempts import configuration_value
    attempt = OperationalAttempt.objects.filter(run__mdm_input_capture__source_id=owner.source_id,
        status='SUCCEEDED').select_related('configuration').order_by('-business_date', '-created_at').first()
    if attempt is not None:
        value = configuration_value(attempt.configuration)
        for item in value['settings']:
            append('Operations', item['name'], item['ordinal'], item['value'],
                'OperationalSetting', str(attempt.configuration_id))
        for item in value['alerts']:
            append('Operational alerts', item['name'], item['ordinal'], item['active'],
                'OperationalAlertSetting', str(attempt.configuration_id))
    from mta.runtime.report_definition_models import ReportDefinitionRegistration
    for registration in ReportDefinitionRegistration.objects.filter(initialization=owner).order_by('registered_at', 'pk'):
        for item in registration.report_rows.order_by('ordinal').values(
                'ordinal', 'ReportName', 'Active', 'Compression', 'DeleteOldFile', 'Placement'):
            for field in ('Active', 'Compression', 'DeleteOldFile', 'Placement'):
                append('Registered reports', item['ReportName'] + '.' + field, item['ordinal'], item[field],
                    'RegisteredRuntimeReport', registration.pk)
        for item in registration.ui_rows.order_by('ordinal').values('ordinal', 'ReportName', 'Active', 'GenerationScope'):
            for field in ('Active', 'GenerationScope'):
                append('Registered UI reports', item['ReportName'] + '.' + field, item['ordinal'], item[field],
                    'RegisteredDownloadableUiSetting', registration.pk)
    return rows
