"""Transactional reporting lifecycle checks on an existing migrated publication."""
import json
import os
from pathlib import Path
import sys
from uuid import uuid4


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
    import django
    django.setup()
    from django.db import connection, transaction, DatabaseError
    from django.test import override_settings
    from mta.presentation.context import selected_run, PublicationUnavailable
    from mta.presentation import admission, btr_reporting as reporting
    from mta.runtime.models import BtrReportingGeneration as Generation, BtrJoinReference as Reference
    target = Path(sys.argv[1])
    if target.exists():
        raise ValueError('Preserve existing evidence')
    run = selected_run()
    generation = Generation.objects.get(run=run, status='READY')
    before = admission.admit()
    checks = []
    result = dict(status='FAILED', generation=str(generation.pk), checks=checks)
    try:
        with override_settings(VF_BTR_REPORTING_GENERATION=str(generation.pk)):
            active = admission.admit()
            assert active['admission_digest'] != before['admission_digest']
            assert reporting.selected_generation(run).pk == generation.pk
            assert admission.require_admission() == active['admission_digest']
            checks.append('exact_generation_startup_and_request_admission')
            observer = connection.copy(alias='btr_lifecycle_observer')
            try:
                with transaction.atomic():
                    private = Generation.objects.create(run=run, source_kind=run.kind,
                        business_date=run.business_date, source_digest='0'*64)
                    Reference.objects.create(generation=private, branch='tech', export=False,
                                             sku_code='PRIVATE', location_code='PRIVATE', a_ordinal=0)
                    with observer.cursor() as cursor:
                        cursor.execute('SELECT count(*) FROM mta.fresh_mta_btrjoinreference WHERE generation_id=%s', [private.pk])
                        assert cursor.fetchone()[0] == 0
                    assert admission.require_admission() == active['admission_digest']
                    assert reporting.selected_generation(run).pk == generation.pk
                    transaction.set_rollback(True)
                checks.append('private_build_invisible_to_independent_connection_and_selected_reader')
            finally:
                observer.close()
            # Actual PostgreSQL guards, each in a rolled-back savepoint.
            for name, query, params in (
                ('generation_update', 'UPDATE mta.fresh_mta_btrreportinggeneration SET eligible=false WHERE id=%s', [generation.pk]),
                ('reference_update', 'UPDATE mta.fresh_mta_btrjoinreference SET sku_code=sku_code WHERE id=(SELECT min(id) FROM mta.fresh_mta_btrjoinreference WHERE generation_id=%s)', [generation.pk]),
                ('reference_delete', 'DELETE FROM mta.fresh_mta_btrjoinreference WHERE id=(SELECT min(id) FROM mta.fresh_mta_btrjoinreference WHERE generation_id=%s)', [generation.pk]),
                ('reference_insert', "INSERT INTO mta.fresh_mta_btrjoinreference (generation_id,branch,export,a_ordinal) VALUES (%s,'tech',false,0)", [generation.pk]),
                ('reference_truncate', 'TRUNCATE mta.fresh_mta_btrjoinreference', [])):
                try:
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute(query, params)
                        transaction.set_rollback(True)
                except DatabaseError as exc:
                    assert 'BTR' in str(exc), str(exc)
                    checks.append(name + '_denied')
                else:
                    raise AssertionError(name + ' unexpectedly allowed')
            with override_settings(VF_BTR_REPORTING_GENERATION=str(uuid4())):
                try:
                    admission.require_admission()
                except PublicationUnavailable:
                    checks.append('unknown_generation_fail_closed')
                else:
                    raise AssertionError('Unknown generation admitted')
            admission.admit()
            reporting.verify_generation(generation)
        restored = admission.admit()
        assert restored == before
        checks.append('accepted_selection_rollback_restores_exact_admission')
        result.update(status='PASS', accepted_admission=before, reporting_admission=active)
    finally:
        target.write_text(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
