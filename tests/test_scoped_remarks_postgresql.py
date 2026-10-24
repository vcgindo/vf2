"""Actual accepted BPR/captured/live histories; all component writes roll back."""
from dataclasses import replace
from datetime import datetime,timezone,timedelta
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_pick_files_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF')=='1','Owned PostgreSQL required')
class ScopedRemarkTests(unittest.TestCase):
    for _name in ('setUp','rollback','accept','bpr'):
        locals()[_name]=getattr(fixtures.ScopedPickFileTests,_name)

    def owner(self,**options):
        return fixtures.ScopedPickFileTests.owner(self,remark_inputs=self.snapshot,**options)

    def parents(self,*,rows=(),missing=False,counter=False):
        from mta.presentation import ancillary_live as live,scoped_report_storage as facts,scoped_prepared as prepared
        from mta.serialization import digest
        self.snapshot=None
        if not missing:
            provenance=dict(fixture='scoped-remark-component-facts-no-native-certification')
            live.initialize_owner(live.BPR,provenance_digest=digest(provenance),provenance_receipt=provenance)
            for row in rows:
                live.append(live.BPR,[{k:v for k,v in row.items() if k!='RemarkDate'}],actor_id='component',timestamp=row['RemarkDate'])
            self.snapshot=live.snapshot_all(business_date='2037-04-10',bpr_remark_horizon=13)
        self.bpr(counter=counter)
        self.report=facts.prepare(self.receipt.pk,expected_digest=self.receipt.digest,action_revision=0)
        self.projection=prepared.prepare(self.report.pk,expected_report_digest=self.report.digest,action_revision=0)

    def binding(self,**options):
        from mta.presentation.scoped_prepared import bind
        return bind(self.report.pk,expected_digest=self.projection.digest,expected_report_digest=self.report.digest,
            action_revision=0,**dict(dict(include_remarks=True),**options))

    @staticmethod
    def row(remark,stamp,**changes):
        from tests.production_h3_fixture import CHILD
        return dict(SKUCode='SUPPLIED-Z9',WhCode=CHILD,Remark=remark,Username=None,RemarkDate=stamp,**changes)

    def test_capture_later_prefix_dates_null_text_duplicate_ties_and_exact_query(self):
        from mta.presentation import ancillary_live as live
        from mta.serialization import storage
        from django.db import connection
        cutoff=datetime(2037,3,28,tzinfo=timezone.utc)
        retained=cutoff+timedelta(seconds=1)
        initial=[self.row('excluded',cutoff),self.row(None,retained),self.row('same time',retained)]
        self.parents(rows=initial)
        bound=self.binding();before=bound.read_identity
        expected=storage(initial[1:]);self.assertEqual(bound.remarks.rows(),expected)
        bound.remarks.verify_rows()
        live.append(live.BPR,[{k:v for k,v in self.row('later-boundary',cutoff).items() if k!='RemarkDate'}],actor_id='later',timestamp=cutoff)
        later=datetime(2037,4,11,tzinfo=timezone.utc)  # legacy has no upper-date cutoff
        value=self.row('later-visible',later)
        live.append(live.BPR,[{k:v for k,v in value.items() if k!='RemarkDate'}],actor_id='later',timestamp=later)
        self.assertEqual(bound.remarks.rows(),expected);self.assertEqual(bound.read_identity,before)
        fresh=self.binding();self.assertNotEqual(fresh.read_identity,before)
        self.assertEqual(fresh.remarks.rows(),storage([*initial[1:],value]))
        with connection.cursor() as cursor:
            query,params=fresh.remarks.query();cursor.execute('SELECT * FROM ('+query+') R ORDER BY vf_ordinal',params)
            names=[c[0] for c in cursor.description];rows=[dict(zip(names,r)) for r in cursor.fetchall()]
        self.assertEqual([r.pop('vf_source_ordinal') for r in rows],[1,2,4])
        self.assertEqual([r.pop('vf_ordinal') for r in rows],[0,1,3])
        self.assertEqual(storage(rows),fresh.remarks.rows())
        self.assertIn('ordinal<%s',query)

    def test_owned_empty_and_default_independence_read_counter_neutrality(self):
        from mta.runtime.scope_revisions import require_current
        from unittest.mock import patch
        self.parents(counter=True);before=require_current(self.run)
        ordinary=self.binding(include_remarks=False)
        with patch('mta.presentation.scoped_remarks.models.BprCapturedRemark.objects.filter',side_effect=AssertionError('row hydration in admission')):
            bound=self.binding()
        self.assertIsNone(ordinary.remarks);self.assertEqual(bound.remarks.rows(),[])
        bound.remarks.verify_rows()
        self.assertEqual(bound.projection.digest,ordinary.projection.digest)
        self.assertEqual(bound.reports.generation.digest,ordinary.reports.generation.digest)
        self.assertEqual(require_current(self.run),before)
        self.assertEqual(self.binding().read_identity,bound.read_identity)

    def test_late_guard_admitted_capture_insert_cannot_change_bound_rows(self):
        from mta.runtime.ancillary_models import BprCapturedRemark
        from mta.presentation.context import PublicationUnavailable
        self.parents(rows=[self.row('original',datetime(2037,4,9,tzinfo=timezone.utc))])
        bound=self.binding();before=bound.read_identity;rows=bound.remarks.rows()
        # The original writer verifies the complete captured bag. Its immutable
        # prefix remains usable even though the RUNNING insert guard admits a
        # surplus ordinal; this adapter makes no whole-table sealing claim.
        bound.remarks.verify_rows()
        BprCapturedRemark.objects.create(capture_id=bound.remarks.capture_id,
            ordinal=bound.remarks.row_count,source_ordinal=bound.remarks.watermark,
            **self.row('surplus',datetime(2037,4,11,tzinfo=timezone.utc)))
        self.assertEqual(bound.remarks.rows(),rows)
        self.assertEqual(bound.read_identity,before)
        self.assertEqual(self.binding().remarks.rows(),rows)
        with self.assertRaises(PublicationUnavailable):bound.remarks.verify_rows()

    def test_missing_capture_denies_without_touching_independent_bags(self):
        from mta.presentation.context import PublicationUnavailable
        self.parents(missing=True)
        independent=self.binding(include_remarks=False)
        before={name:independent.rows(name) for name in ('bpr_candidates','bpr_master','git_master')}
        with self.assertRaises(PublicationUnavailable):self.binding()
        independent=self.binding(include_remarks=False)
        self.assertEqual({name:independent.rows(name) for name in before},before)

    def test_wrong_configuration_capture_owner_and_guard_changes_are_denied(self):
        from mta.presentation import scoped_remarks
        from mta.presentation.context import PublicationUnavailable
        from django.db import connection,transaction
        self.parents();bound=self.binding()
        with self.assertRaises(PublicationUnavailable):scoped_remarks.bind(bound.sources,configuration_digest='f'*64)
        from copy import copy
        import uuid
        wrong=copy(bound.sources.run);wrong.pk=uuid.uuid4()
        with self.assertRaises(PublicationUnavailable):scoped_remarks.bind(replace(bound.sources,run=wrong),configuration_digest=self.report.configuration_digest)
        with connection.cursor() as cursor:cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')
        for sql in ('ALTER TABLE mta.fresh_mta_bprcapturedremark DISABLE TRIGGER daily_capture_immutable',
                    'ALTER FUNCTION mta.guard_daily_live_remark() SECURITY DEFINER'):
            with self.subTest(sql=sql),transaction.atomic():
                with connection.cursor() as cursor:cursor.execute(sql)
                with self.assertRaises(PublicationUnavailable):self.binding()
                transaction.set_rollback(True)
        self.assertEqual(self.binding().remarks.rows(),[])

    def test_actual_wrong_capture_cutoff_and_live_owner_are_denied(self):
        from mta.presentation import ancillary_live as live
        from mta.presentation.context import PublicationUnavailable
        from mta.serialization import digest
        from django.db import transaction
        original=live.snapshot_all
        for mismatch in ('cutoff','owner'):
            def supplied(**options):
                snapshots=original(**options);snapshot=snapshots[live.BPR]
                if mismatch=='cutoff':
                    snapshot['cutoff']=(datetime.fromisoformat(snapshot['cutoff'])-timedelta(days=1)).isoformat()
                else:
                    snapshot['provenance_receipt']={'fixture':'different-captured-owner'}
                    snapshot['provenance_digest']=digest(snapshot['provenance_receipt'])
                return snapshots
            with self.subTest(mismatch=mismatch),transaction.atomic():
                with patch.object(live,'snapshot_all',side_effect=supplied):self.parents()
                self.assertIsNone(self.binding(include_remarks=False).remarks)
                with self.assertRaises(PublicationUnavailable):self.binding()
                transaction.set_rollback(True)

    def test_bpr_count_grid_and_export_consume_exact_bound_latest_ties(self):
        from mta.presentation import bpr_prepared as reader,ancillary_live
        from mta.presentation.permissions import PermissionCodes
        from django.db import connection
        stamp=datetime(2037,4,9,tzinfo=timezone.utc)
        self.parents(rows=[self.row(None,stamp),self.row('tied',stamp)])
        bound=self.binding(include_inherited_btr=True)
        attrs={name:bound.sources.rows('closing/importer/'+name) for name in ('SkuAttributeData','LocationAttributeData')}
        products=PermissionCodes({r['SKUCode']:1 for r in attrs['SkuAttributeData']})
        locations=PermissionCodes({r['WHCode']:1 for r in attrs['LocationAttributeData']})
        def execute(bound,**flags):
            query,params=reader._build(self.run,{},attrs,{},live_remarks=True,read_binding=bound,**flags)
            with connection.cursor() as cursor:
                cursor.execute(query,params);names=[c[0] for c in cursor.description]
                return [dict(zip(names,r)) for r in cursor.fetchall()]
        with patch.object(reader,'scope',return_value=(products,locations)),patch.object(ancillary_live,'image_query',side_effect=AssertionError('terminal live query')):
            base=self.binding(include_remarks=False,include_inherited_btr=True)
            # Independent complete unchanged-row comparison: use the ordinary
            # explicit captured dictionary branch to establish expected output.
            def expected(**flags):
                query,params=reader._build(self.run,{},attrs,{'BPRReport_RemarkDetails':bound.remarks.rows()},
                    read_binding=base,**flags)
                with connection.cursor() as c:
                    c.execute(query,params);names=[d[0] for d in c.description]
                    return [dict(zip(names,r)) for r in c.fetchall()]
            for flags in ({'count':True},{'paging':(1,10000)},{'export':True}):
                with self.subTest(flags=flags):self.assertEqual(execute(bound,**flags),expected(**flags))
            live_value=self.row('newest',datetime(2037,4,12,tzinfo=timezone.utc))
            ancillary_live.append(ancillary_live.BPR,[{k:v for k,v in live_value.items() if k!='RemarkDate'}],actor_id='later',timestamp=live_value['RemarkDate'])
            self.assertEqual(execute(bound,count=True),expected(count=True))
            fresh=self.binding(include_inherited_btr=True)
            self.assertNotEqual(execute(fresh,count=True),execute(bound,count=True))


if __name__=='__main__':unittest.main()
