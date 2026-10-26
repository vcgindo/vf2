"""Actual candidate files, recovery boundaries and catalogue visibility."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from unittest import TestCase
from uuid import uuid4

from mta.application.runtime_report_configuration import SCHEMA, last_generated
from mta.application.runtime_report_projection import describe
from mta.runtime import runtime_report_candidates as candidates
from tests.test_runtime_report_files import row, writer, VARIABLES
from tests.test_runtime_demand_reports import sources as total_sources
from mta.application.runtime_demand_reports import SPIKE_FIELDS


def spike(quantity=2):
    value = dict.fromkeys(SPIKE_FIELDS)
    value.update(OrderKey=1, CustomerOrderId='order', PartId=2, IsSpike=True,
                 IsElephant=False, OriginalQty=quantity, Qty=quantity, SKUCode='S', WhCode='W')
    return value


def arguments(definitions=None):
    definitions = definitions if definitions is not None else [row(7), row(10)]
    inputs = {}
    for definition in definitions:
        spec = describe(definition)
        values = {'spike_order_data': [spike(), spike()]} if spec['captured_source_id'] == 7 else total_sources()
        inputs[definition['Id']] = dict(sources={logical:values[key] for key,logical in spec['sources'].items()},
            provenance=dict(query_sha256=spec['query_sha256'], unit_source=True))
    config = dict(schema=SCHEMA, RuntimeReports=definitions, DownloadableUIReportSettings=[])
    return dict(report_configuration=config, last_generated=last_generated(config), placement='PostBPR',
                variables=VARIABLES, inputs=inputs, archive_writer=writer)


class RuntimeReportCandidateTests(TestCase):
    def test_streamed_source_projection_files_and_exact_completed_readback(self):
        with tempfile.TemporaryDirectory() as root:
            identity = str(uuid4())
            result = candidates.materialize(root=root, candidate_id=identity, **arguments())
            self.assertEqual([r['report_id'] for r in result['reports']], [7,10])
            self.assertEqual(len(result['files']), 4)
            self.assertNotIn('output/Spiker_Order_Dump.csv', result['files'])
            archive = result['files']['download/Spiker_Order_Dump.zip']
            self.assertEqual([m['name'] for m in archive['members']], ['Spiker_Order_Dump.csv'])
            self.assertGreater(archive['members'][0]['size_bytes'], 0)
            self.assertEqual(candidates.verify(root=root, candidate_id=identity,
                                              expected_digest=result['digest']), result)
            self.assertEqual(result['reports'][1]['last_generated_file_name'], VARIABLES['TotalReqReport'])

    def test_catalogue_cleanup_preserves_prior_bytes_and_delete_old_false_keeps_visibility(self):
        for delete_old in (True, False):
            with tempfile.TemporaryDirectory() as root:
                definition = row(10); definition.update(LastGeneratedFileName=None, DeleteOldFile=delete_old)
                args = arguments([definition]); frozen = deepcopy(args['report_configuration'])
                args['variables'] = dict(VARIABLES, TotalReqReport='Old')
                first = candidates.materialize(root=root, candidate_id=str(uuid4()), **args)
                before = {str(p.relative_to(root)):p.read_bytes() for p in Path(root).rglob('*') if p.is_file()}
                args.update(variables=dict(VARIABLES, TotalReqReport='New'), last_generated=first['last_generated_after'])
                second = candidates.materialize(root=root, candidate_id=str(uuid4()), **args)
                self.assertEqual(first['configuration_digest'], second['configuration_digest'])
                self.assertEqual(args['report_configuration'], frozen)
                self.assertEqual(second['last_generated_before'], [{'Id':10,'LastGeneratedFileName':'Old'}])
                self.assertEqual(second['last_generated_after'], [{'Id':10,'LastGeneratedFileName':'New'}])
                catalog = candidates.catalog_changes(candidates.catalog_changes({}, first), second)
                self.assertNotIn('output/Old.csv', catalog)
                self.assertEqual('download/Old.csv' in catalog, not delete_old)
                for path, value in before.items():self.assertEqual(Path(root,path).read_bytes(), value)
                self.assertEqual(catalog['download/New.csv']['candidate_id'], second['candidate_id'])

    def test_late_failure_leaves_orphan_and_new_candidate_retries_without_touching_prior(self):
        with tempfile.TemporaryDirectory() as root:
            args = arguments([row(7)])
            prior = candidates.materialize(root=root, candidate_id=str(uuid4()), **args)
            bad = deepcopy(args)
            bad['inputs'][7]['sources']['BPR/SpikeOrderData'].append(spike('bad integer'))
            failed = str(uuid4())
            with self.assertRaises(ValueError):candidates.materialize(root=root,candidate_id=failed,**bad)
            self.assertTrue(Path(root, failed, 'output/Spiker_Order_Dump.csv').exists())
            self.assertFalse(Path(root, failed, candidates.MANIFEST).exists())
            with self.assertRaises(FileExistsError):candidates.materialize(root=root,candidate_id=failed,**args)
            retry = candidates.materialize(root=root,candidate_id=str(uuid4()),**args)
            self.assertEqual(retry['files']['output/Spiker_Order_Dump.zip']['members'],
                             prior['files']['output/Spiker_Order_Dump.zip']['members'])
            self.assertEqual(candidates.verify(root=root,candidate_id=prior['candidate_id'],
                                              expected_digest=prior['digest']),prior)

    def test_completed_candidate_is_not_overwritten_and_tampering_denies(self):
        for mutation in ('bytes','extra','manifest','digest'):
            with tempfile.TemporaryDirectory() as root:
                identity = str(uuid4())
                args = arguments([row(10)])
                result = candidates.materialize(root=root,candidate_id=identity,**args)
                with self.assertRaises(FileExistsError):candidates.materialize(root=root,candidate_id=identity,**args)
                directory = Path(root,identity)
                expected = result['digest']
                if mutation == 'bytes':(directory/'download/TotalReqReport_2026-04-08.csv').write_bytes(b'corrupt')
                elif mutation == 'extra':(directory/'unexpected.txt').write_bytes(b'extra')
                elif mutation == 'manifest':(directory/candidates.MANIFEST).write_text('{}')
                else:expected = '0'*64
                with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                    candidates.verify(root=root,candidate_id=identity,expected_digest=expected)

    def test_exact_path_overwrite_uses_id_order_and_only_final_surviving_bytes(self):
        first, second = row(7), dict(row(7), Id=17)
        args = arguments([second, first])
        args['inputs'][17]['sources']['BPR/SpikeOrderData'] = [spike(9)]
        with tempfile.TemporaryDirectory() as root:
            result = candidates.materialize(root=root,candidate_id=str(uuid4()),**args)
            self.assertEqual([r['report_id'] for r in result['reports']],[7,17])
            self.assertEqual(len(result['files']),2)
            self.assertNotEqual(result['reports'][0]['write'][0]['members'], result['reports'][1]['write'][0]['members'])
            self.assertEqual(result['files']['output/Spiker_Order_Dump.zip'],result['reports'][1]['write'][0])

    def test_preflight_wrong_inputs_paths_or_separate_ui_producer_creates_no_directory(self):
        for change in ('source','case','ui','path'):
            args = arguments([row(7)])
            if change == 'source':args['inputs'][7]['provenance']['query_sha256']='0'*64
            elif change == 'case':
                args['last_generated'][0]['LastGeneratedFileName']='spiker_order_dump'
            elif change == 'ui':
                args['report_configuration']['DownloadableUIReportSettings']=[dict(ReportName='RRR',Active=True,
                    GenerationScope='PostBPR',DestFolder='download')]
            else:args['variables'] = dict(VARIABLES,ReportsDownloadLoc='../outside')
            with tempfile.TemporaryDirectory() as root:
                with self.subTest(change=change),self.assertRaises(ValueError):
                    candidates.materialize(root=root,candidate_id=str(uuid4()),**args)
                self.assertEqual(list(Path(root).iterdir()),[])

    def test_empty_placement_is_explicit_metadata_and_does_not_drop_prior_catalogue(self):
        with tempfile.TemporaryDirectory() as root:
            args=arguments([row(7)]);args.update(placement='PostDBM',inputs={})
            result=candidates.materialize(root=root,candidate_id=str(uuid4()),**args)
            self.assertEqual(result['files'],{})
            self.assertEqual(result['reports'],[])
            prior={'download/keep.csv':{'candidate_id':'prior','file':{'retained':True}}}
            self.assertEqual(candidates.catalog_changes(prior,result),prior)

    def test_missing_duplicate_or_wrong_filename_state_is_not_silently_reset(self):
        for value in (None, [], [{'Id':7,'LastGeneratedFileName':None}]*2,
                      [{'Id':99,'LastGeneratedFileName':None}]):
            args = arguments([row(7)]); args['last_generated'] = value
            with tempfile.TemporaryDirectory() as root:
                with self.assertRaises(ValueError):
                    candidates.materialize(root=root,candidate_id=str(uuid4()),**args)
                self.assertEqual(list(Path(root).iterdir()),[])

    def test_prior_catalogue_case_alias_cannot_survive_or_evade_cleanup(self):
        with tempfile.TemporaryDirectory() as root:
            definition = dict(row(10), FileName='New', LastGeneratedFileName='Old')
            candidate = candidates.materialize(root=root,candidate_id=str(uuid4()),**arguments([definition]))
            for path in ('download/old.csv', 'download/new.csv'):
                prior = {path: {'candidate_id':'untouched', 'file':{'original':True}}}
                before = deepcopy(prior)
                with self.subTest(path=path),self.assertRaisesRegex(ValueError,'Cross-candidate'):
                    candidates.catalog_changes(prior,candidate)
                self.assertEqual(prior,before)
