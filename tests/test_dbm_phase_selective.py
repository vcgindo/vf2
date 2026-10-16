"""The post-action full DBM read includes the existing typed phase owner."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from mta.presentation.selective import image_metadata, image_rows
from mta.presentation.context import PublicationUnavailable
from mta.runtime.dbm_phase_storage import TABLE


class PhaseSelectiveTest(unittest.TestCase):
    path = 'closing/dbm/PhaseOutRecommendation'

    def run_value(self, **changes):
        item = dict(image=self.path, table=TABLE, count=1,
                    digest='retained', fields=[['SKUCode', 'SKUCode', 'str']])
        item.update(changes)
        return SimpleNamespace(kind='DAILY_CHAIN', production_manifest={
            'images': {self.path: item}}), item

    def test_existing_phase_owner_resolves_without_empty_default(self):
        for rows in ([], [{'SKUCode': '337'}, {'SKUCode': '337'}]):
            run, item = self.run_value(count=len(rows))
            with patch('mta.presentation.qualified_consumption.empty_metadata', return_value=None), \
                 patch('mta.presentation.daily_preparation.production_branch', return_value=True), \
                 patch('mta.presentation.selective.load_image', return_value=rows) as load:
                self.assertIs(image_metadata(run, self.path), item)
                self.assertIs(image_rows(run, self.path), rows)
                load.assert_called_once_with(run, item)

    def test_missing_wrong_owner_image_and_column_still_rejected(self):
        for change in ({'table': 'DBM/DBMMaster'}, {'image': 'other'},
                       {'fields': [['SKUCode', 'unregistered', 'str']]}):
            run, _ = self.run_value(**change)
            with patch('mta.presentation.qualified_consumption.empty_metadata', return_value=None), \
                 patch('mta.presentation.daily_preparation.production_branch', return_value=True):
                with self.assertRaises(PublicationUnavailable):
                    image_metadata(run, self.path)
        run, _ = self.run_value()
        run.production_manifest['images'].clear()
        with patch('mta.presentation.qualified_consumption.empty_metadata', return_value=None), \
             patch('mta.presentation.daily_preparation.production_branch', return_value=True):
            with self.assertRaises(PublicationUnavailable):
                image_metadata(run, self.path)

    def test_typed_checksum_failure_propagates(self):
        run, _ = self.run_value()
        with patch('mta.presentation.qualified_consumption.empty_metadata', return_value=None), \
             patch('mta.presentation.daily_preparation.production_branch', return_value=True), \
             patch('mta.presentation.selective.load_image', side_effect=ValueError('Operational image drift')):
            with self.assertRaisesRegex(ValueError, 'Operational image drift'):
                image_rows(run, self.path)
