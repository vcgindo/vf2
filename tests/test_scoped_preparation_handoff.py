"""Producer handoffs reject mixed/stale owners without admitting a serving view."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()
from dataclasses import replace
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from mta.presentation import scoped_preparation as handoff
from mta.presentation.scoped_sources import BprSources
from mta.presentation.scoped_report_storage import ReportBinding
from mta.presentation.scoped_prepared import PreparedBinding
from mta.presentation.scoped_pick_storage import PickBinding
from mta.presentation.scoped_transit_storage import TransitBinding
from mta.presentation.context import PublicationUnavailable
from mta.serialization import digest


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(handoff,'connection',NS(in_atomic_block=True)))
        self.current=self.enterContext(patch('mta.runtime.scoped_actions.revision',return_value=4))
        run=NS(pk='run',input_digest='input')
        snapshot=NS(run_id='run',acceptance_id='phase',state_digest='snapshot',input_digest='input',
                    manifest={'references':{'profile':'configuration'}})
        self.phase=NS(pk='phase',phase='BPR',run_id='run',state_sealed=True,digest='phase-digest',
                      input_digest='input',snapshot=snapshot)
        self.sources=BprSources(run,'phase','phase-digest','snapshot',4,None,'sources',{})
        self.owner=dict(run_id='run',phase_id='phase',action_revision=4,source_digest='sources',
                        configuration_digest='configuration')
        self.report=NS(pk='report',phase=self.phase,sealed=True,sealed_at='time',metadata={},digest=digest({}),**self.owner)
        self.reports=ReportBinding(self.report)
        self.projection=NS(generation_id='report',report_generation_digest=self.report.digest,
                           sealed=True,sealed_at='time',metadata={},digest=digest({}))
        self.prepared=PreparedBinding(self.projection,self.reports,self.sources)
        self.pick=PickBinding(NS(pk='pick',sealed=True,sealed_at='time',metadata={},digest=digest({}),**self.owner),self.sources)
        self.transit=TransitBinding(NS(pk='transit',sealed=True,sealed_at='time',metadata={},digest=digest({}),**self.owner))

    def test_exact_handles_and_optional_stage_capabilities_are_retained(self):
        self.assertIs(handoff.require_sources(self.phase,self.sources),self.sources)
        self.assertIs(handoff.require_reports(self.reports,self.sources),self.reports)
        self.assertIs(handoff.require_prepared(self.prepared),self.prepared)
        self.assertIs(handoff.require_pick(self.prepared,self.pick),self.pick)
        self.assertIs(handoff.require_transit(replace(self.prepared,transit=self.transit)),self.transit)
        self.assertIsNone(self.prepared.transit)

    def test_transaction_and_current_revision_are_mandatory(self):
        with patch.object(handoff,'connection',NS(in_atomic_block=False)):
            with self.assertRaises(PublicationUnavailable):handoff.require_sources(self.phase,self.sources)
        self.current.return_value=5
        with self.assertRaises(PublicationUnavailable):handoff.require_prepared(self.prepared)

    def test_phase_snapshot_input_and_owner_cannot_be_mixed(self):
        for field,value in (('acceptance_id','foreign'),('acceptance_digest','foreign'),
                            ('snapshot_digest','foreign'),('action_revision',True),('action_revision',-1)):
            with self.subTest(field=field),self.assertRaises(PublicationUnavailable):
                handoff.require_sources(self.phase,replace(self.sources,**{field:value}))
        self.phase.snapshot.run_id='other-run'
        with self.assertRaises(PublicationUnavailable):handoff.require_sources(self.phase,self.sources)

    def test_report_seal_checksum_configuration_and_revision_are_required(self):
        for field,value in (('sealed',False),('sealed_at',None),('digest','changed'),
                            ('run_id','other'),('source_digest','other'),('configuration_digest','other'),('action_revision',3)):
            original=getattr(self.report,field)
            with self.subTest(field=field),self.assertRaises(PublicationUnavailable):
                setattr(self.report,field,value);handoff.require_reports(self.reports,self.sources)
            setattr(self.report,field,original)

    def test_projection_must_belong_to_exact_sealed_report(self):
        for field,value in (('generation_id','other'),('report_generation_digest','other'),('sealed',False),('digest','other')):
            original=getattr(self.projection,field)
            with self.subTest(field=field),self.assertRaises(PublicationUnavailable):
                setattr(self.projection,field,value);handoff.require_prepared(self.prepared)
            setattr(self.projection,field,original)

    def test_pick_and_transit_must_share_all_owner_dimensions(self):
        for field in self.owner:
            for binding in (self.pick,self.transit):
                original=getattr(binding.generation,field)
                with self.subTest(field=field,kind=type(binding)),self.assertRaises(PublicationUnavailable):
                    setattr(binding.generation,field,'other')
                    if binding is self.pick:handoff.require_pick(self.prepared,binding)
                    else:handoff.require_transit(replace(self.prepared,transit=binding))
                setattr(binding.generation,field,original)
        with self.assertRaises(PublicationUnavailable):handoff.require_transit(self.prepared)


if __name__=='__main__':unittest.main()
