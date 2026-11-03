from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from django.db import connection, transaction, DatabaseError
from django.test import TestCase
from django.utils import timezone

from mta.presentation import btr_reference_projection as projection, btr_snapshot_storage as snapshot
from mta.presentation.btr_calendar_sources import advance
from mta.presentation.context import PublicationUnavailable
from mta.runtime.models import BtrReportingGeneration, DailyReportGeneration
from mta.runtime import test_btr_calendar_guards as fixtures
from mta.serialization import digest


class ReferenceProjectionTests(TestCase):
    def test_scratch_order_and_typed_values_have_distinct_dispositions(self):
        with connection.cursor() as c:
            c.execute("""CREATE TEMP TABLE ref_source AS SELECT * FROM mta.fresh_mta_btrjoinreference WITH NO DATA""")
            c.execute("""CREATE TEMP TABLE ref_display AS SELECT * FROM mta.fresh_mta_btrpresentationrow WITH NO DATA""")
            gen = SimpleNamespace(pk='3383dc18-0331-43a0-ae32-d910459a78d9',
                                  lineage={'images':{'tech_A':{'count':2},'eco_A':{'count':0}}})
            c.execute("""INSERT INTO ref_display(id,generation_id,branch,filter_a_skucode,a_ordinal,sla_ordinal)
                         VALUES(10,%s,'tech','S ',4,8),(12,%s,'tech','Q',1,3)""", [gen.pk,gen.pk])
            c.execute("""INSERT INTO ref_source(id,generation_id,branch,export,sku_code,a_ordinal,sla_ordinal)
                         SELECT d.id+100*e::int,d.generation_id,d.branch,e,d.filter_a_skucode,d.a_ordinal,
                                CASE WHEN NOT e THEN d.sla_ordinal END
                         FROM ref_display d CROSS JOIN (VALUES(false),(true)) k(e)""")
            with patch.object(projection,'TABLE','pg_temp.ref_display'):
                def check():
                    return projection.certify(None,gen,'pg_temp.ref_source',{'tech':2,'eco':0})
                self.assertEqual(check()['bounds']['tech'], (10,12))
                c.execute('UPDATE ref_source SET id=220-id WHERE export')
                with self.assertRaises(projection.RequiresPhysicalReferences):
                    check()
                c.execute("UPDATE ref_source SET sku_code='' WHERE export AND sku_code='S '")
                with self.assertRaisesMessage(PublicationUnavailable,'occurrences_differ'):
                    check()

    def test_seal_requires_own_derived_report_population_and_bounds(self):
        fixture = fixtures.BtrDirectoryGuardTests()
        run = fixture.create_run(date(2026,4,8))
        derived = fixture.start(run,3)
        with connection.cursor() as c:
            c.execute("SELECT set_config('fresh.report_generation',%s,true)", [str(run.pk)])
        metadata = dict(schema='fresh-derived-report-generation-v3', btr_calendar=advance(run),
                        images={snapshot.PATH:snapshot.save(run,[])})
        DailyReportGeneration.objects.filter(pk=derived.pk).update(metadata=metadata,digest=digest(metadata),
                                                                   status='READY',sealed_at=timezone.now())
        lineage = dict(version=4,run=str(run.pk),production_digest=run.production_digest,
                       output_digest=run.output_digest,dated_report_digest=digest(metadata),
                       images={'tech_A':{'count':0},'eco_A':{'count':0}})
        values = dict(run=run,version=4,source_kind=run.kind,business_date=run.business_date,source_digest=digest(lineage))
        with self.assertRaisesMessage(DatabaseError,'own completed dated source'), transaction.atomic():
            BtrReportingGeneration.objects.create(**values,lineage=dict(lineage,dated_report_digest='a'*64))
        generation = BtrReportingGeneration.objects.create(**values,lineage=lineage)
        proof = dict(format=projection.FORMAT,bounds=dict(tech=[None,None],eco=[None,None]))
        def seal(proof):
            BtrReportingGeneration.objects.filter(pk=generation.pk).update(status='READY',eligible=True,
                completed_at=timezone.now(),rows_digest=digest([]),row_count=0,
                qualification=dict(reference_projection=proof,populations=dict(tech=0,eco=0)))
        with self.assertRaisesMessage(DatabaseError,'bounds, population'), transaction.atomic():
            seal(dict(proof,bounds=dict(tech=[0,0],eco=[None,None])))
        seal(proof)
        with self.assertRaises(DatabaseError), transaction.atomic():
            BtrReportingGeneration.objects.filter(pk=generation.pk).update(qualification={})
