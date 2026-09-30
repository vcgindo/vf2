from copy import deepcopy
import json
from pathlib import Path
import unittest

from mta.planning.engine import calculate_current_day
from mta.application.r1_gulfoil_input import prepare_gulfoil_standard_input
from mta.serialization import digest, storage
from parity.verify_gulfoil import typed_adapter_rows


class GulfOilTest(unittest.TestCase):
    def setUp(self):
        self.source=json.loads(Path('mta/fixtures/r1_gulfoil_common_selected.json').read_text())

    def test_file_source_is_not_mutated_and_lineage_is_preserved(self):
        original=deepcopy(self.source)
        output=storage(calculate_current_day(self.source))
        self.assertEqual(self.source,original)
        adapter=output['r1_gulfoil_adapter'][0]
        self.assertEqual(adapter['source'],original)
        self.assertEqual(adapter['source_checksum'],digest(original))
        standard,_=prepare_gulfoil_standard_input(original)
        self.assertEqual(adapter['standard_checksum'],digest(standard))
        self.assertTrue(output['r1_order_route'])

    def test_seeded_feed_is_rejected(self):
        self.source['order_input'] = {'ignored':True}
        self.source['standard_input']['order_input']['feed_rows']=[{'Qty':1}]
        with self.assertRaisesRegex(ValueError,'own daily and PSO feed'):
            calculate_current_day(self.source)

    def test_checksum_failure_is_not_empty_success(self):
        self.source['files'][0]['text']+='x'
        with self.assertRaisesRegex(ValueError,'checksum'):
            calculate_current_day(self.source)

    def test_typed_comparator_rejects_fraction_and_preserves_null(self):
        with self.assertRaisesRegex(ValueError,'Non-INT'):
            typed_adapter_rows('PSOData',[dict(OrderId='A',Qty='1.5')])
        self.assertEqual(typed_adapter_rows('PSOData',[dict(OrderId='A',Qty=None)]),[dict(OrderID='A',Qty=None)])
