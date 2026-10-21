"""Owned finalizers must not traverse unrelated closing populations.

DO NOT MODIFY FRONTEND CODE OR THE MTO STACK. Preserve the original frontend presentation and behavior. No frontend redesign, substitute screens, refactoring or MTO changes. Any future exception requires explicit human authorization.
"""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','unit-only')
import django
django.setup()
import unittest
from copy import deepcopy
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock,patch
from mta.mdm import season_capture as season,phase_controls_capture as phase,daily_current
from mta.serialization import storage,digest
from mta.row_sequences import RecordRows


class Unrelated(dict):
    def items(self):
        raise AssertionError('Unrelated population was traversed')


def query(rows):
    result=MagicMock()
    result.__iter__.side_effect=lambda:iter(rows)
    result.order_by.return_value=result
    return result


class OwnedLifetimeTests(unittest.TestCase):
    def season(self,spooled=False,bad_fields=False,changed_owner=False):
        request=dict.fromkeys(season.REQUEST_FIELDS)
        request.update(SKUCode='SKU01',WhCode='WH01',StartDate=date(2026,4,1),
            EndDate=date(2026,5,1),TargetNorm=10,Approved=False)
        current=dict.fromkeys(season.SEASON_FIELDS)
        current.update({k:v for k,v in request.items() if k in current},OrigNorm=Decimal('1.00'),
            NewNorm=Decimal('2.00'),Status=None,Comment='exact ®',LastProcessedOn=None)
        queues=[dict(request),dict(request)]
        currents=[dict(current),dict(current)]
        if bad_fields:currents[0]['Unexpected']=1
        frozen_current=[dict(storage(r),id=i,revision=1,ordinal=i) for i,r in enumerate(currents,1)]
        frozen_queue=[dict(storage(r),id=i,revision=1) for i,r in enumerate(queues,1)]
        owner=MagicMock(receipt_digest='source',last_run_id=None,root_state_digest='root',
            closing_queue_digest='q',closing_current_digest='c',generation=2)
        snapshot=dict(source_id=1,season=dict(source_digest='wrong' if changed_owner else 'source',
            anchor=dict(run_id=None,root_state_digest='root',queue_digest='q',current_digest='c',generation=2),
            rows=frozen_queue,current=frozen_current))
        queue_rows=[MagicMock(pk=r['id'],revision=1,**{k:r[k] for k in season.REQUEST_FIELDS}) for r in frozen_queue]
        current_rows=[MagicMock(pk=r['id'],revision=1,**{k:r[k] for k in season.SEASON_FIELDS}) for r in frozen_current]
        queue_manager=MagicMock();queue_manager.select_for_update.return_value.filter.return_value=query(queue_rows)
        current_manager=MagicMock();current_manager.select_for_update.return_value.filter.return_value=query(current_rows)
        current_model=MagicMock(objects=current_manager,side_effect=lambda **kw:SimpleNamespace(**kw))
        raw=deepcopy((queues,currents))
        closing=dict(control_aux=dict(season_requests=RecordRows.from_rows(queues) if spooled else queues,
            unrelated=Unrelated()),dbm=dict(Seasonality=RecordRows.from_rows(currents) if spooled else currents,
            unrelated=Unrelated()),unrelated=Unrelated())
        with patch.object(season.MdmSeasonOwner.objects,'select_for_update') as owners, \
                patch.object(season.MdmSeasonQueue,'objects',queue_manager), \
                patch.object(season,'MdmSeasonCurrent',current_model), \
                patch.object(season.MdmSeasonConsumed.objects,'create') as consumed:
            owners.return_value.get.return_value=owner
            if bad_fields or changed_owner:
                with self.assertRaisesRegex(ValueError,'field roster' if bad_fields else 'owner changed'):
                    season.finalize('run',snapshot,dict(ClosingState=[closing]))
                self.assertFalse(current_manager.bulk_create.called)
            else:
                season.finalize('run',snapshot,dict(ClosingState=[closing]))
                written=current_manager.bulk_create.call_args.args[0]
                self.assertEqual([storage({k:getattr(r,k) for k in season.SEASON_FIELDS}) for r in written],storage(raw[1]))
                self.assertEqual([r.ordinal for r in written],[1,2])
                self.assertEqual([c.kwargs['cleared'] for c in consumed.call_args_list],[False,False])
                self.assertEqual(owner.closing_queue_digest,digest(storage(raw[0])))
                self.assertEqual(owner.closing_current_digest,digest(storage(raw[1])))
                self.assertTrue(all(not r.delete.called for r in queue_rows))
            self.assertEqual(storage(closing['control_aux']['season_requests']),storage(raw[0]))
            self.assertEqual(storage(closing['dbm']['Seasonality']),storage(raw[1]))

    def test_season_lists_preserve_full_values_nulls_duplicates_and_input(self):self.season()
    def test_season_actual_spools_preserve_full_values_and_duplicate_ordinals(self):self.season(spooled=True)
    def test_season_invalid_owned_fields_remain_rejected(self):self.season(bad_fields=True)
    def test_season_changed_owner_is_rejected_before_reading_closing(self):self.season(changed_owner=True)

    def test_phase_lists_and_spools_do_not_traverse_other_controls(self):
        for spooled in (False,True):
            with self.subTest(spooled=spooled):
                owner=MagicMock(receipt_digest='source',last_run_id=None,closing_queue_digest='q',generation=1)
                frozen={name:[] for name in phase.FIELDS}
                frozen.update(source_digest='source',anchor=dict(run_id=None,queue_digest='q',generation=1))
                remaining={name:RecordRows.from_rows([]) if spooled else [] for name in phase.FIELDS}
                models={name:MagicMock() for name in phase.QUEUES}
                for model in models.values():model.objects.select_for_update.return_value.filter.return_value=query([])
                with patch.object(phase.MdmPhaseControlsOwner.objects,'select_for_update') as owners,patch.dict(phase.QUEUES,models):
                    owners.return_value.get.return_value=owner
                    phase.finalize('run',dict(source_id=1,phase_controls=frozen),dict(ClosingState=[dict(control_aux=dict(remaining,unrelated=Unrelated()))]))
                self.assertEqual(owner.closing_queue_digest,digest({name:[] for name in phase.FIELDS}))
                self.assertTrue(all(model.objects.bulk_create.call_args.args[0]==[] for model in models.values()))

    def test_current_projection_identity_reuses_the_same_validated_generation(self):
        from mta.mdm import location_projection
        model=type('NativeProjection',(),{})
        rows=[dict(Value=Decimal('1.00'),Note=None),dict(Value=Decimal('1.00'),Note=None)]
        batch=(1,model,dict(owner='BTR'),rows,'/source')
        proof=dict(sources=[dict(source_digest='same')])
        with patch.object(daily_current,'owner_batches',return_value=[]), \
                patch.object(location_projection,'additional_owners',return_value=([batch],proof)) as prepare, \
                patch.object(daily_current,'business_fields',return_value=[SimpleNamespace(name='Value'),SimpleNamespace(name='Note')]):
            batches,metadata=daily_current._closing_projection({},version=location_projection.VERSION)
            expected=[dict(family=1,model='NativeProjection',owner='BTR',fields=['Value','Note'],rows=2,digest=digest(storage(rows)))]
            self.assertEqual(daily_current._partition_identity(batches),expected)
            self.assertIs(metadata,proof)
            self.assertIs(batches[0][3],rows)
            self.assertEqual(prepare.call_count,1)
            self.assertEqual(rows,[dict(Value=Decimal('1.00'),Note=None)]*2)

    def test_absent_owners_do_not_read_output(self):
        season.finalize('run',{},None)
        phase.finalize('run',{},None)


if __name__=='__main__':unittest.main()
