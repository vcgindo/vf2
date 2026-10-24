"""Accepted phase SELECT/prepared contracts; no native serving/legacy claim."""
from decimal import Decimal,ROUND_HALF_UP
from itertools import product
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_pick_files_postgresql as fixtures


def native_key(*values):
    return None if any(value is None for value in values) else tuple(str(value).rstrip(' ').lower() for value in values)


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedPreparedTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner','accept','bpr'):
        locals()[_name]=getattr(fixtures.ScopedPickFileTests,_name)

    def parent(self,*,counter=False):
        from mta.presentation.scoped_report_storage import prepare
        self.bpr(counter=counter)
        self.report=prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)

    def prepare(self):
        from mta.presentation.scoped_prepared import prepare
        return prepare(self.report.pk,expected_report_digest=self.report.digest,action_revision=0)

    def binding(self,row):
        from mta.presentation.scoped_prepared import bind
        return bind(row.pk,expected_digest=row.digest,expected_report_digest=self.report.digest,action_revision=0)

    def manual_candidates(self,sources):
        from mta.presentation.bpr_prepared_fields import SOURCES,FIELDS,field_name
        bags={owner:list(enumerate(sources.rows(path))) for owner,path in SOURCES.items()}
        result=[]
        for aordinal,a in bags['A']:
            matched=[]
            for owner,sku,location in (('V','SKUCode','WhCode'),('S','SKUCode','WhCode'),
                    ('C','SKUCode',None),('D',None,'WHCode'),('B','SKUCode','LocCode')):
                names=[name for name in (sku,location) if name]
                keys=[a['SKUCode'] if name==sku else a['WhCode'] for name in names]
                target=native_key(*keys)
                matched.append([(i,row) for i,row in bags[owner]
                    if target is not None and native_key(*(row[name] for name in names))==target] or [(None,None)])
            for joined in product(*matched):
                selected=dict(A=(aordinal,a),**dict(zip(('V','S','C','D','B'),joined)))
                row=dict(ordinal=len(result),sku_key=None if a['SKUCode'] is None else native_key(a['SKUCode'])[0],
                    location_key=None if a['WhCode'] is None else native_key(a['WhCode'])[0])
                row.update({owner.lower()+'_ordinal':value[0] for owner,value in selected.items()})
                for owner,fields in FIELDS.items():
                    for name,kind in fields.items():
                        value=selected[owner][1]
                        value=None if value is None else value[name]
                        if value is not None:
                            value=Decimal(str(value)) if kind=='numeric' else int(value) if kind=='bigint' else str(value)
                        row[field_name(owner,name)]=value
                result.append(row)
        from mta.serialization import storage
        return storage(result)

    def test_manual_candidate_join_complete_rows_and_planning_source_values(self):
        from django.db import connection
        from mta.presentation.scoped_prepared import TABLES
        from mta.serialization import storage
        self.parent();row=self.prepare();bound=self.binding(row)
        self.assertEqual(bound.rows('bpr_candidates'),self.manual_candidates(bound.sources))
        master=bound.sources.rows('closing/importer/MasterData')
        expected=[]
        for i,source in enumerate(master):
            expected.append(dict(source_ordinal=i,sku_key=native_key(source['SKUCode'])[0],
                location_key=native_key(source['WhCode'])[0],
                parent_key=None if source['ParentWhCode'] is None else native_key(source['ParentWhCode'])[0],
                SKUCode=source['SKUCode'],WHCode=source['WhCode'],Norm=source['Norm'],
                ParentWhCode=source['ParentWhCode'],SKUIntroDate=None if source['SKUIntroDate'] is None else str(source['SKUIntroDate'])[:10]))
        self.assertEqual(bound.rows('bpr_master'),expected)
        rationed=bound.sources.rows('reports/bpr/vf_RationedReqReport')
        standards=bound.sources.rows('closing/dbm/SKULocStandardAttributes')
        git=[]
        for i,a in enumerate(rationed):
            if a['GIT'] is None or a['GIT']<=0:continue
            for j,b in enumerate(standards):
                if native_key(a['SKUCode'],a['WhCode'])!=native_key(b['SKUCode'],b['WhCode']):continue
                value=dict(rationed_ordinal=i,standard_ordinal=j,sku_key=native_key(a['SKUCode'])[0],
                    location_key=native_key(a['WhCode'])[0],parent_key=None if a['ParentWhCode'] is None else native_key(a['ParentWhCode'])[0],
                    Status='',SKUCode=a['SKUCode'],WhCode=a['WhCode'],Tags=b['Tags'],ParentWhCode=a['ParentWhCode'],
                    Norm=a['Norm'],VirtualNorm=a['VirtualNorm'],Stock=a['Stock'],Git=a['GIT'],
                    PhysicalInventoryPen=a['PhysicalInventoryPen'],PhysicalInventoryColor=a['PhysicalInventoryColor'],
                    PipelineInventoryPen=a['DispatchPen'],PipelineInventoryColor=a['DispatchColor'],Req=a['Req'],
                    Price=None if b['Price'] is None else int(Decimal(str(b['Price']))),IsReceiving=True)
                for field in ('PhysicalInventoryPen','PipelineInventoryPen'):
                    if value[field] is not None:value[field]=Decimal(str(value[field])).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
                git.append(value)
        for value in git:
            value['IsParent']=any(native_key(value['SKUCode'],value['WhCode'])==native_key(child['SKUCode'],child['ParentWhCode']) for child in git)
        self.assertEqual(bound.rows('git_master'),storage(git))
        for name,(_model,_fields,ordinals,_dense) in TABLES.items():
            with self.subTest(name=name),connection.cursor() as cursor:
                query,params=bound.query(name)
                cursor.execute(query+' ORDER BY '+','.join('R.'+connection.ops.quote_name(f) for f in ordinals),params)
                fields=[column[0] for column in cursor.description]
                values=[dict(zip(fields,record)) for record in cursor.fetchall()]
                for value in values:self.assertEqual(value.pop('run_id'),self.run.pk)
                self.assertEqual(storage(values),bound.rows(name))

    def test_shared_bpr_full_insert_text_and_parameters_are_unchanged(self):
        from mta.presentation import daily_native_prepared as full,scoped_sources
        import ast
        from pathlib import Path
        from django.core.management.base import CommandError
        from mta.presentation.bpr_prepared_fields import SOURCES,FIELDS
        from mta.presentation.rrr_sql import equal,key
        from mta.runtime.relational_state import CATALOG,PG_TYPES,quote
        from django.db import connection,transaction,DatabaseError
        from mta.runtime.models import BprPreparedRow
        # Execute only the retained SQL function, without importing the retired
        # command's removed fixture/login machinery. Its function body is intact.
        path=Path(__file__).resolve().parents[1]/'mta/runtime/management/commands/prepare_bpr_fixture.py'
        tree=ast.parse(path.read_text(encoding='utf-8'))
        function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='insert_query')
        self.parent()
        sources=scoped_sources.bind(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        def metadata(run,path):return sources.metadata(path)
        def query(run,path):return sources.query(path)
        namespace=dict(SOURCES=SOURCES,FIELDS=FIELDS,CATALOG=CATALOG,PG_TYPES=PG_TYPES,
            quote=quote,key=key,equal=equal,CommandError=CommandError,BprPreparedRow=BprPreparedRow,
            ROW_FIELDS=full.BPR_ROW_FIELDS,image_metadata=metadata,image_query=query)
        exec(compile(ast.Module(body=[function],type_ignores=[]),str(path),'exec'),namespace)
        with patch.object(full,'image_metadata',side_effect=metadata),patch.object(full,'image_query',side_effect=query):
            actual=full._bpr_insert_query(self.run)
            self.assertEqual(actual,namespace['insert_query'](self.run))
        # The ordinary Full target still refuses this incomplete real run.
        with self.assertRaises(DatabaseError),transaction.atomic():
            with connection.cursor() as cursor:cursor.execute(*actual)
        self.assertFalse(BprPreparedRow.objects.filter(run=self.run).exists())

    def test_projection_failure_repeat_and_actual_counter_neutrality(self):
        from mta.presentation import scoped_prepared as module
        from mta.runtime.models import ScopeSourceProjection
        from mta.runtime.scope_revisions import require_current
        self.parent(counter=True);before=require_current(self.run)
        parent_digest=self.report.digest
        original=module._planning_inserts
        def interrupted(*args):
            for name,query,params in original(*args):
                if name=='git_master':raise OSError('late prepared failure')
                yield name,query,params
        with patch.object(module,'_planning_inserts',side_effect=interrupted),self.assertRaisesRegex(OSError,'late prepared failure'):
            self.prepare()
        self.assertFalse(ScopeSourceProjection.objects.filter(generation=self.report).exists())
        for model,*_rest in module.TABLES.values():self.assertEqual(model.objects.count(),0)
        self.report.refresh_from_db();self.assertEqual((self.report.sealed,self.report.digest),(True,parent_digest))
        self.assertEqual(require_current(self.run),before)
        row=self.prepare();self.assertEqual(require_current(self.run),before)
        self.assertTrue(all(row.metadata['images'][name]['count'] for name in module.TABLES))
        with patch.object(module,'_bpr_insert',side_effect=AssertionError('prepared replay')):
            self.assertEqual(self.prepare().digest,row.digest)
        self.assertEqual(require_current(self.run),before)

    def test_read_adapters_use_this_generation_and_missing_btr_stays_unavailable(self):
        from django.db import connection
        from mta.presentation import bpr_prepared,planning_sources
        from mta.presentation.permissions import PermissionCodes
        from mta.presentation.context import PublicationUnavailable
        self.parent();row=self.prepare();bound=self.binding(row)
        importer={name:bound.sources.rows('closing/importer/'+name) for name in ('SkuAttributeData','LocationAttributeData','SkuLocAttributeData')}
        products=PermissionCodes({source['SKUCode']:2 for source in importer['SkuAttributeData']})
        locations=PermissionCodes({source['WHCode']:3 for source in importer['LocationAttributeData']})
        with patch.object(bpr_prepared,'scope',return_value=(products,locations)), \
                patch.object(bpr_prepared,'image_query',side_effect=AssertionError('terminal source fallback')):
            with patch('mta.presentation.ancillary_live.image_query',side_effect=AssertionError('terminal live remarks')) as terminal:
                for flags in ({'count':True},{'analytics':True},{'export':True}):
                    with self.subTest(flags=flags),self.assertRaisesRegex(PublicationUnavailable,'phase_live_remarks_source_unavailable'):
                        bpr_prepared._build(self.run,{},importer,{},live_remarks=True,read_binding=bound,**flags)
                terminal.assert_not_called()
            query,params=bpr_prepared._build(self.run,{},importer,{'BPRReport_RemarkDetails':[]},count=True,read_binding=bound)
            with connection.cursor() as cursor:
                cursor.execute(query,params);count=cursor.fetchone()[0]
            expected=6*sum(record['s_ordinal'] is not None for record in bound.rows('bpr_candidates'))
            self.assertEqual(count,expected)
            with self.assertRaisesRegex(PublicationUnavailable,'source_unavailable'):
                bpr_prepared._build(self.run,{},importer,{'BPRReport_RemarkDetails':[]},export=True,read_binding=bound)
        self.assertEqual(set(planning_sources.admitted_sources(self.run,read_binding=bound)),{'bpr_master','git_master'})
        with self.assertRaises(PublicationUnavailable):planning_sources.admitted_sources(self.run)
        import uuid
        from types import SimpleNamespace
        other=SimpleNamespace(pk=uuid.uuid4())
        with self.assertRaises(PublicationUnavailable):bpr_prepared._prepared_query(other,bound)
        with self.assertRaises(PublicationUnavailable):planning_sources.admitted_sources(other,read_binding=bound)

    def test_bad_identity_sealed_mutations_and_unsealed_commit_are_denied(self):
        from django.db import connection,transaction,DatabaseError
        from mta.presentation import scoped_prepared as module
        from mta.presentation.context import PublicationUnavailable
        from mta.runtime.models import ScopeSourceProjection
        self.parent()
        with self.assertRaises(PublicationUnavailable):
            module.prepare(self.report.pk,expected_report_digest='f'*64,action_revision=0)
        with self.assertRaises(PublicationUnavailable):
            module.prepare(self.report.pk,expected_report_digest=self.report.digest,action_revision=1)
        with self.assertRaisesRegex(DatabaseError,'Unsealed scope source'),transaction.atomic():
            with module._owner(self.report.pk):
                ScopeSourceProjection.objects.create(generation=self.report,
                    report_generation_digest=self.report.digest,recipe_digest=module.recipe_digest())
            with connection.cursor() as cursor:cursor.execute('SET CONSTRAINTS scope_source_complete IMMEDIATE')
        row=self.prepare()
        with self.assertRaises(PublicationUnavailable):
            module.bind(self.report.pk,expected_digest='f'*64,expected_report_digest=self.report.digest,action_revision=0)
        tables=['fresh_mta_scopesourceprojection',*(model._meta.db_table for model,*_ in module.TABLES.values())]
        for table in tables:
            for query in ('UPDATE mta.'+table+' SET generation_id=generation_id WHERE generation_id=%s',
                          'DELETE FROM mta.'+table+' WHERE generation_id=%s','TRUNCATE mta.'+table):
                with self.subTest(query=query),self.assertRaises(DatabaseError),transaction.atomic():
                    with connection.cursor() as cursor:cursor.execute(query,[] if query.startswith('TRUNCATE') else [row.pk])
        with connection.cursor() as cursor:cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('ALTER TABLE mta.fresh_mta_scopebprcandidaterow DISABLE TRIGGER scope_source_rows_insert')
            with self.assertRaises(PublicationUnavailable):self.binding(row)
            transaction.set_rollback(True)
        self.assertTrue(self.binding(row).projection.sealed)


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedPreparedFullCoexistenceTests(unittest.TestCase):
    from tests import test_scoped_common_final_postgresql as _fixtures
    for _name in ('setUp','rollback','owner','accept','prepare_dbm','finish','publication_opening'):
        locals()[_name]=getattr(_fixtures.ScopedCommonFinalTests,_name)

    def test_same_run_full_completion_and_report_build_preserve_prepared_phase_bags(self):
        from django.db import connection
        from django.utils import timezone
        from mta.presentation import scoped_report_storage as facts,scoped_prepared as partial,operational_reports as full
        from mta.runtime.models import RunPhaseAcceptance,DailyReportGeneration
        from mta.serialization import digest
        self.owner(claim=False);self.prepare_dbm()
        phase=RunPhaseAcceptance.objects.get(run=self.run,phase='BPR')
        reports=facts.prepare(phase.pk,expected_digest=phase.digest,action_revision=0)
        projection=partial.prepare(reports.pk,expected_report_digest=reports.digest,action_revision=0)
        bound=partial.bind(reports.pk,expected_digest=projection.digest,expected_report_digest=reports.digest,action_revision=0)
        before={name:bound.rows(name) for name in partial.TABLES}
        facts_before={name:bound.reports.rows(name) for name in facts.TABLES}
        result=self.finish()
        self.assertEqual((result.pk,result.status),(reports.run_id,'SUCCEEDED'))
        # Actual unchanged Full report builder/sealer inside the rollback-only
        # component fixture; no public autocommit/native UI admission claim.
        terminal=DailyReportGeneration.objects.create(run=result,
            source_digest=result.production_digest,recipe_digest=full.recipe_identity())
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.report_generation',%s,true)",[str(result.pk)])
        terminal.metadata=full._build(result);terminal.digest=digest(terminal.metadata)
        terminal.status='READY';terminal.sealed_at=timezone.now()
        terminal.save(update_fields=['metadata','digest','status','sealed_at'])
        full.verify_rows(result,full.generation(result).metadata)
        rebound=partial.bind(reports.pk,expected_digest=projection.digest,
            expected_report_digest=reports.digest,action_revision=0)
        self.assertEqual({name:rebound.rows(name) for name in partial.TABLES},before)
        self.assertEqual({name:rebound.reports.rows(name) for name in facts.TABLES},facts_before)
        projection.refresh_from_db();self.assertEqual(projection.digest,bound.projection.digest)
        with connection.cursor() as cursor:cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')


if __name__=='__main__':unittest.main()
