"""The optional remark cache capability never widens the baseline profile."""
from copy import deepcopy
from datetime import datetime, timezone
import unittest
from unittest.mock import patch
from mta.runtime import scoped_remark_ownership as capability
from mta.mdm import owned_namespace as owned


class ScopedRemarkCapabilityTests(unittest.TestCase):
    def catalogue(self):
        frozen = capability.migration()
        return dict(objects=[], functions=[dict(name='mta.' + name + '()', body=body,
            security_definer=False, returns='trigger', configuration=['search_path=pg_catalog, mta'])
            for name, body in (('guard_scoped_remark_cache_writer', frozen.GUARD),
                ('stamp_scoped_remark_transaction', frozen.STAMP))])

    def test_optional_exact_capability_and_finite_write_set(self):
        self.assertEqual(capability.application_grants(dict(functions=[])), {})
        grants = capability.application_grants(self.catalogue())
        self.assertEqual(set(grants), {'mta.' + name for name in capability.migration().TARGETS})
        self.assertTrue(all(name not in owned.APPLICATION_GRANTS for name in grants))
        self.assertEqual(grants['mta.fresh_mta_scopeexpediteparentgeneration']['columns'],
            ['metadata', 'digest', 'sealed', 'sealed_at'])
        self.assertTrue(all(set(v['table']) <= {'INSERT', 'UPDATE'} for v in grants.values()))
        self.assertTrue(all('guard_scoped_remark' not in name for name in owned.APPLICATION_FUNCTIONS))

    def test_partial_tampered_definer_and_path_capabilities_deny(self):
        catalogue = self.catalogue()
        for index in range(2):
            for change in (dict(body='changed'), dict(security_definer=True),
                    dict(returns='void'), dict(configuration=None)):
                bad = deepcopy(catalogue); bad['functions'][index].update(change)
                with self.subTest(index=index, change=change), self.assertRaises(ValueError):
                    capability.application_grants(bad)
        with self.assertRaises(ValueError): capability.application_grants(dict(functions=catalogue['functions'][:1]))

    def test_only_explicit_uuid_tables_omit_sequence(self):
        catalogue = self.catalogue()
        for name in capability.UUID_TABLES:
            self.assertEqual(owned.application_sequences(catalogue, name, production=True), [])
            with self.assertRaises(ValueError): owned.application_sequences(catalogue, name)
            bad = deepcopy(catalogue)
            bad['objects'].append(dict(name='unexpected', kind='S', sequence_for=name + '.id'))
            with self.assertRaises(ValueError): owned.application_sequences(bad, name, production=True)
        with self.assertRaises(ValueError):
            owned.application_sequences(catalogue, 'mta.fresh_mta_scopeexpediteparentbase', production=True)

    def test_full_parser_keeps_dictionary_order_username_and_provider_failure_contract(self):
        from django.db import DatabaseError
        from mta.presentation import bpr_remarks
        payload = dict(data=[dict(skucode='SKU', WHCODE='LOC', remark='retained')])
        actor = dict(id='fixture', name='Name')
        with patch.object(bpr_remarks, '_run') as selected, patch.object(bpr_remarks.ancillary_live, 'append', return_value='1') as append:
            self.assertEqual(bpr_remarks.append(payload, actor), '1')
            selected.assert_called_once_with()
            self.assertEqual(append.call_args.args[1], [dict(SKUCode='SKU', WhCode='LOC', Remark='retained', Username='Name')])
            self.assertEqual(append.call_args.kwargs['actor_id'], 'fixture')
            self.assertEqual(append.call_args.kwargs['timestamp'].tzinfo, timezone.utc)
            append.side_effect = DatabaseError('canonical provider failure')
            self.assertEqual(bpr_remarks.append(payload, actor), '')

    def test_invalid_or_out_of_scope_batch_never_appends(self):
        from mta.presentation import bpr_remarks
        with patch.object(bpr_remarks.ancillary_live, 'append') as append:
            self.assertEqual(bpr_remarks.append(dict(data=[dict(SKUCode='A', WhCode='B', unknown='x')]),
                dict(id='fixture', name='Name'), read_binding=object()), '')
            with self.assertRaisesRegex(ValueError, 'scope'):
                bpr_remarks.append(dict(data=[dict(SKUCode='A', WhCode='B')]), dict(id='fixture', name='Name'),
                    read_binding=object(), validate_rows=lambda rows: (_ for _ in ()).throw(ValueError('scope')))
            append.assert_not_called()
