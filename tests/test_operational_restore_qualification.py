from copy import deepcopy
import unittest

from mta.application.operational_restore_qualification import (
    POLICY, RUNTIME_POLICY, compare_restore_images, runtime_policy,
)


class RuntimeRestoreQualificationTest(unittest.TestCase):
    def setUp(self):
        constraints=runtime_policy()['constraints']
        self.source=dict(relations=[dict(schema=r['schema'],name=r['table'],
            constraints=[[r['constraint'],r['left']]],rows=[[['str','kept']], [['str','kept']], [['null',None]]])
            for r in constraints],definitions={'views':[]},
            runtime_cast_metadata=[dict(schema=r['schema'],table=r['table'],constraint=r['constraint'],
                column=r['column'],rows=[r['metadata']]) for r in constraints])
        self.restored=deepcopy(self.source)
        for row,item in zip(self.restored['relations'],constraints):
            row['constraints'][0][1]=item['right']

    def test_exact_images_remain_exact(self):
        self.assertEqual(compare_restore_images(self.source,self.source)['comparison'],'EXACT')

    def test_only_approved_policy_qualifies_eleven_pairs(self):
        result=compare_restore_images(self.source,self.restored,qualification=RUNTIME_POLICY)
        self.assertEqual(result['comparison'],'QUALIFIED_LOGICAL_RESTORE')
        self.assertNotEqual(result['logical_digest'],result['restored_digest'])
        for policy in (None,'unknown',POLICY):
            with self.subTest(policy=policy),self.assertRaises(ValueError):
                compare_restore_images(self.source,self.restored,qualification=policy)

    def test_rejects_changed_rows_duplicates_nulls_and_other_definitions(self):
        for mutation in ('value','duplicate','null','view','expression','extra-constraint'):
            target=deepcopy(self.restored)
            if mutation=='value':target['relations'][0]['rows'][0][0][1]='changed'
            elif mutation=='duplicate':target['relations'][0]['rows'].pop(0)
            elif mutation=='null':target['relations'][0]['rows'][2]=[['str','']]
            elif mutation=='view':target['definitions']['views']=['changed']
            elif mutation=='expression':target['relations'][0]['constraints'][0][1]='CHECK (true)'
            else:target['relations'][0]['constraints'].append(['new','CHECK (true)'])
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                compare_restore_images(self.source,target,qualification=RUNTIME_POLICY)

    def test_rejects_missing_or_changed_metadata_even_when_both_sides_match(self):
        for missing in (True,False):
            source,target=deepcopy(self.source),deepcopy(self.restored)
            for image in (source,target):
                if missing:del image['runtime_cast_metadata']
                else:image['runtime_cast_metadata'][0]['rows'][0][0]=False
            with self.subTest(missing=missing),self.assertRaisesRegex(ValueError,'metadata'):
                compare_restore_images(source,target,qualification=RUNTIME_POLICY)


if __name__=='__main__':unittest.main()
