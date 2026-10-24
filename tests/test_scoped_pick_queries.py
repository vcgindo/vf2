"""Canonical band wire and target bigint boundaries; no business output seed."""
import os
import unittest
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()
from mta.presentation import scoped_pick_queries as subject
from mta.presentation.context import PublicationUnavailable
from mta.runtime.models import CalculationRun


class ScopedPickBandContractTests(unittest.TestCase):
    def row(self):
        return dict(sku_code='SKU',location_code='WH',parent_location_code='PARENT',
            to_black='0',to_red='-1',to_yellow='2',to_green='3',to_blue='4')

    def test_exact_codes_canonical_signed_integer_and_bigint_endpoints(self):
        row=self.row();row.update(to_black=str(-(2**63)),to_blue=str(2**63-1))
        subject.validate_band_rows(CalculationRun(),[row,dict(row)])

    def test_invalid_shape_code_wire_or_bigint_is_not_normalized(self):
        for changes in (dict(sku_code=None),dict(location_code=''),dict(parent_location_code='x'*51),
                dict(to_red='01'),dict(to_red='-0'),dict(to_red=1),dict(to_red='1.0'),
                dict(to_red=str(2**63)),dict(to_red=str(-(2**63)-1)),dict(extra='unowned')):
            with self.subTest(changes=changes),self.assertRaises(PublicationUnavailable):
                subject.validate_band_rows(CalculationRun(),[dict(self.row(),**changes)])
