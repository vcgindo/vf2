"""Opening COPY qualification, independently selectable after the staging patch."""
from decimal import Decimal
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from mta.row_sequences import RecordRows
from mta.runtime import opening_storage as opening, relational_state as relational
from tests.test_ingestion_copy_transport import CopyCursor, ReadCursor, database, owner


class OpeningCopyTransportTests(TestCase):
    def test_copy_matches_insert_types_manifest_and_readback(self):
        from mta.mdm.initialization_rows import TABLES
        table = 'Importer/SkuLocAttributeData'
        image = next(path for path, target in TABLES.items() if target == table)
        row = {name: None for name, _ in opening.STORAGE_TABLES[table]}
        row.update(SKUCode='雪\n\t\\', LocCode='', PackSize=0, SpikeThreshold='1.2300',
            PSOThreshold='-2.5', NonNMS=False)
        rows = RecordRows(500, lambda: (dict(row) for _ in range(500)))
        attempt, snapshots = owner(), []
        for vendor in ('sqlite', 'postgresql'):
            cursor, inserted = CopyCursor(), []
            db = database(cursor, vendor)
            with patch.object(opening, 'connection', db), patch.object(relational, 'connection', db), \
                    patch.object(opening, 'bulk', side_effect=lambda sql, rows: inserted.extend(rows)):
                metadata = opening.save_image(attempt, image, 'unused', rows, table=table)
            snapshots.append((metadata, cursor.rows if vendor == 'postgresql' else inserted))
        self.assertEqual(snapshots[0], snapshots[1])
        self.assertTrue(cursor.sql.startswith('COPY mta_opening."importer_skulocattributedata" ("vf_initialization_id","vf_image","vf_ordinal",'))
        self.assertEqual(cursor.rows[0][:3], (attempt.pk, image, 0))
        self.assertEqual(cursor.rows[0][3:8], ('雪\n\t\\', '', 0, Decimal('1.2300'), Decimal('-2.5')))
        db = SimpleNamespace(chunked_cursor=lambda: ReadCursor(record[2:] for record in cursor.rows))
        with patch.object(opening, 'connection', db):
            self.assertEqual(list(opening.iter_image(attempt, metadata)), [row] * 500)

    def test_empty_and_small_population_keep_insert(self):
        attempt = owner()
        for count in (0, 499):
            rows = [dict(shape_id=0) for _ in range(count)]
            with patch.object(opening, 'bulk') as bulk, patch.object(opening, 'copy_rows') as copy:
                meta = opening.save_image(attempt, 'input/fixture/shape', 'unused', rows, table='input/row_shape')
            self.assertEqual(meta['count'], count)
            self.assertEqual(bulk.call_count, int(count > 0))
            copy.assert_not_called()
