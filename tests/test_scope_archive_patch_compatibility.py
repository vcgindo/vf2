"""Production v1 file custody across metadata patches; no database or business calls."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','scope-archive-patch-unit-only')
import django
django.setup()
from contextlib import ExitStack
from copy import deepcopy
from datetime import date
import hashlib
import inspect
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import zipfile

from mta.presentation import scoped_artifacts as archive, scoped_batch_files as batch, scoped_batch_downloads as downloads
from mta.presentation.context import PublicationUnavailable
from mta.runtime import production_scope_policy as policy
from mta.serialization import digest
from tests import test_scoped_batch_files as batch_fixture


def sha(raw):return hashlib.sha256(raw).hexdigest()


def disposition():
    return dict(schema=policy.SCHEMA,purpose=policy.PURPOSE,site_code='SITE',
        hooks={name:policy.MODE for name in policy.HOOKS},input_download='enabled-five-file-four-table-archive',
        authority='Explicit unit generic policy')


class ScopeArchivePatchCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch('django.db.backends.base.base.BaseDatabaseWrapper.connect',
                                side_effect=AssertionError('Database forbidden')))

    def test_production_recipes_avoid_native_alias_and_track_actual_codecs(self):
        from mta.runtime import retained_registered_execution_compatibility as historical
        from mta.application import operational_sqlcmd
        original=inspect.getsource
        with patch.object(historical,'_recipe_sources',side_effect=AssertionError('Whole-native dependency forbidden')):
            before=(archive._recipe(production=True),batch.recipe_digest(production=True))
            # A metadata module outside the producer dependency set cannot be
            # consulted, whereas changing the actual encoder changes identity.
            def metadata_patch(module):
                if module.__name__.endswith(('ingestion_admission','upgrade_database')):
                    raise AssertionError('Unrelated admission source was consulted')
                return original(module)
            with patch('inspect.getsource',side_effect=metadata_patch):
                self.assertEqual(before,(archive._recipe(production=True),batch.recipe_digest(production=True)))
            def encoder_patch(module):
                return original(module)+('\n# changed actual encoder\n' if module is operational_sqlcmd else '')
            with patch('inspect.getsource',side_effect=encoder_patch):
                after=(archive._recipe(production=True),batch.recipe_digest(production=True))
            self.assertNotEqual(before[0],after[0]);self.assertNotEqual(before[1],after[1])
            for recipe in (archive._recipe,batch.recipe_digest):
                with self.assertRaisesRegex(AssertionError,'Whole-native'):recipe()

    def test_archive_recipe_tracks_actual_transit_columns_and_typed_value_decoder(self):
        from mta.runtime import operational_archive,relational_state
        before=archive._recipe(production=True)
        columns=deepcopy(operational_archive.TRANSIT_COLUMNS)
        columns[0]['nullable']=not columns[0]['nullable']
        with patch.object(operational_archive,'TRANSIT_COLUMNS',columns):
            self.assertNotEqual(before,archive._recipe(production=True))
        original=inspect.getsource
        def changed_codec(value):
            return original(value)+('\n# typed conversion drift\n' if value is relational_state.wire_value else '')
        with patch('inspect.getsource',side_effect=changed_codec):
            self.assertNotEqual(before,archive._recipe(production=True))

    def archive_fixture(self,parent,*,production=True):
        root=Path(parent)/'artifact';declaration=Path(parent)/'declaration.json'
        value=dict(schema=archive.PRODUCTION_SCHEMA,purpose=policy.PURPOSE,
            run_id='10000000-0000-4000-8000-000000000001',phase_id='20000000-0000-4000-8000-000000000002',
            phase_digest='a'*64,input_digest='b'*64,input_manifest_digest='c'*64,
            site_code='SITE',post_bpr_hook=policy.MODE,input_download=True,importer_database='owned_mta',
            physical_files=list(archive.PHYSICAL),input_tables=list(archive.TABLES),
            archive_clock='business-midnight-Asia-Kolkata',authority='Explicit unit generic policy')
        if not production:
            value.update(schema=archive.SCHEMA,purpose='owned-scoped-test',site_code='SUPPLIED-INSTANCE',
                         post_bpr_hook='explicit-test-no-op',importer_database='VFTEST_Fresh_Unit')
        declaration.write_bytes(json.dumps(value).encode());pin=sha(declaration.read_bytes())
        phase=NS(pk=value['phase_id'],run_id=value['run_id'],snapshot=NS(state_digest='d'*64),
                 run=NS(business_date=date(2026,10,24)))
        self.enterContext(patch.object(archive,'_bind',return_value=phase))
        self.enterContext(patch.object(archive,'_root',return_value=root))
        physical={name:b'physical\r\n' for name in archive.PHYSICAL}
        exports={value['importer_database']+'_'+name+'.CSV':b'NULL,2\r\n' for name in archive.TABLES}
        self.enterContext(patch.object(archive,'payloads',return_value=(physical,exports,{'sealed':'producer'})))
        receipt=archive.prepare(value['phase_id'],expected_digest=value['phase_digest'],
            declaration_file=declaration,declaration_sha256=pin)
        def read(**changes):
            arguments=dict(expected_digest=value['phase_digest'],declaration_file=declaration,
                           declaration_sha256=pin,receipt_sha256=receipt['receipt_sha256'])
            arguments.update(changes)
            return archive.verify(value['phase_id'],**arguments)
        return root,value,receipt,read

    def test_production_pinned_archive_keeps_original_recipe_without_producer_reentry(self):
        with TemporaryDirectory() as parent:
            root,value,receipt,read=self.archive_fixture(parent)
            with patch.object(archive,'_recipe',side_effect=AssertionError('Reader must not produce')), \
                    patch.object(archive,'payloads',side_effect=AssertionError('Reader must not produce')):
                self.assertEqual(read()['recipe_digest'],receipt['recipe_digest'])
            with patch.object(archive,'_recipe',return_value='f'*64):
                self.assertEqual(read(receipt_sha256=None)['recipe_digest'],receipt['recipe_digest'])
            with patch.object(archive,'payloads',return_value=({}, {}, {'changed':'producer'})):
                with self.assertRaisesRegex(ValueError,'producer bytes differ'):read(receipt_sha256=None)
            path=root/'artifact.json';stored=json.loads(path.read_bytes());stored['declaration']['authority']='changed'
            path.write_bytes(json.dumps(stored).encode())
            with self.assertRaisesRegex(ValueError,'independently pinned'):read()
            with self.assertRaisesRegex(ValueError,'receipt owner'):read(receipt_sha256=sha(path.read_bytes()))

    def test_production_archive_unknown_shape_recipe_and_re_pinned_bad_member_deny(self):
        for defect in ('schema','field','recipe','member','member-field','download-field'):
            with self.subTest(defect=defect),TemporaryDirectory() as parent:
                root,value,receipt,read=self.archive_fixture(parent)
                path=root/'artifact.json';stored=json.loads(path.read_bytes())
                if defect=='schema':stored['schema']='future-format'
                elif defect=='field':stored['unexpected']=True
                elif defect=='recipe':stored['recipe_digest']='not-a-sha'
                elif defect=='member-field':next(iter(stored['members'].values()))['unexpected']=True
                elif defect=='download-field':stored['download']['unexpected']=True
                else:
                    target=root/'download/InputData.zip';target.unlink()
                    with zipfile.ZipFile(target,'x') as output:
                        for name in stored['members']:output.writestr(name,b'changed')
                    stored['download'].update(size_bytes=target.stat().st_size,sha256=sha(target.read_bytes()))
                path.write_bytes(json.dumps(stored).encode())
                with self.assertRaises(ValueError):read(receipt_sha256=sha(path.read_bytes()))

    def test_test_archive_keeps_current_recipe_equality_even_with_independent_pin(self):
        with TemporaryDirectory() as parent,patch.object(archive,'_recipe',return_value='e'*64):
            root,value,receipt,read=self.archive_fixture(parent,production=False)
            with patch.object(archive,'_recipe',return_value='f'*64):
                with self.assertRaisesRegex(ValueError,'receipt owner'):read()

    def batch_fixture(self,parent):
        helper=batch_fixture.ScopedBatchFilesTests();phase,bags=helper.fixture()
        root=Path(parent)/'batch'
        with helper.context(phase,bags),patch('mta.runtime.input_reader.read_input',return_value={'scope_request':{'dispositions':disposition()}}):
            metadata,paths=batch.prepare('phase',expected_digest='phase-digest',declaration=deepcopy(batch.PRODUCTION_DECLARATION),root=root)
        def read(pin=None):
            with patch('mta.runtime.scope_runtime_reports.require_test_database'),patch.object(downloads.scoped_sources,'_accepted_phase',return_value=phase), \
                    patch('mta.runtime.input_reader.read_input',return_value={'scope_request':{'dispositions':disposition()}}):
                return downloads.verify('phase',expected_digest='phase-digest',expected_run_id='run',expected_snapshot_digest='snapshot',
                    manifest_file=root/'scoped-batch-files.json',manifest_sha256=pin or sha((root/'scoped-batch-files.json').read_bytes()))
        return root,metadata,read

    def rewrite_batch(self,root,change):
        path=root/'scoped-batch-files.json';value=json.loads(path.read_bytes());change(value)
        value['payload_digest']=digest({k:v for k,v in value.items() if k not in ('digest','payload_digest','files','wrappers')})
        value['digest']=digest({k:v for k,v in value.items() if k!='digest'})
        path.write_bytes(json.dumps(value).encode())

    def test_production_batch_old_recipe_reads_and_test_recipe_stays_strict(self):
        with TemporaryDirectory() as parent:
            root,metadata,read=self.batch_fixture(parent)
            with patch.object(batch,'recipe_digest',side_effect=AssertionError('Producer forbidden')), \
                    patch.object(batch,'payload',side_effect=AssertionError('Producer forbidden')):
                self.assertEqual(read()['recipe_digest'],metadata['recipe_digest'])
            self.rewrite_batch(root,lambda value:value.update(declaration=deepcopy(batch.TEST_DECLARATION)))
            with patch.object(batch,'recipe_digest',return_value='f'*64),self.assertRaises(PublicationUnavailable):read()

    def test_production_batch_shape_pin_source_and_file_tampering_deny(self):
        for defect in ('schema','field','recipe','declaration','source','file','pin'):
            with self.subTest(defect=defect),TemporaryDirectory() as parent:
                root,metadata,read=self.batch_fixture(parent)
                if defect=='pin':
                    with self.assertRaises(PublicationUnavailable):read('0'*64)
                    continue
                if defect=='file':(root/downloads.DOWNLOAD).write_bytes(b'changed')
                elif defect=='schema':self.rewrite_batch(root,lambda value:value.update(schema='future-format'))
                elif defect=='field':self.rewrite_batch(root,lambda value:value.update(unexpected=True))
                elif defect=='recipe':self.rewrite_batch(root,lambda value:value.update(recipe_digest='not-a-sha'))
                elif defect=='declaration':self.rewrite_batch(root,lambda value:value['declaration'].update(IsMTOEnvironment=True))
                else:self.rewrite_batch(root,lambda value:value['sources']['state/importer/MasterData'].update(rows_digest='f'*64))
                with self.assertRaises(PublicationUnavailable):read()

