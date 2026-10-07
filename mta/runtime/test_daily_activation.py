"""PostgreSQL proof that access activation cannot replace native readiness."""
from unittest.mock import patch
from django.db import connection, transaction, DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from mta.runtime.models import CalculationRun, DailyUiPublication, DailyUiActivation
from mta.presentation import daily_activation as activation, daily_publication as publication
from mta.presentation.context import PublicationUnavailable


@override_settings(VF_MTA_DAILY_PUBLICATION=True, VF_MTA_PUBLISHED_RUN='',
    VF_MTA_PERMISSIONS_SHA256='', VF_MTA_HIERARCHY_SHA256='',
    VF_MTA_SYNTHETIC_ROSTER='core-without-bor-v1')
class DailyActivationTests(TestCase):
    def setUp(self):
        self.run = CalculationRun.objects.create(kind='DAILY_CHAIN', status='SUCCEEDED',
            business_date='2026-06-06', input_digest='i'*64, output_digest='o'*64,
            production_digest='p'*64, execution_revision=self._testMethodName,
            parity_summary={'status':'PASS'}, input_payload={}, production_manifest={})
        from mta.presentation.daily_preparation import required_layers
        self.layers = {name:dict(status='READY', receipt={'name':name}) for name in required_layers()}
        self.pub = DailyUiPublication(run=self.run, output_digest=self.run.output_digest,
            source_digest='s'*64, configuration_digest=publication.configuration_identity(),
            recipe_digest=publication.recipe_identity(), status='READY', layers=self.layers,
            sealed_at=timezone.now())
        self.pub.seal_digest = publication.seal_identity(self.pub)
        self.pub.save()
        self.before = DailyUiPublication.objects.filter(run=self.run).values().get()
        for target, kwargs in (
            ('mta.presentation.daily_publication.source_identity', {'return_value':'s'*64}),
            ('mta.presentation.daily_activation.access_manifest', {'return_value':{'approved':True}}),
        ):
            mocked = patch(target, **kwargs); mocked.start(); self.addCleanup(mocked.stop)
        self.access = override_settings(VF_MTA_PERMISSIONS_SHA256=activation.CATALOGUE,
                                       VF_MTA_HIERARCHY_SHA256='h'*64)
        self.access.enable(); self.addCleanup(self.access.disable)

    def activate(self):
        return activation.activate(self.run, expected_output_digest=self.run.output_digest,
            expected_seal=self.pub.seal_digest)

    def test_exact_binding_revalidates_18_and_retains_original_seal(self):
        with self.assertRaisesRegex(PublicationUnavailable, 'activation_missing'):
            publication.require_ready(self.run)
        with patch('mta.presentation.daily_preparation.verify_layer') as verify:
            result = self.activate()
            self.assertEqual(verify.call_count, 18)
            self.assertEqual({call.args[1] for call in verify.call_args_list}, set(self.layers))
            self.assertEqual(self.activate().pk, result.pk)
        self.assertEqual(DailyUiActivation.objects.count(), 1)
        publication.require_ready(self.run)
        self.assertEqual(DailyUiPublication.objects.filter(run=self.run).values().get(), self.before)
        with override_settings(VF_MTA_HIERARCHY_SHA256='x'*64):
            with self.assertRaisesRegex(PublicationUnavailable, 'activation_missing_or_changed'):
                publication.require_ready(self.run)

    def test_third_configuration_change_denied(self):
        with override_settings(VF_MTA_ACTIONS_ENABLED=not __import__('django.conf',fromlist=['settings']).settings.VF_MTA_ACTIONS_ENABLED):
            with self.assertRaisesRegex(PublicationUnavailable, 'non_access_configuration_changed'):
                self.activate()
        self.assertFalse(DailyUiActivation.objects.exists())

    def test_failed_layer_cannot_create_activation(self):
        with patch('mta.presentation.daily_preparation.verify_layer', side_effect=ValueError('changed rows')):
            with self.assertRaisesRegex(ValueError, 'changed rows'): self.activate()
        self.assertFalse(DailyUiActivation.objects.exists())

    def test_output_seal_acceptance_and_recipe_are_not_waived(self):
        with self.assertRaises(PublicationUnavailable):
            activation.activate(self.run, expected_output_digest='wrong', expected_seal=self.pub.seal_digest)
        with self.assertRaises(PublicationUnavailable):
            activation.activate(self.run, expected_output_digest=self.run.output_digest, expected_seal='wrong')
        with patch('mta.presentation.daily_publication.recipe_identity', return_value='wrong'):
            with self.assertRaises(PublicationUnavailable): self.activate()
        self.run.parity_summary = {'status':'FAIL'}
        with self.assertRaises(PublicationUnavailable): self.activate()
        self.assertFalse(DailyUiActivation.objects.exists())

    def test_database_owner_and_append_only_guards(self):
        expected = activation.values(self.run, self.pub)
        with self.assertRaises(DatabaseError), transaction.atomic():
            DailyUiActivation.objects.create(publication=self.pub, **expected)
        with patch('mta.presentation.daily_preparation.verify_layer'): self.activate()
        for query in (
            lambda: DailyUiActivation.objects.update(hierarchy_digest='wrong'),
            lambda: DailyUiActivation.objects.all().delete(),
            lambda: DailyUiActivation.objects.create(publication=self.pub, **expected),
        ):
            with self.assertRaises(DatabaseError), transaction.atomic(): query()
        with self.assertRaises(DatabaseError), transaction.atomic(), connection.cursor() as cursor:
            cursor.execute('TRUNCATE mta.fresh_mta_dailyuiactivation')
        self.assertEqual(DailyUiPublication.objects.filter(run=self.run).values().get(), self.before)

    def test_supplement_never_authorizes_builder_or_fixture(self):
        self.assertFalse(activation.native_verification_with_access(self.run, False))
        self.assertFalse(activation.native_verification_with_access(None, True))
        self.assertTrue(activation.native_verification_with_access(self.run, True))
