"""Archive contract and fail-closed frozen compatibility for the retained failure."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from types import SimpleNamespace
import zipfile
from mta.serialization import digest
from mta.runtime import scoped_dbm_archive_recovery as recovery


class ScopedDbmArchiveRecoveryTests(unittest.TestCase):
    def test_archive_recovery_cannot_route_frozen_request_to_another_day(self):
        from mta.runtime import production_upto_dbm as entry
        for run in (None,SimpleNamespace(pk='another-run')):
            with self.subTest(run=run),patch.object(entry.transaction,'get_autocommit',return_value=True), \
                    patch.object(entry,'request',return_value={}), \
                    patch('mta.runtime.production_scope.authorize'), \
                    patch('mta.runtime.scope_runtime_reports.require_test_database'), \
                    patch.object(recovery,'resolve',return_value={}), \
                    patch('mta.runtime.production_scope.repeated',return_value=run), \
                    patch('mta.runtime.production_daily.execute') as capture,patch.object(entry,'advance') as advance:
                with self.assertRaisesRegex(ValueError,'exact retained day'):
                    entry.execute(b'input','a'*64,command_key='test',worker_reference='worker',
                        runtime_reports={},dispositions={},archive_recovery=True,initialization_id=recovery.INITIALIZATION)
                capture.assert_not_called();advance.assert_not_called()

    def test_lowercase_postgresql_name_produces_actual_native_archive(self):
        from mta.runtime.production_upto_dbm import archive_label
        from mta.application.operational_input_archive import write_input_archive
        from mta.application.operational_io import inspect_file
        from mta.application.operational_inputs import PHYSICAL_TABLES
        label=archive_label('vftest_fresh_retained_owned')
        self.assertEqual(label.casefold(),'vftest_fresh_retained_owned')
        def writer(*,root,staging,members,destination):
            target=Path(root)/destination;target.parent.mkdir(parents=True,exist_ok=True)
            with zipfile.ZipFile(target,'w') as archive:
                for name in members:archive.write(Path(root)/staging/name,arcname=name)
            return dict(inspect_file(root,destination),members=members)
        with TemporaryDirectory() as root:
            physical={name+'.csv':b'raw\r\n' for name in (*PHYSICAL_TABLES,'InTransitRaw')}
            exports={label+'_'+name+'.CSV':b'typed\r\n' for name in PHYSICAL_TABLES}
            result=write_input_archive(root,physical=physical,table_exports=exports,importer_database=label,
                business_date='2026-10-25',archive_writer=writer)
            with zipfile.ZipFile(Path(root)/'download/InputData.zip') as archive:
                self.assertEqual(set(archive.namelist()),set(physical)|set(exports)|{result['marker']})
                self.assertEqual(len(archive.namelist()),10)
                for name,raw in {**physical,**exports}.items():self.assertEqual(archive.read(name),raw)
            self.assertTrue(result['staging_removed'])
        for name in ('production','vftest_fresh_','vftest_fresh_x/other'):
            with self.assertRaises(ValueError):archive_label(name)

    def test_source_boundary_rejects_any_other_change_addition_or_entry_omission(self):
        files=dict.fromkeys(recovery.ENTRY_FILES,'a'*64)
        files['mta/temporal/chain.py']='b'*64
        with patch.object(recovery,'PROTECTED',digest({'mta/temporal/chain.py':'b'*64})):
            recovery.unchanged_sources(files)
            for changed in (dict(files,**{'mta/temporal/chain.py':'c'*64}),dict(files,**{'new.py':'d'*64}),
                    {k:v for k,v in files.items() if k!='mta/runtime/production_upto_dbm.py'}):
                with self.assertRaises(ValueError):recovery.unchanged_sources(changed)

    def test_frozen_request_rejects_changed_request_recipe_or_original_digest(self):
        request=dict(schema='fresh-native-upto-dbm-request-v1',scope='UptoDBM',command_key='retained',
            runtime_reports={'RuntimeReports':[]},dispositions={'hooks':'original'})
        recipe='c'*64
        expected=digest(dict(request=request,release=recovery.PREVIOUS,phase_recipe=recipe))
        frozen=dict(request,compatibility_digest=expected)
        current=dict(request,compatibility_digest='new-release')
        with patch.object(recovery,'COMPATIBILITY',expected):
            self.assertIs(recovery.frozen_request(frozen,current,recipe),frozen)
            for key in request:
                with self.subTest(field=key),self.assertRaises(ValueError):
                    recovery.frozen_request(frozen,dict(current,**{key:'changed'}),recipe)
            with self.assertRaises(ValueError):recovery.frozen_request(frozen,current,'changed-recipe')
            with self.assertRaises(ValueError):recovery.frozen_request(dict(frozen,compatibility_digest='changed'),current,recipe)
