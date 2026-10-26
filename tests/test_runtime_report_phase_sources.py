"""Phase/image ownership denials; actual persisted proof is recorded separately."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'runtime-report-source-unit-only')
import django
django.setup()

from copy import deepcopy
from datetime import date
from types import SimpleNamespace as NS
from uuid import uuid4
from unittest import TestCase
from unittest.mock import patch

from mta.runtime import runtime_report_phase_sources as sources
from mta.runtime.phase_state import SCHEMA
from mta.serialization import digest


def fixture(empty=False):
    run = NS(pk=uuid4(), business_date=date(2026,10,25), input_digest='i'*64,
             input_manifest_digest='m'*64)
    raw = dict(profile={'configured':True}, scope_request={'scope':'UptoDBM','runtime_reports':'captured'})
    refs = dict(profile=digest(raw['profile']), day={'business_date':digest(run.business_date.isoformat())})
    meta = dict(table='Importer/SkuAttributeData', image='phase/PRE_BPR/importer/SkuAttributeData',
                count=0 if empty else 1, fields=[] if empty else [['SKUCode','SKUCode','str']],
                digest=digest([] if empty else [{'SKUCode':'S'}]))
    phases = {}
    parent = None
    for name in ('PRE_BPR','BPR'):
        logical = 'phase/'+name+'/importer/SkuAttributeData'
        manifest = dict(schema=SCHEMA,phase=name,references=deepcopy(refs),
            metadata={'identity':str(run.pk)}, state={'importer':{'SkuAttributeData':{'image':logical}}},
            images={logical:deepcopy(meta)})
        phase = NS(pk=uuid4(), run=run, run_id=run.pk, phase=name, digest=('a' if parent is None else 'b')*64,
            metadata={'effects':{} if parent is None else {'parent_acceptance_digest':parent.digest}})
        phase.snapshot = NS(pk=uuid4(), parent=None if parent is None else parent.snapshot,
            parent_id=None if parent is None else parent.snapshot.pk,
            acceptance_id=phase.pk,manifest=manifest,state_digest=digest(manifest))
        phases[phase.pk]=phase
        parent=phase
    return phase,phases,raw


def arguments(phase,raw):
    return dict(expected_digest=phase.digest, expected_phase='BPR', expected_action_revision=0,
                expected_profile_digest=digest(raw['profile']), expected_request_digest=digest(raw['scope_request']))


class RuntimeReportPhaseSourcesTests(TestCase):
    def bind(self,phase,phases,raw,**changes):
        def accepted(identity,checksum):
            value=phases[identity]
            self.assertEqual(checksum,value.digest)
            return value
        with patch('mta.runtime.scoped_pick_files._accepted',side_effect=accepted) as auth, \
                patch('mta.runtime.input_reader.read_input',return_value=raw) as read:
            result=sources.bind(phase.pk,**dict(arguments(phase,raw),**changes))
            read.assert_called_once_with(phase.run,components=('profile','scope_request'))
            self.assertEqual(auth.call_count,2)
            return result

    def test_authenticated_ancestor_image_retains_physical_owner_and_configuration(self):
        phase,phases,raw=fixture()
        bound=self.bind(phase,phases,raw)
        with patch('mta.runtime.relational_state.load_image',return_value=[{'SKUCode':'S'}]):
            rows,reference=bound.image(('state','importer','SkuAttributeData'),
                logical_image='phase/BPR/importer/SkuAttributeData',physical_table='Importer/SkuAttributeData',fields=('SKUCode',))
            self.assertEqual(list(rows),[{'SKUCode':'S'}])
        self.assertEqual(reference['physical_image'],'phase/PRE_BPR/importer/SkuAttributeData')
        self.assertEqual(reference['physical_table'],'Importer/SkuAttributeData')
        self.assertEqual(reference['captured_request_digest'],digest(raw['scope_request']))
        self.assertEqual(reference['business_date'],'2026-10-25')
        self.assertEqual(reference['action_revision'],0)
        self.assertEqual(reference['digest'],digest({k:v for k,v in reference.items() if k!='digest'}))

    def test_valid_empty_image_still_denies_wrong_table_node_and_physical_lineage(self):
        phase,phases,raw=fixture(empty=True)
        bound=self.bind(phase,phases,raw)
        with patch('mta.runtime.relational_state.load_image',return_value=[]) as reader:
            kwargs=dict(logical_image='phase/BPR/importer/SkuAttributeData',physical_table='Importer/SkuAttributeData',fields=('SKUCode',))
            rows,_=bound.image(('state','importer','SkuAttributeData'),**kwargs)
            self.assertEqual(list(rows),[])
            reader.reset_mock()
            for node,changed in ((('state','missing'),{}),
                    (('state','importer','SkuAttributeData'),{'physical_table':'BPR/SkuAttributeData'}),
                    (('state','importer','SkuAttributeData'),{'logical_image':'phase/DBM/importer/SkuAttributeData'})):
                with self.assertRaises(ValueError):bound.image(node,**dict(kwargs,**changed))
            # Same table and zero rows do not authorize a different physical path.
            bound.manifests[0]['images'][kwargs['logical_image']]['image']='phase/PRE_BPR/importer/Other'
            with self.assertRaisesRegex(ValueError,'lineage'):
                bound.image(('state','importer','SkuAttributeData'),**kwargs)
            reader.assert_not_called()

    def test_ordered_report_sources_require_exact_nonnegative_integer_index(self):
        phase,phases,raw=fixture(empty=True)
        manifest=phase.snapshot.manifest
        logical='phase/BPR/importer/SkuAttributeData'
        manifest['state']['reports']=[{'source':{'image':logical}}]
        phase.snapshot.state_digest=digest(manifest)
        bound=self.bind(phase,phases,raw)
        kwargs=dict(logical_image=logical,physical_table='Importer/SkuAttributeData',fields=('SKUCode',))
        with patch('mta.runtime.relational_state.load_image',return_value=[]) as reader:
            rows,reference=bound.image(('state','reports',0,'source'),**kwargs)
            self.assertEqual(list(rows),[])
            self.assertEqual(reference['node'],['state','reports',0,'source'])
            reader.reset_mock()
            for index in (-1,1,'0',False,0.0):
                with self.subTest(index=index),self.assertRaises(ValueError):
                    bound.image(('state','reports',index,'source'),**kwargs)
            reader.assert_not_called()

    def test_phase_date_identity_and_snapshot_drift_deny_before_reading_input(self):
        for change in ('phase','date','run','digest','action','boolean_action'):
            phase,phases,raw=fixture()
            manifest=phase.snapshot.manifest
            if change=='phase':manifest['phase']='DBM'
            elif change=='date':manifest['references']['day']['business_date']=digest('2026-10-24')
            elif change=='run':manifest['metadata']['identity']=str(uuid4())
            elif change=='action':manifest['metadata']['action_revision']=99
            elif change=='boolean_action':manifest['metadata']['action_revision']=False
            if change!='digest':phase.snapshot.state_digest=digest(manifest)
            else:phase.snapshot.state_digest='0'*64
            with patch('mta.runtime.scoped_pick_files._accepted',return_value=phase), \
                    patch('mta.runtime.input_reader.read_input') as read:
                with self.subTest(change=change),self.assertRaises(ValueError):
                    sources.bind(phase.pk,**arguments(phase,raw))
                read.assert_not_called()

    def test_captured_profile_request_and_expected_revision_cannot_be_substituted(self):
        for change in ({'expected_profile_digest':'c'*64},{'expected_request_digest':'d'*64},
                       {'expected_action_revision':1},{'expected_action_revision':True}):
            phase,phases,raw=fixture()
            with self.assertRaises(ValueError):self.bind(phase,phases,raw,**change)

    def test_ancestor_must_belong_to_same_run_and_dependency_generation(self):
        for change in ('run','references'):
            phase,phases,raw=fixture()
            parent=next(p for p in phases.values() if p.phase=='PRE_BPR')
            if change=='run':parent.run_id=uuid4()
            else:parent.snapshot.manifest['references']['profile']='e'*64
            with self.assertRaisesRegex(ValueError,'ancestor'):
                self.bind(phase,phases,raw)

    def test_existing_authentication_failure_is_not_replaced_with_schema_matching(self):
        phase,_phases,raw=fixture(empty=True)
        with patch('mta.runtime.scoped_pick_files._accepted',side_effect=ValueError('not accepted')), \
                patch('mta.runtime.input_reader.read_input') as read:
            with self.assertRaisesRegex(ValueError,'not accepted'):
                sources.bind(phase.pk,**arguments(phase,raw))
            read.assert_not_called()
