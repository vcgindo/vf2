"""Owned PostgreSQL proof of preparation failure, retry and selection seals."""
from unittest.mock import patch
from django.db import connection, transaction, DatabaseError
from django.test import TransactionTestCase, override_settings
from mta.runtime.models import (CalculationRun, DailySourceReceipt, DailyUiPublication,
    DailyUiPublicationAttempt, BprPreparedRow, BprPreparedProjection)
from mta.presentation import daily_publication as publication
from mta.presentation.context import PublicationUnavailable, selected_run
from mta.presentation.daily_sources import recipe_digest
from mta.serialization import digest


@override_settings(VF_MTA_DAILY_PUBLICATION=True, VF_MTA_PUBLISHED_RUN='', VF_MTA_PUBLISHED_DIGEST='',
                   VF_MTA_SYNTHETIC_ROSTER='')
class DailyPublicationTests(TransactionTestCase):
    # Immutable projection triggers deliberately forbid flush. Each test owns
    # its explicit rollback boundary except the transaction-owner orchestration.
    def setUp(self):
        self.run = CalculationRun.objects.create(kind='DAILY_CHAIN', status='RUNNING',
            business_date='2026-10-06', input_digest='i'*64, output_digest='o'*64,
            production_digest='p'*64, execution_revision=self._testMethodName,
            input_payload={}, production_manifest={'images':{}})
        DailySourceReceipt.objects.create(run=self.run, input_digest=self.run.input_digest,
            recipe_digest=recipe_digest(), images={}, images_digest=digest({}))
        self.run.status='SUCCEEDED'
        self.run.save(update_fields=['status'])

    def test_failure_retry_preserves_success_and_cannot_select_partial(self):
        built=[]
        def build(run,name):
            built.append(name)
            if name=='second' and len(built)==2: raise ValueError('missing exact source')
            return dict(source_digest='source',recipe_digest='recipe',rows_digest=name,row_count=0)
        with patch('mta.presentation.daily_preparation.REQUIRED_LAYERS',('first','second')), \
                patch('mta.presentation.daily_preparation.prepare_layer',side_effect=build), \
                patch('mta.presentation.daily_preparation.verify_layer'):
            first=publication.prepare(self.run.pk,expected_output_digest=self.run.output_digest)
            self.assertEqual(first.status,'INCOMPLETE')
            with self.assertRaises(PublicationUnavailable):publication.require_ready(self.run)
            second=publication.prepare(self.run.pk,expected_output_digest=self.run.output_digest)
            self.assertEqual(second.status,'READY')
            self.assertEqual(built,['first','second','second'])
            self.assertEqual(list(second.attempts.order_by('pk').values_list('status',flat=True)),['FAILED','READY'])
            publication.require_ready(self.run)
            # Preparation never certifies engine parity.
            with override_settings(VF_MTA_PUBLISHED_RUN=str(self.run.pk),VF_MTA_PUBLISHED_DIGEST=self.run.output_digest):
                with self.assertRaisesRegex(PublicationUnavailable,'acceptance_required'):selected_run()
            publication.prepare(self.run.pk,expected_output_digest=self.run.output_digest)
            self.assertEqual(len(built),3)

    def test_production_guard_requires_owner_and_retains_seal(self):
        with self.assertRaises(DatabaseError),transaction.atomic():
            BprPreparedProjection.objects.create(run=self.run,source_digest='s',schema_digest='s',rows_digest='r',row_count=0)
        DailyUiPublication.objects.create(run=self.run,output_digest=self.run.output_digest,
            source_digest='s',configuration_digest='c',recipe_digest='r')
        # Roll back the guarded rows explicitly; flush is prohibited by seals.
        with transaction.atomic():
            with connection.cursor() as c:
                c.execute("SELECT set_config('fresh.daily_publication_build',%s,true)",[str(self.run.pk)])
            BprPreparedProjection.objects.create(run=self.run,source_digest='s',schema_digest='s',rows_digest='r',row_count=0)
            with self.assertRaises(DatabaseError),transaction.atomic():
                BprPreparedProjection.objects.filter(run=self.run).update(row_count=1)
            with self.assertRaises(DatabaseError),transaction.atomic():
                BprPreparedRow.objects.create(run=self.run,ordinal=0,a_ordinal=0)
            from mta.runtime.bpr_prepared_schema import verify_guards
            verify_guards(connection)
            transaction.set_rollback(True)

    def test_worker_interrupt_retains_success_identity_with_rows(self):
        built=[]
        def build(run,name):
            built.append(name)
            if name=='second' and built.count('second')==1:
                raise KeyboardInterrupt('bounded simulated worker loss')
            return dict(source_digest='s',recipe_digest='r',rows_digest=name,row_count=0)
        with patch('mta.presentation.daily_preparation.REQUIRED_LAYERS',('first','second')), \
                patch('mta.presentation.daily_preparation.prepare_layer',side_effect=build), \
                patch('mta.presentation.daily_preparation.verify_layer'):
            with self.assertRaises(KeyboardInterrupt):
                publication.prepare(self.run.pk,expected_output_digest=self.run.output_digest)
            owner=DailyUiPublication.objects.get(run=self.run)
            self.assertEqual(owner.layers['first']['status'],'READY')
            self.assertNotIn('second',owner.layers)
            result=publication.prepare(self.run.pk,expected_output_digest=self.run.output_digest)
            self.assertEqual(result.status,'READY')
            self.assertEqual(built,['first','second','second'])

    def test_typed_color_source_duplicates_round_trip_and_seal(self):
        from mta.presentation.daily_sources import write_sources, image_rows, COLOR_PATH
        from mta.runtime.models import DailyColorSequence
        run=CalculationRun.objects.create(kind='DAILY_CHAIN', business_date='2026-10-06',
            input_digest='colors',execution_revision='source-color',input_payload={})
        rows=[dict(Color='Black',SequenceNo=1),dict(Color='Black',SequenceNo=1)]
        with transaction.atomic():
            write_sources(run,{'BPRFinal':[{'ColorSequence':rows}]},
                opening={'supplier':{'SOBData':[],'MOQData':[]}})
            self.assertEqual(image_rows(run,COLOR_PATH),rows)
            with self.assertRaises(DatabaseError),transaction.atomic():
                DailyColorSequence.objects.filter(run=run).update(SequenceNo=2)
            with self.assertRaises(DatabaseError),transaction.atomic():
                DailyColorSequence.objects.create(run=run,ordinal=2,Color='Red',SequenceNo=2)
            transaction.set_rollback(True)

    def _fixture_teardown(self):
        # Django's global TRUNCATE conflicts with intentional immutable guards.
        # Tests use unique run identities; the exclusively owned test DB is
        # disposed by Django after the suite, never shared with the application.
        pass
