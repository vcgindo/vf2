"""Native input export integrity and authorization, without a running database.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
from datetime import date
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from django.test import Client
from mta.application import native_input_archive as module
from mta.serialization import digest


class NativeArchiveTests(unittest.TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.opening = self.root/'opening.json'
        self.daily = self.root/'daily.json'
        self.opening.write_bytes(b'{"opening":"original bytes"}\n')
        self.daily.write_bytes(b'{"day":"original bytes"}\n')
        self.binding = dict(id='init1', source_digest='source1',
            input_sha256=module._sha(self.opening.read_bytes()))
        self.captured = dict(initialization_binding=self.binding,
            daily_input_sha256=module._sha(self.daily.read_bytes()),
            pick_output_root=str(self.root), rows=[{'value':None}, {'value':'2.000'}, {'value':None}])
        self.run = SimpleNamespace(pk='own-run', status='SUCCEEDED', kind='DAILY_CHAIN',
            business_date=date(2026,10,18), output_digest='output1',
            input_payload={'schema':'typed-input', 'types':[['value','decimal']]})
        self.run.input_digest = digest(self.captured)
        self.run.input_manifest_digest = digest(self.run.input_payload)
        self.download = self.root/'own-run'/'download'
        self.download.mkdir(parents=True)
        (self.download/'LogisticPickListReport.csv').write_bytes(b'own pick file')
        self.addCleanup(patch.stopall)
        patch.object(module, 'read_input', return_value=self.captured).start()
        patch('mta.presentation.pick_downloads.read_input', return_value=self.captured).start()
        patch('mta.presentation.native_publication.require_mode').start()
        patch('mta.presentation.native_publication.identity',
            return_value={'initialization':self.binding}).start()

    def prepare(self):
        return module.prepare(self.run, self.opening, self.daily)

    def rewrite(self, transform):
        path=self.download/'InputData.zip'
        with zipfile.ZipFile(path) as archive:
            parts=[(info.filename,archive.read(info.filename)) for info in archive.infolist()]
        parts=transform(parts)
        with zipfile.ZipFile(path,'w') as archive:
            for name, raw in parts:archive.writestr(name,raw)

    def test_original_bytes_complete_capture_manifest_and_duplicate_order_roundtrip(self):
        result=self.prepare()
        with zipfile.ZipFile(result['path']) as archive:
            self.assertEqual(set(archive.namelist()),module.MEMBERS)
            self.assertEqual(archive.read('NativeOpeningInput.json'),self.opening.read_bytes())
            self.assertEqual(archive.read('NativeDailyInput.json'),self.daily.read_bytes())
            self.assertEqual(json.loads(archive.read('NativeCapturedInput.json')),self.captured)
            self.assertEqual(json.loads(archive.read('NativeInputSchema.json')),self.run.input_payload)
        stream,name=module.open_archive(self.run)
        with stream:self.assertEqual(module._sha(stream.read()),result['sha256'])
        self.assertEqual(name,'InputData.zip')
        self.assertEqual(self.prepare(), result)
        # Resume verifies the preserved bytes instead of overwriting corruption.
        (self.download/'InputData.zip').write_bytes(b'partial previous attempt')
        with self.assertRaises(module.ArchiveDenied):self.prepare()

    def test_original_hash_drift_denies_before_file_creation(self):
        self.daily.write_bytes(b'changed')
        with self.assertRaisesRegex(module.ArchiveDenied,'original_hash'):self.prepare()
        self.assertFalse((self.download/'InputData.zip').exists())

    def test_captured_or_manifest_drift_is_denied(self):
        self.captured['rows'].append({'value':'extra'})
        with self.assertRaisesRegex(module.ArchiveDenied,'identity_drift'):self.prepare()

    def test_cross_run_manifest_denied_even_if_zip_crc_is_valid(self):
        self.prepare()
        def transform(parts):
            result=[]
            for name,raw in parts:
                if name=='manifest.json':
                    value=json.loads(raw);value['run_id']='other-run';raw=json.dumps(value).encode()
                result.append((name,raw))
            return result
        self.rewrite(transform)
        with self.assertRaisesRegex(module.ArchiveDenied,'manifest_drift'):module.open_archive(self.run)

    def test_member_bytes_cannot_be_resealed_with_only_a_new_manifest(self):
        self.prepare()
        def transform(parts):
            changed=b'{"forged":true}'
            result=[]
            for name,raw in parts:
                if name=='NativeCapturedInput.json':raw=changed
                elif name=='manifest.json':
                    value=json.loads(raw);value['files']['NativeCapturedInput.json']={
                        'bytes':len(changed),'sha256':module._sha(changed)};raw=json.dumps(value).encode()
                result.append((name,raw))
            return result
        self.rewrite(transform)
        with self.assertRaisesRegex(module.ArchiveDenied,'file_drift'):module.open_archive(self.run)

    def test_unknown_traversal_and_duplicate_members_are_denied(self):
        self.prepare(); original=(self.download/'InputData.zip').read_bytes()
        for extra in ('../secret','manifest.json'):
            (self.download/'InputData.zip').write_bytes(original)
            self.rewrite(lambda parts:parts+[(extra,b'{}')])
            with self.assertRaisesRegex(module.ArchiveDenied,'member_drift'):module.open_archive(self.run)

    def test_oversized_compressed_or_expanded_archive_is_denied(self):
        self.prepare()
        for field in ('MAX_COMPRESSED','MAX_UNCOMPRESSED'):
            with patch.object(module,field,10):
                with self.assertRaises(module.ArchiveDenied):module.open_archive(self.run)

    def test_symlink_source_denied_without_reading(self):
        with patch.object(Path,'is_symlink',return_value=True):
            with self.assertRaisesRegex(module.ArchiveDenied,'symlink'):self.prepare()

    def test_exact_entitlement_and_zip_http_content_type(self):
        client=Client(); path='/api/mta/DownloadReports/InputData'
        with patch('mta.presentation.views.selected_run',side_effect=AssertionError('must deny first')):
            for actor in ({'id':1}, {'id':1,'entitlements':['mta-report-urls']}):
                response=client.get(path,HTTP_X_VECTORFLOW_IDENTITY=json.dumps(actor))
                self.assertEqual(response.status_code,403)
            response=client.generic('GET',path,json.dumps({'entitlements':['mta-input-archive']}),
                content_type='application/json')
            self.assertEqual(response.status_code,403)
        with patch('mta.presentation.views.selected_run',return_value=self.run), \
                patch.object(module,'open_archive',return_value=(io.BytesIO(b'zip-bytes'),'InputData.zip')):
            response=client.get(path,HTTP_X_VECTORFLOW_IDENTITY=json.dumps(
                {'id':1,'entitlements':['mta-input-archive']}))
            self.assertEqual(response.status_code,200)
            self.assertEqual(response['Content-Type'],'application/zip')
            self.assertEqual(b''.join(response.streaming_content),b'zip-bytes')

    def test_opt_in_large_member_streams_with_bounded_heap(self):
        import tracemalloc
        from mta.row_sequences import RecordRows
        self.captured['rows']=RecordRows(3000,lambda:({'value':'X'*4096} for _ in range(3000)))
        self.run.input_digest=digest(self.captured)
        with patch.object(module,'MAX_UNCOMPRESSED',1024*1024):
            with self.assertRaisesRegex(module.ArchiveDenied,'size_limit'):self.prepare()
            with patch.dict(os.environ,{'VF_INPUT_ARCHIVE_MAX_UNCOMPRESSED_BYTES':str(32*1024**2),
                    'VF_INPUT_ARCHIVE_MAX_COMPRESSED_BYTES':str(2*1024**2)}):
                tracemalloc.start()
                try:
                    result=self.prepare()
                    stream,name=module.open_archive(self.run);stream.close()
                    _,peak=tracemalloc.get_traced_memory()
                finally:tracemalloc.stop()
        self.assertGreater(result['manifest']['files']['NativeCapturedInput.json']['bytes'],12*1024**2-1024**2)
        self.assertLess(peak,8*1024**2)
        self.assertEqual(name,'InputData.zip')

    def test_invalid_or_unbounded_policy_is_denied(self):
        for name,values in (
            ('VF_INPUT_ARCHIVE_MAX_COMPRESSED_BYTES',('0','-1','unlimited',str(4*1024**3+1))),
            ('VF_INPUT_ARCHIVE_MAX_UNCOMPRESSED_BYTES',('0','',str(64*1024**3+1)))):
            for value in values:
                with self.subTest(name=name,value=value),patch.dict(os.environ,{name:value}):
                    with self.assertRaisesRegex(module.ArchiveDenied,'invalid_size_policy'):self.prepare()
        self.assertFalse((self.download/'InputData.zip').exists())

    def test_failed_partial_is_preserved_but_never_promoted(self):
        with patch.object(module,'MAX_COMPRESSED',10):
            with self.assertRaisesRegex(module.ArchiveDenied,'compressed_limit'):self.prepare()
        partials=list(self.download.glob('.InputData.zip.*.partial'))
        self.assertEqual(len(partials),1)
        original=partials[0].read_bytes()
        self.assertFalse((self.download/'InputData.zip').exists())
        self.prepare()
        self.assertEqual(partials[0].read_bytes(),original)

    def test_changed_original_during_streaming_denies_promotion(self):
        original=module._file_parts
        count=0
        def changed(path):
            nonlocal count
            if Path(path)==self.daily:
                count+=1
                if count==2:
                    yield b'changed after preverification'
                    return
            yield from original(path)
        with patch.object(module,'_file_parts',side_effect=changed):
            with self.assertRaisesRegex(module.ArchiveDenied,'original_hash'):self.prepare()
        self.assertFalse((self.download/'InputData.zip').exists())
        self.assertEqual(len(list(self.download.glob('.InputData.zip.*.partial'))),1)

    def test_default_small_archive_bytes_remain_identical_to_original_format(self):
        payloads={'NativeOpeningInput.json':self.opening.read_bytes(),
            'NativeDailyInput.json':self.daily.read_bytes(),
            'NativeCapturedInput.json':module._canonical(self.captured),
            'NativeInputSchema.json':module._canonical(self.run.input_payload)}
        manifest=dict(module._pins(self.run,self.captured),files={name:dict(bytes=len(raw),
            sha256=module._sha(raw)) for name,raw in payloads.items()})
        payloads['manifest.json']=module._canonical(manifest)
        reference=io.BytesIO()
        import stat
        with zipfile.ZipFile(reference,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            for name,raw in payloads.items():
                info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=(stat.S_IFREG|0o440)<<16
                archive.writestr(info,raw)
        result=self.prepare()
        self.assertEqual(Path(result['path']).read_bytes(),reference.getvalue())

    def test_command_is_in_production_export(self):
        from release.export import included
        self.assertTrue(included('mta/runtime/management/commands/prepare_native_input_archive.py'))


if __name__=='__main__':unittest.main()
