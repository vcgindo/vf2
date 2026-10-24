"""Inherited BTR owner/SQL proof; supplied rollback components, no native claim."""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_pick_files_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedInheritedOpeningTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner','accept','bpr'):
        locals()[_name]=getattr(fixtures.ScopedPickFileTests,_name)

    def binding(self):
        from mta.presentation.scoped_sources import bind
        return bind(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0,include_inherited_btr=True)

    def test_explicit_empty_opening_is_typed_and_keeps_its_own_date(self):
        from django.db import connection
        from mta.presentation.scoped_inherited_btr import PATH
        self.bpr();source=self.binding()
        self.assertEqual(source.rows(PATH),[])
        provenance=source.provenance(PATH)
        self.assertEqual((provenance['owner_kind'],provenance['representation']),('CAPTURED_INPUT','explicit_empty'))
        self.assertEqual(provenance['producer_date'],'2037-04-09')
        self.assertEqual(source.display_date.isoformat(),'2037-04-10')
        with connection.cursor() as cursor:
            cursor.execute(*source.query(PATH));self.assertEqual(cursor.fetchall(),[])
            self.assertIn('Availability_01_30',[column[0] for column in cursor.description])
        with patch('mta.runtime.relational_state.load_image',side_effect=AssertionError('whole input value read')):
            self.assertEqual(self.binding().source_digest,source.source_digest)

    def test_missing_population_does_not_become_empty(self):
        from tests.test_h3_daily_integration import frame
        from mta.presentation.scoped_inherited_btr import PATH,bind
        from mta.presentation.context import PublicationUnavailable
        opening=frame();del opening['opening']['state']['btr']['BufferTrendPhysicalInv']
        with patch('tests.test_h3_daily_integration.frame',return_value=opening):self.bpr()
        source=self.binding()
        with self.assertRaisesRegex(PublicationUnavailable,'source_unavailable'):source.query(PATH)

    def test_actual_opening_date_mismatch_denies(self):
        from mta.presentation.scoped_inherited_btr import bind
        from mta.presentation.context import PublicationUnavailable
        self.bpr()
        phase=deepcopy(self.receipt)
        phase.snapshot.manifest['metadata']['opening_date']='2037-04-08'
        with self.assertRaises(PublicationUnavailable):bind(phase)

    def test_nonempty_source_missing_required_availability_columns_is_denied(self):
        from mta.presentation.scoped_inherited_btr import _metadata,PATH,TABLE
        from mta.presentation.context import PublicationUnavailable
        item=dict(image=PATH,table=TABLE,count=1,digest='a'*64,
            fields=[['SKUCode','SKUCode','str'],['WhCode','WhCode','str']])
        with self.assertRaises(PublicationUnavailable):_metadata(item,PATH)


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedInheritedPredecessorTests(unittest.TestCase):
    from tests import test_scoped_common_final_postgresql as _fixtures
    for _name in ('setUp','rollback','owner','accept','prepare_dbm','finish','publication_opening'):
        locals()[_name]=getattr(_fixtures.ScopedCommonFinalTests,_name)

    def parent_reports(self,parent):
        from django.db import connection
        from django.utils import timezone
        from mta.presentation import operational_reports as full
        from mta.runtime.models import DailyReportGeneration
        from mta.serialization import digest
        # Existing Full preparation produces actual derived BTR in its own
        # report owner before the successor is captured. No BTR source is seeded.
        report=DailyReportGeneration.objects.create(run=parent,
            source_digest=parent.production_digest,recipe_digest=full.recipe_identity())
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.report_generation',%s,true)",[str(parent.pk)])
        report.metadata=full._build(parent);report.digest=digest(report.metadata)
        report.status='READY';report.sealed_at=timezone.now()
        report.save(update_fields=['metadata','digest','status','sealed_at'])
        self.parent_report=report
        return report

    def successor(self,*,prepare_parent_reports=True):
        from mta.runtime.models import RunPhaseAcceptance
        from mta.presentation.scoped_sources import bind
        self.owner(claim=False);self.prepare_dbm();parent=self.finish()
        if prepare_parent_reports:self.parent_reports(parent)
        self.owner(claim=False,predecessor=parent,predecessor_input=True);self.prepare_dbm()
        phase=RunPhaseAcceptance.objects.get(run=self.run,phase='BPR')
        return parent,phase,bind(phase.pk,expected_digest=phase.digest,action_revision=0,include_inherited_btr=True)

    def test_exact_actual_predecessor_bag_sql_and_bpr_export_availability(self):
        from django.db import connection
        from mta.presentation import scoped_inherited_btr as inherited,scoped_report_storage as facts,scoped_prepared as prepared,bpr_prepared
        from mta.presentation.permissions import PermissionCodes
        from mta.runtime.relational_state import load_image
        from mta.serialization import storage,digest
        parent,phase,source=self.successor()
        item=self.parent_report.metadata['images'][inherited.PATH]
        expected=storage(load_image(parent,item))
        self.assertTrue(expected)
        self.assertEqual(source.rows(inherited.PATH),expected)
        provenance=source.provenance(inherited.PATH)
        self.assertEqual(provenance['owner_kind'],'PREDECESSOR')
        self.assertEqual(provenance['owner_id'],str(parent.pk))
        self.assertEqual(provenance['owner_digest'],parent.output_digest)
        self.assertEqual(provenance['report_generation']['digest'],self.parent_report.digest)
        self.assertEqual(provenance['producer_date'],parent.business_date.isoformat())
        query,params=source.query(inherited.PATH)
        self.assertEqual(params,[parent.pk,inherited.PATH])
        with connection.cursor() as cursor:
            cursor.execute(query+' ORDER BY vf_ordinal',params)
            fields=[column[0] for column in cursor.description]
            values=[dict(zip(fields,row)) for row in cursor.fetchall()]
        self.assertEqual([row.pop('vf_ordinal') for row in values],list(range(len(expected))))
        self.assertEqual(storage(values),expected)
        # A consumer join retains every occurrence rather than applying DISTINCT.
        with connection.cursor() as cursor:
            cursor.execute('SELECT X.* FROM ('+query+') X CROSS JOIN generate_series(1,2) copies ORDER BY X.vf_ordinal,copies',params)
            fields=[column[0] for column in cursor.description]
            values=[dict(zip(fields,row)) for row in cursor.fetchall()]
        for row in values:row.pop('vf_ordinal')
        self.assertEqual(storage(values),[row for row in expected for _ in range(2)])
        report=facts.prepare(phase.pk,expected_digest=phase.digest,action_revision=0)
        projection=prepared.prepare(report.pk,expected_report_digest=report.digest,action_revision=0)
        bound=prepared.bind(report.pk,expected_digest=projection.digest,expected_report_digest=report.digest,action_revision=0,include_inherited_btr=True)
        bound.sources.inherited_btr.verify_rows()
        self.assertTrue(digest(bound.read_identity))
        importer={name:source.rows('closing/importer/'+name) for name in ('SkuAttributeData','LocationAttributeData','SkuLocAttributeData')}
        products=PermissionCodes({row['SKUCode']:1 for row in importer['SkuAttributeData']})
        locations=PermissionCodes({row['WHCode']:1 for row in importer['LocationAttributeData']})
        with patch.object(bpr_prepared,'scope',return_value=(products,locations)), \
                patch.object(bpr_prepared,'image_query',side_effect=AssertionError('terminal source fallback')):
            sql,values=bpr_prepared._build(self.run,{},importer,{'BPRReport_RemarkDetails':[]},export=True,read_binding=bound)
            with connection.cursor() as cursor:
                cursor.execute(sql,values)
                names=[column[0] for column in cursor.description]
                exported=storage([dict(zip(names,row)) for row in cursor.fetchall()])
        self.assertTrue(exported)
        availability=('Availability_01_30','Availability_31_60','Availability_61_90')
        from mta.presentation.rrr import sql_key
        for row in exported:
            matching=[old for old in expected if sql_key(old['SKUCode'],old['WhCode'])==sql_key(row['SKUCode'],row['WHCode'])]
            self.assertTrue(matching)
            self.assertIn(tuple(row[field] for field in availability),[tuple(old[field] for field in availability) for old in matching])
        self.assertTrue(any(row['Availability_01_30'] is not None for row in exported))

    def test_parent_report_arrival_preserves_existing_facts_projection_and_inflight_binding(self):
        from mta.presentation import scoped_report_storage as facts,scoped_prepared as prepared
        from mta.presentation.scoped_inherited_btr import PATH
        from mta.presentation.context import PublicationUnavailable
        from mta.serialization import digest
        parent,phase,source=self.successor(prepare_parent_reports=False)
        self.assertIsNone(source.inherited_btr)
        report=facts.prepare(phase.pk,expected_digest=phase.digest,action_revision=0)
        projection=prepared.prepare(report.pk,expected_report_digest=report.digest,action_revision=0)
        before=prepared.bind(report.pk,expected_digest=projection.digest,expected_report_digest=report.digest,action_revision=0,include_inherited_btr=True)
        bags={name:before.reports.rows(name) for name in facts.TABLES}
        prepared_bags={name:before.rows(name) for name in prepared.TABLES}
        initial_identity=digest(before.read_identity)
        self.parent_reports(parent)
        after=prepared.bind(report.pk,expected_digest=projection.digest,expected_report_digest=report.digest,action_revision=0,include_inherited_btr=True)
        self.assertEqual(after.sources.source_digest,before.sources.source_digest)
        self.assertEqual({name:after.reports.rows(name) for name in facts.TABLES},bags)
        self.assertEqual({name:after.rows(name) for name in prepared.TABLES},prepared_bags)
        self.assertEqual(prepared.prepare(report.pk,expected_report_digest=report.digest,action_revision=0).digest,projection.digest)
        self.assertNotEqual(digest(after.read_identity),initial_identity)
        self.assertEqual(digest(before.read_identity),initial_identity)
        with self.assertRaises(PublicationUnavailable):before.image_query(PATH)
        self.assertTrue(after.sources.rows(PATH))

        # Optional analytics drift cannot block binding the independent facts.
        with patch('mta.presentation.operational_reports.generation',side_effect=ValueError('bad optional parent')):
            self.assertEqual(facts.bind(report.pk,expected_digest=report.digest,action_revision=0).generation.pk,report.pk)
            self.assertEqual(prepared.bind(report.pk,expected_digest=projection.digest,
                expected_report_digest=report.digest,action_revision=0).projection.digest,projection.digest)
            with self.assertRaises(PublicationUnavailable):
                prepared.bind(report.pk,expected_digest=projection.digest,expected_report_digest=report.digest,
                    action_revision=0,include_inherited_btr=True)

    def test_wrong_predecessor_lineage_and_date_are_denied(self):
        from mta.presentation.scoped_inherited_btr import bind
        from mta.presentation.context import PublicationUnavailable
        from mta.runtime.input_reader import read_input
        parent,phase,source=self.successor()
        original=read_input
        raw=original(phase.run,components=('lineage','initialization_binding'))
        for field,value in (('run_id',str(phase.run.pk)),('output_digest','f'*64),('commands',[{}])):
            changed=deepcopy(raw);changed['lineage'][field]=value
            def read(run,**options):return changed if run.pk==phase.run_id else original(run,**options)
            with self.subTest(field=field),patch('mta.runtime.input_reader.read_input',side_effect=read):
                with self.assertRaises(PublicationUnavailable):bind(phase)
        changed=deepcopy(phase);changed.snapshot.manifest['metadata']['opening_date']='2037-04-09'
        with self.assertRaises(PublicationUnavailable):bind(changed)

    def test_initialization_namespace_reader_uses_real_typed_rows_and_initialization_key(self):
        """SQL storage component only; no native registration/certification claim."""
        import uuid
        from django.db import connection,DatabaseError,transaction
        from mta.runtime.models import ProductionInitialization,MdmSource
        from mta.runtime import opening_storage
        from mta.runtime.input_storage import save_input
        from mta.mdm.initialization_rows import select
        from mta.presentation.scoped_inherited_btr import InheritedBtr,PATH,INPUT
        from mta.serialization import digest,storage
        from mta.runtime.input_reader import read_input
        parent,phase,source=self.successor()
        rows=source.rows(PATH)
        raw=dict(profile=read_input(parent,components=('profile',))['profile'],
            opening=dict(identity='BTR_SQL_STORAGE_COMPONENT',opening_date=parent.business_date.isoformat(),
                state=dict(btr=dict(BufferTrendPhysicalInv=rows))))
        identifier=uuid.uuid4()
        # Exact SQL schema discriminator carrier, not an installed native
        # source: no registration, certification, family or accepted day.
        # This standalone reader test cannot pass native phase admission.
        tag=dict(schema='fresh-production-mdm-source-v1',
            fixture='SQL_OPENING_STORAGE_ONLY_NO_NATIVE_CERTIFICATION',identity=str(identifier))
        sql_source=MdmSource.objects.create(digest=digest(tag),dll_digest='',
            database_name=connection.settings_dict['NAME'],receipt=tag)
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.production_initialization',%s,true)",[str(identifier)])
        try:
            owner=ProductionInitialization.objects.create(id=identifier,source=sql_source,
                opening_identity='BTR_SQL_COMPONENT_'+identifier.hex,opening_date=parent.business_date,
                input_sha256=uuid.uuid4().hex*2,recipe_sha256='b'*64,configuration_digest=digest(raw['profile']),
                implementation_digest='c'*64,input_digest=digest(raw))
            owner.input_payload=save_input(owner,raw,version=3,
                image_writer=opening_storage.save_image,table_selector=select)
            owner.input_manifest_digest=digest(owner.input_payload)
            owner.save(update_fields=['input_payload','input_manifest_digest'])
        except DatabaseError:
            transaction.set_rollback(True);raise
        finally:
            if not connection.needs_rollback:
                with connection.cursor() as cursor:cursor.execute("SELECT set_config('fresh.production_initialization','',true)")
        locator=dict(source.provenance(PATH),owner_kind='INITIALIZATION',owner_id=str(owner.pk),
            owner_digest=owner.input_manifest_digest,report_generation=None,
            image=owner.input_payload['images'][INPUT+'/values'])
        bound=InheritedBtr(owner,locator);bound.verify_rows()
        self.assertEqual(bound.rows(),rows)
        query,params=bound.query()
        self.assertIn('mta_opening.',query);self.assertIn('vf_initialization_id=%s',query)
        self.assertEqual(params,[owner.pk,INPUT+'/values'])
        with connection.cursor() as cursor:
            cursor.execute(query+' ORDER BY vf_ordinal',params)
            fields=[column[0] for column in cursor.description]
            actual=[dict(zip(fields,row)) for row in cursor.fetchall()]
        self.assertEqual([row.pop('vf_ordinal') for row in actual],list(range(len(rows))))
        self.assertEqual(storage(actual),rows)


if __name__=='__main__':unittest.main()
