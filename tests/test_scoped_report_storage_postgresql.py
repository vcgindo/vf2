"""Actual PostgreSQL phase fact ownership/coexistence; all fixtures roll back."""
import os
import unittest
from unittest.mock import patch

from tests import test_scoped_pick_files_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopeReportStorageTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner','accept','bpr'):
        locals()[_name]=getattr(fixtures.ScopedPickFileTests,_name)

    def prepare(self):
        from mta.presentation.scoped_report_storage import prepare
        return prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)

    def binding(self,row):
        from mta.presentation.scoped_report_storage import bind
        return bind(row.pk,expected_digest=row.digest,action_revision=0)

    def test_complete_cells_queries_empty_nulls_and_idempotent_repeat(self):
        from django.db import connection
        from mta.presentation import scoped_reports
        from mta.presentation.scoped_report_storage import TABLES
        from mta.runtime.models import ScopeReportGeneration,DailyReportGeneration
        from mta.serialization import storage
        self.bpr()
        _metadata,expected=scoped_reports.produce(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        row=self.prepare();bound=self.binding(row)
        for name in TABLES:
            with self.subTest(name=name),connection.cursor() as cursor:
                self.assertEqual(bound.rows(name),expected[name])
                sql,params=bound.query(name);cursor.execute(sql+' ORDER BY R.ordinal',params)
                fields=[column[0] for column in cursor.description]
                actual=[dict(zip(fields,record)) for record in cursor.fetchall()]
                for i,record in enumerate(actual):
                    self.assertEqual(record.pop('run_id'),self.run.pk)
                    self.assertEqual(record.pop('ordinal'),i)
                self.assertEqual(storage(actual),expected[name])
        self.assertEqual(bound.rows('ExcessInventoryDetails'),[])
        self.assertTrue(bound.rows('ExpediteDispatches'))
        self.assertTrue(all(record['BRAge'] is None for record in bound.rows('ExpediteDispatches')))
        with patch('mta.presentation.excess.produce',side_effect=AssertionError('producer replay')):
            repeated=self.prepare()
        self.assertEqual((repeated.pk,repeated.digest),(row.pk,row.digest))
        self.assertEqual(ScopeReportGeneration.objects.filter(run=self.run).count(),1)
        self.assertFalse(DailyReportGeneration.objects.filter(run=self.run).exists())

    def test_failed_late_write_rolls_back_generation_and_all_bags(self):
        from mta.presentation.scoped_report_storage import TABLES
        from mta.runtime.models import ScopeReportGeneration,ScopeExpediteRow,RunPhaseAcceptance
        self.bpr()
        prefix=list(RunPhaseAcceptance.objects.filter(run=self.run).values_list('id','digest'))
        with patch.object(ScopeExpediteRow.objects,'bulk_create',side_effect=OSError('late fact write failure')), \
                self.assertRaisesRegex(OSError,'late fact write failure'):
            self.prepare()
        self.assertFalse(ScopeReportGeneration.objects.filter(run=self.run).exists())
        for model,_fields in TABLES.values():self.assertEqual(model.objects.count(),0)
        self.assertEqual(list(RunPhaseAcceptance.objects.filter(run=self.run).values_list('id','digest')),prefix)
        self.assertTrue(self.prepare().sealed)

    def test_wrong_digest_phase_action_and_missing_generation_are_denied(self):
        from mta.presentation.scoped_report_storage import prepare,bind
        from mta.presentation.context import PublicationUnavailable
        import uuid
        self.bpr();row=self.prepare()
        for identifier,checksum,revision in ((self.pre_receipt.pk,self.pre_receipt.digest,0),
                (self.receipt.pk,'f'*64,0),(self.receipt.pk,self.receipt.digest,1)):
            with self.subTest(identifier=identifier,revision=revision),self.assertRaises(PublicationUnavailable):
                prepare(identifier,expected_digest=checksum,action_revision=revision)
        with self.assertRaises(PublicationUnavailable):bind(row.pk,expected_digest='f'*64,action_revision=0)
        with self.assertRaises(PublicationUnavailable):bind(uuid.uuid4(),expected_digest=row.digest,action_revision=0)

    def test_all_five_derived_fact_writes_leave_actual_input_counters_unchanged(self):
        """Actual SQL counters through explicit metadata carrier, not native certification."""
        from mta.runtime.scope_revisions import require_current
        from mta.runtime.models import ScopeReportGeneration,ScopeExpediteRow
        from mta.presentation.scoped_report_storage import TABLES
        from tests.production_h3_fixture import supplied_day,PARENT
        def excess_input(*args,**kwargs):
            value=supplied_day(*args,**kwargs)
            for fact in value['day']['raw_daily']:
                if fact['WhCode']==PARENT:
                    # Retained opening stock40, no consumption:40+960=1000.
                    # Explicit external fact delta exercises positive Excess.
                    fact.update(Stock=1000,Receipts=960)
            return value
        with patch('tests.production_h3_fixture.supplied_day',side_effect=excess_input):self.bpr(counter=True)
        before=require_current(self.run)
        with patch.object(ScopeExpediteRow.objects,'bulk_create',side_effect=OSError('counter rollback')), \
                self.assertRaisesRegex(OSError,'counter rollback'):
            self.prepare()
        self.assertFalse(ScopeReportGeneration.objects.filter(run=self.run).exists())
        self.assertEqual(require_current(self.run),before)
        row=self.prepare();bound=self.binding(row)
        for name in TABLES:self.assertTrue(bound.rows(name),name)
        self.assertEqual(require_current(self.run),before)
        with patch('mta.presentation.excess.produce',side_effect=AssertionError('producer replay')):
            self.assertEqual(self.prepare().pk,row.pk)
        self.assertEqual(require_current(self.run),before)

    def test_sql_immutability_and_empty_table_insert_denial(self):
        from django.db import connection,transaction,DatabaseError
        from mta.presentation.scoped_report_storage import TABLES
        self.bpr();row=self.prepare()
        statements=[('UPDATE mta.fresh_mta_scopereportgeneration SET digest=digest WHERE id=%s',[row.pk]),
            ('DELETE FROM mta.fresh_mta_scopereportgeneration WHERE id=%s',[row.pk]),
            ('TRUNCATE mta.fresh_mta_scopereportgeneration',[]),
            ('INSERT INTO mta.fresh_mta_scopeexcessrow (generation_id,ordinal) VALUES (%s,0)',[row.pk])]
        for model,_fields in TABLES.values():
            table='mta.'+connection.ops.quote_name(model._meta.db_table)
            statements.append(('TRUNCATE '+table,[]))
            if model.objects.filter(generation=row).exists():
                statements.extend([('UPDATE '+table+' SET ordinal=ordinal WHERE generation_id=%s',[row.pk]),
                                   ('DELETE FROM '+table+' WHERE generation_id=%s',[row.pk])])
        for sql,params in statements:
            with self.subTest(sql=sql),self.assertRaises(DatabaseError),transaction.atomic():
                with connection.cursor() as cursor:cursor.execute(sql,params)
        self.assertEqual(self.binding(row).rows('ExcessInventoryDetails'),[])

    def test_unsealed_generation_cannot_commit_and_guard_drift_denies_binding(self):
        from django.db import connection,transaction,DatabaseError
        from mta.runtime.models import ScopeReportGeneration
        from mta.presentation import scoped_report_storage as module,scoped_sources
        from mta.presentation.context import PublicationUnavailable
        self.bpr()
        sources=scoped_sources.bind(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        candidate=ScopeReportGeneration(run=sources.run,phase=self.receipt,action_revision=0,
            source_digest=sources.source_digest,recipe_digest=module.recipe_digest(),
            configuration_digest=self.receipt.snapshot.manifest['references']['profile'])
        with self.assertRaisesRegex(DatabaseError,'Unsealed scope report'),transaction.atomic():
            with module._owner(candidate.pk):candidate.save(force_insert=True)
            with connection.cursor() as cursor:cursor.execute('SET CONSTRAINTS scope_report_complete IMMEDIATE')
        self.assertFalse(ScopeReportGeneration.objects.filter(pk=candidate.pk).exists())
        row=self.prepare()
        with connection.cursor() as cursor:cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
        for sql in ('ALTER TABLE mta.fresh_mta_scopeexpediterow DISABLE TRIGGER scope_report_rows_insert',
                    'ALTER FUNCTION mta.guard_scope_report_generation() SECURITY DEFINER'):
            with self.subTest(sql=sql),transaction.atomic():
                with connection.cursor() as cursor:cursor.execute(sql)
                with self.assertRaises(PublicationUnavailable):self.binding(row)
                transaction.set_rollback(True)
        self.assertTrue(self.binding(row).generation.sealed)

    def test_scope_scalar_fields_match_terminal_contracts(self):
        from mta.runtime import models
        from mta.presentation.scoped_report_storage import TABLES
        terminals=dict(ExcessInventoryDetails=models.ExcessInventoryRow,
            OrderFulfillmentSummary=models.FulfillmentSummaryRow,
            OrderFulfillmentDetails=models.FulfillmentDetailRow,
            ExpediteDispatches=models.ExpediteRow,PickPost=models.PickPostRow)
        for name,(model,fields) in TABLES.items():
            for field in fields:
                scoped=model._meta.get_field(field);full=terminals[name]._meta.get_field(field)
                with self.subTest(report=name,field=field):
                    self.assertEqual(scoped.deconstruct()[1:],full.deconstruct()[1:])


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopeReportFullCoexistenceTests(unittest.TestCase):
    from tests import test_scoped_common_final_postgresql as _fixtures
    for _name in ('setUp','rollback','owner','accept','prepare_dbm','finish','publication_opening'):
        locals()[_name]=getattr(_fixtures.ScopedCommonFinalTests,_name)

    def test_same_run_phase_facts_then_full_preparation_preserves_phase_facts(self):
        from django.db import connection
        from django.utils import timezone
        from mta.presentation import scoped_report_storage as partial,operational_reports as full
        from mta.runtime.models import RunPhaseAcceptance,DailyReportGeneration,ExpediteRow
        from mta.serialization import digest
        self.owner(claim=False);self.prepare_dbm()
        phase=RunPhaseAcceptance.objects.get(run=self.run,phase='BPR')
        generation=partial.prepare(phase.pk,expected_digest=phase.digest,action_revision=0)
        bound=partial.bind(generation.pk,expected_digest=generation.digest,action_revision=0)
        before={name:bound.rows(name) for name in partial.TABLES}
        result=self.finish()
        self.assertEqual(result.pk,generation.run_id);self.assertEqual(result.status,'SUCCEEDED')
        # Existing Full prepare() owns autocommit. This rollback-only component
        # invokes its unchanged actual builder/sealer inside the outer fixture
        # transaction; it does not claim public command qualification.
        terminal=DailyReportGeneration.objects.create(run=result,
            source_digest=result.production_digest,recipe_digest=full.recipe_identity())
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('fresh.report_generation',%s,true)",[str(result.pk)])
        terminal.metadata=full._build(result);terminal.digest=digest(terminal.metadata)
        terminal.status='READY';terminal.sealed_at=timezone.now()
        terminal.save(update_fields=['metadata','digest','status','sealed_at'])
        full.verify_rows(result,full.generation(result).metadata)
        self.assertTrue(ExpediteRow.objects.filter(run=result).exists())
        rebound=partial.bind(generation.pk,expected_digest=generation.digest,action_revision=0)
        self.assertEqual({name:rebound.rows(name) for name in partial.TABLES},before)
        generation.refresh_from_db();self.assertEqual(generation.digest,bound.generation.digest)
        self.assertTrue(all(row['BRAge'] is None for row in rebound.rows('ExpediteDispatches')))
        with connection.cursor() as cursor:cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')


if __name__=='__main__':unittest.main()
