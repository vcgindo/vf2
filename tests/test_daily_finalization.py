"""Focused real final-writer adapters; no complete business-day invocation."""
from copy import deepcopy
import unittest

from mta.application import daily_finalization as final


class DailyFinalizationTests(unittest.TestCase):
    def test_active_completion_metadata_cannot_select_an_inactive_or_missing_writer(self):
        from mta.serialization import digest
        profile=dict(complete_daily=dict(policy=final.ACTIVE_POLICY,consumption_days=43,remark_days=13))
        complete=dict(ScriptExecutedFlag=deepcopy(final.FLAG_SEED))
        cohort=dict(policy=final.ACTIVE_POLICY,business_date='2037-04-10',configuration_digest=digest(profile),
            qualification=final.qualification(final.ACTIVE_POLICY),flag_digest=digest(complete['ScriptExecutedFlag']))
        output=dict(ClosingState=[dict(complete=complete)],Lineage=[dict(cohort1=cohort)])
        final.verify_finalization_identity(output,profile,'2037-04-10')
        for change in ('missing','policy','date','configuration','flags'):
            bad=deepcopy(output)
            if change=='missing':bad['Lineage'][0].pop('cohort1')
            elif change=='policy':bad['Lineage'][0]['cohort1']['policy']=final.POLICY
            elif change=='date':bad['Lineage'][0]['cohort1']['business_date']='2037-04-09'
            elif change=='configuration':bad['Lineage'][0]['cohort1']['configuration_digest']='0'*64
            else:bad['ClosingState'][0]['complete']['ScriptExecutedFlag'][0]['IsScriptExecuted']=True
            with self.assertRaisesRegex(ValueError,'identity differs'):
                final.verify_finalization_identity(bad,profile,'2037-04-10')

    def test_transactional_writer_rejects_drifted_active_cohort_before_consuming(self):
        import os
        from contextlib import nullcontext
        from datetime import date
        from types import SimpleNamespace
        from unittest.mock import MagicMock,patch
        os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
        os.environ.setdefault('VF_SECRET_KEY','finalization-gate-unit-only')
        import django
        django.setup()
        from mta.runtime.services import finish_run
        from mta.serialization import digest
        profile=dict(complete_daily=dict(policy=final.ACTIVE_POLICY,consumption_days=43,remark_days=13))
        run=SimpleNamespace(pk='run',status='RUNNING',kind='DAILY_CHAIN',checkpoints=MagicMock(),
            input_payload={},input_digest=digest(dict(profile=profile)),business_date=date(2037,4,10))
        run.checkpoints.exists.return_value=False
        output=dict(ClosingState=[dict(complete=dict(ScriptExecutedFlag=deepcopy(final.FLAG_SEED)))],
            Lineage=[dict(cohort1=dict(policy=final.POLICY))])
        with patch('mta.runtime.services.transaction.atomic',return_value=nullcontext()), \
                patch('mta.runtime.services.CalculationRun.objects') as runs, \
                patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects') as captures, \
                patch('mta.runtime.services.read_input',return_value=dict(profile=profile)), \
                patch('mta.mdm.daily_input.finalize_consumption') as consume, \
                patch('mta.mdm.daily_current.publish') as current:
            runs.select_for_update.return_value.get.return_value=run
            captures.filter.return_value.values_list.return_value.first.return_value=None
            with self.assertRaisesRegex(ValueError,'identity differs'):
                finish_run(run,output,expected_digest=run.input_digest)
            consume.assert_not_called();current.assert_not_called()
            self.assertEqual(run.status,'RUNNING')

    def test_active_policy_requires_all_native_flags_and_never_uses_inactive_waiver(self):
        complete = {'ScriptExecutedFlag': deepcopy(final.FLAG_SEED)}
        for row in complete['ScriptExecutedFlag']:
            row['IsScriptExecuted'] = True
        settings = [dict(Parameter='NMSActive', Value='1'),
            dict(Parameter='BatchFileExecutionDate', Value='2026-06-06'),
            dict(Parameter='IsBPRBatchFileExecuted', Value='1'),
            dict(Parameter='IsBatchFileExecuted', Value='0')]
        with self.assertRaisesRegex(ValueError, 'NMSActive=0'):
            final.finish(deepcopy(complete), settings, '2026-06-06')
        result = final.finish(deepcopy(complete), settings, '2026-06-06', policy=final.ACTIVE_POLICY)
        self.assertEqual(next(r['Value'] for r in result if r['Parameter'] == 'IsBatchFileExecuted'), '1')
        for script in ('NMSImportData.sql', 'NMSClearInputTables.sql', 'GenerateBPR.sql'):
            missing = deepcopy(complete)
            next(r for r in missing['ScriptExecutedFlag'] if r['ScriptName'] == script)['IsScriptExecuted'] = False
            with self.subTest(script=script), self.assertRaisesRegex(ValueError, 'completion failed'):
                final.finish(missing, settings, '2026-06-06', policy=final.ACTIVE_POLICY)

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
