"""Accepted terminal publication reuses intake, preserving occurrence decisions."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from contextlib import ExitStack, nullcontext
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from mta.application import accepted_inputs
from mta.mdm import (force_capture as force, season_capture as season,
    stop_pipo_capture as stop, phase_controls_capture as phase, supplier_capture as supplier)
from mta.serialization import digest, storage


def admission(enabled):
    context = SimpleNamespace(native_daily=True, identity='run')
    accepted_inputs._complete(context)
    return accepted_inputs.consume(context) if enabled else nullcontext()


def rows_query(rows):
    query = MagicMock()
    query.__iter__.side_effect = lambda: iter(rows)
    query.order_by.return_value = query
    return query


def owner():
    return MagicMock(source='source', receipt_digest='receipt', last_run_id=None,
        root_state_digest='root', closing_queue_digest='queue', closing_digest='queue',
        closing_log_digest='logs', closing_current_digest='current', generation=2)


def anchor():
    return dict(run_id=None, root_state_digest='root', queue_digest='queue',
        log_digest='logs', current_digest='current', generation=2)


class AcceptedTerminalTests(unittest.TestCase):
    def stop_case(self, admitted, bad=False, revision=1, missing=False):
        values = dict(SKUCode='sku ', WhCode=None)
        frozen = [dict(values, id=i, revision=1) for i in (1, 2)]
        live = [MagicMock(pk=i, revision=revision, **dict(values, SKUCode='drift' if bad else 'sku '))
                for i in (1, 2)]
        current_owner = owner()
        with ExitStack() as stack:
            stack.enter_context(admission(admitted))
            owners = stack.enter_context(patch.object(stop.MdmStopPipoOwner.objects, 'select_for_update'))
            owners.return_value.get.return_value = current_owner
            queue = stack.enter_context(patch.object(stop.MdmStopPipoQueue.objects, 'select_for_update'))
            queue.return_value.filter.return_value = rows_query([] if missing else live)
            writes = stack.enter_context(patch.object(stop.MdmStopPipoConsumed.objects, 'create'))
            hashes = stack.enter_context(patch.object(stop, 'digest', wraps=digest))
            stop.finalize('run', dict(source_id=1, stop_pipo=dict(source_digest='receipt',
                anchor=anchor(), rows=frozen)), dict(ClosingState=[dict(control_aux=dict(phase_stops=[values, values]))]))
            return ([call.kwargs for call in writes.call_args_list],
                [row.delete.call_count for row in live], current_owner.closing_queue_digest, hashes.call_count)

    def test_stop_duplicate_null_order_writes_identical_without_source_rehash(self):
        ordinary = self.stop_case(False)
        admitted = self.stop_case(True)
        self.assertEqual(ordinary[:3], admitted[:3])
        self.assertEqual(ordinary[3] - admitted[3], 2)
        with self.assertRaisesRegex(ValueError, 'changed or disappeared'):
            self.stop_case(False, bad=True)
        self.stop_case(True, bad=True)  # Not an audit of unchecked test fixtures.
        for missing, revision in ((True, 1), (False, 2)):
            with self.assertRaisesRegex(ValueError, 'changed or disappeared'):
                self.stop_case(True, missing=missing, revision=revision)

    def phase_case(self, admitted, bad=False):
        frozen = {name: [dict.fromkeys(fields)] for name, fields in phase.FIELDS.items()}
        for rows in frozen.values():
            rows[0].update(SKUCode='sku ', WhCode=None, Approved=False, id=1, revision=1)
        remaining = {name: [{f: (v.strip(' ') if isinstance(v, str) else v)
                    for f, v in rows[0].items() if f in phase.FIELDS[name]}]
                     for name, rows in frozen.items()}
        models = {name: MagicMock(side_effect=lambda **kwargs: kwargs) for name in phase.QUEUES}
        live = {}
        consumed = {name: MagicMock() for name in models}
        for name, model in models.items():
            live[name] = MagicMock(pk=1, revision=1, **{f: ('drift' if bad and f == 'SKUCode' else frozen[name][0][f]) for f in phase.FIELDS[name]})
            model.objects.select_for_update.return_value.filter.return_value = rows_query([live[name]])
        current_owner = owner()
        with admission(admitted), patch.dict(phase.QUEUES, models), patch.dict(phase.CONSUMED, consumed), \
                patch.object(phase.MdmPhaseControlsOwner.objects, 'select_for_update') as owners, \
                patch.object(phase, 'digest', wraps=digest) as hashes:
            owners.return_value.get.return_value = current_owner
            phase.finalize('run', dict(source_id=1, phase_controls=dict(source_digest='receipt',
                anchor=anchor(), **frozen)), dict(ClosingState=[dict(control_aux=remaining)]))
            return ({name: (consumed[name].objects.create.call_args.kwargs,
                    models[name].objects.bulk_create.call_args.args[0], live[name].delete.call_count)
                    for name in models}, current_owner.closing_queue_digest, hashes.call_count)

    def test_phase_same_rebuild_without_assertion_hash_scans(self):
        ordinary, admitted = self.phase_case(False), self.phase_case(True)
        self.assertEqual(ordinary[:2], admitted[:2])
        self.assertEqual(admitted[2], 1)  # New closing receipt only.
        self.assertGreater(ordinary[2], admitted[2])
        with self.assertRaisesRegex(ValueError, 'changed or disappeared'):
            self.phase_case(False, bad=True)

    def force_case(self, admitted, bad=False, newer=False):
        values = dict(SKUCode='sku', WhCode=None, NewNorm=10, Approved=True, RequestedBy=None)
        frozen = [dict(values, id=i, revision=1) for i in (1, 2)]
        live = [MagicMock(pk=i, revision=2 if newer else 1,
            **dict(values, NewNorm=20 if newer else 10)) for i in (1, 2)]
        log = dict.fromkeys(force.LOG_FIELDS)
        log.update(SKUCode='sku', WHCode=None, ActionTimeStamp='2026-10-30T12:00:00', id=3)
        after = {('WhCode' if n == 'WHCode' else n): log[n] for n in force.LOG_FIELDS}
        after['OldNorm'] = 7
        logrow = MagicMock(pk=3, **{n: ('drift' if bad and n == 'SKUCode' else log[n]) for n in force.LOG_FIELDS})
        current_owner = owner()
        with admission(admitted), patch.object(force.MdmForceOwner.objects, 'select_for_update') as owners, \
                patch.object(force.MdmForceQueue.objects, 'select_for_update') as queues, \
                patch.object(force.MdmForceUploadLog.objects, 'select_for_update') as logs, \
                patch.object(force.MdmForceConsumed.objects, 'create') as writes, \
                patch.object(force.MdmForceQueue.objects, 'create') as adds, \
                patch.object(force, 'native_log', wraps=force.native_log) as check_log, \
                patch.object(force, 'digest', wraps=digest) as hashes:
            owners.return_value.get.return_value = current_owner
            queues.return_value.filter.return_value = rows_query(live)
            logs.return_value.get.return_value = logrow
            force.finalize('run', dict(source_id=1, force=dict(source_digest='receipt', anchor=anchor(),
                rows=frozen, upload_log=[log])), dict(ClosingState=[dict(importer=dict(ForceNormChange=[]),
                    controls=dict(upload_log=[after]))]))
            return ([c.kwargs for c in writes.call_args_list], [r.delete.call_count for r in live],
                adds.call_count, logrow.OldNorm, logrow.save.call_args.kwargs,
                current_owner.closing_digest, current_owner.closing_log_digest, check_log.call_count, hashes.call_count)

    def test_force_same_writes_and_newer_scalar_survives_without_log_recheck(self):
        for newer in (False, True):
            ordinary, admitted = self.force_case(False, newer=newer), self.force_case(True, newer=newer)
            self.assertEqual(ordinary[:7], admitted[:7])
            self.assertEqual(admitted[1], [0, 0] if newer else [1, 1])
            self.assertEqual(admitted[7], 0)
            self.assertEqual(ordinary[8] - admitted[8], 2)
        with self.assertRaisesRegex(ValueError, 'upload-log occurrence changed'):
            self.force_case(False, bad=True)

    def season_case(self, admitted, newer=False, bad=False):
        request = dict.fromkeys(season.REQUEST_FIELDS)
        request.update(SKUCode='sku', WhCode=None, Approved=False)
        frozen_rows = [dict(storage(request), id=i, revision=1) for i in (1, 2)]
        current = dict.fromkeys(season.SEASON_FIELDS)
        current.update(SKUCode='sku', WhCode=None, Status=None, Comment='exact ®')
        before = dict(storage(current), id=3, revision=1, ordinal=1)
        live_rows = [MagicMock(pk=r['id'], revision=1, **{n:r[n] for n in season.REQUEST_FIELDS}) for r in frozen_rows]
        current_row = MagicMock(pk=3, revision=2 if newer else 1, **dict(current,
            Status='later' if newer else None, SKUCode='drift' if bad else 'sku'))
        current_model = MagicMock(side_effect=lambda **kwargs: kwargs)
        current_model.objects.select_for_update.return_value.filter.return_value = rows_query([current_row])
        current_owner = owner()
        with admission(admitted), patch.object(season.MdmSeasonOwner.objects, 'select_for_update') as owners, \
                patch.object(season.MdmSeasonQueue.objects, 'select_for_update') as queues, \
                patch.object(season, 'MdmSeasonCurrent', current_model), \
                patch.object(season.MdmSeasonConsumed.objects, 'create') as writes, \
                patch.object(season, 'digest', wraps=digest) as hashes:
            owners.return_value.get.return_value = current_owner
            queues.return_value.filter.return_value = rows_query(live_rows)
            season.finalize('run', dict(source_id=1, season=dict(source_digest='receipt', anchor=anchor(),
                rows=frozen_rows, current=[before])), dict(ClosingState=[dict(
                    control_aux=dict(season_requests=[]), dbm=dict(Seasonality=[current]))]))
            return ([c.kwargs for c in writes.call_args_list], [r.delete.call_count for r in live_rows],
                current_model.objects.bulk_create.call_args.args[0], current_owner.closing_queue_digest,
                current_owner.closing_current_digest, hashes.call_count)

    def test_season_same_writes_and_later_status_overlay(self):
        for newer in (False, True):
            ordinary, admitted = self.season_case(False, newer), self.season_case(True, newer)
            self.assertEqual(ordinary[:5], admitted[:5])
            self.assertEqual(admitted[2][0]['Status'], 'later' if newer else None)
            self.assertEqual(ordinary[5] - admitted[5], 2)
        with self.assertRaisesRegex(ValueError, 'outside its status writer'):
            self.season_case(False, bad=True)

    def supplier_case(self, admitted, newer=False):
        values = dict(SKUCode='sku', WhCode=None, SupplierCode='s', SOB=10, Approved=True)
        frozen = [dict(values, id=i, revision=1) for i in (1, 2)]
        queues = {name: [] for name in supplier.QUEUES}
        queues['NMSSOB'] = frozen
        models = {name: MagicMock() for name in queues}
        archives = {name: MagicMock() for name in queues}
        live = [MagicMock(pk=i, revision=2 if newer else 1, **dict(values, SOB=20 if newer else 10)) for i in (1, 2)]
        models['NMSSOB'].objects.select_for_update.return_value.get.side_effect = live
        raw = {name: [] for name in supplier.MODELS}
        final = deepcopy(raw)
        final['SOBDataRaw'] = [dict(Value=None), dict(Value=None)]
        raw_models = {name: MagicMock(side_effect=lambda **kwargs: kwargs) for name in raw}
        captured = dict(source_digest='receipt', moq_format='WithDestLoc', raw=raw, queues=queues)
        source = SimpleNamespace(pk=1)
        with admission(admitted), patch('mta.runtime.mdm_models.MdmSource.objects.select_for_update') as sources, \
                patch.object(supplier.MdmSupplierConfiguration.objects, 'get',
                    return_value=SimpleNamespace(receipt_digest='receipt', moq_format='WithDestLoc')), \
                patch.object(supplier, 'capture', return_value=captured) as recapture, \
                patch.dict(supplier.QUEUES, models), patch.dict(supplier.ARCHIVES, archives), \
                patch.dict(supplier.MODELS, raw_models), patch.object(supplier, 'columns', return_value=list(values)), \
                patch.object(supplier, 'archive_populations', wraps=supplier.archive_populations) as archive_check:
            sources.return_value.get.return_value = source
            supplier.finalize('run', dict(source_id=1, nms_active=True, supplier=captured,
                configuration=dict(run_timestamp='2026-10-30T12:00:00')),
                dict(ClosingState=[dict(complete=final)]))
            return ([dict(c.kwargs, source=1) for c in archives['NMSSOB'].objects.create.call_args_list],
                [r.delete.call_count for r in live], raw_models['SOBDataRaw'].objects.bulk_create.call_args.args[0],
                recapture.call_count, archive_check.call_count)

    def test_supplier_no_recapture_or_archive_revalidation_and_same_writes(self):
        for newer in (False, True):
            ordinary, admitted = self.supplier_case(False, newer), self.supplier_case(True, newer)
            # Replace the independently allocated source object in raw inserts.
            for result in (ordinary, admitted):
                for row in result[2]: row['source'] = 1
            self.assertEqual(ordinary[:3], admitted[:3])
            self.assertEqual(admitted[1], [0, 0] if newer else [1, 1])
            self.assertEqual(admitted[3:], (0, 0))

    def test_pending_no_source_hash_replay_and_missing_errors_propagate(self):
        snapshot = dict(source_id=1, supplier=dict(moq_format='WithDestLoc', pending=[
            dict(family='sob', history_pk=7, task_id='task', row_digest='bad')]))
        output = dict(ClosingState=[dict(complete={name: [] for name in supplier.MODELS})])
        output['ClosingState'][0]['complete']['SOBDataRaw'] = [dict(SKUCode='sku', WHCode=None, SupplierCode='s')]
        row = MagicMock(SKUCode='sku', WhCode=None, SupplierCode='s')
        with patch.object(supplier.MdmSobHistory.objects, 'select_for_update') as history, \
                patch.object(supplier, 'columns', return_value=['SKUCode', 'WhCode', 'SupplierCode']), \
                patch.object(supplier, 'digest', wraps=digest) as hashes:
            history.return_value.get.return_value = row
            with self.assertRaisesRegex(ValueError, 'pending history changed'):
                supplier.finalize_pending(snapshot, output)
            hashes.reset_mock()
            with admission(True): supplier.finalize_pending(snapshot, output)
            hashes.assert_not_called()
            row.save.assert_not_called()  # Canonical NULL identity exclusion.
            history.return_value.get.side_effect = RuntimeError('unexpected database failure')
            with admission(True), self.assertRaisesRegex(RuntimeError, 'unexpected database failure'):
                supplier.finalize_pending(snapshot, output)

    def test_pending_same_transition_and_deferred_task_is_not_read(self):
        values = dict(SKUCode='sku', WhCode='loc', SupplierCode='supplier')
        item = dict(family='sob', history_pk=7, task_id='task', row_digest=digest(values))
        snapshot = dict(source_id=1, supplier=dict(moq_format='WithDestLoc', pending=[item]))
        raw = {name: [] for name in supplier.MODELS}
        raw['SOBDataRaw'] = [dict(SKUCode='sku', WHCode='loc', SupplierCode='supplier')]
        output = dict(ClosingState=[dict(complete=raw)])
        results = []
        for admitted in (False, True):
            row = MagicMock(**values)
            with admission(admitted), patch.object(supplier.MdmSobHistory.objects, 'select_for_update') as history, \
                    patch.object(supplier, 'columns', return_value=list(values)), \
                    patch.object(supplier, 'digest', wraps=digest) as hashes:
                history.return_value.get.return_value = row
                supplier.finalize_pending(snapshot, output)
                results.append((row.Status, row.Comments, row.save.call_args.kwargs))
                self.assertEqual(hashes.call_count, 0 if admitted else 1)
                history.reset_mock()
                supplier.finalize_pending(snapshot, output, deferred_tasks={(4, 'task')})
                history.assert_not_called()
        self.assertEqual(results[0], results[1])

    def test_admitted_terminal_raw_reuses_producer_without_trace_scan(self):
        class NoScan:
            def __iter__(self):
                raise AssertionError('Repeated trace validation')
        raw = {name: [dict(Value=None), dict(Value=None)] for name in supplier.MODELS}
        output = dict(ClosingState=[dict(complete=raw)], SupplierStages=NoScan())
        with admission(True):
            result = supplier.terminal_raw(output)
        for name in raw:
            self.assertIs(result[name], raw[name])


if __name__ == '__main__':
    unittest.main()
