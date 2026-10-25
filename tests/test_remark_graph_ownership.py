"""The optimized command cannot accept a caller's bound graph or lose its transaction."""
import inspect,unittest
from types import SimpleNamespace
from unittest.mock import MagicMock,patch
from mta.presentation import scoped_remark_writer as writer
from mta.presentation.context import PublicationUnavailable


class RemarkGraphOwnershipTests(unittest.TestCase):
    def setUp(self):
        blocker=patch('django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection',
            side_effect=AssertionError('Database forbidden in source-only ownership tests'))
        blocker.start();self.addCleanup(blocker.stop)

    def test_public_command_has_no_view_or_validation_bypass_parameter(self):
        signature=inspect.signature(writer.append)
        self.assertEqual(list(signature.parameters),['payload','actor'])
        with self.assertRaises(TypeError):signature.bind({}, {}, view=object())

    def test_transaction_identity_requires_atomic_live_connection_and_tracks_role_and_full_xid(self):
        physical=SimpleNamespace(closed=False)
        database=SimpleNamespace(in_atomic_block=True,connection=physical,cursor=MagicMock())
        cursor=database.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value=('18446744073709551615','runtime','runtime')
        with patch.object(writer,'connection',database):
            self.assertEqual(writer._transaction_identity(),(physical,('18446744073709551615','runtime','runtime')))
            for change in (dict(in_atomic_block=False),dict(connection=None),dict(connection=SimpleNamespace(closed=True))):
                before={k:getattr(database,k) for k in change}
                for key,value in change.items():setattr(database,key,value)
                with self.assertRaises(PublicationUnavailable):writer._transaction_identity()
                for key,value in before.items():setattr(database,key,value)

    def test_private_producer_rejects_untyped_or_nonadvancing_cuts(self):
        with self.assertRaisesRegex(PublicationUnavailable,'previous_cut'):
            writer._refresh_after_append(object(),before=0,highwater=1)
