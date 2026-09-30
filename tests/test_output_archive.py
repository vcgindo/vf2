from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from mta.serialization import digest
from parity.output_archive import OutputArchive, write_rows
from tests.test_temporal_oracle import OracleCoverageTest


class OutputArchiveTest(unittest.TestCase):
    def archive(self,directory,value):
        items=[]
        for name,rows in sorted(value.items()):
            path=Path(directory)/(name+'.jsonl.gz')
            items.append(dict(name=name,path=path.name,**write_rows(path,rows)))
        path=Path(directory)/'manifest.json'
        path.write_text(json.dumps(dict(schema='fresh-output-archive-v1',output_digest=digest(value),checkpoints=items)))
        return OutputArchive(path)

    def test_all_eight_boundaries_compared_without_loading_a_boundary_array(self):
        fixture=OracleCoverageTest()
        legacy,modern,states=fixture.pair()
        with TemporaryDirectory() as directory:
            archive=self.archive(directory,modern)
            archive.verify(digest(modern))
            original=OutputArchive.__getitem__
            def bounded(current,name):
                if name=='MajorBoundaries':raise AssertionError('Whole boundary array was loaded')
                return original(current,name)
            with patch.object(OutputArchive,'__getitem__',bounded):
                checks=fixture.compare(legacy,archive,states)
            self.assertEqual(len(checks),29)
            self.assertTrue(all(item['status']=='PASS' for item in checks))

    def test_changed_population_and_duplicate_boundary_are_not_hidden(self):
        fixture=OracleCoverageTest()
        legacy,modern,states=fixture.pair()
        modern['MajorBoundaries'].append(modern['MajorBoundaries'][0])
        with TemporaryDirectory() as directory:
            archive=self.archive(directory,modern)
            with self.assertRaisesRegex(ValueError,'roster/multiplicity'):
                fixture.compare(legacy,archive,states)

    def test_file_corruption_fails_even_when_other_checkpoints_are_valid(self):
        value={'Rows':[{'v':1},{'v':None},{'v':True},{'v':1}]}
        with TemporaryDirectory() as directory:
            archive=self.archive(directory,value)
            self.assertEqual(archive['Rows'],value['Rows'])
            archive.items['Rows']['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'file drift'):
                archive.verify(digest(value))
