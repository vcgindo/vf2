"""Focused native binding read and owner-verification proofs; no database."""
import os
from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, call, patch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY', 'native-binding-unit-only')
import django
django.setup()

from mta.mdm import families
from mta.mdm import production_families as production
from mta.mdm.initialization_contract import SOURCE_SCHEMA
from mta.mdm.location_projection import VERSION
from mta.serialization import digest


class OrderedRows:
    def __init__(self, rows):
        self.rows = rows

    def order_by(self, *names):
        return self.rows


def empty_frame():
    return {'opening': {'state': {
        'importer_settings': [
            {'Parameter': 'NMSMOQInputDataFormat', 'Value': 'WithDestLoc'},
            {'Parameter': 'ActivateNMSUIUploadLogs', 'Value': '0'},
        ],
        'complete': {'SOBDataRaw': [], 'MOQDataRaw1': [], 'MOQDataRaw2': []},
        'importer': {'ForceNormChange': [], 'MasterData': []},
        'controls': {'upload_log': []},
        'control_aux': {'season_requests': [], 'phase_stops': [],
                        'phase_requests': [], 'phase_in_requests': []},
        'dbm': {'Seasonality': []},
    }}}


class NativeBindingReadTests(unittest.TestCase):
    def test_expected_reuses_supplied_verified_frame_without_another_opening_read(self):
        initialization = SimpleNamespace()
        frame = empty_frame()
        with patch('mta.mdm.initialization.read_initialized_input',
                   side_effect=AssertionError('opening was read again')) as opening_read:
            actual_frame, bags = production._expected(initialization, frame=frame)
        self.assertIs(actual_frame, frame)
        self.assertEqual(set(bags), set(production.GROUPS))
        opening_read.assert_not_called()

    def test_require_binding_uses_one_verified_frame_for_every_owner_check(self):
        source = SimpleNamespace(pk=17, digest='source-digest', receipt={
            'schema': SOURCE_SCHEMA, 'families': {'1': {'owner': 'sku'}}})
        initialization = SimpleNamespace(pk=23, input_digest='opening-digest', source=source)
        frame = empty_frame()
        bags = {family: {'rows': []} for family in production.GROUPS}
        family_rows = [SimpleNamespace(master_id=value, digest='family-'+str(value))
                       for value in range(2, 14)]
        family_digests = {'1': digest(source.receipt['families']['1'])}
        family_digests.update({str(row.master_id): row.digest for row in family_rows})
        configuration = {family: family+'-configuration' for family in production.GROUPS}
        receipt = dict(schema=production.INTEGRATION_SCHEMA, source_digest=source.digest,
            initialization_id=str(initialization.pk),
            initialization_content_digest=initialization.input_digest,
            families=family_digests, required_families=list(range(1, 14)),
            configuration=configuration, adapter_digest='adapter',
            closing_projection_version=VERSION, source_manifest_digest='runtime-source')
        seal = SimpleNamespace(receipt=receipt, digest=digest(receipt))
        owners = {family: SimpleNamespace(source_id=source.pk, family=family)
                  for family in production.GROUPS}
        owner_models = (
            ('mta.runtime.mdm_supplier_models.MdmSupplierConfiguration', 'supplier'),
            ('mta.runtime.mdm_force_models.MdmForceOwner', 'force'),
            ('mta.runtime.mdm_season_models.MdmSeasonOwner', 'season'),
            ('mta.runtime.mdm_stop_pipo_models.MdmStopPipoOwner', 'stop_pipo'),
            ('mta.runtime.mdm_phase_controls_models.MdmPhaseControlsOwner', 'phase_controls'),
        )
        verified = MagicMock(return_value=(initialization, frame))
        expected = MagicMock(return_value=(frame, bags))
        owner_check = MagicMock(side_effect=lambda source, owner, *args: owner)
        with ExitStack() as stack:
            stack.enter_context(patch.object(production, '_verified_initialization', verified))
            stack.enter_context(patch.object(production, '_expected', expected))
            stack.enter_context(patch.object(production, '_configuration', return_value=configuration))
            stack.enter_context(patch.object(production, 'adapter_digest', return_value='adapter'))
            stack.enter_context(patch('mta.mdm.location_transition.source_manifest_digest',
                                      return_value='runtime-source'))
            stack.enter_context(patch.object(production, '_verify_owner', owner_check))
            stack.enter_context(patch.object(production.MdmSourceIntegration.objects, 'get', return_value=seal))
            stack.enter_context(patch.object(production.MdmFamilySource.objects, 'filter',
                                             return_value=OrderedRows(family_rows)))
            captures = MagicMock()
            captures.exists.return_value = False
            stack.enter_context(patch.object(production.MdmDailyInputCapture.objects, 'filter',
                                             return_value=captures))
            for dotted, family in owner_models:
                module_name, model_name = dotted.rsplit('.', 1)
                model = getattr(__import__(module_name, fromlist=[model_name]), model_name)
                stack.enter_context(patch.object(model.objects, 'get', return_value=owners[family]))
            self.assertIs(production.require_binding(source), seal)

        verified.assert_called_once_with(source)
        expected.assert_called_once_with(initialization, frame=frame)
        self.assertEqual([item.args[2] for item in owner_check.call_args_list],
                         ['supplier', 'force', 'season', 'stop_pipo', 'phase_controls'])
        self.assertEqual(owner_check.call_count, 5)
        for item in owner_check.call_args_list:
            self.assertIs(item.args[0], source)
            self.assertIs(item.args[3], initialization)
            self.assertIs(item.args[4], frame)
            self.assertIs(item.args[5], bags)
            self.assertIs(item.args[6], True)

    def test_each_owner_family_keeps_full_drift_denial(self):
        source = SimpleNamespace(pk=31, digest='source-digest', receipt={'schema': SOURCE_SCHEMA})
        initialization = SimpleNamespace(pk=41, input_digest='opening-digest', source=source)
        frame = {'opening': {'state': {'sealed': True}}}
        bags = {family: {'rows': [family]} for family in production.GROUPS}
        configuration = {family: family+'-configuration' for family in production.GROUPS}

        def family_rows(**query):
            group = tuple(query['master_id__in'])
            family = next(name for name, ids in production.GROUPS.items() if ids == group)
            expected = production._provenance(initialization, family, bags[family])
            return OrderedRows([SimpleNamespace(master_id=master_id, receipt=expected,
                                                digest=digest(expected))
                                for master_id in group])

        with patch.object(production, '_configuration', return_value=configuration), \
                patch.object(production, '_actual',
                             side_effect=lambda source, family: bags[family]) as actual, \
                patch.object(production.MdmFamilySource.objects, 'filter',
                             side_effect=family_rows):
            for family in production.GROUPS:
                expected = production._provenance(initialization, family, bags[family])
                values = dict(source_id=source.pk, provenance=expected,
                              receipt_digest=digest(expected))
                if family != 'supplier':
                    values['root_state_digest'] = digest(frame['opening']['state'])
                owner = SimpleNamespace(**values)
                self.assertIs(production._verify_owner(source, owner, family,
                    initialization, frame, bags, True), owner)

                drifted = SimpleNamespace(**{**values, 'provenance': {'drift': family}})
                with self.assertRaisesRegex(ValueError,
                        'Native MDM '+family+' opening owner differs'):
                    production._verify_owner(source, drifted, family,
                        initialization, frame, bags, True)
        self.assertEqual(actual.call_args_list,
                         [call(source, family) for family in production.GROUPS])

    def test_native_installed_ids_checks_complete_binding_once(self):
        source = SimpleNamespace(receipt={'schema': SOURCE_SCHEMA})
        ids = list(range(2, 14))
        query = MagicMock()
        query.order_by.return_value.values_list.return_value = ids
        with patch.object(families.MdmFamilySource.objects, 'filter', return_value=query), \
                patch.object(production, 'require_binding') as require_binding:
            self.assertEqual(families.installed_ids(source), [1, *ids])
        require_binding.assert_called_once_with(source)


if __name__ == '__main__':
    unittest.main()
