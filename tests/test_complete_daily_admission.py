"""Standalone complete-operation correspondence and denial proofs; no engines."""
from copy import deepcopy
import unittest
from mta.presentation import complete_daily_admission as policy

SHA = 'a' * 64
UUID = '143d37ed-ff01-43b6-bbab-9f016b89401c'


def evidence():
    contract, records, proofs = [], [], []
    for index, kind in enumerate(('typed', 'file', 'absence')):
        output = dict(id='output', kind=kind)
        if kind == 'typed':
            output.update(schema_sha256=SHA)
        elif kind == 'file':
            output.update(path='reports/example.csv')
        else:
            output.update(reason='qualified_disabled_branch')
        spec = dict(id='operation-' + str(index),
            canonical_source=dict(path='Scripts/example.sql', sha256=SHA),
            implementation_source=dict(path='mta/domain/example.py', sha256=SHA),
            qualification_sha256=SHA, outputs=[output])
        row = dict(operation_id=spec['id'],
            canonical_source=deepcopy(spec['canonical_source']),
            implementation_source=deepcopy(spec['implementation_source']),
            qualification_sha256=SHA, clock_id='worker-one',
            started_ns=index * 10, completed_ns=index * 10 + 5,
            status='SUCCEEDED', error=None, outputs=[dict(output, sha256=SHA,
                                                       verification_sha256=SHA)])
        if kind == 'typed':
            row['outputs'][0]['row_count'] = 3
        elif kind == 'file':
            row['outputs'][0]['size_bytes'] = 20
        proof = dict(operation_id=spec['id'], canonical_source=deepcopy(spec['canonical_source']),
            implementation_source=deepcopy(spec['implementation_source']), status='PASS',
            receipt_sha256=SHA, proof_sha256=SHA, output_ids=['output'])
        contract.append(spec)
        records.append(row)
        proofs.append(proof)
    return contract, records, proofs


class CompleteDailyAdmissionTests(unittest.TestCase):
    def test_complete_correspondence_returns_identity_not_readiness(self):
        self.assertEqual(len(policy.validate_operations(*evidence())), 64)

    def test_missing_duplicate_reordered_unknown_operations(self):
        for change in ('missing', 'duplicate', 'reordered', 'unknown'):
            with self.subTest(change=change):
                contract, records, proofs = evidence()
                if change == 'missing':
                    records.pop()
                elif change == 'duplicate':
                    records[1] = deepcopy(records[0])
                elif change == 'reordered':
                    records.reverse()
                else:
                    records[0]['operation_id'] = 'unknown'
                with self.assertRaisesRegex(ValueError, 'operation_order_or_roster_mismatch'):
                    policy.validate_operations(contract, records, proofs)

    def test_unqualified_or_changed_sources_and_execution_fail_closed(self):
        for field, value, reason in (
            ('implementation_source', {'path': 'other.py', 'sha256': SHA}, 'operation_source_mismatch'),
            ('canonical_source', {'path': 'other.sql', 'sha256': SHA}, 'operation_source_mismatch'),
            ('qualification_sha256', 'b'*64, 'operation_not_qualified'),
            ('status', 'FAILED', 'operation_not_successful'),
            ('error', 'native SQL CATCH result', 'operation_not_successful'),
            ('started_ns', True, 'operation_timing_invalid'),
            ('completed_ns', -1, 'operation_timing_invalid'),
            ('clock_id', '', 'operation_clock_required'),
        ):
            with self.subTest(field=field):
                contract, records, proofs = evidence()
                records[0][field] = value
                with self.assertRaisesRegex(ValueError, reason):
                    policy.validate_operations(contract, records, proofs)
        contract, records, proofs = evidence()
        proofs[0]['status'] = 'PENDING'
        with self.assertRaisesRegex(ValueError, 'operation_not_qualified'):
            policy.validate_operations(contract, records, proofs)

    def test_qualification_roster_is_independent_and_complete(self):
        for change in ('missing', 'duplicate'):
            contract, records, proofs = evidence()
            if change == 'missing':
                proofs.pop()
            else:
                proofs[1] = deepcopy(proofs[0])
            with self.assertRaisesRegex(ValueError, 'qualification_roster_mismatch'):
                policy.validate_operations(contract, records, proofs)

    def test_count_alone_files_outside_owner_and_false_absence_rejected(self):
        for index, field, value, reason in (
            (0, 'verification_sha256', '', 'operation_output_unverified'),
            (0, 'schema_sha256', 'b'*64, 'typed_output_invalid'),
            (0, 'row_count', True, 'typed_output_invalid'),
            (1, 'path', '../outside.csv', 'file_output_invalid'),
            (1, 'size_bytes', -1, 'file_output_invalid'),
            (2, 'reason', 'missing_turned_empty', 'absence_output_invalid'),
        ):
            with self.subTest(field=field):
                contract, records, proofs = evidence()
                records[index]['outputs'][0][field] = value
                with self.assertRaisesRegex(ValueError, reason):
                    policy.validate_operations(contract, records, proofs)
        contract, records, proofs = evidence()
        records[0]['outputs'] = []
        with self.assertRaisesRegex(ValueError, 'operation_output_roster_mismatch'):
            policy.validate_operations(contract, records, proofs)

    def test_operation_clocks_and_overlapping_order_rejected(self):
        for field, value, reason in (
            ('clock_id', 'other-worker', 'operation_clock_mismatch'),
            ('started_ns', 2, 'operation_timing_invalid'),
        ):
            contract, records, proofs = evidence()
            records[1][field] = value
            with self.assertRaisesRegex(ValueError, reason):
                policy.validate_operations(contract, records, proofs)

    def test_exact_native_binding_and_missing_predecessor(self):
        actual = {name: SHA for name in policy.BINDING_FIELDS}
        for name in ('owner_id', 'run_id', 'btr_generation'):
            actual[name] = UUID
        actual.update(database_name='owned_test_only', business_date='2026-06-06',
                      predecessor_id=None, predecessor_output_digest='')
        expected = deepcopy(actual)
        self.assertEqual(len(policy.validate_binding(actual, expected)), 64)
        for name in ('owner_id', 'database_name', 'input_digest', 'output_digest',
                     'action_digest', 'source_digest', 'publication_seal', 'hierarchy_digest'):
            changed = deepcopy(actual)
            changed[name] = 'changed'
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'binding_mismatch'):
                policy.validate_binding(changed, expected)
        changed = deepcopy(actual)
        changed['predecessor_output_digest'] = SHA
        with self.assertRaisesRegex(ValueError, 'initial_predecessor_mismatch'):
            policy.validate_binding(changed, changed)
        changed.pop('source_digest')
        with self.assertRaisesRegex(ValueError, 'binding_roster_mismatch'):
            policy.validate_binding(changed, expected)
