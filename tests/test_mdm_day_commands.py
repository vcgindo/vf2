import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

from tools.cohort6_bind_day import MDM_DAY_TEMPLATE_SHA, bind
from tools.mdm_approval_day_workflow import REVIEW_TIME, schedule


class MdmHierarchyBindingTests(unittest.TestCase):
    def test_native_ids_are_distinct_and_reviews_retain_exact_clock(self):
        rows = schedule()
        self.assertEqual([r['master_id'] for r in rows], list(range(1, 14)))
        self.assertEqual(rows[0]['submitted'].isoformat(), '2026-06-06T12:59:47+05:30')
        self.assertEqual(rows[-1]['submitted'].isoformat(), '2026-06-06T12:59:59+05:30')
        self.assertEqual(len({'2_' + r['submitted'].strftime('%Y%m%d%H%M%S') for r in rows}), 13)
        self.assertTrue(all(r['submitted'] < r['reviewed'] == REVIEW_TIME for r in rows))

    def test_three_dates_require_exact_approved_template(self):
        template = {
            'version': 'fresh-presentation-hierarchy-v1',
            'role': 'presentation-only-retained-hierarchy',
            'catalogue_sha256': '18df4d8e84633848062c45e1896615a7a46d350d0c0cd8657f38cb7b0948c356',
            'allowed_fields': {'products': ['SL1', 'SL2', 'SL3'],
                               'locations': ['LL1', 'LL2', 'LL3']},
            'catalogue_counts': {'products': 200, 'locations': 20},
            'publications': [],
            'authorization': 'Approved MDM approval-to-day S1 retained catalogue/hierarchy projection; exact own June 6-8 runs only after separate execution approval. No serving change.',
        }
        # The registered Windows artifact retains its original CRLF bytes.
        raw = (json.dumps(template, indent=2) + '\n').replace('\n', '\r\n').encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), MDM_DAY_TEMPLATE_SHA)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'template.json'
            source.write_bytes(raw)
            receipt = root / 'receipt.json'
            run_id = str(uuid4())
            for day in ('2026-06-06', '2026-06-07', '2026-06-08', '2026-06-09'):
                value = dict(status='SUCCEEDED', run_id=run_id, business_date=day,
                             input_digest='a' * 64, output_digest='b' * 64,
                             validation_digest='', evidence_mode='production',
                             seconds=1, publication={})
                receipt.write_text(json.dumps(value))
                output = root / (day + '.json')
                if day.endswith('09'):
                    with self.assertRaises(ValueError):
                        bind(source, MDM_DAY_TEMPLATE_SHA, receipt, day, output)
                    self.assertFalse(output.exists())
                else:
                    result = bind(source, MDM_DAY_TEMPLATE_SHA, receipt, day, output)
                    self.assertEqual(result['run_id'], run_id)
                    self.assertEqual(json.loads(output.read_bytes())['publications'],
                                     [dict(run_id=run_id, business_date=day,
                                           output_digest='b' * 64)])
            value['business_date'] = '2026-06-08'
            receipt.write_text(json.dumps(value))
            source.write_bytes(raw + b' ')
            with self.assertRaises(ValueError):
                bind(source, MDM_DAY_TEMPLATE_SHA, receipt, value['business_date'], root / 'bad.json')
            changed_sha = hashlib.sha256(source.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):
                bind(source, changed_sha, receipt, value['business_date'], root / 'bad.json')


if __name__ == '__main__':
    unittest.main()
