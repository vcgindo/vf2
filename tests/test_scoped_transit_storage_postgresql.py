"""Real typed scoped transit preparation; all supplied component writes roll back."""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_transit_postgresql as fixtures
from tests import test_scoped_common_final_postgresql as final_fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopeTransitStorageTests(unittest.TestCase):
    for _name in ('setUp','rollback','accept','bpr','positive'):
        locals()[_name]=fixtures.ScopedTransitTests.__dict__[_name]
    for _name in ('prepare_dbm','finish','publication_opening'):
        locals()[_name]=final_fixtures.ScopedCommonFinalTests.__dict__[_name]

    def owner(self,**options):
        from tests import test_h3_daily_integration as supplied
        from tests.production_h3_fixture import SEASON,CHILD
        opening=supplied.frame()
        if getattr(self,'full_factor',False):
            opening['opening']['state']['dbm']['VFSettings'].append(
                dict(Parameter='SuperDelayFactor',Value='2',Description='Declared matching Full test setting'))
        if getattr(self,'action_case',False):
            for state,name in ((opening['opening']['state']['dbm'],'Suggestions'),
                    (opening['opening']['state']['controls'],'suggestions')):
                state[name]=[dict(SKUCode=SEASON,WhCode=CHILD,Type=1,NewNorm=24)]
        with patch.object(supplied,'frame',return_value=opening):
            fixtures.ScopedTransitTests.owner(self,**options)

    def prepare(self,revision=0):
        from mta.presentation.scoped_transit_storage import prepare
        return prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=revision)

    def binding(self,row,revision=0):
        from mta.presentation.scoped_transit_storage import bind
        return bind(row.pk,expected_digest=row.digest,action_revision=revision)

    def test_complete_typed_cells_order_sql_relations_and_idempotent_repeat(self):
        from django.db import connection
        from mta.presentation import scoped_transit,scoped_transit_storage as module
        from mta.runtime.models import ScopeTransitGeneration,DailyTransitRaw,DailyTransitRow
        from mta.serialization import storage
        self.positive(duplicates=True,quantity=-3);self.bpr()
        metadata,expected=scoped_transit.produce(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        row=self.prepare();bound=self.binding(row)
        self.assertEqual(row.metadata['transit'],metadata)
        for name in module.TABLES:
            self.assertTrue(expected[name],name)
            self.assertEqual(bound.rows(name),storage(expected[name]))
            bound.verify_rows(name)
            query,params=bound.query(name)
            with connection.cursor() as cursor:
                cursor.execute(query+' ORDER BY R.ordinal',params);fields=[c[0] for c in cursor.description]
                actual=[dict(zip(fields,record)) for record in cursor.fetchall()]
            for i,record in enumerate(actual):
                self.assertEqual(record.pop('run_id'),self.run.pk);self.assertEqual(record.pop('ordinal'),i)
            self.assertEqual(storage(actual),storage(expected[name]))
        for path,name in module.PATHS.items():
            query,params=bound.image_query(path)
            with connection.cursor() as cursor:
                cursor.execute(query+' ORDER BY vf_ordinal',params);fields=[c[0] for c in cursor.description]
                actual=[dict(zip(fields,r)) for r in cursor.fetchall()]
            self.assertEqual([r.pop('vf_ordinal') for r in actual],list(range(len(actual))))
            self.assertEqual(storage(actual),bound.rows(name))
        with patch('mta.application.daily_transit.validate_goods_in_transit',side_effect=AssertionError('transit replay')):
            self.assertEqual(self.prepare().pk,row.pk)
        self.assertEqual(ScopeTransitGeneration.objects.filter(run=self.run).count(),1)
        self.assertFalse(DailyTransitRaw.objects.filter(run=self.run).exists())
        self.assertFalse(DailyTransitRow.objects.filter(run=self.run).exists())

    def test_failed_last_bag_rolls_back_all_rows_and_leaves_input_counters_neutral(self):
        from mta.presentation.scoped_transit_storage import TABLES
        from mta.runtime.models import ScopeTransitGeneration,ScopeTransitDiagnostic,RunPhaseAcceptance
        from mta.runtime.scope_revisions import require_current
        self.positive(quantity=-3);self.bpr(counter=True)
        before=require_current(self.run)
        prefix=list(RunPhaseAcceptance.objects.filter(run=self.run).values_list('id','digest'))
        with patch.object(ScopeTransitDiagnostic.objects,'bulk_create',side_effect=OSError('late transit failure')), \
                self.assertRaisesRegex(OSError,'late transit failure'):self.prepare()
        self.assertFalse(ScopeTransitGeneration.objects.filter(run=self.run).exists())
        for model,_ in TABLES.values():self.assertEqual(model.objects.count(),0)
        self.assertEqual(require_current(self.run),before)
        row=self.prepare();self.assertEqual(require_current(self.run),before)
        self.assertEqual(self.prepare().digest,row.digest);self.assertEqual(require_current(self.run),before)
        self.assertEqual(list(RunPhaseAcceptance.objects.filter(run=self.run).values_list('id','digest')),prefix)

    def test_owned_empty_seal_late_insert_and_sql_mutation_denials(self):
        from tests.test_production_source_inputs import source_day
        from django.db import connection,transaction,DatabaseError
        from mta.presentation.scoped_transit_storage import TABLES
        self.transit_sources=source_day()['producer_sources']
        self.transit_sources['shipments']['rows']=[];self.transit_sources['transporters']['rows']=[]
        self.bpr();row=self.prepare();bound=self.binding(row)
        for name in TABLES:self.assertEqual(bound.rows(name),[])
        statements=[('UPDATE mta.fresh_mta_scopetransitgeneration SET digest=digest WHERE id=%s',[row.pk]),
            ('DELETE FROM mta.fresh_mta_scopetransitgeneration WHERE id=%s',[row.pk]),
            ('TRUNCATE mta.fresh_mta_scopetransitgeneration',[])]
        for model,_ in TABLES.values():
            table='mta.'+connection.ops.quote_name(model._meta.db_table)
            statements.append(('TRUNCATE '+table,[]))
        for sql,params in statements:
            with self.subTest(sql=sql),self.assertRaises(DatabaseError),transaction.atomic():
                with connection.cursor() as cursor:cursor.execute(sql,params)
        for name,(model,_) in TABLES.items():
            values=dict(generation=row,ordinal=0)
            if name=='TransitRejectedMaster':values.update(SKUCode='SUPPLIED-Z9',WhCode='OWN-WH8',
                RejectionDate='2037-04-10T00:00:00',ReasonCode=-166)
            with self.subTest(name=name),self.assertRaisesRegex(DatabaseError,'unsealed generation'),transaction.atomic():
                model.objects.create(**values)
        self.assertTrue(self.binding(row).generation.sealed)

    def test_nonempty_rows_update_delete_and_unsealed_commit_are_denied(self):
        from django.db import connection,transaction,DatabaseError
        from mta.presentation import scoped_transit_storage as module,scoped_sources
        from mta.runtime.models import ScopeTransitGeneration
        self.positive(quantity=-3);self.bpr();row=self.prepare()
        for model,_ in module.TABLES.values():
            table='mta.'+connection.ops.quote_name(model._meta.db_table)
            for sql in ('UPDATE '+table+' SET ordinal=ordinal WHERE generation_id=%s',
                    'DELETE FROM '+table+' WHERE generation_id=%s'):
                with self.assertRaisesRegex(DatabaseError,'immutable'),transaction.atomic():
                    with connection.cursor() as cursor:cursor.execute(sql,[row.pk])
        sources=scoped_sources.bind(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        candidate=ScopeTransitGeneration(run=self.run,phase=self.receipt,action_revision=0,
            source_digest=sources.source_digest,configuration_digest=row.configuration_digest,recipe_digest='e'*64)
        with self.assertRaisesRegex(DatabaseError,'Unsealed scope transit'),transaction.atomic():
            with module._owner(candidate.pk):candidate.save(force_insert=True)
            with connection.cursor() as cursor:cursor.execute('SET CONSTRAINTS scope_transit_complete IMMEDIATE')
        self.assertFalse(ScopeTransitGeneration.objects.filter(pk=candidate.pk).exists())

    def test_wrong_identity_missing_sources_and_guard_drift_deny(self):
        import uuid
        from django.db import connection,transaction
        from mta.presentation import scoped_transit_storage as module
        from mta.presentation.context import PublicationUnavailable
        self.positive();self.bpr();row=self.prepare()
        for phase,checksum,revision in ((self.pre_receipt.pk,self.pre_receipt.digest,0),
                (self.receipt.pk,'f'*64,0),(self.receipt.pk,self.receipt.digest,1)):
            with self.assertRaises(PublicationUnavailable):
                module.prepare(phase,expected_digest=checksum,action_revision=revision)
        with self.assertRaises(PublicationUnavailable):module.bind(uuid.uuid4(),expected_digest=row.digest,action_revision=0)
        with self.assertRaises(PublicationUnavailable):module.bind(row.pk,expected_digest='f'*64,action_revision=0)
        with patch.object(module,'recipe_digest',return_value='f'*64),self.assertRaises(PublicationUnavailable):self.binding(row)
        with connection.cursor() as cursor:cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
        for sql in ('ALTER TABLE mta.fresh_mta_scopetransitrow DISABLE TRIGGER scope_transit_rows_insert',
                'ALTER FUNCTION mta.guard_scope_transit_generation() SECURITY DEFINER',
                'ALTER TABLE mta.fresh_mta_scopetransitdiagnostic ALTER COLUMN "RejectionDate" '
                'TYPE timestamp with time zone'):
            with transaction.atomic():
                with connection.cursor() as cursor:cursor.execute(sql)
                with self.assertRaises(PublicationUnavailable):self.binding(row)
                transaction.set_rollback(True)
        self.assertTrue(self.binding(row).generation.sealed)

    def test_real_sleep_invalidates_fresh_bind_but_retains_inflight_generation(self):
        from mta.runtime.scope_execution import _setting,_close_attempt
        from mta.runtime.scoped_actions import record
        from mta.presentation.context import PublicationUnavailable
        from tests.production_h3_fixture import SEASON,CHILD
        self.action_case=True;self.positive();self.bpr();row=self.prepare();bound=self.binding(row)
        before={name:bound.rows(name) for name in ('InTransitData','GoodsInTransitTransporterMaster','TransitRejectedMaster')}
        with _setting('fresh.scope_worker',self.attempt.worker_token):
            _close_attempt(self.attempt,self.run,'RELEASED',{})
        event=record(self.run.pk,phase_id=self.receipt.pk,phase_digest=self.receipt.digest,
            expected_revision=0,operation='SLEEP',selected=[[SEASON,CHILD]],timestamp='2037-04-10T10:00:00',
            actor='owned-transit-component',idempotency_key='transit-sleep')
        self.assertTrue(event.state_sealed)
        with self.assertRaises(PublicationUnavailable):self.binding(row)
        fresh=self.prepare(event.pk);self.assertNotEqual(fresh.pk,row.pk)
        self.assertEqual({name:bound.rows(name) for name in before},before)
        self.assertEqual({name:self.binding(fresh,event.pk).rows(name) for name in before},before)

    def test_optional_prepared_binding_uses_exact_transit_and_bpr_wire(self):
        from django.db import connection
        from mta.presentation import scoped_prepared,scoped_report_storage as facts,bpr_prepared as reader
        from mta.presentation.permissions import PermissionCodes
        from mta.presentation.context import PublicationUnavailable
        self.positive(duplicates=True);self.bpr();transit=self.prepare()
        report=facts.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        prepared=scoped_prepared.prepare(report.pk,expected_report_digest=report.digest,action_revision=0)
        options=dict(expected_digest=prepared.digest,expected_report_digest=report.digest,action_revision=0,
            include_inherited_btr=True)
        ordinary=scoped_prepared.bind(report.pk,**options)
        bound=scoped_prepared.bind(report.pk,**options,transit_generation_id=transit.pk,expected_transit_digest=transit.digest)
        self.assertIsNone(ordinary.read_identity['transit'])
        self.assertEqual(bound.read_identity['transit']['digest'],transit.digest)
        with self.assertRaises(PublicationUnavailable):ordinary.image_query('sources/bpr/InTransitData')
        for extra in (dict(transit_generation_id=transit.pk),dict(expected_transit_digest=transit.digest),
                dict(transit_generation_id=transit.pk,expected_transit_digest='f'*64)):
            with self.assertRaises(PublicationUnavailable):scoped_prepared.bind(report.pk,**options,**extra)
        attrs={name:bound.sources.rows('closing/importer/'+name) for name in ('SkuAttributeData','LocationAttributeData')}
        products=PermissionCodes({r['SKUCode']:1 for r in attrs['SkuAttributeData']})
        locations=PermissionCodes({r['WHCode']:1 for r in attrs['LocationAttributeData']})
        with patch.object(reader,'scope',return_value=(products,locations)):
            query,params=reader._build(self.run,{},attrs,{'BPRReport_RemarkDetails':[]},paging=(1,10000),
                daily_transit=True,read_binding=bound)
            with connection.cursor() as cursor:
                cursor.execute(query,params);names=[c[0] for c in cursor.description]
                records=[dict(zip(names,r)) for r in cursor.fetchall()]
        colours={(r['SKUCode'],r['WHCode']):r['_base_eco'] for r in records}
        wire=list(reader._with_transit(records,{'InTransitData':bound.transit.rows('InTransitData')}))
        selected=[r for r in wire if (r['SKUCode'],r['WHCode'])==('SUPPLIED-Z9','OWN-WH8')]
        self.assertTrue(selected)
        expected=dict(lc='O-1',cd='2037-04-08',slt=None,tlt=1,ag=2,eta=None,cl=None,qty=4,remarks=None,
            exeecocolor=colours['SUPPLIED-Z9','OWN-WH8'])
        self.assertTrue(all(r['intransit']==[expected,expected] for r in selected))
        self.positive();self.bpr();other=self.prepare()
        with self.assertRaisesRegex(PublicationUnavailable,'read_owner_differs'):
            scoped_prepared.bind(report.pk,**options,transit_generation_id=other.pk,expected_transit_digest=other.digest)

    def test_same_run_partial_then_actual_full_keeps_original_partial_rows(self):
        from mta.runtime.models import RunPhaseAcceptance,DailyTransitRow,ScopeTransitRow
        from mta.presentation import scoped_transit_storage as module
        self.full_factor=True;self.positive();self.owner(claim=False);self.prepare_dbm()
        self.receipt=RunPhaseAcceptance.objects.get(run=self.run,phase='BPR')
        row=self.prepare();bound=self.binding(row);before={name:bound.rows(name) for name in module.TABLES}
        finished=self.finish()
        self.assertEqual((finished.pk,finished.status),(row.run_id,'SUCCEEDED'))
        self.assertTrue(DailyTransitRow.objects.filter(run=finished).exists())
        self.assertTrue(ScopeTransitRow.objects.filter(generation=row).exists())
        self.assertEqual({name:self.binding(row).rows(name) for name in before},before)
        row.refresh_from_db();self.assertEqual(row.digest,bound.generation.digest)

    def test_transit_model_scalar_contract_matches_existing_terminal_rows(self):
        from mta.runtime.models import ScopeTransitRow,DailyTransitRow
        from mta.application.daily_transit import TRANSIT_FIELDS
        for field in TRANSIT_FIELDS:
            self.assertEqual(ScopeTransitRow._meta.get_field(field).deconstruct()[1:],
                DailyTransitRow._meta.get_field(field).deconstruct()[1:])

    def test_diagnostic_sql_datetime_retains_wall_clock_under_non_utc_timezone(self):
        from datetime import datetime,timezone
        from django.db import connection
        from django.test import override_settings
        from mta.runtime.models import ScopeTransitDiagnostic
        self.positive(quantity=-3);self.bpr()
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL TIME ZONE 'Pacific/Auckland'")
            cursor.execute("SELECT format_type(atttypid,atttypmod),attnotnull FROM pg_attribute "
                "WHERE attrelid='mta.fresh_mta_scopetransitdiagnostic'::regclass AND attname='RejectionDate'")
            self.assertEqual(cursor.fetchone(),('timestamp without time zone',True))
        with override_settings(TIME_ZONE='Asia/Kolkata'):
            row=self.prepare();bound=self.binding(row)
        self.assertEqual(bound.rows('TransitRejectedMaster')[0]['RejectionDate'],'2037-04-10T00:00:00')
        actual=ScopeTransitDiagnostic.objects.get(generation=row).RejectionDate
        self.assertEqual(actual,datetime(2037,4,10));self.assertIsNone(actual.tzinfo)
        field=ScopeTransitDiagnostic._meta.get_field('RejectionDate')
        with self.assertRaisesRegex(ValueError,'timezone-free'):
            field.get_prep_value(datetime(2037,4,10,tzinfo=timezone.utc))
