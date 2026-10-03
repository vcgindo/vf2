import os
import unittest
from contextlib import nullcontext
from unittest.mock import MagicMock, patch

os.environ.setdefault('VF_SECRET_KEY', 'unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
import django
django.setup()
from mta.presentation import fixture_count_plan as plan


class FixtureCountPlanTests(unittest.TestCase):
    def test_restores_prior_settings_inside_atomic_boundary(self):
        cursor=MagicMock();cursor.fetchone.return_value=('3','on')
        with patch.object(plan.transaction,'atomic',return_value=nullcontext()) as atomic, \
             patch.object(plan.connection,'cursor') as factory:
            factory.return_value.__enter__.return_value=cursor
            with plan.count_cursor(True) as active:
                self.assertIs(active,cursor)
            atomic.assert_called_once()
        calls=cursor.execute.call_args_list
        self.assertEqual(calls[1].args,('SET LOCAL max_parallel_workers_per_gather=0',))
        self.assertEqual(calls[2].args,('SET LOCAL enable_nestloop=off',))
        self.assertEqual(calls[-1].args[1],('3','on'))

    def test_normal_and_grid_readers_do_not_set_planner_options(self):
        cursor=MagicMock()
        with patch.object(plan.transaction,'atomic') as atomic,patch.object(plan.connection,'cursor') as factory:
            factory.return_value.__enter__.return_value=cursor
            with plan.count_cursor(False) as active:self.assertIs(active,cursor)
        atomic.assert_not_called();cursor.execute.assert_not_called()
