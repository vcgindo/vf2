"""Accepted source/query boundary, not native serving or whole-scope readiness."""
from copy import deepcopy
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_pick_files_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedSourcesTests(unittest.TestCase):
    for _name in ('setUp','rollback','owner','accept','bpr'):
        locals()[_name]=getattr(fixtures.ScopedPickFileTests,_name)

    def binding(self,**kwargs):
        from mta.presentation.scoped_sources import bind
        return bind(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0,**kwargs)

    def test_all_bound_queries_equal_actual_typed_rows_without_calculation_or_write(self):
        from django.db import connection
        from mta.serialization import storage
        from mta.runtime.models import RunPhaseAcceptance,RunScopeAttempt,ScopePickFiles
        from mta.presentation.scoped_sources import SOURCES
        self.bpr()
        before=list(RunPhaseAcceptance.objects.filter(run=self.run).values_list('id','digest'))
        with patch('mta.temporal.chain.produce_bpr',side_effect=AssertionError('business replay')):
            bound=self.binding()
            self.assertEqual(bound.display_date,self.receipt.run.business_date)
            self.assertEqual(bound.acceptance_digest,self.receipt.digest)
            for path in SOURCES:
                with self.subTest(path=path),connection.cursor() as cursor:
                    sql,params=bound.query(path)
                    cursor.execute(sql+' ORDER BY vf_ordinal',params)
                    fields=[column[0] for column in cursor.description]
                    actual=[dict(zip(fields,row)) for row in cursor.fetchall()]
                    self.assertEqual([r.pop('vf_ordinal') for r in actual],list(range(len(actual))))
                    self.assertEqual(storage(actual),bound.rows(path))
        self.assertEqual(list(RunPhaseAcceptance.objects.filter(run=self.run).values_list('id','digest')),before)
        self.assertEqual(RunScopeAttempt.objects.filter(run=self.run).count(),1)
        self.assertEqual(ScopePickFiles.objects.filter(phase__run=self.run).count(),0)
        self.run.refresh_from_db();self.assertEqual(self.run.status,'RUNNING');self.assertFalse(self.run.output_digest)

    def test_inherited_pre_image_keeps_physical_identity_and_bpr_provenance(self):
        self.bpr();bound=self.binding()
        path='closing/importer/SkuAttributeData'
        item=bound.metadata(path)
        self.assertTrue(item['image'].startswith('phase/PRE_BPR/'))
        sql,params=bound.query(path)
        self.assertEqual(params,[self.run.pk,item['image']])
        self.assertNotIn(path,params)
        provenance=bound.provenance(path)
        self.assertEqual(provenance['owner'],'accepted_BPR')
        self.assertEqual(provenance['physical_image'],item['image'])
        self.assertEqual(provenance['snapshot_digest'],self.receipt.snapshot.state_digest)
        item['digest']='changed'
        self.assertNotEqual(bound.metadata(path)['digest'],'changed')

    def test_wrong_phase_digest_action_and_missing_owners_are_unavailable(self):
        from mta.presentation.scoped_sources import bind
        from mta.presentation.context import PublicationUnavailable
        self.bpr()
        for identifier,checksum,revision in ((self.pre_receipt.pk,self.pre_receipt.digest,0),
                (self.receipt.pk,'f'*64,0),(self.receipt.pk,self.receipt.digest,1),
                (self.receipt.pk,self.receipt.digest,True)):
            with self.subTest(identifier=identifier,revision=revision),self.assertRaises(PublicationUnavailable):
                bind(identifier,expected_digest=checksum,action_revision=revision)
        bound=self.binding()
        for path in ('closing/dbm/DBMMaster','closing/btr/BufferTrendPhysicalInv',
                     'sources/bpr/InTransitData','sources/planning/OpenExpediteRequests'):
            with self.assertRaisesRegex(PublicationUnavailable,'source_unavailable'):bound.rows(path)

    def test_explicit_empty_population_is_owned_and_queryable(self):
        from django.db import connection
        from tests.production_h3_fixture import supplied_day
        def empty_orders(*args,**kwargs):
            value=supplied_day(*args,**kwargs)
            value['day']['order_feed']=[]
            return value
        with patch('tests.production_h3_fixture.supplied_day',side_effect=empty_orders):self.bpr()
        bound=self.binding()
        # Declared empty order-feed input, processed by the real producer. Its
        # typed empty result differs from the unowned transit/request sources.
        path='closing/orders/SpikeOrderData'
        self.assertEqual(bound.metadata(path)['count'],0)
        self.assertEqual(bound.rows(path),[])
        with connection.cursor() as cursor:
            cursor.execute(*bound.query(path));self.assertEqual(cursor.fetchall(),[])
            self.assertIn('OrderKey',[column[0] for column in cursor.description])

    def test_declared_duplicate_input_keeps_canonical_grouping_and_join_multiplicity(self):
        from tests.test_h3_daily_integration import frame
        from mta.serialization import storage
        from django.db import connection
        opening=frame()
        original=opening['opening']['state']['importer']['SkuAttributeData']
        original.append(deepcopy(original[0]))
        with patch('tests.test_h3_daily_integration.frame',return_value=opening):self.bpr()
        bound=self.binding();rows=bound.rows('closing/importer/SkuAttributeData')
        self.assertEqual(rows,storage(self.phase.importer['SkuAttributeData']))
        # The actual importer groups attributes by SKU. Duplicating an opening
        # row is not permission to invent a duplicate calculated attribute.
        self.assertEqual(rows.count(rows[0]),1)
        self.assertTrue(any(value is None for row in rows for value in row.values()))
        sql,params=bound.query('closing/importer/SkuAttributeData')
        with connection.cursor() as cursor:
            cursor.execute('SELECT A.* FROM ('+sql+') A CROSS JOIN generate_series(1,2) copies '
                'ORDER BY A.vf_ordinal,copies',params)
            fields=[column[0] for column in cursor.description]
            joined=[dict(zip(fields,row)) for row in cursor.fetchall()]
        for row in joined:row.pop('vf_ordinal')
        self.assertEqual(storage(joined),[row for row in rows for _ in range(2)])


if __name__=='__main__':unittest.main()
