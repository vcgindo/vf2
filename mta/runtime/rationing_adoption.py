"""One-time storage anchor owned by the normal maintenance upgrade transaction."""
from contextlib import closing

from django.db import connection, transaction

from mta.serialization import digest
from mta.runtime.models import CalculationRun, ProductionInitialization
from mta.runtime.rationing_reader import FAMILY, IMAGE, TABLE, read_cut
from mta.runtime.state_cut_models import OperationalStateCut


def adopt(owner):
    """Preserve accepted runs; copy only the exact terminal old-format image.

    The normal upgrade already holds source/job locks and proves maintenance.
    This adapter requires its provisioning role and its existing transaction;
    there is no daily fallback, operator switch or accepted-run reseal.
    """
    if not connection.in_atomic_block:
        raise ValueError('Storage adoption requires the existing upgrade transaction')
    from mta.runtime.ingestion_authority import _provisioner
    from mta.runtime.input_reader import read_execution_input
    from mta.runtime.execution_settings import require_snapshot
    from mta.runtime.rationing_writer import begin_initial_anchor, seal_initial_anchor, seal_anchor_rows
    from mta.runtime import relational_state
    with transaction.atomic(), connection.cursor() as cursor:
        _provisioner(cursor)
        owner = ProductionInitialization.objects.select_for_update().get(pk=owner.pk)
        captured = CalculationRun.objects.filter(mdm_input_capture__source_id=owner.source_id)
        if captured.filter(status='RUNNING').exists():
            raise ValueError('Storage adoption refuses unfinished calculation')
        accepted = captured.filter(status='SUCCEEDED', mdm_input_capture__status='CONSUMED')
        # A branch is an ambiguity, not a reason to choose by date or UUID.
        parents = CalculationRun.objects.filter(status__in=('RUNNING', 'SUCCEEDED'),
            predecessor_id__isnull=False).values('predecessor_id')
        terminal = list(accepted.exclude(pk__in=parents)[:2])
        if len(terminal) > 1 or not terminal and accepted.exists():
            raise ValueError('Storage adoption requires one exact accepted terminal prefix')
        run = terminal[0] if terminal else None
        existing = OperationalStateCut.objects.filter(initialization=owner, family=FAMILY).order_by('-position').first()
        if existing is not None:
            cut = read_cut(existing.pk)
            if cut.run != (run.pk if run else None):
                raise ValueError('Storage anchor does not cover the current accepted prefix')
            return dict(status='EXISTING', cut_id=str(cut.identity), root_digest=cut.root_digest)
        if run is None:
            cut = begin_initial_anchor(owner)
            seal_initial_anchor(cut, owner)
        else:
            if (run.production_manifest.get('version') not in (2, 3)
                    or digest(run.production_manifest) != run.production_digest):
                raise ValueError('Storage adoption requires its intact native accepted manifest')
            item = run.production_manifest['images'][IMAGE]
            if item.get('table') != TABLE or item.get('image') != IMAGE or 'storage_format' in item:
                raise ValueError('Storage adoption requires the exact legacy rationing image')
            frozen = read_execution_input(run, components=('profile', 'execution_settings', 'initialization_binding'))
            if frozen['initialization_binding']['id'] != str(owner.pk):
                raise ValueError('Storage adoption captured initialization differs')
            settings = require_snapshot(owner, frozen['profile'], frozen.get('execution_settings'), run.business_date)
            cut = OperationalStateCut.objects.create(initialization=owner, family=FAMILY, position=0,
                run=run, input_digest=run.input_digest, settings_digest=settings)
            anchor = dict(owner_kind='RUN', owner_id=str(run.pk), manifest_digest=run.production_digest,
                          image=IMAGE, digest=item['digest'], count=item['count'])
            # Exhaust the original checksum reader once and close it before a
            # possible savepoint rollback. Never replay the business producer.
            with closing(relational_state.iter_image(run, item)) as rows:
                seal_anchor_rows(cut, item, rows, anchor)
        accepted_cut = read_cut(cut.pk)
        return dict(status='ADOPTED', cut_id=str(cut.pk), root_digest=accepted_cut.root_digest,
                    source_run=str(run.pk) if run else None, rows=accepted_cut.body['count'])
