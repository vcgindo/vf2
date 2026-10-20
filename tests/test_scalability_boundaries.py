"""Non-semantic opening, CSV transport, export and interruption boundaries.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import hashlib
from contextlib import contextmanager, nullcontext
from copy import deepcopy
from datetime import date
from decimal import Decimal
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'scalability-focused-only')
import django
django.setup()

from mta.runtime.opening_scope import (immutable, opening_scope, release_opening,
    certify_opening, require_certified_opening, current_certified_opening)
from mta.application.production_csv import assemble, parse_csv, CsvIntakeError, IssueRows
from mta.application.streamed_input import JsonInputFile
from mta.runtime.production_daily import decode
from mta.runtime import daily_feed, relational_state
from mta.serialization import rows_digest


def owner():
    return SimpleNamespace(pk=17, source_id=3, input_digest='input', input_manifest_digest='manifest',
        receipt_digest='receipt', configuration_digest='configuration', recipe_sha256='recipe',
        implementation_digest='implementation', input_sha256='sha', _state=SimpleNamespace(db='default'))


class ScalabilityBoundaryTests(unittest.TestCase):
    def test_native_root_preparation_preserves_full_wire_and_working_isolation(self):
        from mta.runtime.temporal import prepare_native_opening
        from mta.serialization import storage, digest
        initialized = owner()
        initialized.source = SimpleNamespace(pk=3, digest='source')
        frame = dict(profile={'rule': Decimal('1.20')}, opening=dict(identity='root',
            opening_date='2026-04-07', state={'rows': [dict(code='a', value=None),
                dict(code='a', value=Decimal('2.00'), when=date(2026, 4, 7))]}))
        wire = storage(frame)
        _, (initial, prior, opening_date, lineage) = prepare_native_opening(
            initialized, frame, wire['profile'], deepcopy(frame['opening']), None)
        self.assertEqual(initial, wire['opening'])
        self.assertEqual(prior, wire['opening']['state'])
        self.assertEqual(opening_date, '2026-04-07')
        self.assertEqual(lineage['opening_digest'], digest(wire['opening']))
        prior['rows'][0]['value'] = 7
        self.assertIsNone(initial['state']['rows'][0]['value'])
        self.assertIsNone(frame['opening']['state']['rows'][0]['value'])
        changed = deepcopy(frame['opening'])
        changed['state']['rows'].reverse()
        with self.assertRaisesRegex(ValueError, 'initial opening differs'):
            prepare_native_opening(initialized, frame, wire['profile'], changed, None)

    def test_locked_native_seal_drift_stops_before_consumers_or_capture(self):
        from mta.runtime import temporal
        from mta.mdm import production_families, initialization
        from mta.runtime.models import ProductionInitialization
        initialized = owner()
        initialized.source = SimpleNamespace(pk=3, digest='source')
        changed = deepcopy(initialized)
        changed.receipt_digest = 'another-seal'
        profile = {'delivery': {'site_code': 'test'},
                   'complete_pick': {'policy': 'canonical-tied-order-v1'}}
        frame = dict(profile=profile, opening=dict(identity='root', opening_date='2026-04-07', state={}))
        locked = MagicMock()
        locked.select_related.return_value.get.return_value = changed
        with patch.object(temporal.transaction, 'get_autocommit', return_value=True), \
                patch.object(temporal.transaction, 'atomic', side_effect=lambda: nullcontext()), \
                patch.object(temporal, 'connection'), \
                patch('mta.mdm.supplier_revisions.source_lock', side_effect=lambda key: nullcontext()), \
                patch('mta.application.daily_finalization.configuration', return_value={'policy': 'native'}), \
                patch.object(temporal, 'resolved_pick_root', return_value='pick'), \
                patch.object(production_families, 'prepare_opening', return_value=initialized), \
                patch.object(production_families, 'require_initialization') as admission, \
                patch.object(initialization, 'read_initialized_input', return_value=frame), \
                patch.object(ProductionInitialization.objects, 'select_for_update', return_value=locked), \
                patch('mta.runtime.production_daily.initialize_consumers') as consumers, \
                patch.object(temporal.CalculationRun.objects, 'create') as create:
            with self.assertRaisesRegex(ValueError, 'changed after immutable opening preparation'):
                temporal.execute_day(day={'business_date': '2026-04-08'}, profile=profile,
                    execution_revision='seal-drift-proof', opening=frame['opening'],
                    production_initialization=initialized, mdm_source=initialized.source,
                    daily_input_sha256='a'*64, pick_output_root='pick')
        admission.assert_not_called()
        consumers.assert_not_called()
        create.assert_not_called()

    def test_live_owner_comparison_preserves_nulls_duplicate_count_and_order(self):
        from mta.mdm.production_families import _same_bags
        expected = {'enabled': '1', 'rows': [dict(code='a', qty=None),
            dict(code='a', qty=Decimal('1.00')), dict(code='a', qty=Decimal('1.00'))]}
        def observed(rows):
            return {'enabled': '1', 'rows': (row for row in rows)}
        self.assertTrue(_same_bags(observed(expected['rows']), expected))
        self.assertFalse(_same_bags(observed(expected['rows'][:-1]), expected))
        self.assertFalse(_same_bags(observed(expected['rows'][::-1]), expected))
        changed = deepcopy(expected['rows'])
        changed[0]['qty'] = 0
        self.assertFalse(_same_bags(observed(changed), expected))
        self.assertFalse(_same_bags({'rows': iter(expected['rows'])}, expected))

    def test_combined_family_anchors_hash_actual_unmodified_root_once(self):
        from mta.mdm import integration_source
        from mta.serialization import digest
        prior = {'rows': [{'value': None}, {'value': 0}, {'value': 0}]}
        before = deepcopy(prior)
        captured = []
        def prepare(snapshot, actual, day, predecessor, *, opening_digest):
            self.assertEqual(actual, before)
            captured.append(opening_digest)
            return lambda: actual['rows'].append({'value': 'applied'})
        with patch.object(integration_source, 'digest', wraps=digest) as root_hash, \
                patch('mta.mdm.force_capture.prepare_working_input', side_effect=prepare), \
                patch('mta.mdm.season_capture.prepare_working_input', side_effect=prepare), \
                patch('mta.mdm.stop_pipo_capture.replace_working_input'), \
                patch('mta.mdm.phase_controls_capture.replace_working_input'):
            integration_source.replace_working_inputs({}, prior, {}, None)
        self.assertEqual(root_hash.call_count, 1)
        self.assertEqual(captured, [digest(before), digest(before)])
        self.assertEqual(len(prior['rows']), 5)

    def test_capture_model_batches_preserve_all_occurrences_in_bounded_order(self):
        from mta.mdm.daily_input import _create_capture_rows
        batches, observed = [], []
        model = MagicMock()
        model.side_effect = lambda **value: SimpleNamespace(**value)
        def insert(batch, **kwargs):
            self.assertEqual(kwargs['batch_size'], 500)
            batches.append(len(batch))
            observed.extend((row.ordinal, row.value) for row in batch)
        model.objects.bulk_create.side_effect = insert
        _create_capture_rows(model, (model(ordinal=i, value=None if i % 3 else 0)
            for i in range(1001)))
        self.assertEqual(batches, [500, 500, 1])
        self.assertEqual(observed, [(i, None if i % 3 else 0) for i in range(1001)])

    def test_opening_cache_is_operation_identity_and_failure_scoped(self):
        source = owner()
        build = MagicMock(side_effect=lambda: object())
        self.assertIsNot(immutable(source, 'frame', build), immutable(source, 'frame', build))
        with opening_scope():
            first = immutable(source, 'frame', build)
            with opening_scope():
                self.assertIs(immutable(source, 'frame', build), first)
            source.input_manifest_digest = 'new-manifest'
            self.assertIsNot(immutable(source, 'frame', build), first)
            failure = MagicMock(side_effect=[ValueError('drift'), 'checked'])
            with self.assertRaisesRegex(ValueError, 'drift'):
                immutable(source, 'bad', failure)
            self.assertEqual(immutable(source, 'bad', failure), 'checked')
            current = immutable(source, 'frame', build)
            release_opening()
            self.assertIsNot(immutable(source, 'frame', build), current)
        with opening_scope():
            self.assertIsNot(immutable(source, 'frame', build), first)

    def test_certified_opening_handle_is_explicit_operation_local_and_seal_bound(self):
        initialized = owner()
        metadata = ('initialization', 'source', 'configuration', 'certification',
                    'revision', 3, 4)
        with self.assertRaisesRegex(ValueError, 'active operation'):
            certify_opening(initialized, metadata)
        with opening_scope():
            handle = certify_opening(initialized, metadata)
            self.assertIs(certify_opening(initialized, metadata), handle)
            with self.assertRaisesRegex(ValueError, 'metadata differs'):
                certify_opening(initialized, metadata + ('different',))
            self.assertEqual(require_certified_opening(initialized, handle), metadata)
            self.assertIs(current_certified_opening(initialized), handle)
            release_opening()
            self.assertEqual(require_certified_opening(initialized, handle), metadata)
            initialized.input_manifest_digest = 'changed'
            with self.assertRaisesRegex(ValueError, 'absent or stale'):
                require_certified_opening(initialized, handle)
            with self.assertRaisesRegex(ValueError, 'stale'):
                current_certified_opening(initialized)
            with self.assertRaisesRegex(ValueError, 'stale'):
                certify_opening(initialized, metadata)
            initialized.input_manifest_digest = 'manifest'
            self.assertEqual(require_certified_opening(initialized, handle), metadata)
        with opening_scope(), self.assertRaisesRegex(ValueError, 'absent or stale'):
            require_certified_opening(initialized, handle)

    def test_certified_daily_handle_reads_only_profile_and_finite_binding_receipts(self):
        from mta.mdm import production_families as production
        from mta.serialization import digest
        initialized = owner()
        initialized.pk = 'df0386c9-35fe-44ce-9447-c86940f35637'
        initialized.opening_identity = 'opening-identity'
        initialized.opening_date = date(2026, 10, 1)
        initialized.configuration_digest = digest({'policy': 'fixed'})
        source_receipt = {'families': {'1': {'root': 'one'}}}
        source = SimpleNamespace(pk=3, digest=digest(source_receipt), receipt=source_receipt)
        initialized.source = source
        initialized.source_id = source.pk
        certification = SimpleNamespace(initialization_id=initialized.pk,
            source_digest=source.digest, status='CERTIFIED', receipt_digest='c' * 64,
            populations={})
        revision = SimpleNamespace(pk='36a44cc4-07de-4a45-aef7-52c9d6d462a5',
            initialization_id=initialized.pk, status='ACCEPTED', master_epoch=3,
            configuration_epoch=4)
        attempt = SimpleNamespace(initialization_id=initialized.pk,
            certification=certification, master_revision=revision)
        admission = dict(initialization_id=str(initialized.pk), source_digest=source.digest,
            configuration_digest=initialized.configuration_digest,
            certification_digest=certification.receipt_digest,
            master_revision_id=str(revision.pk))
        owner_receipts = {family: {'family': family, 'sealed': True}
                          for family in production.GROUPS}
        family_digests = {'1': digest(source_receipt['families']['1']),
                          **{str(i): ('2' * 64 if i in (2, 3) else
                             digest(owner_receipts[next(name for name, ids in production.GROUPS.items()
                                 if i in ids)])) for i in range(2, 14)}}
        configuration = {'fixed': 'configuration'}
        seal_receipt = dict(source_digest=source.digest, initialization_id=str(initialized.pk),
            initialization_content_digest=initialized.input_digest, families=family_digests,
            required_families=list(range(1, 14)), configuration=configuration)
        seal = SimpleNamespace(receipt=seal_receipt, digest=digest(seal_receipt))
        certification.populations = {'opening_manifest': initialized.input_manifest_digest,
                                     'integration': seal.digest}
        families = MagicMock()
        families.values_list.return_value = [(i, family_digests[str(i)]) for i in range(2, 14)]
        ordered_families = MagicMock()
        ordered_families.values.return_value = [dict(master_id=i,
            receipt=owner_receipts[next(name for name, ids in production.GROUPS.items() if i in ids)],
            digest=family_digests[str(i)]) for i in range(4, 14)]
        families.order_by.return_value = ordered_families
        with opening_scope():
            with patch.object(production.MdmFamilySource.objects, 'filter', return_value=families), \
                    patch('mta.runtime.mdm_force_models.MdmForceOwner.objects.values_list') as roots:
                roots.return_value.get.return_value = 'root-state'
                handle = production.certified_handle(initialized, attempt, admission)
                from mta.runtime.ingestion_admission import CertifiedReadiness
                from mta.runtime.ingestion_context import RevisionCut
                readiness = CertifiedReadiness(str(initialized.pk), source.digest,
                    certification.receipt_digest, str(revision.pk),
                    initialized.configuration_digest, RevisionCut(3, 4, 5, 6, 7))
                with patch('mta.runtime.ingestion_models.InitializationCertification.objects.get',
                        return_value=certification), patch(
                        'mta.runtime.ingestion_models.MasterInputRevision.objects.get',
                        return_value=revision):
                    self.assertIs(production.certified_state_handle(initialized, readiness), handle)
                    stale = CertifiedReadiness(str(initialized.pk), source.digest,
                        certification.receipt_digest, str(revision.pk),
                        initialized.configuration_digest, RevisionCut(2, 4, 5, 6, 7))
                    with self.assertRaisesRegex(ValueError, 'master revision differs'):
                        production.certified_state_handle(initialized, stale)
            with patch('mta.runtime.input_storage.read_input',
                    return_value={'profile': {'policy': 'fixed'}}) as read:
                self.assertEqual(production.certified_profile(initialized, handle),
                                 {'policy': 'fixed'})
                self.assertEqual(read.call_args.kwargs['components'], ('profile',))
            with patch.object(production, '_configuration', return_value=configuration), \
                    patch.object(production.MdmSourceIntegration.objects, 'get', return_value=seal), \
                    patch.object(production.MdmFamilySource.objects, 'filter', return_value=families), \
                    patch.object(production, '_verified_initialization') as full, \
                    patch.object(production, '_expected') as expected:
                self.assertIs(production.require_certified_binding(source, initialized, handle), seal)
                full.assert_not_called(); expected.assert_not_called()
            family_rows = MagicMock()
            family_rows.order_by.return_value = [SimpleNamespace(master_id=13,
                receipt=owner_receipts['force'], digest=digest(owner_receipts['force']))]
            force_owner = SimpleNamespace(source_id=source.pk, provenance=owner_receipts['force'],
                receipt_digest=digest(owner_receipts['force']), root_state_digest='root-state')
            with patch.object(production, '_private_certified',
                    return_value=(initialized, handle)), \
                    patch.object(production, '_verified_initialization') as full, \
                    patch.object(production, 'require_certified_binding', return_value=seal) as fast, \
                    patch.object(production.MdmFamilySource.objects, 'filter',
                                 return_value=family_rows):
                self.assertIs(production.require_initialization(source), initialized)
                self.assertIs(production.prepare_opening(source), initialized)
                self.assertIs(production.require_binding(source), seal)
                self.assertIs(production.require_owner(source, force_owner, 'force'), force_owner)
                full.assert_not_called()
                self.assertGreaterEqual(fast.call_count, 2)
                force_owner.root_state_digest = 'wrong'
                with self.assertRaisesRegex(ValueError, 'owner differs'):
                    production.require_owner(source, force_owner, 'force')

    def test_certified_successor_reads_profile_only_while_root_loads_opening_once(self):
        from mta.runtime.production_daily import _daily_initialization
        from mta.mdm import production_families as production
        initialized = SimpleNamespace(source=object(), opening_identity='opening-identity',
                                      opening_date=date(2026, 10, 1))
        handle, parent = object(), object()
        full_frame = {'profile': {'root': True}, 'opening': {'state': {}}}
        with patch('mta.mdm.production_families.require_certified_binding') as binding, \
                patch('mta.runtime.opening_scope.current_certified_opening',
                      return_value=handle), \
                patch('mta.mdm.production_families.frame_for_daily',
                      return_value={'profile': {'successor': True}, 'opening': {
                          'identity': 'opening-identity', 'opening_date': '2026-10-01'}}) as daily_frame, \
                patch('mta.mdm.initialization.read_initialized_input',
                      return_value=full_frame) as full, \
                patch('mta.mdm.production_families.bootstrap_native_families') as bootstrap, \
                patch('mta.mdm.production_families.require_binding') as public:
            self.assertEqual(_daily_initialization(initialized, parent, None, handle),
                             {'profile': {'successor': True}, 'opening': {
                                 'identity': 'opening-identity', 'opening_date': '2026-10-01'}})
            full.assert_not_called(); daily_frame.assert_called_once_with(initialized, parent)
            self.assertEqual(_daily_initialization(initialized, None, None, handle),
                             {'profile': {'successor': True}, 'opening': {
                                 'identity': 'opening-identity', 'opening_date': '2026-10-01'}})
            daily_frame.assert_called_with(initialized, None)
            self.assertEqual(binding.call_count, 2)
            bootstrap.assert_not_called(); public.assert_not_called()

        with patch.object(production, 'current_certified_opening', return_value=handle), \
                patch.object(production, 'certified_profile',
                             return_value={'successor': True}) as profile, \
                patch.object(production, '_opening_input', return_value=full_frame) as opening:
            self.assertEqual(production.frame_for_daily(initialized, parent),
                             {'profile': {'successor': True}, 'opening': {
                                 'identity': 'opening-identity', 'opening_date': '2026-10-01'}})
            opening.assert_not_called()
            self.assertIs(production.frame_for_daily(initialized, None), full_frame)
            opening.assert_called_once_with(initialized)

        with patch('mta.mdm.production_families.bootstrap_native_families') as bootstrap, \
                patch('mta.mdm.production_families.require_binding') as public, \
                patch('mta.mdm.initialization.read_initialized_input', return_value=full_frame):
            _daily_initialization(initialized, None, None, None)
            bootstrap.assert_called_once_with(initialized); public.assert_not_called()
            _daily_initialization(initialized, parent, None, None)
            public.assert_called_once_with(initialized.source)

    def test_inspection_frame_installs_current_certification_only_for_normal_capture(self):
        from mta.runtime.production_daily import _inspection_frame
        initialized = SimpleNamespace(source=SimpleNamespace(digest='s' * 64))
        readiness = object()
        bounded = {'profile': {}, 'opening': {'identity': 'i', 'opening_date': '2026-10-01'}}
        with patch('mta.runtime.ingestion_admission.preparation_source',
                   return_value=readiness) as fresh, patch(
                   'mta.mdm.production_families.certified_state_handle') as install, patch(
                   'mta.mdm.production_families.frame_for_daily', return_value=bounded) as frame:
            self.assertIs(_inspection_frame(initialized, 'predecessor', None), bounded)
            fresh.assert_called_once_with(initialized.source.digest)
            install.assert_called_once_with(initialized, readiness)
            frame.assert_called_once_with(initialized, 'predecessor')
        with patch('mta.runtime.ingestion_admission.preparation_source') as fresh, patch(
                   'mta.mdm.production_families.certified_state_handle') as install, patch(
                   'mta.mdm.production_families.frame_for_daily', return_value=bounded):
            self.assertIs(_inspection_frame(initialized, 'predecessor', 'retry'), bounded)
            fresh.assert_not_called(); install.assert_not_called()

    def test_opening_scope_never_caches_live_owner_readback(self):
        from mta.mdm import production_families as production
        source = SimpleNamespace(pk=3, receipt={'schema': production.SOURCE_SCHEMA})
        initialized = owner()
        initialized.source = SimpleNamespace(digest='source')
        frame = {'opening': {'state': {'rows': []}}}
        bags = {'force': {'ForceNormChange': [], 'upload_log': []}}
        expected = {'sealed': True}
        actual_owner = SimpleNamespace(source_id=3, provenance=expected,
            receipt_digest=production.digest(expected), root_state_digest=production.digest(frame['opening']['state']))
        family_rows = MagicMock()
        family_rows.order_by.return_value = [SimpleNamespace(master_id=13, receipt=expected,
                                                             digest=production.digest(expected))]
        with opening_scope(), patch.object(production, '_provenance', return_value=expected), \
                patch.object(production, '_actual', side_effect=[bags['force'], {'drift': []}]) as live, \
                patch.object(production.MdmFamilySource.objects, 'filter', return_value=family_rows):
            production._verify_owner(source, actual_owner, 'force', initialized, frame, bags, True)
            with self.assertRaisesRegex(ValueError, 'opening owner differs'):
                production._verify_owner(source, actual_owner, 'force', initialized, frame, bags, True)
            self.assertEqual(live.call_count, 2)

    def test_native_family_creation_never_constructs_an_unbounded_model_batch(self):
        from mta.mdm import production_families as production
        sizes, values = [], []
        model = MagicMock()
        model.__name__ = 'OrdinaryOpeningOwner'
        model.side_effect = lambda **kw: SimpleNamespace(**kw)
        def inserted(batch, **kwargs):
            sizes.append(len(batch))
            values.extend((row.ordinal, row.Value) for row in batch)
        model.objects.bulk_create.side_effect = inserted
        with patch.object(production, '_fields', return_value=['Value']):
            production._create_rows(model, object(), [{'Value': i} for i in range(1001)], ordinal=True)
        self.assertEqual(sizes, [500, 500, 1])
        self.assertEqual(values, [(i + 1, i) for i in range(1001)])

    def test_streamed_csv_native_file_is_byte_identical_and_fully_validated(self):
        from tools.create_daily_csv_example import create
        from mta.application.production_csv_files import load_binding
        with TemporaryDirectory() as directory:
            root = create(Path(__file__).resolve().parents[1] / 'examples/starter-data/vectorflow-starter-inputs-v1.zip',
                          Path(directory) / 'csv')
            binding = load_binding(root / 'binding-template.json')
            batch = json.loads((root / '2026-10-18/batch.json').read_text())
            paths = {name: root / '2026-10-18' / name for name, state in batch['feeds'].items() if state == 'PRESENT'}
            eager, positions = assemble(batch, binding, {name: path.read_bytes() for name, path in paths.items()}, first_day=True)
            target = root / 'native.json'
            streamed, observed = assemble(batch, binding, paths, first_day=True, output_file=target)
            self.assertIsInstance(streamed, JsonInputFile)
            self.assertEqual(target.read_bytes(), eager)
            self.assertEqual(observed, positions)
            sha = hashlib.sha256(eager).hexdigest()
            self.assertEqual(decode(streamed, sha), decode(eager, sha))
            target.write_bytes(eager + b' ')
            with self.assertRaisesRegex(ValueError, 'bytes differ'):
                decode(streamed, sha)

    def test_all_csv_rejections_are_disk_backed_not_truncated(self):
        columns = [dict(name='Qty', type='int', nullable=False)]
        with self.assertRaises(CsvIntakeError) as caught:
            parse_csv(b'Qty\n' + b'bad\n' * 10001, columns, 'large.csv')
        issues = caught.exception.issues
        self.assertIsInstance(issues, IssueRows)
        self.assertEqual(len(issues), 10001)
        self.assertEqual(issues[-1]['record'], 10001)
        self.assertEqual([row['record'] for row in issues[:10]], list(range(1, 11)))

    def test_json_input_hashes_the_descriptor_it_actually_decodes(self):
        import io
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'native.json'
            original = b'{"value":1}'
            path.write_bytes(original)
            real_open = Path.open
            def intercepted(current, mode='r', *args, **kwargs):
                # An independently reopened text path could point at another
                # payload while the original pathname/stat is restored.
                if mode == 'r':
                    return io.StringIO('{"value":2}')
                return real_open(current, mode, *args, **kwargs)
            with patch.object(Path, 'open', autospec=True, side_effect=intercepted) as opened:
                value = JsonInputFile(path).decode(hashlib.sha256(original).hexdigest(),
                    object_pairs_hook=dict, parse_constant=lambda value: value)
                self.assertEqual(value, {'value': 1})
                self.assertEqual(opened.call_count, 1)

    def test_lost_daily_connection_records_unreconciled_failure_without_status_rewrite(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'native-day.json'
            path.write_bytes(b'{}')
            attempt = SimpleNamespace(attempt_id='attempt', phase='VALIDATED', accepted_facts={}, run_id=None,
                status='RUNNING', archive_path=directory, input_sha256=hashlib.sha256(b'{}').hexdigest(),
                predecessor=None, batch_digest='batch', pk=1, refresh_from_db=MagicMock())
            checks = MagicMock(side_effect=[None, RuntimeError('session lost')])
            @contextmanager
            def locked(owner):
                yield checks
            with patch.object(daily_feed, 'binding_owner', return_value=({}, object())), \
                    patch.object(daily_feed, '_bound_attempt', return_value=attempt), \
                    patch.object(daily_feed, 'job_lock', locked), \
                    patch.object(daily_feed, '_parameters', return_value={}), \
                    patch.object(daily_feed, 'save') as save, \
                    patch('mta.runtime.production_daily.execute', side_effect=ValueError('database disconnected')):
                with self.assertRaisesRegex(ValueError, 'database disconnected'):
                    daily_feed.execute('attempt', 'binding', pick_root=directory)
            record = json.loads((Path(directory) / 'interrupted.json').read_text())
            self.assertEqual(record['status'], 'INTERRUPTED_RECONCILIATION_REQUIRED')
            self.assertEqual(record['error']['message'], 'database disconnected')
            attempt.refresh_from_db.assert_not_called()
            self.assertEqual(save.call_count, 1)  # initial CALCULATE only

    def test_export_uses_server_cursor_and_preserves_cells_empty_rows_and_digest(self):
        rows = [{'values': ['é', None, 7]}, {'values': []}]
        item = dict(version=2, image='reports/example', count=2, digest=rows_digest(rows))
        chunked = MagicMock()
        chunked.fetchmany.side_effect = [[(0, 3, 0, 'str', 'é', None, None, None),
            (0, 3, 1, 'null', None, None, None, None), (0, 3, 2, 'int', None, 7, None, None),
            (1, 0, None, None, None, None, None, None)], []]
        plain = MagicMock()
        plain.fetchone.return_value = (0,)
        with patch.object(relational_state.connection, 'chunked_cursor') as server, \
                patch.object(relational_state.connection, 'cursor') as normal:
            server.return_value.__enter__.return_value = chunked
            normal.return_value.__enter__.return_value = plain
            self.assertEqual(list(relational_state.iter_export(SimpleNamespace(pk=1), item)), rows)
            self.assertEqual(chunked.execute.call_count, 1)
            self.assertEqual(plain.execute.call_count, 1)

    def test_lost_session_unlock_does_not_mask_original_error(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (True, 123)
        fake = SimpleNamespace(in_atomic_block=False, needs_rollback=False,
            connection=SimpleNamespace(closed=False), cursor=MagicMock())
        fake.cursor.return_value.__enter__.return_value = cursor
        with patch.object(daily_feed, 'connection', fake):
            with self.assertRaisesRegex(ValueError, 'original failure'):
                with daily_feed.job_lock(SimpleNamespace(pk=1)):
                    cursor.execute.side_effect = RuntimeError('connection lost')
                    raise ValueError('original failure')


if __name__ == '__main__':
    unittest.main()
