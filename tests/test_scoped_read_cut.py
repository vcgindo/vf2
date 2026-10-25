"""Live-reference transitions using the ORM's actual FK/metadata representation.

These are contract tests. Native PostgreSQL publication/rollback and real UI
timings remain separate acceptance proofs; no mocked test certifies those.
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()
from copy import deepcopy
from datetime import datetime,timezone
from uuid import uuid4
import unittest
from mta.runtime.models import (CalculationRun,RunPhaseAcceptance,DailyPhaseSnapshot,
    ScopeReportGeneration,ScopeReadReference,RunCommand)
from mta.presentation import scoped_read_cut as cut
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest


class ReadCutTests(unittest.TestCase):
    def setUp(self):
        self.run=CalculationRun(id=uuid4(),input_digest='a'*64,input_manifest_digest='b'*64)
        self.phase=RunPhaseAcceptance(id=uuid4(),run=self.run,source_id='source',phase='BPR',
            state_sealed=True,digest='c'*64,snapshot=DailyPhaseSnapshot(id=11,state_digest='d'*64))
        self.dbm=RunPhaseAcceptance(id=uuid4(),run=self.run,source_id='source',phase='DBM',
            state_sealed=True,digest='e'*64,snapshot=DailyPhaseSnapshot(id=12,parent=self.phase.snapshot,
                manifest={'references':{'profile':'configuration'}}),
            metadata={'effects':{'parent_acceptance_digest':self.phase.digest}})
        self.report=ScopeReportGeneration(run=self.run,phase=self.phase,action_revision=4,configuration_digest='configuration',
            sealed=True,sealed_at=datetime.now(timezone.utc))
        self.base=ScopeReadReference(report_generation=self.report,git_generation_id=uuid4(),
            expedite_parent_generation_id=uuid4(),pick_files_id=self.phase.pk,runtime_reports_digest='f'*64,
            metadata=dict(schema=cut.SCHEMA,run_id=str(self.run.pk),phase_id=str(self.phase.pk),
                phase_digest=self.phase.digest,snapshot_digest=self.phase.snapshot.state_digest,
                input_digest=self.run.input_digest,input_manifest_digest=self.run.input_manifest_digest,
                action_revision=4,transition=None,bpr={'remarks':{'live_highwater':3}}))
        self.seal(self.base)

    @staticmethod
    def seal(row):
        row.digest=digest(row.metadata)
        # Simulate the ORM state of a materialized default-database row. The
        # PostgreSQL tests separately establish actual guarded persistence.
        row._state.adding=False;row._state.db='default'
        return row

    def action(self,previous,identifier):
        row=ScopeReadReference(report_generation=previous.report_generation,
            git_generation_id=previous.git_generation_id,
            expedite_parent_generation_id=previous.expedite_parent_generation_id,
            pick_files_id=previous.pick_files_id,runtime_reports_digest=previous.runtime_reports_digest,
            previous_reference=previous,metadata=deepcopy(previous.metadata))
        row.action_command=RunCommand(id=identifier,run=self.run,phase_acceptance=self.dbm,
            state_sealed=True,scope_parent_revision=cut.revision(previous),
            payload={'actor':'fixture','operation':'APPLY'})
        row.metadata.update(action_revision=identifier,
            transition=cut.transition(row.action_command,previous,'ACTION'))
        return self.seal(row)

    def remark(self,previous):
        row=ScopeReadReference(report_generation=previous.report_generation,
            git_generation_id=previous.git_generation_id,expedite_parent_generation_id=uuid4(),
            pick_files_id=previous.pick_files_id,runtime_reports_digest=previous.runtime_reports_digest,
            previous_reference=previous,action_command=previous.action_command,metadata=deepcopy(previous.metadata))
        row.metadata['bpr']['remarks']['live_highwater']+=1
        row.metadata['transition']=cut.transition(row.action_command,previous,'REMARK')
        return self.seal(row)

    def require(self,row,current=None):
        return cut.require(row,self.phase,build_revision=4,
            current_revision=cut.revision(row) if current is None else current)

    def test_initial_reference_requires_its_current_build_cut(self):
        self.assertEqual(self.require(self.base),4)
        with self.assertRaises(PublicationUnavailable):self.require(self.base,5)

    def test_constructed_or_different_database_reference_cannot_admit_retained_sources(self):
        row=self.action(self.base,5);row._state.adding=True
        with self.assertRaises(PublicationUnavailable):self.require(row)
        row._state.adding=False;row._state.db='other'
        with self.assertRaises(PublicationUnavailable):self.require(row)

    def test_successive_actions_retain_the_same_report_and_advance_live_cut(self):
        first=self.action(self.base,5);second=self.action(first,7)
        self.assertEqual(self.require(first),5)
        self.assertEqual(self.require(second),7)
        self.assertEqual(second.report_generation_id,self.base.report_generation_id)
        self.assertEqual(second.report_generation.action_revision,4)
        with self.assertRaises(PublicationUnavailable):self.require(first,7)

    def test_action_remark_action_and_remark_action_remark(self):
        for row in (self.action(self.remark(self.action(self.base,5)),8),
                    self.remark(self.action(self.remark(self.base),5))):
            self.assertEqual(self.require(row),cut.revision(row))
            self.assertEqual(row.report_generation.action_revision,4)

    def test_noop_still_owns_a_successor_reference(self):
        row=self.action(self.base,5)
        row.action_command.before_digest=row.action_command.after_digest='1'*64
        row.action_command.payload['operation']='SLEEP'
        self.assertEqual(self.require(row),5)

    def test_action_cannot_change_unchanged_report_population_or_remark_prefix(self):
        for mutate in (lambda r:setattr(r,'git_generation_id',uuid4()),
                       lambda r:setattr(r,'expedite_parent_generation_id',uuid4()),
                       lambda r:r.metadata['bpr']['remarks'].update(live_highwater=4),
                       lambda r:r.metadata.update(configuration_digest='changed')):
            row=self.action(self.base,5);mutate(row);self.seal(row)
            with self.subTest(mutate=mutate),self.assertRaises(PublicationUnavailable):self.require(row)

    def test_command_must_be_sealed_same_run_exact_dbm_child(self):
        for mutate in (lambda c:setattr(c,'state_sealed',False),
                       lambda c:setattr(c,'run_id',uuid4()),
                       lambda c:setattr(c,'scope_parent_revision',3),
                       lambda c:c.payload.update(actor=''),
                       lambda c:c.payload.update(operation='OTHER')):
            row=self.action(self.base,5);mutate(row.action_command)
            with self.subTest(mutate=mutate),self.assertRaises(PublicationUnavailable):self.require(row)
        row=self.action(self.base,5);self.dbm.snapshot.parent_id=999
        with self.assertRaises(PublicationUnavailable):self.require(row)

    def test_remark_cannot_advance_command_or_reuse_highwater(self):
        row=self.remark(self.action(self.base,5))
        row.metadata['bpr']['remarks']['live_highwater']=3;self.seal(row)
        with self.assertRaises(PublicationUnavailable):self.require(row)
        row=self.remark(self.base);row.action_command=self.action(self.base,5).action_command
        row.metadata.update(action_revision=5,transition=cut.transition(row.action_command,self.base,'REMARK'))
        self.seal(row)
        with self.assertRaises(PublicationUnavailable):self.require(row)

    def test_previous_digest_and_transition_identity_cannot_be_forged(self):
        row=self.action(self.base,5)
        row.metadata['transition']['previous_reference_digest']='0'*64;self.seal(row)
        with self.assertRaises(PublicationUnavailable):self.require(row)
        row=self.action(self.base,5);row.previous_reference.metadata['action_revision']=2
        with self.assertRaises(PublicationUnavailable):self.require(row)

    def test_source_input_phase_and_current_revision_must_all_match(self):
        for key,value in (('input_digest','changed'),('phase_id',str(uuid4())),('snapshot_digest','changed')):
            row=self.action(self.base,5);row.metadata[key]=value;self.seal(row)
            with self.subTest(key=key),self.assertRaises(PublicationUnavailable):self.require(row)
        for value in (True,-1,6):
            with self.subTest(current=value),self.assertRaises(PublicationUnavailable):self.require(self.action(self.base,5),value)

    def test_dbm_action_writer_uses_live_revision_and_never_prepares_reports(self):
        from contextlib import ExitStack,nullcontext
        from types import SimpleNamespace as NS
        from unittest.mock import patch
        from mta.presentation import scoped_action_writer as writer
        from mta.presentation.scoped_dbm_view import DbmViewBinding
        reference=self.action(self.base,5)
        source=NS(run=self.run,acceptance_id=self.phase.pk,acceptance_digest=self.phase.digest,action_revision=4)
        state={'Suggestions':[{'SKUCode':'SKU','WhCode':'WH'}],
            'DBMMaster':[{'SKUCode':'SKU','WhCode':'WH'}],'NormAcceptanceTbl':[]}
        view=DbmViewBinding(reference,NS(sources=source),None,None,None,self.dbm,NS(run=self.run,dbm=state))
        event=self.action(reference,6).action_command
        fresh=NS(read_identity={'id':'next','digest':'next'})
        with ExitStack() as stack:
            stack.enter_context(patch.object(writer,'validation_reads',nullcontext))
            stack.enter_context(patch.object(writer.scoped_selection,'selected',side_effect=[view,fresh]))
            stack.enter_context(patch.object(writer,'scope',return_value=({'SKU'},{'WH'})))
            stack.enter_context(patch.object(writer.OperationalAcceptance.objects,'filter',return_value=NS(exists=lambda:False)))
            stack.enter_context(patch.object(writer.scoped_action_ownership,'verify_guards'))
            stack.enter_context(patch.object(writer.scoped_action_ownership,'publication',return_value=nullcontext()))
            record=stack.enter_context(patch.object(writer.scoped_actions,'record',return_value=event))
            advance=stack.enter_context(patch.object(writer.scoped_view,'advance_action',return_value=fresh))
            stack.enter_context(patch.object(writer.scoped_dbm_view,'compose',return_value=fresh))
            stack.enter_context(patch.object(writer.scoped_view,'prepare',side_effect=AssertionError('Action rebuilt reports')))
            actual,_=writer._submit_locked({},'fixture','APPLY',[('SKU','WH')],{'run_id':str(self.run.pk)})
        self.assertIs(actual,event)
        self.assertEqual(record.call_args.kwargs['expected_revision'],5)
        self.assertEqual(record.call_args.kwargs['phase_id'],self.dbm.pk)
        advance.assert_called_once_with(view,event)


if __name__=='__main__':unittest.main()
