"""Migration-enabled BOR persistence proof in an exclusively owned test database."""
import os
from unittest.mock import patch
from django.test import TestCase
from django.core.management import call_command
from django.db import connection,transaction,DatabaseError
from django.utils import timezone
from mta.presentation.bor_contract import RUN_ID,NATIVE_DIGEST,recipe_digest
from mta.presentation.bor_sources import admitted_sources,verify_values,MODELS
from mta.presentation.context import PublicationUnavailable
from mta.runtime.models import CalculationRun,BorSourceReceipt,BorLiveRemark
from mta.runtime.bor_source_schema import verify_guards


class BorSourcePostgresTests(TestCase):
    # TestCase rolls back fixture rows, preserving immutable-table guard semantics.
    def test_exact_publication_retry_rollback_guards_and_live_separation(self):
        self.assertEqual(connection.vendor,'postgresql')
        directory=os.environ['BOR_CAPTURE_DIR']
        run=CalculationRun.objects.create(id=RUN_ID,kind='LEGACY_UI_FIXTURE',
            status='FIXTURE_BLOCKED',business_date='2026-04-07',input_digest='test-bor-owned',
            input_payload={},execution_revision='isolated-schema-proof')
        with patch('mta.presentation.fixture.binding',return_value=(run,NATIVE_DIGEST)):
            with self.assertRaises(CommandError):
                call_command('prepare_bor_sources',verify_only=True,verbosity=0)
            # Publication rolls back completely when its enclosing transaction fails.
            with transaction.atomic():
                call_command('prepare_bor_sources',directory=directory,verbosity=0)
                self.assertEqual(len(verify_values(run)),4)
                transaction.set_rollback(True)
            self.assertFalse(BorSourceReceipt.objects.exists())
            self.assertTrue(all(not m.objects.exists() for m in MODELS.values()))
            call_command('prepare_bor_sources',directory=directory,verbosity=0)
            call_command('prepare_bor_sources',verify_only=True,verbosity=0)
            admitted_sources();verify_guards(connection)
            from mta.runtime.bor_prepared_schema import verify_guards as prepared_guards
            prepared_guards(connection)
            for table,verify in (('fresh_mta_borliveremark',verify_guards),
                                 ('fresh_mta_borpreparedrow',prepared_guards)):
                with transaction.atomic(),connection.cursor() as c:
                    c.execute('CREATE TRIGGER zz_unexpected_bor_trigger BEFORE INSERT ON mta.'+table+
                              ' FOR EACH ROW EXECUTE FUNCTION mta.deny_bor_source_mutation()')
                    with self.assertRaises(ValueError): verify(connection)
                    transaction.set_rollback(True)
                verify(connection)
            original=verify_values(run)
            self.assertEqual(BorSourceReceipt.objects.get().recipe_digest,recipe_digest())
            for model in [*MODELS.values(),BorSourceReceipt]:
                for op in ('UPDATE','DELETE','TRUNCATE'):
                    with self.assertRaises(DatabaseError),transaction.atomic(),connection.cursor() as c:
                        table=connection.ops.quote_name(model._meta.db_table)
                        sql=(f'UPDATE {table} SET run_id=run_id' if op=='UPDATE' else
                             f'DELETE FROM {table}' if op=='DELETE' else f'TRUNCATE {table}')
                        c.execute(sql)
            with self.assertRaises(DatabaseError),transaction.atomic():
                first=MODELS['SOBData'].objects.first()
                first.pk=None;first.ordinal=10000;first.save(force_insert=True)
            values=dict(run=run,actor_id='authenticated-proof',SKUCode='sku',WhCode='wh',
                SupplierCode='supplier',Remark='proof',Username='Fixture proof',RemarkDate=timezone.now())
            with self.assertRaises(DatabaseError),transaction.atomic(): BorLiveRemark.objects.create(**values)
            with connection.cursor() as c:
                c.execute("SELECT set_config('fresh.bor_actor',%s,true)",['authenticated-proof'])
            BorLiveRemark.objects.create(**values)
            BorLiveRemark.objects.create(**values)  # Equal timestamp occurrences remain distinct.
            self.assertEqual(BorLiveRemark.objects.count(),2)
            from mta.presentation import bor_remarks
            actor=dict(id='authenticated-proof',name='Trusted actor')
            key=dict(skucode='optional-remark',whcode='wh',spc='supplier')
            self.assertEqual(bor_remarks.append(dict(data=[key],user={'name':'forged'}),actor),'1')
            stored=bor_remarks.history(key)
            self.assertEqual(len(stored),1)
            self.assertNotIn('r',stored[0])
            self.assertEqual(stored[0]['un'],'Trusted actor')
            self.assertEqual(bor_remarks.history({}),[])
            before_count=BorLiveRemark.objects.count()
            for field in ('skucode','whcode','spc','remark'):
                with self.subTest(field=field),self.assertRaises(ValueError):
                    bor_remarks.append(dict(data=[{**key,field:None}]),actor)
            with self.assertRaises(ValueError):
                bor_remarks.append(dict(data=[key]),dict(actor,name=None))
            self.assertEqual(bor_remarks.append(dict(data=[{**key,'unknown':'x'}]),actor),'')
            self.assertEqual(BorLiveRemark.objects.count(),before_count)
            with self.assertRaises(KeyError):
                bor_remarks.append(dict(data=[{**key,'remark':'x'},key]),actor)
            with self.assertRaises(PublicationUnavailable):
                bor_remarks.append(dict(data=[{**key,'remark':"O'Brien"}]),actor)
            self.assertEqual(verify_values(run),original)
            self.assertEqual(run.commands.count(),0)
            with self.assertRaises(DatabaseError),transaction.atomic(): BorLiveRemark.objects.all().delete()
            with patch('mta.presentation.bor_sources.recipe_digest',return_value='changed'):
                with self.assertRaises(PublicationUnavailable): admitted_sources()
            with patch('mta.presentation.bor_sources.verify_guards',side_effect=ValueError('changed')):
                with self.assertRaises(PublicationUnavailable): admitted_sources()
            with patch('mta.presentation.fixture.binding',return_value=(run,'changed')):
                with self.assertRaises(PublicationUnavailable): admitted_sources()


from django.core.management.base import CommandError
