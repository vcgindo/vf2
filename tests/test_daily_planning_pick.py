import os
import unittest
os.environ.setdefault('VF_SECRET_KEY', 'test-only-not-a-serving-credential')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from mta.presentation.context import PublicationUnavailable
from mta.presentation.daily_planning.pick import verify_bag


class PickOccurrenceTests(unittest.TestCase):
    def test_complete_values_and_duplicate_multiplicity(self):
        row = {'SKUCode': 'x', 'WhCode': 'y', 'PostPipelineInventoryColor': None}
        other = dict(row, PostPipelineInventoryColor='Black')
        verify_bag([row, other, row], [other, row, row])
        for actual in ([row, other], [row, other, other],
                       [dict(row, SKUCode='X'), other, row]):
            with self.assertRaises(PublicationUnavailable):
                verify_bag([row, other, row], actual)

    def test_genuine_empty_population(self):
        verify_bag([], [])
        with self.assertRaises(PublicationUnavailable):
            verify_bag([], [{'PostPipelineInventoryColor': None}])
