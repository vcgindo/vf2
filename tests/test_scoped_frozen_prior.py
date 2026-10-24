"""Native scope restoration keeps the parent's exact action/input boundary."""
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class FrozenPriorTests(unittest.TestCase):
    def setUp(self):
        self.parent=SimpleNamespace(pk='parent',output_digest='output-root')
        self.run=SimpleNamespace(predecessor=self.parent,business_date=date(2037,4,11))
        self.state=dict(importer_settings=[dict(Parameter='UpdatePWh_RLT_RCP_GCP',Value='0')],
                        orders={'duplicates':[1,1]},dbm={'Norm':None})
        self.raw=dict(opening=None,initialization_binding={'id':'owned'},
            lineage=dict(run_id='parent',output_digest='output-root',commands=[]),
            mdm_input={'nms_active':True},day={'control_requests':{}})

    def restore(self):
        from mta.runtime.scoped_final import frozen_prior
        return frozen_prior(self.run,self.raw)

    def test_native_successor_uses_verified_parent_then_exact_frozen_overlay(self):
        from mta.runtime.services import read_outputs
        def commands(parent,state,*,through_date):
            self.assertIs(parent,self.parent)
            self.assertEqual(through_date,self.run.business_date)
            return state,[]
        with patch('mta.runtime.services.read_outputs',return_value={'ClosingState':[self.state]}) as read, \
                patch('mta.runtime.temporal.command_states',side_effect=commands), \
                patch('mta.mdm.integration_source.replace_working_inputs') as overlay:
            result=self.restore()
        read.assert_called_once_with(self.parent,include_reports=False)
        self.assertEqual(result,{**self.state,'importer_settings':[
            dict(Parameter='UpdatePWh_RLT_RCP_GCP',Value='1')]})
        self.assertEqual(self.state['importer_settings'][0]['Value'],'0')
        overlay.assert_called_once()
        self.assertEqual(overlay.call_args.args[0],self.raw['mdm_input'])
        self.assertIs(overlay.call_args.args[3],self.parent)

    def test_changed_parent_output_or_action_set_is_denied_before_overlay(self):
        for field,value in (('output_digest','foreign'),('commands',[{'id':'new'}])):
            with self.subTest(field=field):
                self.setUp();self.raw['lineage'][field]=value
                with patch('mta.runtime.services.read_outputs',return_value={'ClosingState':[self.state]}), \
                        patch('mta.runtime.temporal.command_states',return_value=(deepcopy(self.state),[])), \
                        patch('mta.mdm.integration_source.replace_working_inputs') as overlay:
                    with self.assertRaisesRegex(ValueError,'action revision differs'):
                        self.restore()
                overlay.assert_not_called()

    def test_foreign_parent_or_embedded_successor_opening_is_denied(self):
        for change in ('parent','opening'):
            with self.subTest(change=change):
                self.setUp()
                if change=='parent':self.raw['lineage']['run_id']='foreign'
                else:self.raw['opening']={'state':self.state}
                with self.assertRaisesRegex(ValueError,'predecessor opening differs'):
                    self.restore()

    def test_native_root_restores_frozen_refresh_without_changing_input(self):
        self.run.predecessor=None
        self.raw['opening']={'state':deepcopy(self.state)}
        original=deepcopy(self.raw)
        with patch('mta.mdm.integration_source.replace_working_inputs') as overlay:
            result=self.restore()
        self.assertEqual(result['importer_settings'][0]['Value'],'1')
        self.assertEqual(self.raw,original)
        self.assertIsNone(overlay.call_args.args[3])

    def test_supplied_component_embedded_opening_stays_independent(self):
        self.raw['initialization_binding']=None
        self.raw['opening']={'state':deepcopy(self.state)}
        with patch('mta.runtime.services.read_outputs',side_effect=AssertionError('parent read')):
            result=self.restore()
        self.assertEqual(result,self.state)
        result['orders']['duplicates'].append(2)
        self.assertEqual(self.raw['opening']['state'],self.state)
