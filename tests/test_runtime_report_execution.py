"""Real Full calculation + private files; native transaction authority separate."""
from copy import deepcopy
from dataclasses import replace
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch,Mock
import unittest

from mta.application.native_output_contracts import native_assignments
from mta.runtime import runtime_report_execution as execution
from mta.runtime import runtime_report_request as contract
from mta.runtime import runtime_report_stage_work as stages
from mta.serialization import digest,storage
from mta.temporal import chain
from tests.test_phase_state import native_prepared
from tests.test_daily_calculation_phases import calculation
from tests.test_runtime_report_request import fixture


class PlacementFullCalculationTests(unittest.TestCase):
    def setup_case(self,directory):
        with native_assignments(True):prepared,opening,refs=native_prepared('placement-full-calculation')
        day=refs['day'];profile=refs['profile']
        profile['daily_publication']=True;profile['delivery']['site_code']='SUPPLIED-INSTANCE'
        day.update(production_report_schema=opening['production_report_schema'],
                   production_report_opening={'BOR_OrderAllocationHistory':[],'RRR_OrderAllocationHistory':[]})
        opening['production_report_opening']=deepcopy(day['production_report_opening'])
        reference=fixture();request=contract.request('Full','pure-full-candidate',runtime_reports=reference)
        config,_hook,anchor,_policy=contract.configuration(reference)
        run=SimpleNamespace(pk='placement-full-calculation',business_date=date(2037,4,10),
            predecessor_id=None,input_digest='a'*64,input_manifest_digest='b'*64,
            scope_attempts=SimpleNamespace(exists=lambda:False))
        raw=dict(profile=profile,pick_output_root=directory,scope_request=request)
        return run,refs,opening,(raw,request,config,anchor)

    def test_complete_output_preserved_and_each_file_precedes_final(self):
        with TemporaryDirectory() as directory,patch('release.native_identity.require_current',return_value={'test':'release'}):
            run,refs,opening,config=self.setup_case(directory)
            expected=chain.calculate_day(deepcopy(refs['prior']),'2037-04-09',deepcopy(refs['day']),
                deepcopy(refs['profile']),str(run.pk),calculation,native_daily=True)
            events=[];original_work=execution._bundle_work;original_final=execution.btr_stage.finish_btr_boundary
            def work(*args,**kwargs):
                result=original_work(*args,**kwargs);events.append(args[1]);return result
            def finish(boundary):
                self.assertEqual(events,['PostImporter','PostBPR','PostDBM','PostBTR'])
                events.append('generic-final');return original_final(boundary)
            with patch.object(execution.publication,'configuration',return_value=config), \
                    patch.object(execution,'_remarks',return_value=([],{'source':'explicit-local-empty'})), \
                    patch.object(execution,'_bundle_work',side_effect=work), \
                    patch.object(execution.btr_stage,'finish_btr_boundary',side_effect=finish), \
                    patch('mta.runtime.scope_bpr_histories.complete_sources',wraps=__import__(
                        'mta.runtime.scope_bpr_histories',fromlist=['complete_sources']).complete_sources) as histories:
                actual,completion=execution.calculate_full(run,deepcopy(refs['prior']),'2037-04-09',
                    deepcopy(refs['day']),deepcopy(refs['profile']),calculation,opening=opening)
                self.assertEqual(storage(actual),storage(expected))
                self.assertEqual(digest(actual),digest(expected))
                histories.assert_called_once()
                execution.validate_completion(run,completion,scoped=False)
            self.assertEqual(completion.sources_digest,digest(completion.sources.__dict__))
            self.assertEqual([len(work.candidate['reports']) for work in completion.work],[0,2,0,6])
            self.assertEqual(events[-1],'generic-final')

    def test_postbtr_file_failure_stops_before_final_processing(self):
        with TemporaryDirectory() as directory,patch('release.native_identity.require_current',return_value={'test':'release'}):
            run,refs,opening,config=self.setup_case(directory)
            original=execution._bundle_work
            def fail(*args,**kwargs):
                if args[1]=='PostBTR':raise OSError('injected PostBTR write failure')
                return original(*args,**kwargs)
            with patch.object(execution.publication,'configuration',return_value=config), \
                    patch.object(execution,'_remarks',return_value=([],{'source':'explicit-local-empty'})), \
                    patch.object(execution,'_bundle_work',side_effect=fail), \
                    patch.object(execution.btr_stage,'finish_btr_boundary') as final:
                with self.assertRaisesRegex(OSError,'PostBTR'):
                    execution.calculate_full(run,deepcopy(refs['prior']),'2037-04-09',deepcopy(refs['day']),
                        deepcopy(refs['profile']),calculation,opening=opening)
                final.assert_not_called()

    def test_changed_complete_consumer_population_is_denied_before_publication(self):
        with TemporaryDirectory() as directory,patch('release.native_identity.require_current',return_value={'test':'release'}):
            run,refs,opening,config=self.setup_case(directory)
            with patch.object(execution.publication,'configuration',return_value=config), \
                    patch.object(execution,'_remarks',return_value=([],{'source':'explicit-local-empty'})):
                _,completion=execution.calculate_full(run,deepcopy(refs['prior']),'2037-04-09',deepcopy(refs['day']),
                    deepcopy(refs['profile']),calculation,opening=opening)
                completion.sources.production_reports['BOR_OrderAllocationHistory'].append({})
                with self.assertRaisesRegex(ValueError,'completion calculation'):
                    execution.validate_completion(run,completion,scoped=False)

    def test_rehashed_candidate_and_copied_authority_cannot_replace_producer_cut(self):
        with TemporaryDirectory() as directory,patch('release.native_identity.require_current',return_value={'test':'release'}):
            run,refs,opening,config=self.setup_case(directory)
            with patch.object(execution.publication,'configuration',return_value=config), \
                    patch.object(execution,'_remarks',return_value=([],{'source':'explicit-local-empty'})):
                _,completion=execution.calculate_full(run,deepcopy(refs['prior']),'2037-04-09',
                    deepcopy(refs['day']),deepcopy(refs['profile']),calculation,opening=opening)
                original=completion.work[-1]
                previous=completion.work[-2]
                changed={name:[dict(row) for row in rows] for name,rows in original.sources.items()}
                changed['BPR/ColorSequence'][0]['SequenceNo']+=10
                # Materialize fully self-consistent files from the substituted
                # source, retaining the genuine run/request/phase owner.
                forged=stages.prepare(root=execution.publication.root(run,config[0]),
                    report_configuration=config[2],placement=original.placement,
                    variables=execution.publication.variables(run),
                    last_generated=previous.candidate['last_generated_after'],
                    previous_catalogue=previous.catalogue,previous_digest=previous.candidate['digest'],
                    sources=changed,descriptors=original.descriptors,owner=original.owner)
                forged=replace(forged,_execution_authority=original._execution_authority)
                with self.assertRaisesRegex(ValueError,'original producer cut'):
                    execution.require_stage_authority(run,forged)
                copied=replace(original,_execution_authority=deepcopy(original._execution_authority))
                with self.assertRaisesRegex(ValueError,'original producer cut'):
                    execution.require_stage_authority(run,copied)
                fabricated=replace(original,_execution_authority=execution._StageAuthority())
                with self.assertRaisesRegex(ValueError,'original producer cut'):
                    execution.require_stage_authority(run,fabricated)
                execution.require_stage_authority(run,original)

    def test_materializer_cannot_substitute_owner_cut(self):
        with TemporaryDirectory() as directory,patch('release.native_identity.require_current',return_value={'test':'release'}):
            run,refs,opening,config=self.setup_case(directory)
            original=execution.publication.prepare
            def changed(*args,**kwargs):
                kwargs['source_owner']=dict(kwargs['source_owner'],cut={'stage':'wrong-stage'})
                return original(*args,**kwargs)
            with patch.object(execution.publication,'configuration',return_value=config), \
                    patch.object(execution.publication,'prepare',side_effect=changed), \
                    patch.object(execution.btr_stage,'finish_btr_boundary') as final:
                with self.assertRaisesRegex(ValueError,'original producer cut'):
                    execution.calculate_full(run,deepcopy(refs['prior']),'2037-04-09',deepcopy(refs['day']),
                        deepcopy(refs['profile']),calculation,opening=opening)
                final.assert_not_called()
