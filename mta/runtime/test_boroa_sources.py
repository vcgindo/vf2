"""Migration-enabled BOR-OA source/guard/action proof on an owned PostgreSQL DB."""
import os
from unittest.mock import patch
from django.test import TestCase
from django.core.management import call_command,CommandError
from django.db import connection,transaction,DatabaseError
from mta.presentation.boroa_contract import RUN_ID,NATIVE_DIGEST,source_recipe
from mta.presentation.boroa_sources import verify_values,MODELS
from mta.runtime.models import CalculationRun
from mta.runtime.boroa_models import BorOaSourceReceipt,BorOaLiveRemark
from mta.runtime.boroa_source_schema import verify_guards

class BorOaSourcePostgresTests(TestCase):
    def test_exact_source_atomicity_guards_and_separate_actions(self):
        self.assertEqual(connection.vendor,'postgresql')
        run=CalculationRun.objects.create(id=RUN_ID,kind='LEGACY_UI_FIXTURE',status='FIXTURE_BLOCKED',business_date='2026-04-07',input_digest='boroa-owned-proof',input_payload={},execution_revision='schema-proof')
        with patch('mta.presentation.fixture.binding',return_value=(run,NATIVE_DIGEST)):
            with self.assertRaises(CommandError):call_command('prepare_boroa_sources',verify_only=True,verbosity=0)
            with transaction.atomic():
                call_command('prepare_boroa_sources',directory=os.environ['BOROA_CAPTURE_DIR'],verbosity=0)
                self.assertEqual(len(verify_values(run)),3);transaction.set_rollback(True)
            self.assertFalse(BorOaSourceReceipt.objects.exists())
            self.assertTrue(all(not model.objects.exists() for model in MODELS.values()))
            call_command('prepare_boroa_sources',directory=os.environ['BOROA_CAPTURE_DIR'],verbosity=0)
            call_command('prepare_boroa_sources',verify_only=True,verbosity=0)
            verify_guards(connection)
            from mta.runtime.boroa_prepared_schema import verify_guards as prepared_guards
            prepared_guards(connection)
            receipt=BorOaSourceReceipt.objects.get();self.assertEqual(receipt.recipe_digest,source_recipe())
            for model in [*MODELS.values(),BorOaSourceReceipt]:
                for op in ['UPDATE','DELETE','TRUNCATE']:
                    with self.assertRaises(DatabaseError),transaction.atomic(),connection.cursor() as c:
                        table=connection.ops.quote_name(model._meta.db_table)
                        c.execute('UPDATE '+table+' SET run_id=run_id' if op=='UPDATE' else op+(' FROM ' if op=='DELETE' else ' ')+table)
            with self.assertRaises(DatabaseError),transaction.atomic():
                first=MODELS['BORWithOrderAllocation'].objects.first();first.pk=None;first.ordinal=100000;first.save(force_insert=True)
            with transaction.atomic(),connection.cursor() as c:
                c.execute('CREATE TRIGGER unexpected_boroa BEFORE INSERT ON mta.fresh_mta_boroaliveremark FOR EACH ROW EXECUTE FUNCTION mta.deny_boroa_source_mutation()')
                with self.assertRaises(ValueError):verify_guards(connection)
                transaction.set_rollback(True)
            from mta.presentation import boroa_remarks
            with patch('mta.presentation.boroa_remarks.admitted_sources',return_value=(run,receipt)):
                actor=dict(id='proof',name='Trusted actor');key=dict(skucode='sku',whcode='wh',spc='supplier')
                self.assertEqual(boroa_remarks.append(dict(data=[key],user={'name':'forged'}),actor),'1')
                history=boroa_remarks.history(key);self.assertEqual(history[0]['un'],'Trusted actor');self.assertNotIn('r',history[0])
                for field in ('skucode','whcode','spc','remark'):
                    with self.assertRaises(ValueError):boroa_remarks.append(dict(data=[{**key,field:None}]),actor)
                self.assertEqual(boroa_remarks.append(dict(data=[{**key,'unknown':'x'}]),actor),'')
                self.assertEqual(BorOaLiveRemark.objects.count(),1)
                with self.assertRaises(DatabaseError),transaction.atomic():BorOaLiveRemark.objects.all().delete()
                self.assertEqual(verify_values(run)['history_digest'],receipt.history_digest)
