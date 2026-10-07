"""Recovery and owner checks without launching either engine."""
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tools import offline_temporal_validation as runner


class OfflineRunnerTests(unittest.TestCase):
    def test_identical_selection_receipt_is_reused_and_different_one_denied(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'selection.json'
            runner.retain_selection(path,{'run':'first'})
            original=path.read_bytes()
            runner.retain_selection(path,{'run':'first'})
            self.assertEqual(path.read_bytes(),original)
            with self.assertRaisesRegex(ValueError,'differs'):
                runner.retain_selection(path,{'run':'second'})
            self.assertEqual(path.read_bytes(),original)

    def test_restored_publication_is_not_reported_as_selected(self):
        with TemporaryDirectory() as directory:
            folder=Path(directory)
            runner.save(folder/'selection.json',dict(selected_compose_sha256='new',previous_compose_sha256='old'))
            runner.save(folder/'restoration-a001.json',dict(status='RESTORED',selection_sha256='selection',restored_compose_sha256='old'))
            with patch.object(runner,'sha',side_effect=lambda p:'selection' if Path(p).name=='selection.json' else 'old'):
                self.assertEqual(runner.publication_state(folder),'trial verified; previous selection restored')
            with patch.object(runner,'sha',return_value='unknown'):
                self.assertEqual(runner.publication_state(folder),'selection differs; reconciliation required')

    def test_readiness_waits_for_startup_but_is_bounded(self):
        with patch.object(runner,'command') as command, patch.object(runner,'last_json',return_value={'ready':True}):
            runner.readiness(Path('unused.log'))
        code=command.call_args.args[0][-1]
        import io
        from urllib.error import URLError
        with patch('urllib.request.urlopen',side_effect=[URLError('refused'),io.BytesIO(b'{"ready":true}')]) as probe, patch('time.sleep'):
            exec(code,{})
            self.assertEqual(probe.call_count,2)
        with patch('urllib.request.urlopen',side_effect=URLError('refused')), patch('time.monotonic',side_effect=[0,181]):
            with self.assertRaisesRegex(RuntimeError,'180 seconds'):
                exec(code,{})

    def test_recovery_baseline_allows_only_approved_start_time_changes(self):
        with TemporaryDirectory() as directory:
            folder=Path(directory)
            runner.save(folder/'protected-before.json',{'service':dict(started='old',id='same',image='same')})
            runner.save(folder/'external-recovery-snapshot-001.json',{'service':dict(started='new',id='same',image='same')})
            runner.save(folder/'approved-recovery-baseline.json',dict(
                approval='01a115f2-5d87-7c73-a163-e1012432582c',
                original_sha256=runner.sha(folder/'protected-before.json'),
                recovered_sha256=runner.sha(folder/'external-recovery-snapshot-001.json')))
            self.assertEqual(runner.protected_baseline(folder)['service']['started'],'new')
            changed={'service':dict(started='new',id='different',image='same')}
            with patch.object(runner,'load',side_effect=lambda p: changed if Path(p).name=='external-recovery-snapshot-001.json' else __import__('json').loads(Path(p).read_text())):
                with self.assertRaisesRegex(ValueError,'start-time-only'):
                    runner.protected_baseline(folder)

    def test_approved_runner_transition_rejects_other_source_changes(self):
        with TemporaryDirectory() as directory:
            folder=Path(directory)
            name='tools/offline_temporal_validation.py'
            before='3c3f6d083d72734ccf22d68128fed829f2803fd1128dfb94a7b25b60fc2a7718'
            package=dict(execution_id='temporal-smoke-001',sources={name:before,'mta/engine.py':'engine'})
            transition=dict(schema='fresh-approved-runner-transition-v1',
                approval='call_YuWeGF0oMf7XIT15hu0ZnYmU',execution_id='temporal-smoke-001',
                package_sha256='package',path=name,before=before,after='new')
            runner.save(folder/'runner-transition.json',transition)
            def digest(path):
                return {'package.json':'package','frozen-runner-001.py':before,'runner-transition.json':'receipt'}[Path(path).name]
            with patch.object(runner,'sha',side_effect=digest), patch.object(runner,'sources',return_value={name:'new','mta/engine.py':'engine'}):
                self.assertEqual(runner.require_package_sources(folder,package),'receipt')
            with patch.object(runner,'sha',side_effect=digest), patch.object(runner,'sources',return_value={name:'new','mta/engine.py':'changed'}):
                with self.assertRaisesRegex(ValueError,'approved runner transition'):
                    runner.require_package_sources(folder,package)

    def test_parity_attachment_receives_execution_file_not_directory(self):
        with TemporaryDirectory() as directory:
            folder=Path(directory); modern=folder/'modern-000-a001'; legacy=folder/'legacy-000-a001'
            runner.save(folder/'protected-before.json',{})
            def latest(_,pattern,*args,**kwargs):
                return modern if pattern.startswith('modern') else legacy if pattern.startswith('legacy') else None
            def compare(args,log):
                target=Path(args[args.index('--destination')+1]); target.mkdir()
                runner.save(target/'replay.json',{'status':'PASS'})
                runner.save(target/'rrr-source.json',{'status':'PASS'})
            with patch.object(runner,'latest',side_effect=latest), \
                    patch.object(runner,'modern_day',return_value=modern), \
                    patch.object(runner,'bounded_legacy_command',side_effect=compare), \
                    patch.object(runner,'worker') as worker, \
                    patch.object(runner,'container_path',side_effect=lambda p:str(p)), \
                    patch.object(runner,'summary',return_value={}), \
                    patch('tools.daily_stack_setup.snapshot',return_value={}):
                runner.execute_locked(SimpleNamespace(mode='combined',execution_id='sample'),folder,
                    {'input':{'execution_through':0},'scenario':'trial','execution_id':'sample'})
            attached=next(call.args[1] for call in worker.call_args_list if call.args[1][0]=='record_parity')
            self.assertEqual(attached[attached.index('--modern-execution')+1],str(modern/'execution.json'))

    def test_failed_attempt_is_retained_and_next_attempt_is_new(self):
        with TemporaryDirectory() as directory:
            folder=Path(directory)
            first=runner.next_attempt(folder,'modern-000')
            with patch.object(runner.subprocess,'run') as run:
                run.return_value.returncode=17
                with self.assertRaisesRegex(RuntimeError,'17'):
                    runner.command(['worker'],first.with_suffix('.log'))
            self.assertTrue(first.with_suffix('.log').exists())
            self.assertEqual(runner.next_attempt(folder,'modern-000').name,'modern-000-a002')

    def test_successful_modern_is_reused_after_separate_legacy_failure(self):
        with TemporaryDirectory() as directory:
            folder=Path(directory); modern=folder/'modern-000-a001'; modern.mkdir()
            runner.save(modern/'execution.json',dict(computation_only=False,
                days=[dict(status='COMPUTED_NOT_YET_PARITY')]))
            (folder/'legacy-000-a001.log').write_text('SQL unavailable')
            with patch.object(runner,'worker') as worker:
                self.assertEqual(runner.modern_day(folder,{},0,None,'combined'),modern)
                worker.assert_not_called()
                with self.assertRaisesRegex(ValueError,'mode differs'):
                    runner.modern_day(folder,{},0,None,'modern-only')

    def test_source_cannot_be_adopted_from_another_owner(self):
        with TemporaryDirectory() as directory:
            folder=Path(directory)
            runner.save(folder/'mdm-source.json',dict(owner='another',artifact_sha256='same',id=1,digest='d'))
            with patch.object(runner,'worker') as worker:
                with self.assertRaisesRegex(ValueError,'another execution'):
                    runner.modern_day(folder,dict(execution_id='mine',input=dict(sha256='same')),0,None,'combined')
                worker.assert_not_called()

    def test_owned_paths_and_summary_ids_are_bounded(self):
        for invalid in ('../another','UPPER','x','x/../../other'):
            with self.assertRaises(ValueError):
                runner.owned(invalid)
        with TemporaryDirectory() as directory:
            folder=Path(directory)
            runner.save(folder/'summary-a001.json',{'failure':'retained'})
            self.assertEqual(runner.next_attempt(folder,'summary').name,'summary-a002')
