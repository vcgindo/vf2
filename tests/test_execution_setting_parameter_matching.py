"""Central ownership retains the original consumer-specific occurrence sets."""
from copy import deepcopy
import os,unittest
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','settings-parameter-matching-unit-only')
import django;django.setup()
from mta.runtime.execution_setting_owners import extract,describe,validate
from mta.runtime.execution_setting_projection import project_state
from mta.runtime.execution_setting_catalogue import describe_cells
from mta.domain.dbm_conditional import enabled
from mta.mdm.daily_input import capture_configuration


class ParameterMatchingTests(unittest.TestCase):
    def test_conditional_canonical_variant_and_duplicate_keep_original_count_semantics(self):
        for rows,expected in [([{'Parameter':'NormZeroOneRuleActive','Value':'1'}],True),
                ([{'Parameter':'normzerooneruleactive ','Value':'1'}],True),
                ([{'Parameter':'NormZeroOneRuleActive','Value':'1'},
                  {'Parameter':'normzerooneruleactive ','Value':'1'}],False),
                ([{'Parameter':'NormZeroOneRuleActive','Value':'0'},
                  {'Parameter':'normzerooneruleactive ','Value':'1'}],True)]:
            with self.subTest(rows=rows):
                state={'dbm':{'DBMSettingsTbl':deepcopy(rows)}};cells=extract(state)
                self.assertEqual(len(cells),2*len(rows))
                self.assertEqual(validate(cells),cells)
                result=project_state(state,cells)['dbm']['DBMSettingsTbl']
                self.assertEqual(result,rows)
                self.assertEqual(enabled(rows),expected)
                self.assertEqual(enabled(result),expected)
                self.assertTrue(all(not row['mutable'] for row in describe(state)))
                self.assertEqual(len(describe_cells(cells)),len(cells))

    def test_nms_ci_capture_and_strict_consumers_keep_distinct_spelling_and_counts(self):
        for rows in [[{'Parameter':'nmsactive ','Value':'1'}],
                     [{'Parameter':'NMSActive','Value':'0'},{'Parameter':'nmsactive ','Value':'1'}],
                     [{'Parameter':'NMSActive','Value':'1'},{'Parameter':'nmsactive ','Value':'1'}]]:
            rows=rows+[{'Parameter':'TaskStatusLogHorizon','Value':' 7 '}]
            state={'importer_settings':deepcopy(rows)};cells=extract(state)
            result=project_state(state,cells)['importer_settings']
            self.assertEqual(result,rows)
            self.assertEqual([r for r in result if r['Parameter']=='NMSActive'],
                             [r for r in rows if r['Parameter']=='NMSActive'])
            if sum(r['Value']=='1' for r in rows)>1:
                for bag in (rows,result):
                    with self.assertRaisesRegex(ValueError,'count is neither zero nor one'):
                        capture_configuration(bag)
            else:self.assertEqual(capture_configuration(result),capture_configuration(rows))

    def test_strict_names_leading_spaces_tabs_unknown_unicode_and_owner_namespaces_stay_distinct(self):
        for name in ('spikerulehorizon','SpikeRuleHorizon ','normzerooneruleactive\t',
                     ' normzerooneruleactive','測定',''):
            state={'dbm':{'DBMSettingsTbl':[{'Parameter':name,'Value':'1'}]}}
            self.assertEqual(extract(state),())
            self.assertIs(project_state(state,()),state)
        outside={'dbm':{'VFSettings':[{'Parameter':'superdelayfactor ','Value':'1','Description':None}]}}
        self.assertEqual(extract(outside),())
        state={'dbm':{'DBMSettingsTbl':[{'Parameter':'normzerooneruleactive ','Value':'1'}]}}
        cells=extract(state);state['dbm']['DBMSettingsTbl'][0]['Parameter']='NormZeroOneRuleActive'
        with self.assertRaisesRegex(ValueError,'occurrence sequence'):
            project_state(state,cells)

    def test_incomplete_unreleased_prototype_snapshot_is_refused_never_backfilled(self):
        state={'dbm':{'DBMSettingsTbl':[{'Parameter':'NormZeroOneRuleActive','Value':'1'}]}}
        old_cells=extract(state)
        state['dbm']['DBMSettingsTbl'].append({'Parameter':'normzerooneruleactive ','Value':'1'})
        before=deepcopy(state)
        with self.assertRaisesRegex(ValueError,'occurrence sequence'):
            project_state(state,old_cells)
        self.assertEqual(state,before)


if __name__=='__main__':unittest.main()
