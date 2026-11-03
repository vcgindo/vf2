"""Real PostgreSQL rollback-only storage tests, independent of daily activation."""
from contextlib import closing
from datetime import date

from django.db import connection,transaction,DatabaseError
from django.test import TestCase

from mta.serialization import digest
from mta.runtime.test_rationing_cut_guards import RationingCutGuardTests as Fixture
from mta.runtime.dated_history_delta import FAMILIES,fields
from mta.runtime.dated_history_reader import read_cut,iter_occurrences,iter_image,table
from mta.runtime.dated_history_writer import seal_anchor_rows,write_delta,opening_path
from mta.runtime.state_cut_models import OperationalStateCut


def row(family,stamp):
    result = dict.fromkeys(fields(family))
    result.update(SKUCode='sku ',**{('WHCode' if '/bpr/' in family else 'WhCode'):'wh',FAMILIES[family][0]:stamp})
    return result


class DatedHistoryStorageTests(TestCase):
    seal_initialization = Fixture.seal_initialization
    new_run = Fixture.new_run
    tearDown = Fixture.tearDown

    def setUp(self):
        with connection.cursor() as cursor:
            cursor.execute('SELECT current_user')
            self.assertEqual(cursor.fetchone(),('vectorflow_mta_owner',))
            cursor.execute('SET CONSTRAINTS history_cut_complete DEFERRED')
        Fixture.setUp(self)
        self.opening = {f:[row(f,'2026-07-09'),row(f,'2026-07-09'),row(f,'2026-07-10'),
                           row(f,None if FAMILIES[f][2] else '2026-07-08')] for f in FAMILIES}
        for section in ('dbm','bpr'):
            self.raw['opening']['state'][section] = {f.rsplit('/',1)[1]:r for f,r in self.opening.items() if f.split('/')[1]==section}
        self.owner.input_digest=digest(self.raw)
        self.owner.save(update_fields=['input_digest'])
        pending = {f:OperationalStateCut.objects.create(initialization=self.owner,family=f,position=0,
            input_digest=self.owner.input_digest,settings_digest=self.owner.configuration_digest) for f in FAMILIES}
        self.seal_initialization()
        from mta.runtime.opening_storage import iter_image as opening_rows
        for f,c in pending.items():
            item=self.owner.input_payload['images'][opening_path(f)]
            anchor=dict(owner_kind='INITIALIZATION',owner_id=str(self.owner.pk),manifest_digest=self.owner.input_manifest_digest,
                        image=item['image'],digest=item['digest'],count=item['count'])
            if self._testMethodName == 'test_anchor_rejects_same_count_substitution' and f.endswith('/OrderData'):
                changed=[dict(r) for r in self.opening[f]]
                changed[0]['SKUCode']='substitution'
                with self.assertRaisesRegex(ValueError,'source values/type/order/count'):
                    seal_anchor_rows(c,item,changed,anchor)
                with connection.cursor() as cursor:
                    cursor.execute('SELECT count(*) FROM '+table(f)+' WHERE cut_id=%s',[c.pk])
                    self.assertEqual(cursor.fetchone(),(0,))
            with closing(opening_rows(self.owner,item)) as rows:
                seal_anchor_rows(c,item,rows,anchor)
        self.anchors={f:read_cut(c.pk) for f,c in pending.items()}
        self.constraints()

    def constraints(self):
        with connection.cursor() as cursor:
            cursor.execute('SET CONSTRAINTS history_cut_complete IMMEDIATE')
            cursor.execute('SET CONSTRAINTS history_cut_complete DEFERRED')

    def test_anchor_rejects_same_count_substitution(self):
        # setUp checks the failing transport and its empty rolled-back prefix,
        # then proves the exact original source still seals on that connection.
        f='closing/dbm/OrderData'
        self.assertEqual([r for _,r in iter_occurrences(self.anchors[f])],self.opening[f])

    def pending(self,run,parent):
        return OperationalStateCut.objects.create(initialization=self.owner,family=parent.body['family'],
            position=parent.position+1,parent_id=parent.identity,run=run,input_digest=run.input_digest,
            settings_digest=self.owner.configuration_digest)

    def accept(self,run,images):
        from django.utils import timezone
        from mta.runtime.mdm_daily_models import MdmDailyInputCapture
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.mdm_consuming_run',%s,true)",[str(run.pk)])
        MdmDailyInputCapture.objects.filter(run=run).update(status='CONSUMED',consumed_at=timezone.now())
        run.production_manifest=dict(version=3,images=images)
        run.production_digest=digest(run.production_manifest)
        run.status='SUCCEEDED'
        run.save(update_fields=['production_manifest','production_digest','status'])
        self.constraints()

    def test_all_families_first_own_successor_old_reads_and_only_new_payloads(self):
        from mta.runtime.dated_history_audit import audit_cut,audit_image
        from mta.runtime.accepted_state_read import load_accepted_image
        from mta.runtime.state_image_read import load_image as audited_image
        from mta.presentation.selective import image_field
        run=self.new_run()
        images={};cuts={};expected={}
        for f,parent in self.anchors.items():
            expected[f]=self.opening[f][:2]+self.opening[f][3:]+[row(f,'2026-07-10')]*2
            c=self.pending(run,parent)
            images[f]=write_delta(c,parent,expected[f],today=run.business_date,
                                  horizon=30 if f.endswith('/DailyConsumption') else None)
            cuts[f]=c
        self.accept(run,images)
        next_run=self.new_run(predecessor=run,business_date=date(2026,7,11))
        next_images={}
        for f,c in cuts.items():
            parent=read_cut(c.pk)
            self.assertEqual(list(iter_image(run,images[f])),expected[f])
            new=self.pending(next_run,parent)
            next_images[f]=write_delta(new,parent,expected[f]+[row(f,'2026-07-11')],today=next_run.business_date,
                                       horizon=30 if f.endswith('/DailyConsumption') else None)
        self.accept(next_run,next_images)
        for f in FAMILIES:
            self.assertEqual([v for _,v in iter_occurrences(self.anchors[f])],self.opening[f])
            self.assertEqual(list(iter_image(run,images[f])),expected[f])
            self.assertEqual(list(iter_image(next_run,next_images[f])),expected[f]+[row(f,'2026-07-11')])
            self.assertEqual(list(load_accepted_image(run,images[f])),expected[f])
            self.assertEqual(list(audited_image(next_run,next_images[f])),expected[f]+[row(f,'2026-07-11')])
            self.assertEqual(image_field(run,f,'SKUCode'),[r['SKUCode'] for r in expected[f]])
            self.assertEqual(audit_cut(self.anchors[f])['facts'],4)
            self.assertEqual(audit_image(run,images[f])['facts'],6)
            audited=audit_image(next_run,next_images[f])
            self.assertEqual((audited['cuts'],audited['facts'],audited['removals']),(3,7,1))
            with connection.cursor() as cursor:
                cursor.execute('SELECT born_position,count(*) FROM '+table(f)+' GROUP BY born_position ORDER BY born_position')
                self.assertEqual(cursor.fetchall(),[(0,4),(1,2),(2,1)])

    def test_late_invalid_fact_rolls_back_flushed_writes_and_closures(self):
        f='closing/dbm/OrderData';parent=self.anchors[f];run=self.new_run();c=self.pending(run,parent)
        keep=self.opening[f][:2]+self.opening[f][3:]
        with self.assertRaisesRegex(ValueError,'current retained producer'):
            write_delta(c,parent,keep+[row(f,'2026-07-10')]*501+[row(f,'2026-07-11')],today=run.business_date)
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*),count(closing_cut_id) FROM '+table(f))
            self.assertEqual(cursor.fetchone(),(4,0))
        # Same connection and same pending owner remain usable after rollback.
        item=write_delta(c,parent,keep+[row(f,'2026-07-10')],today=run.business_date)
        self.accept(run,{f:item})
        self.assertEqual(list(iter_image(run,item)),keep+[row(f,'2026-07-10')])

    def test_payload_mutation_delete_truncate_and_runtime_writes_refused(self):
        f='closing/dbm/OrderData'
        for statement in ('UPDATE '+table(f)+' SET "SKUCode"=\'different\'',
                          'DELETE FROM '+table(f),'TRUNCATE '+table(f)):
            with self.subTest(statement=statement),self.assertRaises(DatabaseError),transaction.atomic(),connection.cursor() as cursor:
                cursor.execute(statement)
        with connection.cursor() as cursor:
            cursor.execute('SET LOCAL ROLE vectorflow_mta_runtime')
            try:
                cursor.execute('SELECT current_user')
                self.assertEqual(cursor.fetchone(),('vectorflow_mta_runtime',))
                with self.assertRaises(DatabaseError),transaction.atomic():
                    cursor.execute('UPDATE '+table(f)+' SET end_position=1')
            finally:
                cursor.execute('SET LOCAL ROLE vectorflow_mta_owner')
        self.assertEqual([r for _,r in iter_occurrences(self.anchors[f])],self.opening[f])

    def test_pending_cut_and_wrong_family_or_date_refused(self):
        f='closing/dbm/OrderData';parent=self.anchors[f];run=self.new_run();c=self.pending(run,parent)
        with self.assertRaisesMessage(DatabaseError,'Unsealed history cut'),transaction.atomic():
            self.constraints()
        for target,stamp in ((table('closing/dbm/DailyConsumption'),'2026-07-10'),(table(f),'2026-07-11')):
            date_column='ReportDate' if 'dailyconsumption' in target else 'ImportDate'
            with self.subTest(target=target),self.assertRaises(DatabaseError),transaction.atomic(),connection.cursor() as cursor:
                cursor.execute('INSERT INTO '+target+' (cut_id,vf_ordinal,initialization_id,born_position,"'+date_column+'")'
                               ' VALUES (%s,0,%s,1,%s)',[c.pk,self.owner.pk,stamp])

    def test_foreign_family_closure_rationing_misuse_and_sealed_write_refused(self):
        f='closing/dbm/OrderData';parent=self.anchors[f];run=self.new_run();c=self.pending(run,parent)
        other=self.pending(run,self.anchors['closing/dbm/DailyConsumption'])
        with self.assertRaises(DatabaseError),transaction.atomic(),connection.cursor() as cursor:
            cursor.execute('UPDATE '+table(f)+' SET end_position=1,closing_cut_id=%s WHERE vf_ordinal=0',[other.pk])
        from tests.test_rationing_delta import row as rationing_row
        from mta.runtime.rationing_delta import Fact,Occurrence
        from mta.runtime.rationing_writer import _facts
        with self.assertRaisesMessage(DatabaseError,'Rationing family differs'),transaction.atomic():
            _facts(c,[Fact(Occurrence(1,0),rationing_row('2026-07-10'))])
        keep=self.opening[f][:2]+self.opening[f][3:]
        item=write_delta(c,parent,keep+[row(f,'2026-07-10')],today=run.business_date)
        with self.assertRaisesMessage(DatabaseError,'already sealed'),transaction.atomic(),connection.cursor() as cursor:
            cursor.execute('INSERT INTO '+table(f)+' (cut_id,vf_ordinal,initialization_id,born_position,"ImportDate")'
                           ' VALUES (%s,99,%s,1,%s)',[c.pk,self.owner.pk,run.business_date])
        # Pending other-family cut is intentionally rolled back with this test.

    def test_independent_audit_detects_writer_verifier_payload_fault(self):
        from dataclasses import replace
        from unittest.mock import patch
        from mta.runtime import dated_history_writer as writer
        from mta.runtime.dated_history_delta import Fact
        from mta.runtime.dated_history_audit import audit_image,audit_cut
        f='closing/dbm/OrderData';parent=self.anchors[f];run=self.new_run();c=self.pending(run,parent)
        keep=self.opening[f][:2]+self.opening[f][3:]
        flush,seal=writer._flush,writer._seal
        def corrupt(cut,events):
            flush(cut,[replace(e,values=dict(e.values,SKUCode='fault')) if type(e) is Fact else e for e in events])
        def faulty_verifier(cut,parent,descriptor,counts,checks,anchor=None):
            with patch.object(writer,'stored_digests',return_value=checks):
                return seal(cut,parent,descriptor,counts,checks,anchor)
        with patch.object(writer,'_flush',corrupt),patch.object(writer,'_seal',faulty_verifier):
            item=write_delta(c,parent,keep+[row(f,'2026-07-10')],today=run.business_date)
        self.accept(run,{f:item})
        with self.assertRaisesMessage(ValueError,'audit facts values/type/order differ'):
            audit_image(run,item)
        self.assertEqual(audit_cut(parent)['facts'],4)

    def test_expiry_sparse_order_projection_and_foreign_image_refusal(self):
        f='closing/dbm/DailyConsumption';parent=self.anchors[f];run=self.new_run()
        # horizon=1 removes Jul9 and earlier, replaces Jul10, retains NULL.
        expected=[self.opening[f][-1],row(f,'2026-07-10')]
        c=self.pending(run,parent);item=write_delta(c,parent,expected,today=run.business_date,horizon=1)
        self.accept(run,{f:item})
        current=read_cut(c.pk)
        self.assertEqual([(o.position,o.ordinal) for o,_ in iter_occurrences(current)],[(0,3),(1,0)])
        self.assertEqual([r for _,r in iter_occurrences(current,names=['ReportDate'])],
                         [{'ReportDate':None},{'ReportDate':'2026-07-10'}])
        with self.assertRaises(ValueError):list(iter_image(run,dict(item,count=99)))
        with self.assertRaises(ValueError):list(iter_image(run,dict(item,image='closing/dbm/OrderData')))

    def test_actual_reader_adapters_sparse_dense_and_filtered_orders(self):
        from mta.runtime import accepted_state_read,state_image_read,runtime_report_sources
        from mta.presentation import selective,dbm_read
        from mta.runtime.relational_state import quote,wire_value
        f='closing/dbm/DailyConsumption';parent=self.anchors[f];run=self.new_run()
        # Expired physical ordinals 0/1/2 must not become consumer gaps. New
        # duplicate facts keep their occurrence order, including raw pair keys.
        expected=[self.opening[f][-1],row(f,'2026-07-10'),row(f,'2026-07-10'),
                  dict(row(f,'2026-07-10'),SKUCode='SKU '),
                  dict(row(f,'2026-07-10'),SKUCode='sku'),
                  dict(row(f,'2026-07-10'),WhCode='WH')]
        c=self.pending(run,parent);item=write_delta(c,parent,expected,today=run.business_date,horizon=1)
        self.accept(run,{f:item})
        # This unregistered storage fixture has owner access only. Normal
        # runtime SELECT capability is qualified with packaged admission.
        for reader in (accepted_state_read.load_accepted_image,accepted_state_read.iter_accepted_image,
                       state_image_read.load_image,state_image_read.iter_image):
            self.assertEqual(list(reader(run,item)),expected)
            with self.assertRaises(ValueError):list(reader(run,item,table_registry={}))
        self.assertEqual(list(selective.image_rows(run,f)),expected)
        self.assertEqual(selective.image_field(run,f,'ReportDate'),[r['ReportDate'] for r in expected])
        typed=runtime_report_sources.image_rows(run,item,expected_table='DBM/DailyConsumption',
            fields=('SKUCode','WhCode'))
        self.assertEqual(list(typed),[{k:r[k] for k in ('SKUCode','WhCode')} for r in expected])
        sql,params=selective.image_query(run,f)
        with connection.cursor() as cursor:
            cursor.execute('SELECT vf_ordinal,'+','.join(quote(c) for _,c,_ in item['fields'])+
                           ' FROM ('+sql+') S ORDER BY vf_ordinal',params)
            rows=cursor.fetchall()
        self.assertEqual([r[0] for r in rows],list(range(len(expected))))
        self.assertEqual([{n:wire_value(v,k) for (n,_,k),v in zip(item['fields'],r[1:])} for r in rows],expected)
        sql,params=selective.image_query(run,f,required_fields=('ReportDate',))
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM ('+sql+') S ORDER BY vf_ordinal',params)
            self.assertEqual(cursor.fetchall(),list(enumerate(
                date.fromisoformat(r['ReportDate']) if r['ReportDate'] else None for r in expected)))
        observed=[]
        def watch(execute,sql,params,many,context):
            if 'history_dbm_dailyconsumption' in sql:observed.append(sql)
            return execute(sql,params,many,context)
        with connection.execute_wrapper(watch):
            actual=dbm_read._selected_rows(run,f,{'SKUCode':'sku ','WhCode':'wh'},
                cutoff='2026-07-10',date_field='ReportDate')
        self.assertEqual(actual,expected[:3])
        self.assertEqual(len(observed),1)
        self.assertNotIn('row_number',observed[0].lower())
        self.assertIn('ORDER BY S.born_position,S.vf_ordinal',observed[0])
        self.assertEqual(dbm_read._selected_rows(run,f,{'SKUCode':'missing','WhCode':'wh'}),[])
        with self.assertRaises(ValueError):
            selective.image_query(run,f,metadata=dict(item,count=0))
        with self.assertRaises(ValueError):
            selective.image_query(run,f,required_fields=('not_a_field',))
        from types import SimpleNamespace
        with self.assertRaises(ValueError):
            accepted_state_read.load_accepted_image(SimpleNamespace(pk=self.owner.pk),item)

    def test_large_actual_order_producer_and_execution_local_ordinal_cache(self):
        from mta.domain.dbm_ingestion import import_orders
        from mta.application.native_output_contracts import native_assignments
        from mta.runtime.dated_history_reader import load_image
        from mta.row_sequences import RecordRows
        f='closing/dbm/OrderData';parent=self.anchors[f];run=self.new_run()
        raw=[dict(row(f,'2026-07-10'),OrderID=str(n),OrderQuantity=1,OrderDate='2026-07-10') for n in range(10001)]
        with native_assignments():
            expected=import_orders(run.business_date,self.opening[f],raw)
        c=self.pending(run,parent);item=write_delta(c,parent,expected,today=run.business_date)
        self.accept(run,{f:item})
        accepted=load_image(run,item)
        self.assertIsInstance(accepted,RecordRows)
        queries=[]
        def observe(execute,sql,params,many,context):
            if 'history_dbm_orderdata' in sql and sql.lstrip().upper().startswith('SELECT'):
                queries.append(sql)
            return execute(sql,params,many,context)
        with connection.execute_wrapper(observe):
            # Existing indexed private spool is the explicit ordinal consumer
            # contract; no global cache and no per-pair database request.
            ordinal=accepted.ordinal_source()
            self.assertEqual([ordinal[i] for i in (10003,0,5000,1,9999)],[expected[i] for i in (10003,0,5000,1,9999)])
            self.assertIs(accepted.ordinal_source(),ordinal)
        self.assertEqual(len(queries),1)
        successor=self.new_run(predecessor=run,business_date=date(2026,7,11))
        current=[dict(raw[0],ImportDate='2026-07-11',OrderDate='2026-07-11')]
        with native_assignments():
            produced=import_orders(successor.business_date,accepted,current)
        self.assertEqual(produced,expected+current)
        next_cut=self.pending(successor,read_cut(c.pk))
        next_item=write_delta(next_cut,read_cut(c.pk),produced,today=successor.business_date)
        self.accept(successor,{f:next_item})
        with connection.cursor() as cursor:
            cursor.execute('SELECT count(*) FROM '+table(f)+' WHERE cut_id=%s',[next_cut.pk])
            self.assertEqual(cursor.fetchone(),(1,))
        self.assertEqual(list(iter_image(successor,next_item)),produced)
