"""Read report-stage inputs from completed typed daily owners, without replay."""
from copy import deepcopy

from django.db import transaction
from mta.application.operational_exceptions import (
    BPR_MASTER_FIELDS, DAILY_CONSUMPTION_FIELDS, PHASE_OUT_FIELDS,
)
from mta.application.r1_importer_master import MASTER_COLUMNS
from mta.application.operational_norm_reports import REQUIRED_CONFIGURATION
from mta.runtime.models import CalculationRun
from mta.runtime.services import read_outputs
from mta.runtime.validation_storage import read_input
from mta.serialization import digest


def _population(owner, name, fields):
    if not isinstance(owner, dict) or name not in owner or not isinstance(owner[name], list):
        raise ValueError('Explicit typed operational population absent: ' + name)
    rows = owner[name]
    if any(not isinstance(row, dict) or set(row) != set(fields) for row in rows):
        raise ValueError('Operational source fields differ: ' + name)
    return deepcopy(rows)


@transaction.atomic
def read_report_inputs(*, run_id, expected_output_digest):
    """Bind O2/O3/O6 inputs to their existing canonical stage owners.

    This is deliberately not an all-obligation readiness verdict. BOR's separate
    live-capture owner, openings, files, alerts and backups must still be checked
    by the complete operational runner.
    """
    run = CalculationRun.objects.get(pk=run_id)
    if (run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED'
            or not expected_output_digest or run.output_digest != expected_output_digest):
        raise ValueError('Exact completed daily report owner required')
    if run.input_payload.get('schema') != 'fresh-daily-input-manifest-v2':
        raise ValueError('Operational reports require typed daily inputs, not trace input')
    source = read_input(run, components=('profile',))
    output = read_outputs(run)
    closing_rows = output.get('ClosingState')
    if not isinstance(closing_rows, list) or len(closing_rows) != 1:
        raise ValueError('One typed operational closing owner required')
    closing = closing_rows[0]
    profile = source['profile']
    batch = profile.get('delivery', {}).get('batch')
    # Cohort1 also retained Norm0 calculation cells. The approved Cohort2 file
    # roster excludes all Norm0 files; retaining those cells is not a file grant.
    # Require every setting used by the four enabled exports exactly, and retain
    # the separate source flags in the receipt rather than rewriting them to zero.
    inactive_exports = ('ActivateNorm0Report30Days', 'ActivateNorm0Report60Days', 'ActivateNorm0Report90Days')
    if (not isinstance(batch, dict)
            or any(batch.get(name) != value for name, value in REQUIRED_CONFIGURATION.items()
                   if name not in inactive_exports)
            or any(type(batch.get(name)) is not int or batch[name] not in (0, 1) for name in inactive_exports)):
        raise ValueError('Operational report activation/horizon differs from supported configuration')
    # These are the preserved pre-DBM control image and processed Importer master,
    # not raw input or DBMFinal.PhaseOutTbl after subsequent processing.
    inputs = {
        'O2': dict(bpr_master=_population(closing.get('bpr'), 'BPRMaster', BPR_MASTER_FIELDS),
                   daily_consumption=_population(closing.get('bpr'), 'DailyConsumption', DAILY_CONSUMPTION_FIELDS),
                   sku_descriptions=_population(closing.get('importer'), 'SKUDescriptionTbl', ('SKUCode', 'SKUDescription')),
                   site_descriptions=_population(closing.get('importer'), 'SiteDescriptionTbl', ('WHCode', 'WHDescription')),
                   business_date=run.business_date.isoformat()),
        'O3': dict(master_data=_population(closing.get('importer'), 'MasterData', MASTER_COLUMNS),
                   phase_out=_population(closing.get('controls'), 'phase_out', PHASE_OUT_FIELDS)),
        'O6': dict(reports=deepcopy(output['Reports']), configuration=deepcopy(REQUIRED_CONFIGURATION)),
    }
    return dict(run_id=str(run.pk), business_date=run.business_date.isoformat(),
        output_digest=run.output_digest, input_digest=run.input_digest,
        source_report_configuration={name: batch[name] for name in REQUIRED_CONFIGURATION},
        sources=inputs, source_digests={group: digest(values) for group, values in inputs.items()})
