"""Frozen SQL/Python capability cases for the existing SuggestionsLog graph."""
from copy import deepcopy
from importlib import import_module
import json
import os
import unittest

from mta.runtime.phase_image_storage import FORMAT
from mta.runtime import phase_state_contract as contract


def cases():
    control = 'phase/DBM/controls/suggestions_log'
    dbm = 'phase/DBM/dbm/SuggestionsLog'
    report = 'phase/DBM/report-facts/norm-change-history/SuggestionsLog'
    item = dict(image=control, table='DBM/SuggestionsLog', run_id='child',
                storage_format='inherited-control-history-v1')
    original = dict(schema='fresh-native-phase-state-v1', phase='DBM',
        metadata={'identity':'child'}, phase_contract=contract.describe(), storage_format=FORMAT,
        images={control:item, dbm:item, report:item}, state={
            'control_final':{'suggestions_log':{'image':control}},
            'final_dbm':{'SuggestionsLog':{'image':dbm}}})
    yield 'qualified_chain', original, True
    for version in ('fresh-phase-image-references-v2', 'fresh-phase-image-references-v3'):
        old = deepcopy(original)
        old['storage_format'] = version
        yield 'old_format_alias_'+version, old, False
        old['images'] = {control:item}
        yield 'old_control_'+version, old, version.endswith('v3')
    for label in ('missing_control','different_control','wrong_table','wrong_run',
                  'missing_dbm','wrong_dbm_pointer','wrong_control_pointer','unknown_stage',
                  'closing_path','wrong_phase','wrong_physical_path','unknown_format'):
        bad = deepcopy(original)
        if label == 'missing_control': del bad['images'][control]
        elif label == 'different_control': bad['images'][control] = dict(item,cut_id='other')
        elif label == 'wrong_table': bad['images'][report] = dict(item,table='DBM/OrderData')
        elif label == 'wrong_run': bad['metadata']['identity'] = 'other'
        elif label == 'missing_dbm': del bad['images'][dbm]
        elif label == 'wrong_dbm_pointer': bad['state']['final_dbm']['SuggestionsLog'] = {'image':control}
        elif label == 'wrong_control_pointer': bad['state']['control_final']['suggestions_log'] = {'image':dbm}
        elif label == 'unknown_stage': bad['images']['phase/DBM/report-facts/unknown/SuggestionsLog'] = item
        elif label == 'closing_path': bad['images']['closing/dbm/SuggestionsLog'] = item
        elif label == 'wrong_phase': bad['phase'] = 'BPR'
        elif label == 'wrong_physical_path': bad['images'][report] = dict(item,image=dbm)
        else: bad['storage_format'] = 'unknown'
        yield label, bad, False


class InheritedProjectionContractTests(unittest.TestCase):
    def test_complete_cases_and_frozen_migration_stage_roster(self):
        from mta.runtime.relational_state import REPORT_STAGES
        migration = import_module('mta.runtime.migrations.0279_inherited_history_phase_projection')
        self.assertEqual(set(migration.REPORT_STAGES), REPORT_STAGES)
        for label, manifest, accepted in cases():
            with self.subTest(label=label):
                if accepted:
                    self.assertEqual(contract.effective('a'*64,manifest),contract.LEGACY_LOGICAL)
                else:
                    with self.assertRaises(ValueError):contract.effective('a'*64,manifest)

    @unittest.skipUnless(os.environ.get('VF_IR3_PROJECTION_PG') == '1', 'Explicit existing migrated IR3 DB required')
    def test_actual_migration_and_sql_contract_rollback(self):
        from django.db import connection, transaction
        from django.db.migrations.executor import MigrationExecutor
        self.assertEqual(connection.settings_dict['NAME'],'vftest_fresh_ir3_actiontiming_20261104')
        def definition():
            with connection.cursor() as cursor:
                cursor.execute("SELECT oid,pg_get_functiondef(oid),proacl::text FROM pg_proc "
                    "WHERE oid='mta.phase_logical_contract(text,jsonb)'::regprocedure")
                return cursor.fetchone()
        before = definition()
        with transaction.atomic():
            executor = MigrationExecutor(connection)
            target = [('fresh_mta','0279_inherited_history_phase_projection')]
            plan = executor.migration_plan(target)
            self.assertEqual([(m.name,backwards) for m,backwards in plan],
                             [('0279_inherited_history_phase_projection',False)])
            executor.migrate(target)
            after = definition()
            self.assertEqual((before[0],before[2]),(after[0],after[2]))
            with connection.cursor() as cursor:
                for label, manifest, accepted in cases():
                    cursor.execute('SELECT mta.phase_logical_contract(%s,%s::jsonb)',
                                   ['a'*64,json.dumps(manifest)])
                    self.assertEqual(cursor.fetchone(),
                        (contract.LEGACY_LOGICAL if accepted else None,),label)
            transaction.set_rollback(True)
        self.assertEqual(definition(),before)
        self.assertNotIn(('fresh_mta','0279_inherited_history_phase_projection'),
                         MigrationExecutor(connection).loader.applied_migrations)
