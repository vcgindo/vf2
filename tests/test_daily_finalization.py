"""Focused real final-writer adapters; no complete business-day invocation."""
from copy import deepcopy
import unittest

from mta.application import daily_finalization as final


class DailyFinalizationTests(unittest.TestCase):
    def test_configuration_is_explicit_and_default_is_unchanged(self):
        self.assertIsNone(final.configuration({}))
        good = dict(policy=final.POLICY, consumption_days=90, remark_days=90)
        self.assertEqual(final.configuration({'complete_daily': good}), good)
        for bad in ({}, {**good, 'remark_days': True}, {**good, 'extra': 1}):
            with self.assertRaises(ValueError):
                final.configuration({'complete_daily': bad})

    def test_reset_retains_rows_and_rejects_missing_or_nonempty_queue(self):
        prior = dict(complete={name: [] for name in final.REQUIRED},
            importer_settings=[{'Parameter': 'IsBatchFileExecuted', 'Value': '1'},
                {'Parameter': 'IsBPRBatchFileExecuted', 'Value': '1'},
                {'Parameter': 'BatchFileExecutionDate', 'Value': 'old'},
                {'Parameter': 'NMSActive', 'Value': '0'}])
        prior['complete']['ScriptExecutedFlag'] = deepcopy(final.FLAG_SEED)
        before = deepcopy(prior)
        output = final.begin(prior, '2026-06-06')
        self.assertEqual(prior, before)
        self.assertEqual(output['importer_settings'][0]['Value'], '0')
        self.assertTrue(next(row for row in output['complete']['ScriptExecutedFlag']
            if row['ScriptName'] == 'ResetBatchExecutionFlag.sql')['IsScriptExecuted'])
        for name in final.EMPTY_APPROVAL_QUEUES:
            bad = deepcopy(prior)
            del bad['complete'][name]
            with self.assertRaisesRegex(ValueError, 'opening populations'):
                final.begin(bad, '2026-06-06')
            bad['complete'][name] = [{'Approved': False}]
            with self.assertRaisesRegex(ValueError, 'outside the qualified domain'):
                final.begin(bad, '2026-06-06')

    def test_settings_update_preserves_completion_and_duplicate_rows(self):
        original = [{'Parameter': 'NMSActive', 'Value': '0'},
            {'Parameter': 'IsBatchFileExecuted', 'Value': '0'},
            {'Parameter': 'IsBatchFileExecuted', 'Value': '0'}]
        result = final.preserve_settings(original, [{'Parameter': 'NMSActive', 'Value': '1'}])
        self.assertEqual(result, [{'Parameter': 'NMSActive', 'Value': '1'}, *original[1:]])
        self.assertEqual(original[0]['Value'], '0')

    def test_supplier_production_then_retention_without_mutating_inputs(self):
        complete = {name: [] for name in final.REQUIRED}
        complete['BPRReport_RemarkDetails'] = [dict(RemarkDate='2026-03-08'),
            dict(RemarkDate='2026-03-08T00:00:00.003'), dict(RemarkDate=None)]
        arguments = dict(complete=complete,
            source={'sourcing': [dict(sku_code='S', location_code='W', supplier='P')]},
            calculated={'r1_bor': [dict(case='r1_bor_1', sku='S', location='W', supplier='P',
                original_requirement='12', dispatch_requirement='12', to_red='3',
                to_yellow='4', to_green='5', to_blue='0')]},
            bpr_master=[dict(SKUCode='S', WHCode='W', ParentWhCode='P')],
            importer={'SkuLocAttributeData': [dict(SKUCode='S', LocCode='W',
                **{f'c{i}': None for i in range(1, 16)})]},
            plants=[{'PlantCode': 'P'}],
            report=[dict(SKUCode='S', WhCode='W', Norm=10, Stock=None, GIT=0)],
            late={'BPRDailyConsumption': [dict(SKUCode='S', WHCode='P',
                ReportDate='2026-06-06', Stock=4, GIT=1),
                dict(SKUCode='S', WHCode='P', ReportDate='2026-03-08', Stock=99, GIT=0)]},
            today='2026-06-06', config=dict(consumption_days=90, remark_days=90))
        before = deepcopy(arguments)
        output, daily = final.production_and_retention(**arguments)
        self.assertEqual(arguments, before)
        self.assertEqual(len(output['SupplierDispatchReq'][0]), 28)
        self.assertEqual(output['ProdOrderSuggestions'], [dict(SKUCode='S', PlantCode='P',
            Red=0, Yellow=2, Green=5, TotalReq=7, EcoColor='Yellow', ReportDate='2026-06-06')])
        self.assertEqual(daily, arguments['late']['BPRDailyConsumption'][:1])
        self.assertEqual(output['BPRReport_RemarkDetails'], complete['BPRReport_RemarkDetails'][1:])

    def test_no_flags_are_inserted_and_missing_completion_cannot_pass(self):
        complete = {'ScriptExecutedFlag': []}
        final.mark(complete, 'Missing.sql')
        self.assertEqual(complete['ScriptExecutedFlag'], [])
        with self.assertRaisesRegex(ValueError, 'Generic completion failed'):
            final.validate_completion(complete, [], '2026-06-06', kind='BPR')

    def test_qualified_gate_preserves_native_false_and_denies_other_missing_writer(self):
        complete = {'ScriptExecutedFlag': deepcopy(final.FLAG_SEED)}
        for row in complete['ScriptExecutedFlag']:
            row['IsScriptExecuted'] = row['ScriptName'] not in (
                'NMSImportData.sql', 'NMSClearInputTables.sql')
        settings = [dict(Parameter='NMSActive', Value='0'),
            dict(Parameter='BatchFileExecutionDate', Value='2026-06-06'),
            dict(Parameter='IsBPRBatchFileExecuted', Value='1'),
            dict(Parameter='IsBatchFileExecuted', Value='0')]
        self.assertEqual(final.finish(complete, settings, '2026-06-06'), settings)
        altered = deepcopy(complete)
        next(r for r in altered['ScriptExecutedFlag'] if r['ScriptName'] == 'NMSImportData.sql')['IsScriptExecuted'] = True
        with self.assertRaisesRegex(ValueError, 'skipped flags'):
            final.finish(altered, settings, '2026-06-06')
        altered_settings = deepcopy(settings)
        altered_settings[2]['Value'] = '0'
        with self.assertRaisesRegex(ValueError, 'completed BPR'):
            final.finish(deepcopy(complete), altered_settings, '2026-06-06')
        for parameter in ('NMSActive', 'IsBatchFileExecuted'):
            with self.assertRaises(ValueError):
                final.finish(deepcopy(complete), [r for r in settings if r['Parameter'] != parameter], '2026-06-06')
        for bad in ('', 'invalid', '1', None):
            altered = deepcopy(settings)
            altered[0]['Value'] = bad
            with self.assertRaisesRegex(ValueError, 'explicit NMSActive'):
                final.finish(deepcopy(complete), altered, '2026-06-06')
        next(row for row in complete['ScriptExecutedFlag']
             if row['ScriptName'] == 'GenerateBPR.sql')['IsScriptExecuted'] = False
        with self.assertRaisesRegex(ValueError, 'GenerateBPR.sql'):
            final.finish(complete, settings, '2026-06-06')
        with self.assertRaisesRegex(ValueError, 'completion failed'):
            final.finish({'ScriptExecutedFlag': deepcopy(final.FLAG_SEED)}, settings, '2026-06-07')
        complete['ScriptExecutedFlag'].pop()
        with self.assertRaisesRegex(ValueError, 'roster differs'):
            final.finish(complete, settings, '2026-06-06')

    def test_direct_service_supplement_binding_and_opening_drift(self):
        import hashlib, json
        config = dict(policy=final.POLICY, consumption_days=90, remark_days=90)
        value = dict(schema='generic-finalization-input-v1', artifact_sha256='a'*64,
                     configuration=config, opening_complete={'NMSSOB': []})
        raw = json.dumps(value).encode()
        profile = dict(complete_daily=config, complete_daily_config_sha256=hashlib.sha256(raw).hexdigest(),
                       complete_daily_artifact_sha256='a'*64)
        opening = {'state': {'complete': value['opening_complete']}}
        self.assertEqual(final.validate_supplement(raw, profile, opening)['artifact_sha256'], 'a'*64)
        with self.assertRaisesRegex(ValueError, 'bytes required'):
            final.validate_supplement(raw+b' ', profile, opening)
        with self.assertRaisesRegex(ValueError, 'opening differs'):
            final.validate_supplement(raw, profile, {'state': {'complete': {}}})


if __name__ == '__main__':
    unittest.main()
