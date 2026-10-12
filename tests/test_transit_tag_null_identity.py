"""Canonical NULL equality behavior; no business-day invocation."""
from copy import deepcopy
import unittest

from mta.application.r1_transit_tags import update_transit_tags, validate_tag_input


class TransitTagNullIdentityTests(unittest.TestCase):
    def test_null_target_identities_survive_without_matching_null_sources(self):
        rows = [dict(SKUCode=None, WhCode='PL001', Tags=None),
                dict(SKUCode=None, WhCode='PL001', Tags='retained'),
                dict(SKUCode='S', WhCode=None, Tags='retained'),
                dict(SKUCode=None, WhCode=None, Tags=None)]
        before = deepcopy(rows)
        seasons = [dict(SKUCode=r['SKUCode'], WhCode=r['WhCode'], Status=4) for r in rows]
        phases = [dict(SKUCode=r['SKUCode'], WhCode=r['WhCode'], PhaseInSKUCode='S') for r in rows]
        self.assertEqual(update_transit_tags(rows, seasons, phases), before)
        self.assertEqual(rows, before)

    def test_nonnull_precedence_duplicates_and_statuses_are_unchanged(self):
        rows = [dict(SKUCode='S', WhCode='L', Tags=None)] * 2
        rows += [dict(SKUCode='T', WhCode='L', Tags='old')]
        seasons = [dict(SKUCode='S', WhCode='L', Status=7),
                   dict(SKUCode='T', WhCode='L', Status=21),
                   dict(SKUCode=None, WhCode='L', Status=4)]
        phases = [dict(SKUCode='X', WhCode='L', PhaseInSKUCode='S'),
                  dict(SKUCode='T', WhCode=None, PhaseInSKUCode='T')]
        result = update_transit_tags(rows, seasons, phases)
        self.assertEqual([r['Tags'] for r in result], ['PIPO', 'PIPO', 'old'])
        self.assertEqual([r['Tags'] for r in rows], [None, None, 'old'])

    def test_nonnull_invalid_types_and_shapes_still_fail(self):
        for row in (dict(SKUCode=3, WhCode='L', Tags=None),
                    dict(SKUCode='S', WhCode=' ', Tags=None),
                    dict(SKUCode=None, WhCode='L', Tags=3),
                    dict(SKUCode=None, WhCode='L')):
            with self.subTest(row=row), self.assertRaises(ValueError):
                validate_tag_input([row])
