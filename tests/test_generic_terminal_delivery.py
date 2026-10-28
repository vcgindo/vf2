"""Terminal storage/dispatch contracts; real persisted proof is separate."""
import io
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
import django
django.setup()
from mta.presentation import generic_terminal_delivery as terminal
from mta.presentation import pick_downloads as pick


class GenericTerminalDeliveryTests(unittest.TestCase):
    def test_only_captured_generic_split_contract_routes(self):
        from mta.runtime.production_scope_policy import SCHEMA
        value=dict(scope='UptoBPR',dispositions={'schema':SCHEMA})
        self.assertTrue(terminal.applicable(None,{'scope_request':value}))
        for scope in ('Full','PostBPR',None):
            self.assertFalse(terminal.applicable(None,{'scope_request':{**value,'scope':scope}}))
        self.assertFalse(terminal.applicable(None,{}))
        self.assertFalse(terminal.applicable(None,{'scope_request':{**value,'dispositions':{'schema':'historical'}}}))

    def test_separate_archive_directory_and_same_read_locator(self):
        with TemporaryDirectory() as directory,patch.object(terminal,'binding') as validate:
            run=SimpleNamespace(pk='own-run');root=Path(directory)
            files=root/'own-run'/'scope-pick'/'phase'/'identity'/'download'
            files.mkdir(parents=True)
            original={name:b'unchanged' for name in pick.REPORTS.values()}
            for name,raw in original.items():(files/name).write_bytes(raw)
            target=terminal.archive_path(run,{'pick_output_root':directory},create=True)
            self.assertEqual(target,root/'own-run'/'native-input'/'InputData.zip')
            target.write_bytes(b'zip bytes')
            self.assertEqual(terminal.archive_path(run,{'pick_output_root':directory}),target)
            self.assertEqual({p.name:p.read_bytes() for p in files.iterdir()},original)
            self.assertFalse((root/'own-run'/'download').exists())
            validate.assert_called()
            with self.assertRaises(ValueError):
                terminal.archive_path(SimpleNamespace(pk='../escape'),{'pick_output_root':directory},create=True)

    def test_missing_owner_and_bytes_or_scope_differ_fail_closed(self):
        run=SimpleNamespace(pk='own');view=SimpleNamespace(phase=SimpleNamespace(pk='phase',digest='digest'))
        with patch.object(terminal,'binding',return_value=view), \
             patch.object(pick,'_complete_state',return_value={'typed':'state'}), \
             patch.object(pick,'_fully_scoped',return_value=True) as scope, \
             patch.object(pick,'_expected_chunks',return_value=[b'actual']), \
             patch('mta.runtime.scoped_pick_files.open_file',return_value=io.BytesIO(b'actual')) as owned:
            stream,name=terminal.open_report(run,{},'LogisticPickListReport')
            self.assertEqual(stream.read(),b'actual');stream.close()
            self.assertEqual(name,pick.REPORTS['LogisticPickListReport'])
            owned.assert_called_once_with('phase',name,expected_digest='digest')
            owned.return_value=io.BytesIO(b'actual EXTRA')
            with self.assertRaises(pick.PickDownloadDenied):terminal.open_report(run,{},'LogisticPickListReport')
            self.assertTrue(owned.return_value.closed)
            scope.return_value=False;owned.reset_mock()
            with self.assertRaises(pick.PickDownloadDenied):terminal.open_report(run,{},'LogisticPickListReport')
            owned.assert_not_called()
        with patch.object(terminal,'binding',side_effect=ValueError('wrong owner')):
            with self.assertRaises(ValueError):terminal.open_report(run,{},'LogisticPickListReport')


if __name__=='__main__':unittest.main()
