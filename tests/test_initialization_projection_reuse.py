"""Expected projections are local to a sealed opening, never live-row proof."""
import os
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','projection-reuse-unit-only')
import django
django.setup()
from mta.mdm import initialization as init
from mta.runtime.opening_scope import opening_scope,release_opening


def owner():
    return SimpleNamespace(pk=uuid4(),source_id=7,input_digest='a',input_manifest_digest='b',
        receipt_digest='c',configuration_digest='d',recipe_sha256='e',implementation_digest='f',input_sha256='g')


class ProjectionReuseTests(TestCase):
    def test_success_only_same_seal_reuse_and_certification_release(self):
        item=owner();frame={'opening':{'state':{'marker':'persisted'}}}
        result=[('validated',)]
        with opening_scope(),patch.object(init,'owner_batches',return_value=result) as build:
            self.assertIs(init.validated_master_batches(item,frame),result)
            self.assertIs(init.validated_master_batches(item,frame),result)
            build.assert_called_once_with(frame['opening']['state'],strict=True)
            release_opening()
            self.assertIs(init.validated_master_batches(item,frame),result)
            self.assertEqual(build.call_count,2)
            item.receipt_digest='changed-seal'
            init.validated_master_batches(item,frame)
            self.assertEqual(build.call_count,3)

    def test_failed_validation_is_not_cached_and_scope_does_not_leak(self):
        item=owner();frame={'opening':{'state':{}}}
        with patch.object(init,'owner_batches',side_effect=[ValueError('bad field'),[],[]]) as build:
            with opening_scope():
                with self.assertRaisesRegex(ValueError,'bad field'):init.validated_master_batches(item,frame)
                self.assertEqual(init.validated_master_batches(item,frame),[])
            with opening_scope():init.validated_master_batches(item,frame)
            self.assertEqual(build.call_count,3)

    def test_live_master_comparison_is_not_cached(self):
        item=owner();item.source=object()
        frame={'opening':{'state':{}}}
        with opening_scope(),patch.object(init,'owner_batches',return_value=[]) as expected, \
                patch.object(init,'verify_current_masters') as compare:
            for _ in range(2):
                init.verify_current_masters(item.source,init.validated_master_batches(item,frame))
            self.assertEqual(expected.call_count,1)
            self.assertEqual(compare.call_count,2)
