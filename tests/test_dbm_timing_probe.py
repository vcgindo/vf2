import unittest
from tools.dbm_timing_probe import ModernProfile


class ScalarProfileTest(unittest.TestCase):
    def test_generator_values_and_boundary_are_preserved(self):
        state={'rows':[{'value':1}]}
        def stages():
            yield 'first',state
            yield 'second',state
        profile=ModernProfile()
        values=list(profile.wrap(stages)())
        self.assertIs(values[0][1],state)
        self.assertIs(values[1][1],state)
        result=profile.result()
        self.assertEqual([r['stage'] for r in result['stages']],['first','second','generator-exhaustion'])
        self.assertEqual(result['stages'][0]['cardinalities'],{'rows':1})
        self.assertEqual(result['dbm_wall_seconds'],sum(r['wall_seconds'] for r in result['stages']))
        self.assertTrue(result['functions'])

    def test_failed_boundary_keeps_original_exception(self):
        profile=ModernProfile()
        self.assertEqual(profile.result()['functions'],[])
        def stages():
            raise ValueError('original failure')
            yield
        with self.assertRaisesRegex(ValueError,'original failure'):
            list(profile.wrap(stages)())
        self.assertTrue(profile.result()['functions'])
