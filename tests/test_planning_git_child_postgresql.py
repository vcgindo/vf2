"""Corrected child reader over real scoped seals; synthetic rollback only."""
import os
import unittest
from unittest.mock import patch
from tests import test_scoped_git_postgresql as fixtures


@unittest.skipUnless(os.environ.get('VF_PHASE_POSTGRES_PROOF') == '1', 'Owned PostgreSQL required')
class ChildScopedGitTests(unittest.TestCase):
    for _name in ('setUp', 'rollback', 'accept', 'bpr', 'positive', 'owner', 'parents', 'scopes'):
        locals()[_name] = getattr(fixtures.ScopedGitTests, _name)

    def _prove(self, empty):
        from mta.presentation import planning_git_child as reader, scoped_git, selective, daily_git_preparation
        from mta.runtime.models import RunPhaseAcceptance
        self.parents(empty=empty)
        bound = scoped_git._prepare(self.bound)
        before = list(RunPhaseAcceptance.objects.filter(run=self.run).order_by('pk').values())
        products, locations = self.scopes()
        options = dict(type='child', category='git')
        # Only permission resolution is supplied; SQL admission and all
        # source relations use the real accepted scoped generation.
        with patch.object(reader, 'scope', return_value=(products, locations)), \
                patch.object(reader, 'direct_permissions', return_value=(products, locations)), \
                patch.object(reader, 'image_query', side_effect=AssertionError('Full query')), \
                patch.object(selective, 'image_query', side_effect=AssertionError('Full source')), \
                patch.object(daily_git_preparation, 'image_query', side_effect=AssertionError('Full GIT source')):
            result = reader.grid(self.run, options, read_binding=bound)
            page = reader.grid(self.run, dict(options, paginationParameter=dict(pageNumber=1, recordsPerPage=1)), read_binding=bound)
        self.assertTrue(result['locationWise']['data'])
        groups = result['transporterWise']['data']
        if empty:
            self.assertEqual(groups, [])
        else:
            self.assertEqual(len(groups), 1)
            self.assertEqual((groups[0]['tc'], groups[0]['on']), ('T-1', 'O-1'))
            self.assertTrue(groups[0]['transit'])
            self.assertTrue(all(row['SKUCode'] == 'SUPPLIED-Z9' for row in groups[0]['transit']))
            self.assertEqual(page['transporterWise']['data'], groups)
        self.assertEqual(list(RunPhaseAcceptance.objects.filter(run=self.run).order_by('pk').values()), before)

    def test_positive_child_reader_own_scoped_seals(self):
        self._prove(False)

    def test_empty_child_reader_retains_positive_location_half(self):
        self._prove(True)
