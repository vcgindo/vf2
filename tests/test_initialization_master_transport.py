"""Transport contracts; actual PostgreSQL guards are qualified separately."""
import os
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'initialization-transport-unit-only')
import django
django.setup()

from django.db import connection
from mta.mdm import initialization_transport as transport
from mta.runtime.mdm_models import MdmSkuAttributes
from mta.runtime.mdm_season_models import MdmSeasonQueue


def record():
    return dict(source_id=7, owner='Importer', ordinal=1, SKUCode='雪\t\n\\',
                Weight='1.230', Volume=None, ElephantOrderCapping=0,
                **{f'SL{i}': '' for i in range(1, 6)},
                **{f'c{i}': None for i in range(1, 16)})


class InitializationMasterTransportTests(TestCase):
    def test_threshold_defaults_full_types_order_and_fallback(self):
        for count, vendor in ((0, 'postgresql'), (499, 'postgresql'),
                              (500, 'postgresql'), (501, 'postgresql'), (501, 'sqlite')):
            with self.subTest(count=count, vendor=vendor):
                rows = [record() for _ in range(count)]
                copied, inserted = [], []
                def copy(table, columns, values):
                    self.assertEqual(table, connection.ops.quote_name(MdmSkuAttributes._meta.db_table))
                    self.assertEqual(columns[:3], ['source_id', 'owner', 'ordinal'])
                    copied.extend(values)
                fake = SimpleNamespace(vendor=vendor, ops=connection.ops)
                with patch.object(transport, 'connection', fake), \
                        patch.object(transport, 'copy_rows', side_effect=copy), \
                        patch.object(MdmSkuAttributes.objects, 'bulk_create',
                                     side_effect=lambda values, **kw: inserted.extend(values)):
                    transport.create_rows(MdmSkuAttributes, iter(rows), count=count)
                fields = [f for f in MdmSkuAttributes._meta.concrete_fields if not f.primary_key]
                expected = [tuple(f.get_db_prep_save(getattr(MdmSkuAttributes(**r), f.attname), connection)
                                  for f in fields) for r in rows]
                if count >= 500 and vendor == 'postgresql':
                    self.assertEqual(copied, expected)
                    self.assertFalse(inserted)
                else:
                    self.assertFalse(copied)
                    self.assertEqual([tuple(f.get_db_prep_save(getattr(r, f.attname), connection)
                                            for f in fields) for r in inserted], expected)

    def test_copy_streams_and_does_not_retry_after_conversion_or_server_failure(self):
        for fail_conversion in (True, False):
            seen = []
            def records():
                seen.append('consume')
                yield record()
                if fail_conversion:
                    raise ValueError('fixture conversion failure')
                yield record()
            def copy(table, fields, values):
                self.assertFalse(seen)
                list(values)
                raise ValueError('fixture server rejection')
            with self.subTest(conversion=fail_conversion), \
                    patch.object(transport, 'connection', SimpleNamespace(vendor='postgresql', ops=connection.ops)), \
                    patch.object(transport, 'copy_rows', side_effect=copy), \
                    patch.object(MdmSkuAttributes.objects, 'bulk_create') as bulk:
                with self.assertRaisesRegex(ValueError, 'fixture'):
                    transport.create_rows(MdmSkuAttributes, records(), count=500)
                bulk.assert_not_called()

    def test_missing_values_use_model_defaults_including_revision(self):
        fields = [f for f in MdmSeasonQueue._meta.concrete_fields if not f.primary_key]
        values = dict(source_id=7)
        expected = tuple(f.get_db_prep_save(getattr(MdmSeasonQueue(**values), f.attname), connection)
                         for f in fields)
        observed = []
        with patch.object(transport, 'connection', SimpleNamespace(vendor='postgresql', ops=connection.ops)), \
                patch.object(transport, 'copy_rows', side_effect=lambda table, fields, rows: observed.extend(rows)):
            transport.create_rows(MdmSeasonQueue, (dict(values) for _ in range(500)), count=500)
        self.assertEqual(observed, [expected] * 500)

    def test_foreign_unrecognized_field_is_not_silently_discarded(self):
        with patch.object(transport, 'connection', SimpleNamespace(vendor='postgresql', ops=connection.ops)), \
                patch.object(transport, 'copy_rows', side_effect=lambda table, fields, rows: list(rows)), \
                self.assertRaisesRegex(ValueError, 'Unknown initialization model fields'):
            transport.create_rows(MdmSkuAttributes, iter([{**record(), 'unexpected': 1}]), count=500)
