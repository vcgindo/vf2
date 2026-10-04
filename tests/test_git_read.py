"""Terminal admission guards; synthetic unit probes are not logistics parity."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY', 'unit-test-not-serving')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from mta.presentation import git_read
from mta.presentation.context import PublicationUnavailable


class GitAdmissionTests(unittest.TestCase):
    def test_every_consumer_requires_explicit_terminal_admission(self):
        for consumer in (git_read.grid, git_read.custom, git_read.graph):
            with self.subTest(consumer=consumer.__name__), \
                 patch.object(git_read, 'selected_run', return_value=SimpleNamespace(kind="DAILY_CHAIN")), \
                 patch.object(git_read, 'terminal_ancillary', side_effect=PublicationUnavailable('scope_mismatch')), \
                 patch.object(git_read, 'image_rows', side_effect=AssertionError('read before admission')), \
                 self.assertRaisesRegex(PublicationUnavailable, 'scope_mismatch'):
                consumer(dict(type='child'))

    def test_positive_or_nonempty_transit_is_never_reported_as_empty(self):
        for rationed, transit in (([dict(GIT=1)], []), ([dict(GIT=0)], [dict(SKUCode='337')])):
            with self.subTest(rationed=rationed, transit=transit), \
                 patch.object(git_read, 'selected_run', return_value=SimpleNamespace(kind="DAILY_CHAIN")), \
                 patch.object(git_read, 'terminal_ancillary', return_value=dict(InTransitData=transit)), \
                 patch.object(git_read, 'image_rows', return_value=rationed), \
                 self.assertRaisesRegex(PublicationUnavailable, 'nonempty_transit'):
                git_read.terminal_context({})

    def test_zero_population_does_not_hide_invalid_child_count_filter(self):
        context = SimpleNamespace(attributes={})
        payload = dict(filters=dict(productFilter=dict(filters=[dict(attributeName='p2',operator='equalto',value='Selected')])))
        git_read.validate_filters(payload, context)
        with self.assertRaisesRegex(PublicationUnavailable, 'child transporter count'):
            git_read.validate_filters(payload, context, child_count=True)


if __name__ == '__main__': unittest.main()

