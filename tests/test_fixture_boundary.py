"""Explicit fixture mode must not relax ordinary production admission."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY','fixture-unit-test-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.test import override_settings
from mta.presentation import fixture,context,actions
from mta.serialization import digest


class FixtureBoundaryTest(unittest.TestCase):
    def test_disabled_mode_uses_original_selection(self):
        with override_settings(VF_MTA_FIXTURE_FILE='',VF_MTA_FIXTURE_SHA256='',VF_MTA_PUBLISHED_RUN='',VF_MTA_PUBLISHED_DIGEST=''),patch.object(fixture,'selected_run') as selected:
            with self.assertRaisesRegex(context.PublicationUnavailable,'explicit_publication_identity_required'):
                context.selected_run()
            selected.assert_not_called()

    def test_mixed_production_identity_is_denied_before_file_or_database_read(self):
        with override_settings(VF_MTA_FIXTURE_FILE='not-read',VF_MTA_FIXTURE_SHA256='pinned',VF_MTA_PUBLISHED_RUN='production',VF_MTA_PUBLISHED_DIGEST='digest'):
            with self.assertRaisesRegex(context.PublicationUnavailable,'production_settings_must_be_unset'):
                fixture.policy()

    def test_policy_bytes_are_pinned(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'policy.json';path.write_text('{}')
            with override_settings(VF_MTA_FIXTURE_FILE=str(path),VF_MTA_FIXTURE_SHA256=hashlib.sha256(b'other').hexdigest(),VF_MTA_PUBLISHED_RUN='',VF_MTA_PUBLISHED_DIGEST=''):
                with self.assertRaisesRegex(context.PublicationUnavailable,'policy_changed'):
                    fixture.policy()

    def test_engine_success_fields_are_not_fixture_provenance(self):
        policy=dict(run_id='fixture',identity='dataset',manifest_sha256='source',business_date='2026-04-07')
        payload=dict(origin='human-supplied-original-vm-backups',dataset='dataset',manifest_sha256='source')
        run=SimpleNamespace(input_payload=payload,input_digest=digest(payload),business_date='2026-04-07',execution_revision='stage2-vm-source-copy-v1',output_digest='fake-success')
        with patch.object(fixture,'policy',return_value=policy),patch.object(fixture.CalculationRun.objects,'filter') as query:
            query.return_value.first.return_value=run
            with self.assertRaisesRegex(context.PublicationUnavailable,'run_invariant_changed'):
                fixture.selected_run()

    def test_actor_identity_and_exact_gateway_grants_are_required(self):
        with patch.object(fixture,'policy',return_value={'actors':[dict(id=2,email='fixture@test',products=[1,4],locations=[25])]}):
            identity=dict(id=2,email='fixture@test')
            self.assertTrue(fixture.actor_allowed(identity,dict(product_permissions=[4,1],location_permissions=[25])))
            self.assertFalse(fixture.actor_allowed(identity,dict(product_permissions=[4,1,9],location_permissions=[25])))
            self.assertFalse(fixture.actor_allowed(dict(id=3,email='fixture@test'),dict(product_permissions=[4,1],location_permissions=[25])))

    def test_no_whole_fixture_publication(self):
        with patch.object(fixture,'enabled',return_value=True),patch.object(context,'read_outputs') as read:
            with self.assertRaisesRegex(context.PublicationUnavailable,'fixture_whole_publication_unavailable'):
                context.publication()
            read.assert_not_called()

    def test_image_cannot_point_at_another_valid_catalogue_table(self):
        path='closing/dbm/DBMMaster'
        with patch.object(fixture,'receipt',return_value=dict(image=path,table='Importer/MasterData')):
            with self.assertRaisesRegex(context.PublicationUnavailable,'image_contract_changed'):
                fixture.image_metadata(SimpleNamespace(),path)

    def test_batch_image_metadata_keeps_receipt_and_schema_validation(self):
        path='closing/dbm/DBMMaster'
        item=dict(image=path,table='DBM/DBMMaster',
                  fields=[['SKUCode','SKUCode','str']],
                  provenance={'manifest_sha256':'source'})
        cursor=unittest.mock.MagicMock()
        cursor.fetchall.return_value=[(path,json.dumps(item))]
        run=SimpleNamespace(pk='fixture',kind='LEGACY_UI_FIXTURE')
        with patch.object(fixture,'policy',return_value={'manifest_sha256':'source','run_id':'fixture'}), \
             patch.object(fixture,'enabled',return_value=True), \
             patch.object(fixture.connection,'cursor') as factory:
            factory.return_value.__enter__.return_value=cursor
            self.assertEqual(fixture.image_metadata_batch(run,[path,path]),{path:item})
        cursor.execute.assert_called_once()
        self.assertEqual(cursor.execute.call_args.args[1],[[path]])

    def test_batch_metadata_rejects_missing_changed_or_unselected_sources(self):
        path='closing/dbm/DBMMaster'
        item=dict(image=path,table='DBM/DBMMaster',fields=[['SKUCode','SKUCode','str']],
                  provenance={'manifest_sha256':'source'})
        run=SimpleNamespace(pk='fixture',kind='LEGACY_UI_FIXTURE')
        cases=[([],run,'binding_unavailable'),
               ([(path,{**item,'provenance':{'manifest_sha256':'changed'}})],run,'source_manifest_changed'),
               ([(path,{**item,'image':'wrong'})],run,'image_contract_changed'),
               ([(path,item)],SimpleNamespace(pk='other',kind='LEGACY_UI_FIXTURE'),'not_selected')]
        for rows,selected,error in cases:
            with self.subTest(error=error), \
                 patch.object(fixture,'policy',return_value={'manifest_sha256':'source','run_id':'fixture'}), \
                 patch.object(fixture,'enabled',return_value=True), \
                 patch.object(fixture.connection,'cursor') as factory:
                factory.return_value.__enter__.return_value.fetchall.return_value=rows
                with self.assertRaisesRegex(context.PublicationUnavailable,error):
                    fixture.image_metadata_batch(selected,[path])

    def test_post_pick_fixture_keeps_source_columns_and_checks_identity(self):
        from mta.presentation import pick_post_storage
        names=pick_post_storage.FIELDS[:3]
        source={**dict.fromkeys(names,'key'),'DispatchColor':'Black'}
        post={**dict.fromkeys(names,'key'),'extra':'retained'}
        run=SimpleNamespace(kind='LEGACY_UI_FIXTURE')
        with patch.object(pick_post_storage,'inputs',return_value=[source]),patch.object(fixture,'projection_rows',return_value=[post]):
            self.assertEqual(pick_post_storage.read_pick_post(run,output={},bands=[]),[{**source,**post}])
        with patch.object(pick_post_storage,'inputs',return_value=[source]),patch.object(fixture,'projection_rows',return_value=[]):
            with self.assertRaisesRegex(ValueError,'ordinal identity'):
                pick_post_storage.read_pick_post(run,output={},bands=[])

    def test_fixture_grid_pruning_preserves_native_pair_bags(self):
        a=dict(SKUCode='a',WhCode='x');b=dict(SKUCode='b',WhCode='y')
        state=dict(Suggestions=[a,b],DBMMaster=[a,a,b],NormAcceptanceTbl=[],
            SkuLocAttributeData=[dict(SKUCode='a',LocCode='x'),dict(SKUCode='b',LocCode='y')],
            LocationAttributeData=['all parent and child attributes'])
        with patch.object(context,'scope',return_value=({'a'},{'x'})):
            result=fixture.grid_subjects(state,{})
        self.assertEqual(result['DBMMaster'],[a,a])
        self.assertEqual(result['Suggestions'],[a])
        self.assertEqual(len(result['SkuLocAttributeData']),1)
        self.assertIs(result['LocationAttributeData'],state['LocationAttributeData'])
        self.assertEqual(state['Suggestions'],[a,b])

    def test_bounded_grid_matches_native_bags_nulls_missing_and_acceptance(self):
        from mta.presentation.dbm import dbm_rows
        suggestions=[dict(SKUCode=s,WhCode=l,Type=1,NewNorm=n) for s,l,n in
            [('b','y',3),('a','x',4),('b','y',5),('gone','x',6),('accepted','x',7)]]
        state=dict(Suggestions=suggestions,
            DBMMaster=[dict(SKUCode=s,WhCode=l,Norm=2,ParentWhCode=None) for s,l in
                [('a','x'),('b','y'),('b','y'),('accepted','x')]],
            NormAcceptanceTbl=[dict(SKUCode='accepted',WhCode='x')],
            SKUDescriptionTbl=[dict(SKUCode=s,SKUDescription=s+' ') for s in ('a','b','accepted')],
            SiteDescriptionTbl=[dict(WHCode=l,WHDescription=l+' ') for l in ('x','y')],
            ReasonCodes=[dict(Id=1,Reason='one '),dict(Id=1,Reason='two ')],
            SkuAttributeData=[dict(SKUCode='b',c1=None),dict(SKUCode='b',c1='')],
            SkuLocAttributeData=[dict(SKUCode='b',LocCode='y',c2='v')],
            LocationAttributeData=[dict(WHCode='y',c1=None)])
        for predicate in (None,lambda s,m,sa,la,sla:2 if s['SKUCode']=='b' else 0):
            expected=dbm_rows(state,predicate=predicate)
            self.assertTrue(expected)
            self.assertEqual(fixture.dbm_grid_rows(state,predicate=predicate),expected)
