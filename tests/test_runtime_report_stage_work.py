"""Private filesystem/typed plan proof; native publication is separate."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from mta.application import runtime_report_configuration as configuration
from mta.runtime import runtime_report_stage_work as stage
from mta.runtime.runtime_report_candidates import verify
from mta.runtime.runtime_report_request import configuration as captured_configuration
from tests import test_runtime_report_postbtr_inputs as fixture_module
from tests.test_runtime_report_request import fixture


class StageWorkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_module.PostBtrInputTests.setUpClass()
        source=fixture_module.PostBtrInputTests()
        boundary,sources=source.boundary(True)
        cls.bundle=source.build(boundary,sources)
        cls.config,_,cls.anchor,_=captured_configuration(fixture())

    def arguments(self,root):
        return dict(root=root,report_configuration=self.config,placement='PostBTR',
            variables=dict(ReportsDownloadLoc='download',TotalReqReport='TotalReqReport_2037-04-10'),
            last_generated=configuration.last_generated(self.config),previous_catalogue={},
            previous_digest=None,sources=self.bundle['sources'],descriptors=self.bundle['descriptors'],
            owner=dict(kind='explicit-local-test-only',run_id='10000000-0000-4000-8000-000000000001',
                       hook='test-no-op',cut='before-generic-final'))

    def test_six_actual_projections_materialize_then_recover_exact_candidate(self):
        with TemporaryDirectory() as directory:
            args=self.arguments(Path(directory));work=stage.prepare(**args)
            self.assertEqual([x['report_id'] for x in work.candidate['reports']],[2,3,4,5,6,8])
            self.assertEqual(len(work.source_manifest['images']),len(self.bundle['sources']))
            recovered=stage.prepare(**args,candidate_id=work.candidate_id,
                expected_candidate_digest=work.candidate['digest'])
            self.assertEqual(work.candidate,recovered.candidate)
            self.assertEqual(work.source_manifest,recovered.source_manifest)
            self.assertEqual(work.catalogue,recovered.catalogue)
            for report in work.candidate['reports']:
                if report['report_id'] in (2,3):
                    self.assertEqual(len(report['write'][0]['members']),1)
                else:self.assertEqual(report['write'][0]['members'],[])

    def test_changed_owner_or_source_cannot_reuse_candidate(self):
        with TemporaryDirectory() as directory:
            args=self.arguments(Path(directory));work=stage.prepare(**args)
            changed=dict(args,owner=dict(args['owner'],cut='terminal-substitution'))
            with self.assertRaises(ValueError):
                stage.prepare(**changed,candidate_id=work.candidate_id,
                    expected_candidate_digest=work.candidate['digest'])
            sources={name:list(rows) for name,rows in args['sources'].items()}
            sources['BPR/ColorSequence']=deepcopy(sources['BPR/ColorSequence'])
            sources['BPR/ColorSequence'][0]['SequenceNo']=42
            with self.assertRaises(ValueError):
                stage.prepare(**dict(args,sources=sources),candidate_id=work.candidate_id,
                    expected_candidate_digest=work.candidate['digest'])
            self.assertEqual(verify(root=args['root'],candidate_id=work.candidate_id,
                expected_digest=work.candidate['digest']),work.candidate)

    def test_empty_stage_retains_catalogue_and_names_without_source_substitution(self):
        with TemporaryDirectory() as directory:
            args=self.arguments(Path(directory));previous=stage.prepare(**args)
            final=stage.prepare(**dict(args,placement='Final',sources={},descriptors={},
                last_generated=previous.candidate['last_generated_after'],
                previous_catalogue=previous.catalogue,previous_digest=previous.candidate['digest']))
            self.assertEqual(final.catalogue,previous.catalogue)
            self.assertEqual(final.candidate['reports'],[])
            self.assertEqual(final.source_manifest['images'],{})
            self.assertEqual(final.candidate['last_generated_after'],previous.candidate['last_generated_after'])
            self.assertEqual(verify(root=args['root'],candidate_id=previous.candidate_id,
                expected_digest=previous.candidate['digest']),previous.candidate)

    def test_file_failure_never_overwrites_prior_candidate(self):
        with TemporaryDirectory() as directory:
            args=self.arguments(Path(directory));previous=stage.prepare(**args)
            with patch.object(stage.candidates.runtime_files,'publish',side_effect=OSError('injected file failure')):
                with self.assertRaisesRegex(OSError,'injected'):
                    stage.prepare(**dict(args,last_generated=previous.candidate['last_generated_after'],
                        previous_catalogue=previous.catalogue,previous_digest=previous.candidate['digest']))
            self.assertEqual(verify(root=args['root'],candidate_id=previous.candidate_id,
                expected_digest=previous.candidate['digest']),previous.candidate)

    def test_missing_or_extra_source_denied_before_files_are_created(self):
        with TemporaryDirectory() as directory:
            args=self.arguments(Path(directory));sources=dict(args['sources']);sources.pop('BPR/ColorSequence')
            with self.assertRaises(ValueError):stage.prepare(**dict(args,sources=sources))
            self.assertEqual(list(Path(directory).iterdir()),[])
            with self.assertRaises(ValueError):
                stage.prepare(**dict(args,placement='Final'))
            self.assertEqual(list(Path(directory).iterdir()),[])

    def test_mutation_before_persistence_is_denied_before_first_write(self):
        with TemporaryDirectory() as directory:
            args=self.arguments(Path(directory))
            sources={name:deepcopy(list(rows)) for name,rows in args['sources'].items()}
            work=stage.prepare(**dict(args,sources=sources))
            sources['BPR/ColorSequence'][0]['SequenceNo']=42
            with patch.object(stage.images,'write') as writer:
                with self.assertRaisesRegex(ValueError,'changed after preparation'):
                    stage.persist_sources(None,work)
                writer.assert_not_called()
