"""Native wrapper contract; underlying full engine is always mocked."""
from datetime import date
from decimal import Decimal
import unittest
from unittest.mock import patch
from mta.temporal.chain import calculate_day


class TemporalMemoryTest(unittest.TestCase):
    def test_native_wrapper_keeps_business_values_without_diagnostic_normalization(self):
        row={'quantity':Decimal('1.2500'),'null':None,'day':date(2026,6,17)}
        output={'ClosingState':[row,row],'Reports':[]}
        with patch('mta.temporal.chain._calculate_day_native',return_value=output), \
                patch('mta.temporal.chain.json_value',side_effect=AssertionError('diagnostic normalization')):
            actual=calculate_day(None,None,None,None,None,None,None)
        self.assertIs(actual,output)
        self.assertIs(actual['ClosingState'][0],row)
        self.assertIs(actual['ClosingState'][1],row)
        self.assertEqual(actual['ClosingState'][0]['quantity'],Decimal('1.2500'))

    def test_native_wrapper_preserves_arguments_failure_and_return_ownership(self):
        arguments=({'prior':True},'2026-06-16',{'day':True},{'profile':True},'same-run',object(),None)
        output={'ClosingState':[],'Reports':[]}
        with patch('mta.temporal.chain._calculate_day_native',return_value=output) as producer:
            self.assertIs(calculate_day(*arguments,native_daily=True),output)
        producer.assert_called_once_with(*arguments,native_daily=True)
        with patch('mta.temporal.chain._calculate_day_native',side_effect=ValueError('producer failed')):
            with self.assertRaisesRegex(ValueError,'producer failed'):calculate_day(*arguments)
