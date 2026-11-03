from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import UUID

from mta.runtime import placement_rationing as placement
from mta.runtime import runtime_report_stage_storage as images


class ReferencedHistoryPreparationTests(TestCase):
    def test_compare_prepared_history_and_independent_cut_once_before_writes(self):
        identity = '10000000-0000-4000-8000-000000000001'
        logical = placement.history.TABLE
        rows = [{'SKUCode': 'A'}, {'SKUCode': 'A'}]
        other = 'BPR/ColorSequence'
        sources = {other: [{'Color': 'Red', 'SequenceNo': 2}], logical: rows}
        manifest = images.capture(None, candidate_id=identity, placement='PostBTR', sources=sources,
            row_writer=lambda name, bag: images.describe(identity, name, bag)[0])
        work = SimpleNamespace(placement='PostBTR', candidate_id=identity, source_manifest=manifest, sources=sources)
        cut = SimpleNamespace(identity=UUID(identity), root_digest='a'*64)
        for changed_cut, changed_prepared in [(False, False), (True, False), (False, True)]:
            projected = [dict(row) for row in rows]
            prepared = [dict(row) for row in rows]
            if changed_cut:
                projected[-1]['SKUCode'] = 'B'
            if changed_prepared:
                prepared[-1]['SKUCode'] = 'B'
            work.sources = {**sources, logical: prepared}
            with self.subTest(changed_cut=changed_cut, changed_prepared=changed_prepared), \
                    patch.object(placement, '_pending_cut', return_value=cut), \
                    patch.object(placement, '_project', return_value=projected), \
                    patch.object(images, 'describe', wraps=images.describe) as describe, \
                    patch.object(images, 'write', return_value=manifest['images'][other]) as write:
                if changed_cut or changed_prepared:
                    with self.assertRaisesRegex(ValueError, 'PostBTR closing projection|PostBTR prepared source'):
                        placement.persist(None, work, {})
                    write.assert_not_called()
                else:
                    saved, reference = placement.persist(None, work, {})
                    self.assertEqual(saved, manifest)
                    self.assertEqual(reference['projection_digest'], manifest['images'][logical]['digest'])
                    checked = [call.args[2] for call in describe.call_args_list if call.args[1] == logical]
                    self.assertEqual(len(checked), 2)
                    self.assertIs(checked[0], projected)
                    self.assertIs(checked[1], prepared)
                    write.assert_called_once_with(None, identity, other, sources[other])
