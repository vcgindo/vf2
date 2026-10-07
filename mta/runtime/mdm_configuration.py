"""Carry declared connector configuration outside canonical closing projections."""
from copy import deepcopy

from mta.serialization import digest


def capture_configuration_for_day(importer_settings, *, predecessor=None, source=None):
    from mta.mdm.daily_input import (capture_configuration, NMS_DATA_HISTORY_HORIZON,
                                    SCHEMA, SQL_DIGEST)
    from mta.runtime.validation_storage import read_input

    horizons = [row for row in importer_settings
                if row.get('Parameter') == 'TaskStatusLogHorizon']
    if horizons or predecessor is None:
        # Preserve the existing parser's missing-root, duplicate and value rules.
        return capture_configuration(importer_settings)
    capture = getattr(predecessor, 'mdm_input_capture', None)
    if (source is None or predecessor.status != 'SUCCEEDED'
            or predecessor.kind != 'DAILY_CHAIN' or capture is None
            or capture.status != 'CONSUMED' or capture.source_id != source.pk):
        raise ValueError('Successor MDM configuration requires its consumed same-source predecessor')
    snapshot = read_input(predecessor, components=('mdm_input',)).get('mdm_input')
    if (not isinstance(snapshot, dict) or snapshot.get('schema') != SCHEMA
            or snapshot.get('source_id') != source.pk
            or snapshot.get('source_digest') != source.digest
            or snapshot.get('sql_digest') != SQL_DIGEST
            or capture.sql_digest != SQL_DIGEST
            or snapshot.get('nms_active') != capture.nms_active
            or snapshot.get('revision_digest') != capture.revision_digest
            or digest({k:v for k,v in snapshot.items() if k != 'revision_digest'})
                != capture.revision_digest):
        raise ValueError('Successor MDM configuration capture integrity differs')
    configuration = snapshot.get('configuration', {})
    horizon = configuration.get('task_status_log_horizon')
    if (type(horizon) is not int
            or configuration.get('nms_data_history_horizon') != NMS_DATA_HISTORY_HORIZON):
        raise ValueError('Successor MDM configuration lacks exact frozen horizons')
    resolved = deepcopy(importer_settings)
    resolved.append({'Parameter': 'TaskStatusLogHorizon', 'Value': horizon})
    return capture_configuration(resolved)
