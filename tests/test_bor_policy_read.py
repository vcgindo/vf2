"""BOR policy reads still reject absent or unapproved contracts."""
from copy import deepcopy
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import patch

from mta.application.production_output_policy import SOURCE_SCHEMA, contract
from mta.presentation.bor_sources import _production_policy
from mta.presentation.context import PublicationUnavailable
from mta.runtime.input_v3 import V3


class BorPolicyReadTests(TestCase):
    def test_selective_v3_read_keeps_exact_policy_validation(self):
        physical = NS(input_payload={'schema': V3})
        valid = {'production_report_schema': SOURCE_SCHEMA,
                 'production_report_policy': {'output_contract': contract()}}
        invalid = [None, {}, valid | {'production_report_schema': 'wrong'},
                   valid | {'production_report_policy': None},
                   valid | {'production_report_policy': {'output_contract': {}}}]
        with patch('mta.runtime.input_reader.read_input', return_value={'day': valid}) as read:
            self.assertEqual(_production_policy(physical), contract())
            self.assertEqual(read.call_args.kwargs['components'],
                ('input/day/production_report_schema', 'input/day/production_report_policy'))
            for day in invalid:
                read.return_value = {'day': deepcopy(day)}
                with self.assertRaisesRegex(PublicationUnavailable, 'output_contract_required'):
                    _production_policy(physical)

    def test_captured_input_must_pass_original_origin_verifier(self):
        from mta.runtime.captured_input import FINAL
        run = NS(input_payload={'schema': FINAL})
        with patch('mta.runtime.captured_input.origin', side_effect=ValueError('bad ancestry')), \
                patch('mta.runtime.input_reader.read_input') as read:
            with self.assertRaisesRegex(ValueError, 'bad ancestry'):
                _production_policy(run)
            read.assert_not_called()
