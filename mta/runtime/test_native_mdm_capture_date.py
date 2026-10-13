"""Actual temporal caller/date/retry routing; no business calculation or DB writes.

Persistence/admission are explicit doubles. The native compose implementation
and execute_day request/date/retry checks run unchanged up to composition.
"""
from contextlib import ExitStack, nullcontext
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from mta.application.daily_finalization import ACTIVE_POLICY
from mta.application.r1_importer_master import RAW_COLUMNS
from mta.mdm.daily_input import SCHEMA, compose
from mta.runtime import temporal
from mta.serialization import digest


class CaptureReached(Exception):
    pass


class NativeMdmCaptureDateTests(SimpleTestCase):
    def setUp(self):
        self.profile = dict(delivery={'site_code':'DATE-ROUTING'},
            complete_pick={'policy':'canonical-tied-order-v1'},
            complete_daily={'policy':ACTIVE_POLICY,'consumption_days':7,'remark_days':7})
        self.opening = dict(identity='date-routing',opening_date='2026-07-04',
                            state={'importer_settings':[]})
        self.day = dict(business_date='2026-07-05',raw_master=[])
        self.base = dict.fromkeys(RAW_COLUMNS)
        self.base.update(SKUCode='337',WhCode='DP010290',Norm=12,
                         ParentWhCode='LDC001',SKUIntroDate='2025-01-01')
        self.added = dict(SKUCode='6249',WhCode='DP010290',Norm=12,MinNorm=0,
            RLT=7,RCP=0,GCP=0,OCP=None,ParentWhCode='LDC001',PackSize=2,
            SpikeThreshold='50.00',PSOThreshold='50.00',FGRMFlag='FG',
            NormPercentReservation=0,MinOrderCount=None,StockPercentForRat=100,
            Approved=True,**{f'SKULocAtt{i:02}':None for i in range(1,16)})
        self.snapshot = dict(schema=SCHEMA,nms_active=True,pair_exclusions=[],
            configuration={'task_status_log_horizon':7},rows={
                'sku':{'descriptions':[],'attributes':[],'approved':[]},
                'location':{'descriptions':[],'attributes':[],'approved':[]},
                'skuloc':{'additions':[self.added],'modifications':[],
                          'removals':[],'attributes':[]}})
        self.snapshot['revision_digest'] = digest(self.snapshot)
        self.source = SimpleNamespace(pk=1,digest='a'*64,receipt={})
        self.initialized = SimpleNamespace(pk='initialization',source=self.source,source_id=1,
            input_sha256='b'*64,input_digest='c'*64,configuration_digest='d'*64)
        self.failed = SimpleNamespace(pk='failed',status='FAILED',predecessor_id=None,
            business_date=date(2026,7,5),execution_revision='first')
        self.origin = SimpleNamespace(pk='capture',source_id=1,run=self.failed,
            run_id=self.failed.pk,status='CAPTURED',request_digest=None,
            revision_digest=self.snapshot['revision_digest'])
        self.requests = []
        self.composed = []

    def invoke(self, *, native, retry=False, wrong_date=False):
        from mta.runtime import mdm_models, mdm_daily_models, models
        request_input = temporal.request_input
        def request(**kwargs):
            result = request_input(**kwargs)
            self.requests.append(deepcopy(result))
            return result
        def capture(snapshot, master, *, last_run_date):
            self.composed.append((deepcopy(snapshot),last_run_date,
                compose(snapshot,master,last_run_date=last_run_date)))
            raise CaptureReached
        source_manager = MagicMock()
        source_manager.select_for_update.return_value.get.return_value = self.source
        init_manager = MagicMock()
        init_manager.select_for_update.return_value.select_related.return_value.get.return_value = self.initialized
        captures = MagicMock()
        captures.get.return_value = self.origin
        captures.select_for_update.return_value.select_related.return_value.get.return_value = self.origin
        captures.select_related.return_value.filter.return_value.first.return_value = None
        captures.filter.return_value.values_list.return_value = [self.failed.pk]
        if wrong_date:
            self.origin.run.business_date = date(2026,7,4)
        with ExitStack() as stack:
            for target,kwargs in (
                ('mta.runtime.temporal.transaction',dict(new=SimpleNamespace(
                    get_autocommit=lambda:True,atomic=lambda:nullcontext()))),
                ('mta.runtime.temporal.connection',dict(new=MagicMock())),
                ('mta.runtime.temporal.daily_sources_enabled',dict(return_value=False)),
                ('mta.runtime.temporal.resolved_pick_root',dict(side_effect=lambda p:p)),
                ('mta.runtime.temporal.request_input',dict(side_effect=request)),
                ('mta.application.daily_finalization.validate_supplement',dict(return_value=None)),
                ('mta.mdm.supplier_revisions.source_lock',dict(side_effect=lambda *_a,**_k:nullcontext())),
                ('mta.mdm.initialization.read_initialized_input',dict(return_value={'profile':self.profile,'opening':self.opening})),
                ('mta.mdm.production_families.require_initialization',dict(return_value=None)),
                ('mta.runtime.production_daily.initialize_consumers',dict(return_value=None)),
                ('mta.mdm.integration_source.verify_predecessor',dict(return_value=None)),
                ('mta.runtime.mdm_configuration.capture_configuration_for_day',dict(return_value=(True,7))),
                ('mta.mdm.daily_input.compose_pair_exclusions',dict(side_effect=lambda s,_m:s)),
                ('mta.mdm.daily_input.nms_master_raw',dict(return_value=[self.base])),
                ('mta.mdm.daily_input.compose',dict(side_effect=capture)),
                ('mta.runtime.temporal.read_input',dict(return_value={'mdm_input':deepcopy(self.snapshot)})),
            ):
                stack.enter_context(patch(target,**kwargs))
            stack.enter_context(patch.object(mdm_models.MdmSource,'objects',source_manager))
            stack.enter_context(patch.object(models.ProductionInitialization,'objects',init_manager))
            stack.enter_context(patch.object(mdm_daily_models.MdmDailyInputCapture,'objects',captures))
            selected = stack.enter_context(patch('mta.mdm.daily_input.select_capture',return_value=deepcopy(self.snapshot)))
            options=dict(day=self.day,profile=self.profile,execution_revision='retry' if retry else 'first',
                opening=self.opening,pick_output_root='unused-date-routing',
                mdm_retry=self.failed if retry else None,mdm_source=None if retry else self.source)
            if native:
                options.update(production_initialization=self.initialized,daily_input_sha256='e'*64,
                               evidence_mode='production',consumer_opening={})
            with self.assertRaises(ValueError if wrong_date else CaptureReached) as error:
                temporal.execute_day(**options)
            if wrong_date:
                self.assertIn('retry does not match',str(error.exception))
            if retry:
                selected.assert_not_called()

    def expected(self, added_date):
        old=deepcopy(self.base);old.update(WHDescription='ND',ParentDescription='ND')
        new=dict.fromkeys(RAW_COLUMNS)
        for field in ('SKUCode','WhCode','Norm','MinNorm','RLT','RCP','GCP','OCP',
            'ParentWhCode','PackSize','SpikeThreshold','PSOThreshold','FGRMFlag',
            'NormPercentReservation','MinOrderCount'):
            new[field]=self.added[field]
        new.update(SKUIntroDate=added_date,StockPercentForRationing=100,
                   WHDescription='ND',ParentDescription='ND')
        return [old,new]

    def test_native_added_pair_uses_current_day_and_retry_keeps_frozen_date(self):
        self.invoke(native=True)
        self.assertEqual(self.composed[0][1: ],('2026-07-05',self.expected('2026-07-05')))
        self.origin.request_digest=digest(self.requests[0])
        self.invoke(native=True,retry=True)
        self.assertEqual(self.composed[1],self.composed[0])
        self.assertEqual(self.requests[1],self.requests[0])
        self.invoke(native=True,retry=True,wrong_date=True)
        self.assertEqual(len(self.composed),2)

    def test_legacy_call_retains_opening_date_and_existing_pair_date(self):
        self.invoke(native=False)
        self.assertEqual(self.composed[0][1: ],('2026-07-04',self.expected('2026-07-04')))
