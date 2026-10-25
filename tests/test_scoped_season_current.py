"""Seasonality reads the accepted current owner without inventing a Full day."""
import os
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','scoped-season-unit-only')
import django;django.setup()
from mta.mdm import season_current as reader
from mta.presentation import scoped_selection,scoped_dbm
from mta.presentation.context import PublicationUnavailable

class ScopedSeasonTests(TestCase):
    def setUp(self):
        self.source=NS(pk=7)
        self.run=NS(pk='current',mdm_input_capture=NS(source_id=7))
        self.sources=NS(acceptance_id='bpr',acceptance_digest='digest',action_revision=6,
            rows=lambda path:[dict(LastRunDate='2026-10-24')])
        self.view=NS(run=self.run,run_id='current',bpr=NS(sources=self.sources))
        self.enabled=patch.object(scoped_selection,'enabled',return_value=True);self.enabled.start();self.addCleanup(self.enabled.stop)
        self.selected=patch.object(scoped_selection,'selected',return_value=self.view);self.selected.start();self.addCleanup(self.selected.stop)
    def test_current_family_owner_and_source_must_match_selected_phase(self):
        with patch('mta.mdm.season_source.require_installed',return_value=NS(last_run_id='current')):
            self.assertIs(reader.publication(self.source),self.run)
        for previous in (None,'predecessor'):
            with patch('mta.mdm.season_source.require_installed',return_value=NS(last_run_id=previous)),self.assertRaises(PublicationUnavailable):
                reader.publication(self.source)
        self.run.mdm_input_capture.source_id=8
        with self.assertRaises(PublicationUnavailable):reader._phase(self.source)
    def test_master_duplicates_nulls_and_action_revision_are_retained(self):
        rows=[dict(SKUCode='A',WhCode='X',Norm=None),dict(SKUCode='A',WhCode='X',Norm=None)]
        with patch.object(scoped_dbm,'bind',return_value=NS(dbm={'DBMMaster':rows})) as bind:
            self.assertIs(reader.consumer_rows(self.source,self.run,'closing/dbm/DBMMaster',single_pass=True),rows)
            bind.assert_called_once_with('bpr',expected_digest='digest',action_revision=6)
        with self.assertRaises(PublicationUnavailable):reader.consumer_rows(self.source,NS(pk='other'),'closing/dbm/DBMMaster')
    def test_histories_are_exact_opening_rows_but_marker_is_current(self):
        rows=[dict(ReportDate='2026-10-23')]
        with patch.object(scoped_dbm,'_opening_rows',return_value=rows) as opening:
            self.assertIs(reader.consumer_rows(self.source,self.run,'closing/dbm/DailyConsumption'),rows)
            opening.assert_called_once_with(self.sources,'DailyConsumption')
        self.assertEqual(reader.consumer_rows(self.source,self.run,'closing/dbm/LastBatchRunTbl'),[dict(LastRunDate='2026-10-24')])
        with self.assertRaises(PublicationUnavailable):reader.consumer_rows(self.source,self.run,'closing/dbm/Invented')
    def test_valid_empty_current_family_returns_empty_list_and_count(self):
        with patch.object(reader,'publication',return_value=self.run),patch.object(reader,'live_rows',return_value=[]):
            payload=dict(id=10,product_permissions=[1],location_permissions=[1],fields=[dict(key='sc')])
            self.assertEqual(reader.read(self.source,payload),[])
            self.assertEqual(reader.read(self.source,payload,count=True),'0')
    def test_full_selection_and_original_image_reader_remain_default(self):
        with patch.object(scoped_selection,'enabled',return_value=False),patch('mta.mdm.season_source.require_installed',return_value=NS(last_run_id='current')),patch.object(reader,'selected_run',return_value=self.run):
            self.assertIs(reader.publication(self.source),self.run)
            with patch.object(reader,'image_rows',return_value=['original']) as original:
                self.assertEqual(reader.consumer_rows(self.source,self.run,'closing/dbm/ReasonCodes'),['original'])
                original.assert_called_once_with(self.run,'closing/dbm/ReasonCodes')
