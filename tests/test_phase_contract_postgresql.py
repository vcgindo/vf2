"""Old/new phase row, contract and rollback proof in the owned IR3 fixture."""
from copy import deepcopy
import json

from tests.test_phase_state_postgresql import PhaseStatePostgresTests


class PhaseContractPostgresTests(PhaseStatePostgresTests):
    def setUp(self):
        from django.db import connection, transaction
        if connection.settings_dict['NAME'] != 'vftest_fresh_ir3_history1_20261103':
            raise RuntimeError('Phase contract proof requires its exact owned IR3 fixture')
        self.atomic = transaction.atomic()
        self.atomic.__enter__()
        self.addCleanup(self.rollback)

    def test_legacy_bpr_new_dbm_preserves_original_rows_and_complete_continuation(self):
        from tests import phase_state_v1_reference as legacy
        from mta.runtime import phase_state
        from mta.runtime.models import DailyPhaseSnapshot
        from mta.application.native_output_contracts import native_assignments
        from mta.serialization import storage
        from mta.temporal import chain
        from mta.runtime.relational_state import production_projection
        run, bpr, sources = self.owner()
        with native_assignments(True):
            expected = chain.produce_btr(chain.produce_dbm(deepcopy(bpr)))
            old = legacy.save(run, bpr, sources)
            original = DailyPhaseSnapshot.objects.values().get(pk=old.pk)
            restored, captured = phase_state.read(old, **self.references(run))
            new = phase_state.save(run, chain.produce_dbm(restored), captured, parent=old)
            self.assertNotEqual(new.recipe_digest, old.recipe_digest)
            self.assertEqual(DailyPhaseSnapshot.objects.values().get(pk=old.pk), original)
            terminal, captured = phase_state.read(new, **self.references(run))
            actual = chain.produce_btr_from_snapshot(terminal, captured,
                pick_source_digests=new.manifest['metadata']['pick_source_digests'])
            self.assertEqual(storage(production_projection(actual.output)),
                             storage(production_projection(expected)))
            # Old data remains independently readable after creating a v2 child.
            old_phase, old_sources = phase_state.read(old, **self.references(run))
            self.assertEqual(storage(old_phase.control_final), storage(bpr.control_final))
            self.assertEqual(storage(old_sources.__dict__), storage(sources.__dict__))

    def test_sql_contract_agrees_with_python_and_rejects_unknown_semantics(self):
        from django.db import connection
        from mta.runtime import phase_state_contract as contract
        from mta.runtime.phase_image_storage import FORMAT
        old = dict(schema='fresh-native-phase-state-v1')
        new = dict(old, phase_contract=contract.describe(), storage_format=FORMAT)
        cases = [(contract.LEGACY_RECIPE, old, contract.LEGACY_LOGICAL),
                 ('a'*64, new, contract.LEGACY_LOGICAL),
                 ('a'*64, dict(new,storage_format='fresh-phase-image-references-v2'),contract.LEGACY_LOGICAL),
                 ('a'*64, old, None), (contract.LEGACY_RECIPE, new, None),
                 ('a'*64, dict(new, storage_format='unqualified'), None),
                 ('a'*64, dict(new, phase_contract=dict(schema=contract.SCHEMA, digest='b'*64)), None)]
        path='phase/BPR/controls/suggestions_log'
        inherited=dict(new,phase='BPR',metadata={'identity':'child'},images={path:dict(
            image='phase/PRE_BPR/controls/suggestions_log',
            storage_format='inherited-control-history-v1',run_id='child')})
        old_inherited=dict(inherited);old_inherited.pop('phase_contract');old_inherited.pop('storage_format')
        cases += [('a'*64,inherited,contract.LEGACY_LOGICAL),
                  ('a'*64,dict(inherited,storage_format='fresh-phase-image-references-v2'),None),
                  (contract.LEGACY_RECIPE,old_inherited,None),
                  ('a'*64,dict(inherited,images={'phase/BPR/dbm/SuggestionsLog':inherited['images'][path]}),None),
                  ('a'*64,dict(inherited,metadata={'identity':'another-child'}),None)]
        with connection.cursor() as cursor:
            for recipe, manifest, expected in cases:
                cursor.execute('SELECT mta.phase_logical_contract(%s,%s::jsonb)',
                               [recipe, json.dumps(manifest)])
                self.assertEqual(cursor.fetchone(), (expected,))

    def test_new_writer_bad_contract_rolls_back_images_before_same_connection_retry(self):
        from django.db import transaction, DatabaseError, connection
        from unittest.mock import patch
        from mta.runtime import phase_state
        from mta.runtime.models import DailyPhaseSnapshot
        run, bpr, sources = self.owner()
        encode = phase_state.encode
        def wrong(*args, **kwargs):
            result = encode(*args, **kwargs)
            result['phase_contract']['digest'] = 'e'*64
            return result
        with self.assertRaises(DatabaseError), patch.object(phase_state, 'encode', side_effect=wrong):
            phase_state.save(run, bpr, sources)
        self.assertFalse(DailyPhaseSnapshot.objects.filter(run=run).exists())
        self.assertFalse(connection.needs_rollback)
        accepted = phase_state.save(run, bpr, sources)
        self.assertEqual(DailyPhaseSnapshot.objects.filter(run=run).count(), 1)
        phase_state.read(accepted, **self.references(run))
