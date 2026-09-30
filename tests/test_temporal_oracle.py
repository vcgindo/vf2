"""Oracle comparison coverage tests; these stubs are not parity fixtures."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from parity.replay_temporal import compare_day, validate_continuation_sources
from parity.temporal import BOUNDARIES
from parity.temporal_contract import CONTRACT, validate_state


class OracleCoverageTest(unittest.TestCase):
    def pair(self):
        controls=[dict(stage=name,state=dict(dbm_master=[],importer_master=[],triggers=[]))
                  for name in CONTRACT['control_stages']]
        states={name:{} for name in BOUNDARIES}
        states['controls']={'diagnostics':{}}
        modern=dict(MajorBoundaries=[dict(boundary=n,state=v) for n,v in states.items()],
                    CalculationOutputs=[dict(capability=n,rows=[]) for n in CONTRACT['calculation_capabilities']],
                    ControlStages=deepcopy(controls),ClosingState=[{'bpr':{'BPRMaster':[]}}],
                    Reports=[dict(stage=n,tables={}) for n in CONTRACT['report_stages']])
        legacy=dict(output=dict(ControlStages=controls,CalculationCheckpoints={}),
                    bpr_import={'BPRMaster':[]},delivery={'reports':deepcopy(modern['Reports'][:-1])})
        return legacy,modern,states

    def compare(self,legacy,modern,states):
        core={str(i):dict(status='PASS') for i in range(15)}
        with patch('parity.replay_temporal.legacy_states',return_value=states),patch(
                'parity.replay_temporal.compare_calculations',return_value=core):
            return compare_day(legacy,modern)

    def test_all_declared_contracts_are_present(self):
        checks=self.compare(*self.pair())
        self.assertEqual(len(checks),29) #8major +15calculation +5master/control +reports
        self.assertEqual(sum(r['contract'].startswith('master/') for r in checks),5)
        self.assertEqual(checks[-1]['contract'],'emitted-reports')

    def test_an_earlier_trigger_cannot_hide_behind_final_cleared_table(self):
        legacy,modern,states=self.pair()
        index=CONTRACT['control_stages'].index('UpdateForceChangedNorms.sql')
        legacy['output']['ControlStages'][index]['state']['triggers']=[{'SKUCode':'337','WhCode':'AG515802','NewNorm':294,'Reason':1}]
        checks=self.compare(legacy,modern,states)
        self.assertEqual(checks[-1]['contract'],'master/norm_change_export')
        self.assertEqual(checks[-1]['status'],'FAIL')

    def test_emitted_reports_cannot_hide_behind_post_cleanup_boundary(self):
        legacy,modern,states=self.pair()
        modern['Reports'][0]['tables']={'ReportRows':[{'values':['337',294]}]}
        checks=self.compare(legacy,modern,states)
        self.assertEqual(checks[-1]['contract'],'emitted-reports')
        self.assertEqual(checks[-1]['status'],'FAIL')

    def test_duplicate_report_stage_is_not_overwritten(self):
        legacy,modern,states=self.pair()
        modern['Reports'].append(deepcopy(modern['Reports'][0]))
        with self.assertRaisesRegex(ValueError,'roster/multiplicity'):
            self.compare(legacy,modern,states)

    def test_report_rows_remain_typed_bags_with_duplicate_multiplicity(self):
        legacy,modern,states=self.pair()
        legacy['delivery']['reports'][0]['tables']={'Rows':[{'v':1},{'v':2},{'v':1}]}
        modern['Reports'][0]['tables']={'Rows':[{'v':2},{'v':1},{'v':1}]}
        self.assertEqual(self.compare(legacy,modern,states)[-1]['status'],'PASS')
        modern['Reports'][0]['tables']['Rows'].pop()
        self.assertEqual(self.compare(legacy,modern,states)[-1]['status'],'FAIL')

    def test_duplicate_control_stage_is_not_overwritten(self):
        legacy,modern,states=self.pair()
        legacy['output']['ControlStages'].append(deepcopy(legacy['output']['ControlStages'][0]))
        with self.assertRaisesRegex(ValueError,'roster/multiplicity'):
            self.compare(legacy,modern,states)

    def test_comparator_change_invalidates_continuation(self):
        with self.assertRaisesRegex(ValueError,'dependency changed'):
            validate_continuation_sources({'parity/temporal.py':'old'},{'parity/temporal.py':'new'})

    def test_exact_nested_roster_required_even_when_missing_table_is_empty(self):
        state={k:{name:[] for name in tables} for k,tables in CONTRACT['closing_tables'].items()}
        state['importer_settings']=[]
        state['dbm']['VFSettings']=[dict(Parameter=n) for n in CONTRACT['dbm_settings_parameters']]
        for section in ('dbm','controls'):
            state[section]['IntermediateTables']=[dict(table=n,rows=[]) for n in CONTRACT['scratch_tables']]
        validate_state(state)
        del state['dbm']['SuspendHistory']
        with self.assertRaisesRegex(ValueError,'roster differs: dbm'):validate_state(state)
