"""PostgreSQL proof of explicit current-request ownership and frozen captures."""
from django.db import transaction, connection, DatabaseError
from django.test import TestCase
from mta.presentation import daily_requests as requests
from mta.runtime.models import CalculationRun, DailyOpenRequest, DailyCapturedRequest
from mta.serialization import digest


class DailyRequestTests(TestCase):
    def run_row(self, suffix):
        return CalculationRun.objects.create(kind='DAILY_CHAIN', status='RUNNING',
            business_date='2026-10-06', input_digest=digest(suffix),
            execution_revision='request-source-'+suffix, input_payload={})

    def test_missing_source_is_unavailable_and_empty_requires_owner(self):
        with transaction.atomic():
            self.assertIsNone(requests.snapshot())
        requests.initialize([], provenance={'source': 'explicit-empty-test'})
        with transaction.atomic():
            value = requests.snapshot()
            run = self.run_row('empty')
            requests.bind(run, value)
        self.assertEqual(requests.rows(run), [])
        self.assertEqual(requests.metadata(run)['count'], 0)

    def test_frozen_retry_preserves_duplicates_nulls_and_text_user(self):
        row = dict.fromkeys(requests.FIELDS)
        row.update(SKUCode='A', WhCode='LOC', UserId='Stage2 Broad',
                   Request='Need stock', RequestDate='2026-10-06T08:00:00')
        owner = requests.initialize([row, row], provenance={'source': 'retained-test-input'})
        with transaction.atomic():
            value = requests.snapshot()
            run = self.run_row('failed')
            requests.bind(run, value)
        run.status = 'FAILED'; run.save(update_fields=['status'])
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.daily_request_owner',%s,true)", [owner.pk])
        DailyOpenRequest.objects.filter(owner=owner).update(Request='Later request')
        owner.revision += 1; owner.save(update_fields=['revision'])
        with transaction.atomic():
            retry = self.run_row('retry')
            requests.bind(retry, value)
        self.assertEqual(requests.rows(run), [row, row])
        self.assertEqual(requests.rows(retry), [row, row])
        self.assertEqual(DailyCapturedRequest.objects.filter(capture_id=retry.pk).count(), 2)

    def test_capture_refuses_unqualified_field_or_digest_changes(self):
        with self.assertRaisesRegex(ValueError, 'Complete native request'):
            requests.initialize([{'SKUCode': 'A'}], provenance={'source': 'test'})
        requests.initialize([], provenance={'source': 'test'})
        with transaction.atomic():
            value = requests.snapshot()
            value['rows_digest'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'Frozen request source drift'):
                requests.bind(self.run_row('drift'), value)

    def test_request_capture_and_provenance_cannot_be_rewritten(self):
        owner = requests.initialize([], provenance={'source': 'retained-test'})
        with transaction.atomic():
            run = self.run_row('sealed')
            requests.bind(run, requests.snapshot())
        from mta.runtime.models import DailyRequestCapture
        with self.assertRaises(DatabaseError), transaction.atomic():
            DailyRequestCapture.objects.filter(run=run).update(rows_digest='0' * 64)
        with self.assertRaises(DatabaseError), transaction.atomic():
            owner.provenance = {'source': 'replacement'}
            owner.save(update_fields=['provenance'])
