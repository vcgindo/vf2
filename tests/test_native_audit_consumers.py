"""Pure native audit consumer proofs; no database or service execution."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from contextlib import ExitStack, nullcontext
from copy import deepcopy
from datetime import date, datetime
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import MagicMock, patch
from uuid import uuid4
from zoneinfo import ZoneInfo

from mta.application import accepted_inputs
from mta.mdm import native_audit as audit
from mta.serialization import digest, storage


POLICY = dict(horizon=7, timezone='Asia/Kolkata', client_folder=None)
FIELDS = ('ActionTimeStamp', 'OldNorm', 'NewNorm', 'Note')


def fixture():
    source = NS(pk=1, digest='source', receipt={'schema':'fresh-production-mdm-source-v1'})
    initialized = NS(pk=uuid4(), source=source, source_id=1, configuration_digest='configuration')
    run = NS(pk=uuid4(), kind='DAILY_CHAIN', status='RUNNING', business_date=date(2026,7,10),
        predecessor_id=None, input_payload={}, production_manifest={'ingestion_preparation':dict(
            initialization_id=str(initialized.pk), source_digest=source.digest,
            configuration_digest=initialized.configuration_digest)})
    daily = NS(run_id=run.pk, source=source, source_id=1, origin_id=None)
    run.mdm_input_capture = daily
    capture = NS(run=run, run_id=run.pk, initialization=initialized, initialization_id=initialized.pk,
        source=source, source_id=1, business_date=run.business_date, predecessor_id=None,
        origin_id=None, configuration_digest='configuration', status='FROZEN',
        frozen_digest='', terminal_digest='', **POLICY)
    capture.save = MagicMock()
    return run, daily, initialized, capture


def admission(run):
    context = NS(identity=str(run.pk), native_daily=True)
    accepted_inputs._complete(context)
    return accepted_inputs.consume(context)


class NativeAuditConsumerTests(TestCase):
    def test_bounded_persisted_capture_checks_metadata_without_profile_or_rows(self):
        run, daily, initialized, capture = fixture()
        capture.status = 'SEALED'
        with patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects.get', return_value=daily), \
                patch('mta.runtime.input_reader.read_input', side_effect=AssertionError('strict input')), \
                patch('mta.runtime.accepted_input_read.read_accepted_input', side_effect=AssertionError('input')), \
                patch.object(audit, 'image_digest', side_effect=AssertionError('row audit')):
            self.assertIs(audit._accepted_capture(capture), capture)
            for field, value in (('source_id', 2), ('initialization_id', uuid4()),
                    ('configuration_digest', 'foreign'), ('business_date', date(2026,7,11)),
                    ('predecessor_id', uuid4()), ('origin_id', uuid4()), ('status', 'FROZEN')):
                original = getattr(capture, field)
                setattr(capture, field, value)
                with self.subTest(field=field), self.assertRaises(ValueError):
                    audit._accepted_capture(capture)
                setattr(capture, field, original)
            with patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects.get', side_effect=RuntimeError('database error')):
                with self.assertRaisesRegex(RuntimeError, 'database error'):
                    audit._accepted_capture(capture)

    def test_receipt_after_python_handoff_has_identical_values_without_audit(self):
        run, daily, initialized, capture = fixture()
        capture.status = 'SEALED'; capture.frozen_digest='frozen'; capture.terminal_digest='terminal'
        with patch.object(audit.NativeUploadAudit.objects, 'select_related') as query, \
                patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects.get', return_value=daily), \
                patch.object(audit, 'identity', return_value={'run_id':str(run.pk)}), \
                patch.object(audit, 'verify', side_effect=AssertionError('diagnostic')), \
                patch('mta.runtime.input_reader.read_input', side_effect=AssertionError('strict input')), \
                patch.object(audit, 'images', side_effect=AssertionError('row audit')):
            query.return_value.filter.return_value.first.return_value = capture
            self.assertIsNone(accepted_inputs.current())
            self.assertEqual(audit.receipt(run), dict(run_id=str(run.pk), status='SEALED',
                frozen_digest='frozen', terminal_digest='terminal'))

    def finalize(self, admitted, drift=False):
        run, daily, initialized, capture = fixture()
        profile = dict(native_upload_audit=POLICY)
        initialized.configuration_digest = digest(profile)
        capture.configuration_digest = initialized.configuration_digest
        run.production_manifest['ingestion_preparation']['configuration_digest'] = initialized.configuration_digest
        stamps = [datetime(2026,7,2,23,59,59,tzinfo=ZoneInfo(POLICY['timezone'])),
                  datetime(2026,7,3,tzinfo=ZoneInfo(POLICY['timezone'])),
                  datetime(2026,7,3,tzinfo=ZoneInfo(POLICY['timezone']))]
        frozen = [dict(source_pk=i, ordinal=i, retained=None, ActionTimeStamp=stamp,
            OldNorm=None, NewNorm=10, Note=None) for i, stamp in enumerate(stamps, 1)]
        live = [dict({f:r[f] for f in FIELDS}, id=r['source_pk'], OldNorm=13) for r in frozen]
        if drift:
            live[0]['Note']='changed'
        source = MagicMock()
        source.objects.select_for_update.return_value.filter.return_value.values.return_value = live
        model = MagicMock(side_effect=lambda **kwargs:kwargs)
        data = {'FROZEN':{'UIUploadLogFNC':deepcopy(frozen)}, 'FINAL':{'UIUploadLogFNC':[]}}
        def write(rows, **kwargs):
            data['FINAL']['UIUploadLogFNC'].extend({key:value for key,value in row.items()
                if key not in ('capture','stage')} for row in rows)
        model.objects.bulk_create.side_effect = write
        with ExitStack() as stack:
            if admitted: stack.enter_context(admission(run))
            stack.enter_context(patch.object(audit, 'BINDINGS', [('UIUploadLogFNC',source,model)]))
            stack.enter_context(patch.object(audit, 'fields', return_value=FIELDS))
            stack.enter_context(patch.object(audit, 'identity', return_value={'fixture':'identity'}))
            images = stack.enter_context(patch.object(audit, 'images', side_effect=lambda cap, stage:deepcopy(data[stage])))
            strict = stack.enter_context(patch('mta.runtime.input_reader.read_input', return_value={'profile':profile}))
            accepted = stack.enter_context(patch('mta.runtime.accepted_input_read.read_accepted_input', return_value={'profile':profile}))
            stack.enter_context(patch('mta.runtime.initialization_models.ProductionInitialization.objects.select_related')) \
                .return_value.get.return_value = initialized
            stack.enter_context(patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects.get', return_value=daily))
            stack.enter_context(patch.object(audit.NativeUploadAudit.objects, 'select_for_update')) \
                .return_value.select_related.return_value.get.return_value = capture
            stack.enter_context(patch.object(audit.connection, 'cursor'))
            capture.frozen_digest = audit.image_digest(capture, 'FROZEN', data['FROZEN'])
            audit.finalize(run)
            result = (data['FINAL'], capture.terminal_digest, source.objects.filter.call_args_list,
                      storage(audit.native_rows(capture, data['FINAL'])))
            return result, strict.call_count, accepted.call_count, [c.args[1] for c in images.call_args_list]

    def test_final_retention_and_export_values_match_without_rereading_new_rows(self):
        ordinary = self.finalize(False)
        admitted = self.finalize(True)
        # Source object is queried by identity; compare the actual deletion PKs.
        for result in (ordinary[0], admitted[0]):
            for call in result[2]: call.kwargs.pop('source', None)
        self.assertEqual(ordinary[0], admitted[0])
        self.assertEqual([r['retained'] for r in admitted[0][0]['UIUploadLogFNC']], [False,True,True])
        self.assertEqual([r['OldNorm'] for r in admitted[0][0]['UIUploadLogFNC']], [13,13,13])
        self.assertEqual(admitted[1:], (0, 1, ['FROZEN']))
        self.assertGreater(ordinary[1], 0)
        self.assertIn('FINAL', ordinary[3])
        with self.assertRaisesRegex(ValueError, 'occurrence changed'):
            self.finalize(False, drift=True)

    def test_owned_exporter_reads_final_once_with_same_wallclock_values(self):
        from mta.runtime import operational_opening
        run,daily,initialized,capture=fixture()
        run.refresh_from_db=MagicMock()
        capture.status='SEALED'
        zone=ZoneInfo(POLICY['timezone'])
        rows={'UIUploadLogFNC':[
            dict(source_pk=1,ordinal=1,retained=False,ActionTimeStamp=datetime(2026,7,2,tzinfo=zone),OldNorm=None,NewNorm=10,Note=None),
            dict(source_pk=2,ordinal=2,retained=True,ActionTimeStamp=datetime(2026,7,3,tzinfo=zone),OldNorm=13,NewNorm=10,Note=None)]}
        with patch.object(audit,'BINDINGS',[('UIUploadLogFNC',None,None)]), \
                patch.object(audit,'fields',return_value=FIELDS), \
                patch.object(audit.NativeUploadAudit.objects,'select_related') as select, \
                patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects.get',return_value=daily), \
                patch('mta.runtime.receipt_integrity.verify_root'), \
                patch.object(audit,'verify',side_effect=AssertionError('diagnostic')), \
                patch('mta.runtime.input_reader.read_input',side_effect=AssertionError('strict input')), \
                patch.object(audit,'images',return_value=rows) as read:
            select.return_value.get.return_value=capture
            result=operational_opening.native_upload_inputs(run)
            self.assertEqual(result['logs'],audit.native_rows(capture,{'UIUploadLogFNC':[rows['UIUploadLogFNC'][1]]}))
            self.assertEqual(result['logs']['UIUploadLogFNC'][0]['ActionTimeStamp'],'2026-07-03T00:00:00')
            read.assert_called_once_with(capture,'FINAL')

    def test_public_diagnostic_verify_still_rejects_frozen_row_drift(self):
        run, daily, initialized, capture = fixture()
        profile = {'native_upload_audit':POLICY}
        initialized.configuration_digest = capture.configuration_digest = digest(profile)
        capture.status='SEALED';capture.frozen_digest='expected'
        with patch('mta.runtime.input_reader.read_input', return_value={'profile':profile}) as reader, \
                patch('mta.runtime.mdm_daily_models.MdmDailyInputCapture.objects.get', return_value=daily), \
                patch.object(audit, 'image_digest', return_value='drift') as rows:
            with self.assertRaisesRegex(ValueError, 'frozen identity/value drift'):
                audit.verify(capture)
            reader.assert_called_once()
            rows.assert_called_once_with(capture, 'FROZEN')

    def test_foreign_private_owner_or_seed_is_denied(self):
        run, daily, initialized, capture = fixture()
        other, *_ = fixture()
        with admission(other), self.assertRaisesRegex(ValueError, 'daily owner differs'):
            audit._production_initialization(run, initialized)
        run.production_manifest['ingestion_preparation']['source_digest']='foreign'
        with admission(run), self.assertRaisesRegex(ValueError, 'source/initialization differs'):
            audit._production_initialization(run, initialized)

    def test_bind_freezes_same_rows_without_profile_hash_or_immediate_verification(self):
        results=[]
        for admitted in (False,True):
            run,daily,initialized,capture=fixture()
            profile={'native_upload_audit':POLICY}
            initialized.configuration_digest=digest(profile)
            run.production_manifest['ingestion_preparation']['configuration_digest']=initialized.configuration_digest
            row=dict(id=1,ActionTimeStamp=datetime(2026,7,3,tzinfo=ZoneInfo(POLICY['timezone'])),
                OldNorm=None,NewNorm=10,Note=None)
            source=MagicMock()
            source.objects.filter.return_value.order_by.return_value.values.return_value=[row]
            model=MagicMock(side_effect=lambda **kw:kw)
            def create(**kw):
                return NS(**kw,save=MagicMock())
            audit_model=MagicMock(side_effect=create)
            with (admission(run) if admitted else nullcontext()), \
                    patch.object(audit,'BINDINGS',[('UIUploadLogFNC',source,model)]), \
                    patch.object(audit,'fields',return_value=FIELDS), \
                    patch.object(audit,'identity',return_value={'fixture':'identity'}), \
                    patch.object(audit,'NativeUploadAudit',audit_model), \
                    patch('mta.runtime.initialization_models.ProductionInitialization.objects.get',return_value=initialized), \
                    patch.object(audit.settings,'VF_MTA_ACTION_TIME_ZONE',POLICY['timezone']), \
                    patch.object(audit.connection,'cursor'), \
                    patch.object(audit,'verify') as verify, \
                    patch.object(audit,'images',side_effect=AssertionError('immediate row reread')), \
                    patch.object(audit,'digest',wraps=digest) as hashes:
                audit.bind(run,daily,profile)
                rows=[{k:v for k,v in r.items() if k!='capture'}
                      for r in model.objects.bulk_create.call_args.args[0]]
                results.append(rows)
                self.assertEqual(verify.call_count,0 if admitted else 1)
                self.assertEqual(hashes.call_count,1 if admitted else 2)
        self.assertEqual(results[0],results[1])
