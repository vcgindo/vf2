"""Owned native predecessor lineage for Guided Excess history preparation."""
from datetime import timedelta

from mta.presentation.context import PublicationUnavailable
from mta.presentation.excess import PRODUCER_SHA
from mta.serialization import digest


IDENTITY_VERSION = 1


def _projection(run, *, verify_rows):
    from mta.runtime.models import ExcessProjection
    try:
        receipt = ExcessProjection.objects.get(run=run)
    except ExcessProjection.DoesNotExist as exc:
        raise PublicationUnavailable('native_guided_excess_projection_required') from exc
    if receipt.producer_sha256 != PRODUCER_SHA:
        raise PublicationUnavailable('native_guided_excess_projection_producer_changed')
    value = dict(producer_sha256=receipt.producer_sha256,
                 source_digest=receipt.source_digest,
                 rows_digest=receipt.rows_digest,
                 row_count=receipt.row_count)
    if verify_rows:
        from mta.presentation.selective import image_rows
        from mta.presentation.excess_storage import read_excess
        output = {
            'BPRReports': [{'vf_RationedReqReport': image_rows(
                run, 'reports/bpr/vf_RationedReqReport')}],
            'ClosingState': [{'dbm': {'SKULocStandardAttributes': image_rows(
                run, 'closing/dbm/SKULocStandardAttributes')}}],
        }
        try:
            rows = read_excess(run, output=output)
        except (ExcessProjection.DoesNotExist, ValueError) as exc:
            raise PublicationUnavailable(
                'native_guided_excess_projection_readback_changed') from exc
        if any(row['ReportDate'] != run.business_date.isoformat() for row in rows):
            raise PublicationUnavailable('native_guided_excess_projection_date_changed')
    return value


def identity(run, verify_rows=False):
    """Return the verified retained lineage and its explicit coverage boundary.

    Rows are retained for dates strictly greater than ``storage_cutoff``.
    ``coverage_cutoff`` is the earliest cutoff a reader may request: a smaller
    cutoff would ask for a day before either retained storage or the root day.
    """
    from mta.presentation.native_publication import identity as native_identity
    from mta.presentation.report_verification import check_active_owner

    lineage = []
    node = run
    seen_runs, seen_dates = set(), set()
    initialization = None
    while node is not None:
        if node.pk in seen_runs or node.business_date in seen_dates:
            raise PublicationUnavailable('native_guided_excess_history_duplicate_day')
        seen_runs.add(node.pk)
        seen_dates.add(node.business_date)
        # In the locked report operation, a predecessor contributes only its
        # Excess projection. Verify those rows and inputs below. The current
        # day's full audit and standalone predecessor audits remain exhaustive.
        guarded_predecessor = verify_rows and node is not run and check_active_owner(node)
        native = native_identity(node, verify_rows=verify_rows and not guarded_predecessor)
        if initialization is None:
            initialization = native['initialization']
        elif native['initialization'] != initialization:
            raise PublicationUnavailable('native_guided_excess_history_initialization_changed')
        lineage.append(dict(ordinal=len(lineage), run_id=str(node.pk),
            business_date=node.business_date.isoformat(), native=native,
            projection=_projection(node, verify_rows=verify_rows)))
        if node.predecessor_id is None:
            root_date = node.business_date
            break
        parent = node.predecessor
        if parent.business_date + timedelta(days=1) != node.business_date:
            raise PublicationUnavailable('native_guided_excess_history_gap')
        node = parent
    cutoff = root_date - timedelta(days=1)
    # This is known presentation coverage, never an assertion that pre-root
    # history was empty or a replacement for a requested report horizon.
    return dict(version=IDENTITY_VERSION, policy='persisted-own-chain-coverage-v1',
        run_id=str(run.pk), coverage_days=len(lineage), root_date=root_date.isoformat(),
        storage_cutoff=cutoff.isoformat(), coverage_cutoff=cutoff.isoformat(),
        lineage=lineage, digest=digest(lineage))


def require_cutoff(value, cutoff):
    """Deny a query which asks for history older than proven coverage."""
    if cutoff.isoformat() < value['coverage_cutoff']:
        raise PublicationUnavailable('native_guided_excess_history_coverage_unavailable')


def source_digest(daily_source, value):
    return digest(dict(version=1, daily_source=daily_source,
                       guided_excess_history=value))
