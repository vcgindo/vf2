"""Application binding to an initialized, completed production day.

Calculation ownership is independent of report readiness. A completed native
day never gains application access merely by passing this source check.
"""
from datetime import timedelta
from django.conf import settings
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest
from mta.presentation.request_scope import once_per_request
from mta.presentation.identity_reuse import native_identity


def enabled():
    return bool(getattr(settings, 'VF_MTA_NATIVE_PUBLICATION', False))


def require_mode():
    """Native admission cannot borrow a fixture or synthetic acceptance policy."""
    from mta.presentation.native_mode import require_configuration
    require_configuration()
    if not enabled() or not getattr(settings, 'VF_MTA_DAILY_PUBLICATION', False):
        raise PublicationUnavailable('native_daily_publication_required')
    if any(getattr(settings, name, '') for name in (
            'VF_MTA_FIXTURE_FILE', 'VF_MTA_FIXTURE_SHA256',
            'VF_MTA_OPERATIONAL_POLICY', 'VF_MTA_OPERATIONAL_RECEIPT',
            'VF_MTA_CONSUMPTION_POLICY', 'VF_MTA_SYNTHETIC_ROSTER')):
        raise PublicationUnavailable('native_admission_mode_conflict')


@once_per_request
@native_identity
def identity(run, *, verify_rows=False):
    from mta.mdm.initialization_contract import SOURCE_SCHEMA
    from mta.runtime.input_reader import read_input
    from mta.runtime.initialization_models import ProductionInitialization
    from mta.runtime.mdm_daily_models import MdmDailyInputCapture
    from mta.presentation import daily_sources
    if (run.kind != 'DAILY_CHAIN' or run.status != 'SUCCEEDED'
            or not run.input_digest or not run.output_digest or not run.production_digest):
        raise PublicationUnavailable('native_completed_day_required')
    if getattr(settings, 'VF_MTA_SYNTHETIC_ROSTER', ''):
        raise PublicationUnavailable('native_full_report_roster_required')
    capture = MdmDailyInputCapture.objects.select_related('source').filter(run=run).first()
    if (capture is None or capture.status != 'CONSUMED'
            or capture.source.receipt.get('schema') != SOURCE_SCHEMA):
        raise PublicationUnavailable('native_consumed_initialization_required')
    owner = ProductionInitialization.objects.select_related('source').filter(source=capture.source).first()
    if owner is None:
        raise PublicationUnavailable('native_initialization_missing')
    binding = dict(id=str(owner.pk), source_digest=owner.source.digest,
        input_sha256=owner.input_sha256, content_digest=owner.input_digest,
        configuration_digest=owner.configuration_digest)
    from mta.presentation.report_verification import profile_reference
    referenced = profile_reference(run, owner)
    components = ('initialization_binding', 'lineage') if referenced else ('initialization_binding', 'profile', 'lineage')
    inputs = read_input(run, components=components)
    if (inputs.get('initialization_binding') != binding or not referenced
            and digest(inputs.get('profile')) != owner.configuration_digest):
        raise PublicationUnavailable('native_initialization_binding_changed')
    lineage = inputs.get('lineage', {})
    if run.predecessor_id:
        parent = run.predecessor
        previous = read_input(parent, components=('initialization_binding',))
        if (parent.kind != 'DAILY_CHAIN' or parent.status != 'SUCCEEDED'
                or previous.get('initialization_binding') != binding
                or parent.business_date + timedelta(days=1) != run.business_date
                or lineage.get('run_id') != str(parent.pk)
                or lineage.get('output_digest') != parent.output_digest):
            raise PublicationUnavailable('native_report_predecessor_changed')
    elif owner.opening_date + timedelta(days=1) != run.business_date:
        raise PublicationUnavailable('native_report_opening_date_changed')
    source = daily_sources.receipt(run)
    if verify_rows:
        from mta.presentation.report_verification import audit_native_rows
        audit_native_rows(run, source)
    return dict(initialization=binding, run_id=str(run.pk),
        business_date=run.business_date.isoformat(), output_digest=run.output_digest,
        input_digest=run.input_digest, production_digest=run.production_digest,
        predecessor_id=str(run.predecessor_id) if run.predecessor_id else None,
        sources_digest=source.images_digest, sources_recipe=source.recipe_digest)


def require_publication(run):
    """Serving requires the full sealed roster and its own Planning summary."""
    value = identity(run)
    if not getattr(settings, 'VF_MTA_DAILY_PUBLICATION', False):
        raise PublicationUnavailable('native_daily_publication_required')
    from mta.presentation.daily_publication import require_ready
    from mta.presentation.planning_summary_daily import require_ready as require_summary
    require_ready(run)
    require_summary(run)
    return value
