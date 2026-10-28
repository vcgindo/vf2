"""Native SQL-name correction and finite schema admission contracts."""
from importlib import import_module
from copy import deepcopy
import unittest


class GenericReadAliasTests(unittest.TestCase):
    def test_only_new_generic_aliases_change(self):
        migration=import_module('mta.runtime.migrations.0242_generic_read_sql_aliases')
        block=migration.ADMISSION
        for old,new in migration.ALIASES.items():
            self.assertNotIn(old+'.value',block)
            block=block.replace(new,old)
        self.assertEqual(block,migration.prior.ADMISSION)
        self.assertEqual(migration.BODY.replace(migration.ADMISSION,migration.prior.ADMISSION),migration.OLD)
        declared=migration.OLD.split('BEGIN',1)[0].casefold()
        self.assertTrue(all(alias.casefold() not in declared for alias in migration.ALIASES.values()))
        self.assertIn("P.prosrc=$expected$"+migration.OLD+"$expected$",migration.SQL)

    def test_only_exact_correction_and_predecessor_are_admitted(self):
        from mta.runtime import generic_read_alias_transition as profile
        from mta.serialization import digest
        spec=dict(previous_release=dict(source_commit=profile.PREVIOUS_COMMIT,
            manifest_sha256=profile.PREVIOUS_RELEASE),migration_pins=profile.migration_pins(),
            catalogue_delta=profile.catalogue_delta())
        profile.require_specification(spec)
        receipt=dict(migration_pins=spec['migration_pins'],previous_release=profile.PREVIOUS_RELEASE,
                     catalogue_delta_digest=digest(spec['catalogue_delta']))
        self.assertTrue(profile.approved_receipt(receipt))
        for key in receipt:
            changed=deepcopy(receipt);changed[key]='altered'
            self.assertFalse(profile.approved_receipt(changed))
        for key in spec:
            changed=deepcopy(spec);changed[key]={} if key=='catalogue_delta' else [] if key=='migration_pins' else dict(spec[key],source_commit='0'*40)
            with self.assertRaises(ValueError):profile.require_specification(changed)

    def test_authority_accepts_exact242_name_only(self):
        from uuid import uuid4
        from mta.runtime import ingestion_authority as authority,generic_read_alias_transition as profile
        body={key:'a'*64 for key in authority.SCHEMA_FIELDS}
        body.update(contract=authority.SCHEMA_CONTRACT,initialization_id=str(uuid4()),
                    target_commit='b'*40,migration_pins=profile.migration_pins())
        self.assertEqual(authority.validate_schema_transition(body),body)
        body['migration_pins']=[['0242_arbitrary','a'*64]]
        with self.assertRaises(ValueError):authority.validate_schema_transition(body)

    def test_effective_schema_preserves_transit_then_alias_ancestry(self):
        import os
        os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
        os.environ.setdefault('VF_SECRET_KEY','generic-alias-component-only')
        import django;django.setup()
        from unittest.mock import patch
        from uuid import uuid4
        from mta.runtime import ingestion_authority as authority,ingestion_admission as admission
        from mta.runtime import generic_read_alias_transition as alias,transit_settings_schema_transition as transit
        from mta.serialization import digest
        origin={key:'fixed' for key in authority.FIELDS}
        origin.update(initialization_id=str(uuid4()),target_commit=transit.PREVIOUS_COMMIT,
                      target_release=transit.PREVIOUS_RELEASE)
        middle=dict(origin,target_commit=alias.PREVIOUS_COMMIT,target_release=alias.PREVIOUS_RELEASE)
        target=dict(origin,target_commit='1'*40,target_release='1'*64)
        cert=dict(schema_digest='s0',guard_digest='g0',receipt_digest='r',release_digest=origin['target_release'])
        bodies={body['target_release']:body for body in (origin,middle,target)}
        def link(profile,parent,child,before,after):
            return dict(contract=authority.SCHEMA_CONTRACT,previous_release=parent['target_release'],
                previous_authority_digest=digest(parent),certification_digest='r',target_commit=child['target_commit'],
                migration_pins=profile.migration_pins(),catalogue_delta_digest=digest(profile.catalogue_delta()),
                before_schema_digest='s'+before,before_guard_digest='g'+before,
                schema_digest='s'+after,guard_digest='g'+after)
        links={middle['target_release']:link(transit,origin,middle,'0','1'),
               target['target_release']:link(alias,middle,target,'1','2')}
        with patch.object(admission,'_activation_metadata',return_value=cert), \
                patch.object(authority,'read',side_effect=lambda c,i,r:bodies[r]), \
                patch.object(authority,'read_schema_transition',side_effect=lambda c,b:links.get(b['target_release'])):
            self.assertEqual(admission.effective_schema(None,target)[2:4],('s2','g2'))
            links[target['target_release']]['catalogue_delta_digest']='tampered'
            with self.assertRaisesRegex(ValueError,'SQL-alias'):admission.effective_schema(None,target)
