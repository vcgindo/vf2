"""Logical copy/hook contracts; native accepted-image proof is separate."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'runtime-report-bpr-source-unit-only')
import django
django.setup()

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import patch
import json

from mta.application.runtime_report_hooks import SCHEMA, configuration
from mta.runtime.runtime_report_phase_sources import PhaseSources
from mta.runtime import runtime_report_bpr_sources as source
from mta.runtime.phase_state import REGISTRY
from mta.mdm.master_owners import phase_copy_batches
from mta.mdm.daily_current import _partition_identity
from mta.serialization import digest

DEFINITIONS = {row['Id']: row for row in json.loads(
    (Path(__file__).parent/'fixtures/runtime_reports_retained_20261019.json').read_bytes())}


def fixture():
    hook = dict(schema=SCHEMA, site_code='EXPLICIT-SITE', placement='PostBPR',
                mode='declared-no-op', authority='Explicit test configuration', source_sha256='a'*64)
    raw = dict(profile={'delivery': {'site_code': 'EXPLICIT-SITE'}},
               scope_request={'report_hooks': hook})
    identity = dict(profile_digest=digest(raw['profile']),
                    captured_request_digest=digest(raw['scope_request']), run_id='owned-unit-run')
    copies = {name: [] for name in ('SkuAttributeData', 'SKUDescriptionTbl',
                                   'LocationAttributeData', 'SiteDescriptionTbl')}
    copies['SKUDescriptionTbl'] = [dict(SKUCode='S', SKUDescription='same, name')]*2
    pair = {name: None for name, _kind in REGISTRY['Importer/SkuLocAttributeData']}
    pair.update(SKUCode='S', LocCode='W')
    populations = {**{'importer/'+name: (rows, 'Importer/'+name) for name, rows in copies.items()},
        'importer/SkuLocAttributeData': ([pair, dict(pair)], 'Importer/SkuLocAttributeData'),
        'orders/SpikeOrderData': ([], 'BPR/SpikeOrderData'),
        'late/vf_RationedReqReport': ([], 'BPR/vf_RationedReqReport'),
        'complete/SupplierDispatchReq': ([], 'complete/BPR/SupplierDispatchReq')}
    images, bags = {}, {}
    for path, (rows, table) in populations.items():
        image = 'phase/BPR/'+path
        images[image] = dict(image=image, table=table, count=len(rows), digest=digest(rows),
            fields=[[field, field, 'str'] for field in rows[0]] if rows else [])
        bags[image] = rows
    state = dict(importer={name: {'image': 'phase/BPR/importer/'+name}
                          for name in (*copies, 'SkuLocAttributeData')},
        order_state={'SpikeOrderData': {'image': 'phase/BPR/orders/SpikeOrderData'}},
        late={'vf_RationedReqReport': {'image': 'phase/BPR/late/vf_RationedReqReport'}},
        complete={'SupplierDispatchReq': {'image': 'phase/BPR/complete/SupplierDispatchReq'}})
    phase = NS(phase='BPR', run='owned-unit-run', metadata={'partitions':
        _partition_identity(phase_copy_batches('BPR', copies))})
    bound = PhaseSources(phase, identity, ({'phase': 'BPR', 'state': state, 'images': images},))
    return bound, raw, bags


class BprReportSourcesTests(TestCase):
    def bind(self, bound, raw, bags, identity=10):
        with patch('mta.runtime.input_reader.read_input', return_value=raw), \
                patch('mta.runtime.relational_state.load_image',
                      side_effect=lambda run, meta, **kwargs: bags[meta['image']]):
            return source.bind_post_bpr(bound, definition=DEFINITIONS[identity])

    def test_copy_witness_keeps_physical_owner_and_pair_is_not_claimed_persisted(self):
        bound, raw, bags = fixture()
        before = digest(bags)
        values, proof = self.bind(bound, raw, bags)
        pair = proof['sources']['BPR/SkuLocAttributeData']
        self.assertEqual(pair['kind'], 'reconstructed-canonical-copy')
        self.assertIs(pair['persisted_bpr_partition'], False)
        self.assertEqual(pair['physical']['physical_table'], 'Importer/SkuLocAttributeData')
        self.assertEqual(pair['import_sql_sha256'], source.IMPORT_DATA_SHA256)
        self.assertEqual(list(values['BPR/SkuLocAttributeData']), bags['phase/BPR/importer/SkuLocAttributeData'])
        self.assertEqual(len(values['BPR/SkuLocAttributeData']), 2)
        for table in ('SiteDescriptionTbl', 'SkuAttributeData', 'LocationAttributeData'):
            ref = proof['sources']['BPR/'+table]
            self.assertEqual(ref['kind'], 'verified-accepted-bpr-copy')
            self.assertEqual(ref['physical']['physical_table'], 'Importer/'+table)
            self.assertEqual(ref['partition']['owner'], 'BPR')
        self.assertEqual(digest(bags), before)
        self.assertEqual(proof['digest'], digest({k:v for k,v in proof.items() if k!='digest'}))

    def test_each_full_copy_identity_must_match_even_unused_description_copy(self):
        for ordinal in range(4):
            for field, changed in (('owner', 'Importer'), ('fields', []), ('rows', 99), ('digest', 'f'*64)):
                bound, raw, bags = fixture()
                bound.phase.metadata['partitions'][ordinal][field] = changed
                with self.subTest(ordinal=ordinal, field=field), self.assertRaisesRegex(ValueError, 'partition'):
                    self.bind(bound, raw, bags)

    def test_spike_uses_bpr_order_image_without_claiming_attribute_copies(self):
        bound, raw, bags = fixture()
        bound.phase.metadata['partitions'] = []
        values, proof = self.bind(bound, raw, bags, identity=7)
        self.assertEqual(list(values), ['BPR/SpikeOrderData'])
        self.assertEqual(proof['sources']['BPR/SpikeOrderData']['physical']['node'],
                         ['state', 'order_state', 'SpikeOrderData'])
        self.assertEqual(list(values['BPR/SpikeOrderData']), [])

    def test_missing_active_wrong_site_or_changed_capture_hook_denies_before_images(self):
        for change in ('missing', 'active', 'site', 'capture', 'blank_authority'):
            bound, raw, bags = fixture()
            if change == 'missing': raw['scope_request'].clear()
            elif change == 'active': raw['scope_request']['report_hooks']['mode'] = 'execute-script'
            elif change == 'site': raw['scope_request']['report_hooks']['site_code'] = 'OTHER'
            elif change == 'blank_authority': raw['scope_request']['report_hooks']['authority'] = ' '
            else: raw['profile']['changed'] = True
            if change != 'capture':
                bound.identity['captured_request_digest'] = digest(raw['scope_request'])
            with patch('mta.runtime.input_reader.read_input', return_value=raw), \
                    patch.object(PhaseSources, 'image') as images:
                with self.subTest(change=change), self.assertRaises(ValueError):
                    source.bind_post_bpr(bound, definition=DEFINITIONS[7])
                images.assert_not_called()

    def test_existing_test_disposition_keeps_its_original_database_and_schema_restrictions(self):
        from mta.runtime.production_upto_dbm import SCHEMA as REQUEST, DISPOSITION
        bound, raw, bags = fixture()
        raw['profile']['delivery']['site_code'] = 'SUPPLIED-INSTANCE'
        raw['scope_request'] = dict(schema=REQUEST, scope='UptoDBM', dispositions=dict(
            schema=DISPOSITION, purpose='owned-scoped-test', site_code='SUPPLIED-INSTANCE',
            hooks={name:'explicit-test-no-op' for name in ('PostBPR', 'PreDBM', 'PostDBM')},
            input_download='enabled-five-file-four-table-archive', authority='Retained exact test approval'))
        bound.identity.update(profile_digest=digest(raw['profile']),
                              captured_request_digest=digest(raw['scope_request']))
        with patch('mta.runtime.scope_runtime_reports.require_test_database') as guard:
            _values, proof = self.bind(bound, raw, bags, identity=7)
            guard.assert_called_once_with()
        self.assertEqual(proof['hook']['kind'], 'captured-owned-test-disposition')
        with patch('mta.runtime.scope_runtime_reports.require_test_database', side_effect=ValueError('not TEST')):
            with self.assertRaisesRegex(ValueError, 'not TEST'):self.bind(bound, raw, bags, identity=7)

    def test_wrong_placement_phase_and_empty_physical_table_deny(self):
        bound, raw, bags = fixture()
        with self.assertRaises(ValueError):source.bind_post_bpr(bound, definition=DEFINITIONS[2])
        bound.phase.phase = 'DBM'
        with self.assertRaises(ValueError):source.bind_post_bpr(bound, definition=DEFINITIONS[7])
        bound.phase.phase = 'BPR'
        bound.manifests[0]['images']['phase/BPR/orders/SpikeOrderData']['table'] = 'Importer/OrderRaw'
        with self.assertRaisesRegex(ValueError, 'table'):self.bind(bound, raw, bags, identity=7)

    def test_declaration_is_exact_bounded_and_has_no_default(self):
        _bound, raw, _bags = fixture()
        value = raw['scope_request']['report_hooks']
        self.assertEqual(configuration(value), value)
        for changed in (None, {}, dict(value, source_sha256='bad'), dict(value, extra=True)):
            with self.assertRaises(ValueError):configuration(changed)
