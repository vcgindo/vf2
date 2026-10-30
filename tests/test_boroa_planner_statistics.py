"""BOROA planner maintenance never changes source admission or row recipes."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from mta.presentation import boroa_sources as sources
from mta.presentation.context import PublicationUnavailable


class Database:
    vendor='postgresql'
    in_atomic_block=True
    def __init__(self,run):
        self.builder=str(run.pk);self.read_only='off';self.marker=None
        self.xid='42';self.owns=True;self.statements=[];self.fail_table=None
    def cursor(self):return self
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def execute(self,sql,params=None):
        self.statements.append((sql,params))
        if "current_setting('fresh.daily_publication_build'" in sql:
            self.row=(self.builder,self.read_only,self.marker)
        elif sql=='SELECT txid_current()::text':self.row=(self.xid,)
        elif 'pg_get_userbyid(c.relowner)=current_user' in sql:self.row=(self.owns,)
        elif sql.startswith('ANALYZE mta.'):
            if self.fail_table and self.fail_table in sql:raise RuntimeError('statistics failed')
        elif "set_config('fresh.boroa_planner_statistics'" in sql:
            self.marker=params[0];self.row=(self.marker,)
        else:raise AssertionError('Unexpected statement: '+sql)
    def fetchone(self):return self.row
    def analyses(self):return [sql for sql,_ in self.statements if sql.startswith('ANALYZE ')]


class BorOaPlannerStatisticsTests(TestCase):
    def setUp(self):
        self.run=NS(pk=uuid4(),kind='DAILY_CHAIN')
        self.db=Database(self.run)

    def test_non_postgres_and_non_atomic_readers_do_no_work(self):
        for attribute,value in (('vendor','sqlite'),('in_atomic_block',False)):
            db=Database(self.run);setattr(db,attribute,value)
            with patch.object(sources,'connection',db):sources._prepare_statistics(self.run)
            self.assertEqual(db.statements,[])

    def test_absent_foreign_and_read_only_builders_never_analyze(self):
        for builder,read_only in ((None,'off'),('','off'),(str(uuid4()),'off'),(str(self.run.pk),'on')):
            db=Database(self.run);db.builder=builder;db.read_only=read_only
            with patch.object(sources,'connection',db):sources._prepare_statistics(self.run)
            self.assertEqual(db.analyses(),[])
            self.assertIsNone(db.marker)
            self.assertFalse(any('txid_current()' in sql for sql,_ in db.statements))

    def test_only_existing_table_owner_analyzes_exact_two_tables_once_per_transaction(self):
        with patch.object(sources,'connection',self.db):
            sources._prepare_statistics(self.run)
            sources._prepare_statistics(self.run)
        self.assertEqual(self.db.analyses(),[
            'ANALYZE mta."fresh_mta_boroasourcerow"',
            'ANALYZE mta."fresh_mta_boroarequirement"'])
        self.assertEqual(self.db.marker,str(self.run.pk)+':42')
        role_calls=[params for sql,params in self.db.statements if 'pg_get_userbyid' in sql]
        self.assertEqual(role_calls,[[['fresh_mta_boroasourcerow','fresh_mta_boroarequirement']]])

    def test_non_owner_does_not_analyze_or_claim_statistics_done(self):
        self.db.owns=False
        with patch.object(sources,'connection',self.db):sources._prepare_statistics(self.run)
        self.assertEqual(self.db.analyses(),[])
        self.assertIsNone(self.db.marker)

    def test_failure_does_not_mark_done_and_retry_repeats_both(self):
        self.db.fail_table='fresh_mta_boroarequirement'
        with patch.object(sources,'connection',self.db):
            with self.assertRaisesRegex(RuntimeError,'statistics failed'):
                sources._prepare_statistics(self.run)
            self.assertIsNone(self.db.marker)
            self.db.fail_table=None
            sources._prepare_statistics(self.run)
        self.assertEqual(len(self.db.analyses()),4)

    def test_next_transaction_or_rolled_back_marker_refreshes_again(self):
        with patch.object(sources,'connection',self.db):
            sources._prepare_statistics(self.run)
            self.db.xid='43'
            sources._prepare_statistics(self.run)
            self.db.marker=None
            sources._prepare_statistics(self.run)
        self.assertEqual(len(self.db.analyses()),6)
        self.assertEqual(self.db.marker,str(self.run.pk)+':43')

    def test_receipt_values_and_guards_remain_required_before_maintenance(self):
        events=[]
        checks={name:'digest-'+name for name in sources.DIGEST_FIELDS.values()}
        receipt=NS(source_digest='source',recipe_digest=sources.production_source_recipe(),**checks)
        with patch.object(sources,'native_binding',return_value=(self.run,'source')), \
                patch.object(sources.BorOaSourceReceipt.objects,'filter') as query, \
                patch.object(sources,'verify_values',side_effect=lambda r:(events.append('values') or checks)), \
                patch('mta.runtime.boroa_source_schema.verify_guards',side_effect=lambda db:events.append('guards')) as guards, \
                patch.object(sources,'_prepare_statistics',side_effect=lambda r:events.append('statistics')) as analyze:
            query.return_value.first.return_value=receipt
            self.assertEqual(sources.admitted_sources(self.run),(self.run,receipt))
            self.assertEqual(events,['values','guards','statistics'])
            receipt.source_digest='foreign'
            analyze.reset_mock();guards.reset_mock()
            with self.assertRaisesRegex(PublicationUnavailable,'receipt_missing_or_changed'):
                sources.admitted_sources(self.run)
            analyze.assert_not_called();guards.assert_not_called()
            receipt.source_digest='source';guards.side_effect=ValueError('guard drift')
            with self.assertRaisesRegex(PublicationUnavailable,'source_guards_changed'):
                sources.admitted_sources(self.run)
            analyze.assert_not_called()

    def test_legacy_fixture_path_is_untouched(self):
        self.run.kind='LEGACY_UI_FIXTURE'
        with patch.object(sources,'_fixture_admitted_sources',create=True,return_value='fixture'), \
                patch.object(sources,'_prepare_statistics',side_effect=AssertionError('fixture statistics')):
            self.assertEqual(sources.admitted_sources(self.run),'fixture')

    def test_existing_publication_and_bor_recipes_are_byte_stable(self):
        from mta.presentation.daily_bor_prepared import production_recipe_digest
        from mta.presentation.daily_publication import recipe_identity
        from mta.presentation.boroa_contract import production_source_recipe,production_prepared_recipe
        self.assertEqual(production_recipe_digest('bor'),'84245c98baf7f9e59b65751d72df97cade7c1f63c224ca245e9768e6ec11d525')
        self.assertEqual(production_recipe_digest('boroa'),'80ef5e1494465457bdb9ef417d44f86f591c008819f4add7aedd59f6702782fc')
        self.assertEqual(production_source_recipe(),'2d8675c62dbfa18ce749fdc17b2ef2a0ee2cbc346f22931c2385b2a6dbf8ba53')
        self.assertEqual(production_prepared_recipe(),'1f781b64208532580ce7e6be11720f7d5b7a5bbb40122bb2792d43f635376784')
        self.assertEqual(recipe_identity(),'229b0219c8fa70cb4c9e503345d1450e233d4b555c06fe5331bbdf8354d4c870')
