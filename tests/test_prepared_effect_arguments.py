"""Actual pre-BPR finalizer arguments versus unchanged complete Full producers."""
from copy import deepcopy
import os
import unittest

os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','prepared-effect-argument-unit-only')
import django
django.setup()


class PreparedEffectArgumentsTests(unittest.TestCase):
    def test_all_family_arguments_are_the_same_actual_values_at_full_completion(self):
        from mta.application.native_output_contracts import native_assignments
        from mta.runtime.prepared_effects import writer_output,RAW
        from mta.temporal import chain
        from mta.serialization import storage
        from tests.test_h3_daily_integration import frame,captured,complete_feeds,compose,nms_master_raw,replace_working_inputs
        from tests.production_h3_fixture import supplied_day
        from tests.test_daily_calculation_phases import calculation
        for fmt in ('WithDestLoc','WithoutDestLoc'):
            with self.subTest(format=fmt),native_assignments(True):
                opening=frame(fmt);prior=deepcopy(opening['opening']['state'])
                day=supplied_day('2037-04-10')['day'];frozen=captured(prior,fmt)
                day.update(raw_master=compose(frozen,nms_master_raw(prior),last_run_date='2037-04-09'),
                    exclusions=[],supplier_feeds=complete_feeds(frozen,prior))
                replace_working_inputs(frozen,prior,day,None)
                prepared=chain.prepare_day(prior,'2037-04-09',day,opening['profile'],
                    'effect-arguments-'+fmt,calculation,native_daily=True)
                expected=chain.produce_btr(chain.produce_dbm(chain.produce_bpr(deepcopy(prepared))))['ClosingState'][0]
                actual=writer_output(prepared)['ClosingState'][0]
                self.assertEqual(storage(actual['importer']['ForceNormChange']),storage(expected['importer']['ForceNormChange']))
                self.assertEqual(storage(actual['controls']['upload_log']),storage(expected['controls']['upload_log']))
                for name in ('season_requests','phase_stops','phase_requests','phase_in_requests'):
                    self.assertEqual(storage(actual['control_aux'][name]),storage(expected['control_aux'][name]))
                self.assertEqual(storage(actual['dbm']['Seasonality']),storage(expected['dbm']['Seasonality']))
                self.assertEqual(storage(actual['complete']),storage({name:expected['complete'][name] for name in RAW}))

    def test_importer_cut_has_exact_full_projection_values_and_excludes_later_copies(self):
        from mta.mdm.master_owners import owner_batches,importer_batches
        from mta.serialization import storage
        from tests.test_phase_state import native_prepared
        prepared,_,_=native_prepared()
        opening=prepared.context.prior
        def record(batch):
            family,model,partition,rows,path=batch
            return family,model.__name__,partition,storage(rows),path
        full=[record(batch) for batch in owner_batches(opening) if batch[2].get('owner','Importer') == 'Importer']
        actual=[record(batch) for batch in importer_batches(opening['importer'],opening['consumer_context']['NMSAllItems'])]
        self.assertEqual(actual,full)
        self.assertEqual(len(actual),10)
