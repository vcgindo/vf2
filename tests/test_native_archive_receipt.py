"""Offline archive attestation, selected-owner isolation and byte integrity."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from django.test import override_settings
from tests.test_native_input_archive import NativeArchiveTests
from mta.application import native_input_archive as archive
from mta import archive_receipt
from mta.presentation import native_selection as selection
from mta.serialization import digest


class AttestedArchiveTests(NativeArchiveTests):
    def setUp(self):
        super().setUp()
        self.binding['source_digest'] = 'a'*64
        self.run.output_digest = 'b'*64
        self.run.input_digest = digest(self.captured)

    def attested(self):
        result = self.prepare()
        receipt = archive_receipt.prepared(result)
        patch('mta.presentation.native_selection.selected_archive', return_value=receipt).start()
        patch('mta.presentation.native_selection.require_selected').start()
        patch('mta.presentation.accepted_publication._qualified_ownership', return_value=True).start()
        return result, receipt

    def test_download_is_exact_original_zip_without_full_fact_reconstruction(self):
        result, _ = self.attested()
        expected = Path(result['path']).read_bytes()
        with patch.object(archive, 'audit_archive', side_effect=AssertionError('HTTP full audit')):
            stream, name = archive.open_archive(self.run)
            with stream:
                self.assertEqual(stream.read(), expected)
            self.assertEqual(name, 'InputData.zip')
        self.assertEqual(archive.read_input.call_args.kwargs['components'],
            ('initialization_binding', 'daily_input_sha256', 'pick_output_root', 'scope_request'))

    def test_all_compressed_bytes_are_verified_before_response(self):
        result, _ = self.attested()
        path = Path(result['path'])
        original = path.read_bytes()
        for changed in (original[:-1], original[:100] + bytes([original[100] ^ 1]) + original[101:], original + b'x'):
            path.write_bytes(changed)
            with self.assertRaisesRegex(archive.ArchiveDenied, 'file_drift'):
                archive.open_archive(self.run)

    def test_guard_drift_is_denied_without_downgrade(self):
        self.attested()
        with patch('mta.presentation.accepted_publication._qualified_ownership', return_value=False), \
                patch.object(archive, 'audit_archive', side_effect=AssertionError('downgrade')):
            with self.assertRaisesRegex(archive.ArchiveDenied, 'immutable_ownership'):
                archive.open_archive(self.run)

    def test_source_daily_and_output_identity_changes_are_denied(self):
        self.attested()
        for target, key in ((self.binding, 'source_digest'), (self.captured, 'daily_input_sha256')):
            old = target[key]; target[key] = 'c'*64
            with self.assertRaisesRegex(archive.ArchiveDenied, 'manifest_drift'):
                archive.open_archive(self.run)
            target[key] = old
        self.run.output_digest = 'c'*64
        with self.assertRaisesRegex(archive.ArchiveDenied, 'manifest_drift'):
            archive.open_archive(self.run)

    def test_current_size_policy_still_applies(self):
        result, _ = self.attested()
        import os
        with patch.dict(os.environ, VF_INPUT_ARCHIVE_MAX_COMPRESSED_BYTES=str(result['bytes']-1)):
            with self.assertRaisesRegex(archive.ArchiveDenied, 'compressed_limit'):
                archive.open_archive(self.run)
        with patch.dict(os.environ, VF_INPUT_ARCHIVE_MAX_UNCOMPRESSED_BYTES='1'):
            with self.assertRaisesRegex(archive.ArchiveDenied, 'member_denied'):
                archive.open_archive(self.run)

    def test_qualification_never_reuses_the_optimized_reader(self):
        result = self.prepare()
        expected = archive_receipt.prepared(result)
        with patch.object(archive, 'open_archive', side_effect=AssertionError('self-attestation')):
            self.assertEqual(archive.audited_receipt(self.run), expected)

    def test_existing_next_day_preparation_does_not_borrow_yesterday_selection(self):
        expected = self.prepare()
        with patch('mta.presentation.native_selection.selected_archive',
                   side_effect=AssertionError('yesterday serving selection')):
            self.assertEqual(self.prepare(), expected)


class ArchiveSelectionTests(unittest.TestCase):
    def bundle(self):
        from datetime import date
        run = SimpleNamespace(pk=uuid4(), business_date=date(2037,4,10), output_digest='a'*64)
        pub = SimpleNamespace(seal_digest='b'*64, configuration_digest='c'*64,
            layers={'btr': {'receipt': {'generation':str(uuid4())}}})
        summary = SimpleNamespace(pk=uuid4(), rows_digest='d'*64)
        native = {'initialization': {'id':str(uuid4())}}
        base = selection.candidate(run,pub,summary,native)
        manifest = dict(schema='fresh-native-input-download-v1', restriction='retained',
            run_id=str(run.pk), business_date=run.business_date.isoformat(),
            initialization_id=native['initialization']['id'], source_digest='e'*64,
            input_digest='f'*64, input_manifest_digest='1'*64, output_digest=run.output_digest,
            files={name:dict(bytes=0,sha256='2'*64)
                   for name in archive_receipt.MEMBERS-{'manifest.json'}})
        manifest['files']['NativeCapturedInput.json']['sha256'] = manifest['input_digest']
        manifest['files']['NativeInputSchema.json']['sha256'] = manifest['input_manifest_digest']
        receipt = dict(schema=archive_receipt.SCHEMA, bytes=100, sha256='3'*64, manifest=manifest)
        return run,pub,summary,native,base,receipt

    def test_exact_v1_lineage_without_resealing_historical_journal(self):
        run,pub,summary,native,base,receipt = self.bundle()
        current = selection.candidate(run,pub,summary,native,input_archive=receipt)
        self.assertNotEqual(current['selection_digest'],base['selection_digest'])
        self.assertEqual(selection.base_digest(current),base['selection_digest'])
        from mta.runtime.csv_scope_operator import require_selection
        require_selection(run.pk,current,str(run.pk),base['selection_digest'])
        with self.assertRaises(ValueError):
            require_selection(run.pk,current,str(run.pk),'9'*64)
        with self.assertRaises(ValueError):
            require_selection(uuid4(),current,str(run.pk),base['selection_digest'])

    def test_next_day_candidate_uses_explicit_new_receipt_not_loaded_yesterday(self):
        old = self.bundle(); new = self.bundle()
        old_bundle = selection.candidate(*old[:4],input_archive=old[5])
        with override_settings(VF_MTA_SELECTION=old_bundle):
            self.assertEqual(selection.candidate(*new[:4]),new[4])
            current = selection.candidate(*new[:4],input_archive=new[5])
        self.assertEqual(current['input_archive']['manifest']['run_id'],str(new[0].pk))
        with self.assertRaisesRegex(ValueError,'selection owner'):
            selection.candidate(*new[:4],input_archive=old[5])

    def test_receipt_tampering_cannot_pass_loaded_selection_equality(self):
        from tempfile import TemporaryDirectory
        run,pub,summary,native,base,receipt = self.bundle()
        current = selection.candidate(run,pub,summary,native,input_archive=receipt)
        with TemporaryDirectory() as root:
            path = Path(root)/'selection.json'; selection.write(path,current)
            with override_settings(VF_MTA_SELECTION=current,VF_MTA_SELECTION_FILE=str(path)):
                selection.require_candidate(current)
                changed = deepcopy(current)
                changed['input_archive']['sha256'] = '4'*64
                changed['selection_digest'] = digest({k:v for k,v in changed.items() if k!='selection_digest'})
                selection.write(path,changed)
                with self.assertRaisesRegex(ValueError,'restart_required'):
                    selection.require_candidate(current)

    def test_receipt_roster_scalar_types_and_cross_owner_are_strict(self):
        run,pub,summary,native,base,receipt = self.bundle()
        for mutate in (lambda x:x.update(bytes=True),
                lambda x:x['manifest'].update(source_digest='wrong'),
                lambda x:x['manifest']['files'].pop('NativeDailyInput.json'),
                lambda x:x['manifest'].update(initialization_id=str(uuid4()))):
            changed = deepcopy(receipt); mutate(changed)
            with self.assertRaises(ValueError):
                selection.candidate(run,pub,summary,native,input_archive=changed)
