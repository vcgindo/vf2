from copy import deepcopy
from datetime import datetime
import unittest

from mta.domain.complete_daily_completion import (
    clear_failed_bpr_reports, mark_script_executed, prune_bpr_history,
    reset_batch_flags, sanitation_failure_count, validate_batch_flags,
)


NOW = datetime(2026, 6, 6)
EQUAL = lambda a, b: a == b


class CompletionTests(unittest.TestCase):
    def settings(self, timestamp=NOW.isoformat()):
        return [{'Parameter': key, 'Value': value} for key, value in (
            ('BatchFileExecutionDate', timestamp), ('IsBPRBatchFileExecuted', '0'),
            ('IsBatchFileExecuted', '0'))]

    def flag(self, name='work.sql', executed=0, critical=1, module='BPR'):
        return dict(ScriptName=name, IsScriptExecuted=executed,
                    IsScriptCritical=critical, ModuleName=module)

    def validate(self, flags, settings=None, kind='BPR'):
        return validate_batch_flags(flags, self.settings() if settings is None else settings,
            NOW, kind=kind, equal=EQUAL, parse_datetime=datetime.fromisoformat)

    def test_missing_critical_writer_fails_until_actual_mark(self):
        flags = [self.flag()]
        self.assertEqual(self.validate(flags)['ImporterSettingsTbl'][1]['Value'], '0')
        marked = mark_script_executed(flags, 'work.sql', equal=EQUAL)
        self.assertEqual(self.validate(marked)['ImporterSettingsTbl'][1]['Value'], '1')
        self.assertEqual(flags[0]['IsScriptExecuted'], 0)

    def test_final_marks_self_before_checking_critical_roster(self):
        flags = [self.flag('ValidateBatchExecutionFlags.sql', module='Importer')]
        result = self.validate(flags, kind='ALL')
        self.assertEqual(result['ImporterSettingsTbl'][2]['Value'], '1')

    def test_native_bpr_marker_spelling_is_not_repaired(self):
        flags = [self.flag('ValidateBPRBatchExecutionFlags.sql')]
        result = self.validate(flags)
        self.assertEqual(result['ScriptExecutedFlag'], flags)
        self.assertEqual(result['ImporterSettingsTbl'][1]['Value'], '0')

    def test_stale_date_optional_and_null_flags(self):
        flags = [self.flag(executed=None), self.flag(critical=0), self.flag(module='Importer')]
        self.assertEqual(self.validate(flags)['ImporterSettingsTbl'][1]['Value'], '1')
        stale = self.validate([], self.settings('2026-06-05T00:00:00'))
        self.assertEqual(stale['ImporterSettingsTbl'][1]['Value'], '0')

    def test_missing_setting_not_inserted_and_duplicate_mark_preserved(self):
        flags = [self.flag(), self.flag()]
        self.assertEqual(len(mark_script_executed(flags, 'work.sql', equal=EQUAL)), 2)
        self.assertEqual(self.validate([], [])['ImporterSettingsTbl'], [])

    def test_reset_all_flags_and_native_date_format_adapter(self):
        flags = [self.flag('ResetBatchExecutionFlag.sql', 1), self.flag(executed=1)]
        result = reset_batch_flags(flags, self.settings(), NOW, equal=EQUAL,
                                   format_datetime=lambda value: 'native-date-text')
        self.assertEqual([r['IsScriptExecuted'] for r in result['ScriptExecutedFlag']], [True, False])
        self.assertEqual(result['ImporterSettingsTbl'][0]['Value'], 'native-date-text')

    def test_four_failure_tables_only(self):
        data = {name: [{'value': 1}] for name in (
            'BPR_Table', 'SupplierDispatchReq', 'vf_PickListReport', 'vf_RationedReqReport', 'Unrelated')}
        result = clear_failed_bpr_reports(data)
        self.assertEqual(result['Unrelated'], data['Unrelated'])
        self.assertTrue(all(not value for key, value in result.items() if key != 'Unrelated'))
        with self.assertRaises(ValueError):
            clear_failed_bpr_reports({})

    def test_sanitation_nulls_duplicate_rows_and_no_double_count(self):
        rows = [{'Critical_Flag': 'Partial', 'Non_Critical_Flag': 'False'}]*2
        rows += [{'Critical_Flag': None, 'Non_Critical_Flag': 'True'}]
        self.assertEqual(sanitation_failure_count(rows, equal=EQUAL), 2)
        self.assertEqual(sanitation_failure_count([], equal=EQUAL), 0)

    def test_retention_midnight_null_and_duplicates(self):
        data = {'DailyConsumption': [{'ReportDate': '2026-03-08'}, {'ReportDate': '2026-03-09'}]}
        for table, field in (('BPRReport_RemarkDetails', 'RemarkDate'),
                             ('OpenExpeditRequestRemarksHistory', 'RemarkDate'),
                             ('InTransitWhereAboutsRemarks', 'RemarksDate')):
            data[table] = [{field: '2026-03-08T00:00:00'}, {field: '2026-03-08T00:00:00.003'},
                           {field: None}, {field: None}]
        original = deepcopy(data)
        result = prune_bpr_history(data, [{'LastRunDate': NOW}], consumption_days=90, remark_days=90)
        self.assertEqual(result['DailyConsumption'], [{'ReportDate': '2026-03-09'}])
        self.assertEqual(len(result['BPRReport_RemarkDetails']), 3)
        self.assertEqual(data, original)
        self.assertEqual(prune_bpr_history(data, [], consumption_days=90, remark_days=90), data)
        with self.assertRaises(ValueError):
            prune_bpr_history(data, [{'LastRunDate': NOW}]*2, consumption_days=90, remark_days=90)
        with self.assertRaises(ValueError):
            prune_bpr_history({}, [], consumption_days=90, remark_days=90)


if __name__ == '__main__':
    unittest.main()
