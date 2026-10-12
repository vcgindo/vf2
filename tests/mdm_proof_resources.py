"""Exact owned PostgreSQL proof identity; never permit the serving database."""
import os


def assert_owned_mdm_proof(test, connection):
    database = os.environ.get('VF_MDM_PROOF_DATABASE', 'fresh_mdm_day_binding_proof_20261010_001')
    host = os.environ.get('VF_MDM_PROOF_HOST', 'freshvcf-complete001-postgres')
    if 'VF_MDM_PROOF_DATABASE' in os.environ or 'VF_MDM_PROOF_HOST' in os.environ:
        test.assertTrue(database.startswith('fresh_mdm_baseline_review_'))
        test.assertTrue(host.startswith('freshvcf-mdm-review-'))
        test.assertEqual(os.environ.get('VF_MDM_PROOF_DATABASE'), database)
        test.assertEqual(os.environ.get('VF_MDM_PROOF_HOST'), host)
    test.assertEqual(connection.settings_dict['NAME'], database)
    test.assertEqual(connection.settings_dict['HOST'], host)
