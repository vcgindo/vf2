"""Revision domain and phase/projection custody for the actual current writer."""
from copy import deepcopy
from types import SimpleNamespace as NS
import os,unittest
from unittest.mock import patch
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','local-unit-only')
import django;django.setup()
from mta.runtime import placement_current_master as cuts


class CurrentMasterCutsTests(unittest.TestCase):
    def test_only_coupled_master_configuration_changes_are_owned(self):
        before=[40,132,474,3417,2]
        for n in (0,1,8,500):
            self.assertEqual(cuts.require_delta(before,[40+n,132+n,474,3417,2]),n)
        for after in ([41,132,474,3417,2],[40,133,474,3417,2],
                [41,133,475,3417,2],[41,133,474,3418,2],[41,133,474,3417,3],
                [39,131,474,3417,2],[True,132,474,3417,2],[],None):
            with self.subTest(after=after),self.assertRaises(ValueError):cuts.require_delta(before,after)

    def test_original_pending_phase_and_sealed_projection_are_required(self):
        run=NS(pk='run',mdm_input_capture=NS(source='source'))
        capture=dict(initialization_id='init',source_digest='source-digest')
        cut=dict(schema=cuts.SCHEMA,run_id='run',initialization_id='init',source_digest='source-digest',
            pending_final_id='final',before=[40,132,474,3417,2],after=[48,140,474,3417,2],
            master_increment=8,projection_id='projection',projection_digest='sealed')
        options=dict(parent=NS(master_epoch=40,configuration_epoch=132),final_id='final')
        with patch('mta.mdm.location_transition.verified_receipt',return_value=NS(pk='projection',digest='sealed')):
            original=deepcopy(cut)
            self.assertEqual(cuts.validate(run,capture,cut,**options),8)
            self.assertEqual(cut,original)
            for name in ('run_id','initialization_id','source_digest','pending_final_id',
                         'projection_id','projection_digest','schema','master_increment'):
                invalid=deepcopy(cut);invalid[name]='foreign'
                with self.subTest(name=name),self.assertRaises(ValueError):cuts.validate(run,capture,invalid,**options)
            invalid=deepcopy(cut);invalid['before'][0]=39
            with self.assertRaises(ValueError):cuts.validate(run,capture,invalid,**options)
            with self.assertRaises(ValueError):cuts.validate(run,capture,None,**options)
