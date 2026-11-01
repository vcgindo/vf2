"""Coordinator-only releases preserve accepted content, not current source text."""
import os
import unittest
from copy import deepcopy
from types import SimpleNamespace as NS
from uuid import uuid4
from unittest.mock import Mock,patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','isolated-publication-compatibility-test')
import django
django.setup()
from django.test import override_settings
from django.db import connection
from mta.presentation import daily_publication as daily,daily_preparation
from mta.presentation.context import PublicationUnavailable


class PublicationPatchTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(override_settings(VF_MTA_PUBLISHED_RUN=''))
        self.enterContext(patch.object(connection,'ensure_connection',
            side_effect=AssertionError('Unit fixture must not open any database')))
        self.run=NS(pk=uuid4(),kind='DAILY_CHAIN',status='SUCCEEDED',output_digest='a'*64)
        self.layers={name:{'status':'READY','receipt':{'row_count':3,'rows_digest':'r'*64}}
            for name in daily_preparation.REQUIRED_LAYERS}
        self.publication=NS(run_id=self.run.pk,output_digest=self.run.output_digest,
            source_digest='b'*64,configuration_digest='c'*64,
            recipe_digest='229b0219c8fa70cb4c9e503345d1450e233d4b555c06fe5331bbdf8354d4c870',
            layers=self.layers,status='READY')
        self.publication.seal_digest=daily.seal_identity(self.publication)
        self.enterContext(patch.object(daily,'source_identity',return_value='b'*64))
        self.enterContext(patch.object(daily,'configuration_identity',return_value='c'*64))
        self.enterContext(patch.object(daily_preparation,'required_layers',return_value=tuple(self.layers)))
        query=self.enterContext(patch.object(daily.DailyUiPublication.objects,'filter'))
        query.return_value.first.return_value=self.publication

    def test_ready_publication_keeps_original_recipe_all20_receipts_and_seal(self):
        before=deepcopy(self.publication.__dict__)
        with patch.object(daily,'recipe_identity',return_value='e'*64), \
                patch.object(daily_preparation,'verify_layer',return_value={}) as verify, \
                patch.object(daily_preparation,'prepare_layer',side_effect=AssertionError('No builder replay')):
            self.assertIs(daily.require_ready(self.run,verify_rows=True),self.publication)
            self.assertEqual(verify.call_count,len(self.layers))
        self.assertEqual(self.publication.__dict__,before)

    def test_changed_stored_recipe_or_layer_content_without_original_seal_is_denied(self):
        for change in ('recipe','rows','roster'):
            original=deepcopy(self.publication.__dict__)
            if change=='recipe':self.publication.recipe_digest='e'*64
            elif change=='rows':self.publication.layers['btr']['receipt']['row_count']=4
            else:self.publication.layers['unknown']={'status':'READY'}
            with self.subTest(change=change),self.assertRaises(PublicationUnavailable):
                daily.require_ready(self.run)
            self.publication.__dict__.clear();self.publication.__dict__.update(original)

    def test_row_verification_failure_is_still_unavailable(self):
        with patch.object(daily_preparation,'verify_layer',side_effect=PublicationUnavailable('typed row mismatch')):
            with self.assertRaisesRegex(PublicationUnavailable,'typed row mismatch'):
                daily.require_ready(self.run,verify_rows=True)

    def test_unknown_producer_is_not_accepted_even_with_a_self_consistent_seal(self):
        self.publication.recipe_digest='f'*64
        self.publication.seal_digest=daily.seal_identity(self.publication)
        with self.assertRaises(PublicationUnavailable):daily.require_ready(self.run)

    def test_explicit_prepare_reuses_ready_data_after_coordinator_only_change(self):
        before=deepcopy(self.publication.__dict__)
        cursor=Mock();cursor.fetchone.return_value=(True,)
        context=Mock();context.__enter__=Mock(return_value=cursor);context.__exit__=Mock(return_value=False)
        with patch.object(connection,'cursor',return_value=context), \
                patch.object(daily.transaction,'get_autocommit',return_value=True), \
                patch.object(daily.CalculationRun.objects,'get',return_value=self.run), \
                patch.object(daily.DailyUiPublication.objects,'get_or_create',return_value=(self.publication,False)), \
                patch.object(daily,'recipe_identity',return_value='e'*64), \
                patch.object(daily_preparation,'prepare_layer',side_effect=AssertionError('No builder replay')):
            self.assertIs(daily.prepare(self.run.pk,expected_output_digest=self.run.output_digest),self.publication)
        self.assertEqual(self.publication.__dict__,before)
