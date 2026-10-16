"""No-DB command boundary tests; PostgreSQL mutation proof is separate."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
os.environ.setdefault('VF_SECRET_KEY','logistics-unit-check-only')
import django
django.setup()
import json
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from django.test import override_settings
from django.db import DatabaseError
from mta.presentation import logistics_commands as commands, logistics_views as views
from tests import test_logistics_reads as reads


class LogisticsCommandContractTests(unittest.TestCase):
    def test_transit_batch_requires_exact_complete_rows_before_writes(self):
        valid=dict.fromkeys(commands.TRANSIT_FIELDS)
        self.assertEqual(commands._batch({'data':[valid]},commands.TRANSIT_FIELDS),[valid])
        for bad in ({}, {'data':[]}, {'data':[dict(valid,actor='spoof')]},
                    {'data':[dict(OrderNo='one')]}, {'data':[None]}):
            with self.assertRaises(ValueError):commands._batch(bad,commands.TRANSIT_FIELDS)

    def test_native_date_and_width_boundaries_do_not_invent_defaults(self):
        self.assertEqual(commands._datetime('',transit=True),datetime(1900,1,1))
        self.assertIsNone(commands._datetime(None,optional=True))
        self.assertEqual(commands._datetime('2026/10/21',transit=True),datetime(2026,10,21))
        for value in ('',None,'2026-10-21T00:00:00Z','0001-01-01'):
            with self.assertRaises((ValueError,TypeError)):commands._datetime(value)
        self.assertEqual(commands._text(None,width=50),'')
        with self.assertRaises(ValueError):commands._text('x'*51,width=50)

    @override_settings(VF_MTA_LOGISTICS_CURRENT=True,
        VF_MTA_LOGISTICS_COMMAND_DATABASE='handoff3005_g3_workflow_20261015_003')
    def test_command_uses_gateway_actor_exact_database_and_truthful_failures(self):
        helper=reads.LogisticsReadContractTests()
        cursor=MagicMock();cursor.__enter__.return_value=cursor
        cursor.fetchone.return_value=('handoff3005_g3_workflow_20261015_003',)
        with patch.object(views.connection,'cursor',return_value=cursor), \
                patch.object(views,'selected_run',return_value='run'), \
                patch.object(commands,'submit_transit',return_value=None) as submit:
            response=helper.call('SubmitRemarksForInTransit',body={'data':[],'actor':'untrusted'})
            self.assertEqual(response.status_code,200)
            self.assertEqual(submit.call_args.args[2],{'id':1,'name':'fixture'})
            for exc,status in ((commands.reader.TargetDenied('denied'),403),
                               (ValueError('shape'),400),(DatabaseError('write failed'),500)):
                submit.side_effect=exc
                response=helper.call('SubmitRemarksForInTransit')
                self.assertEqual(response.status_code,status)
                self.assertNotEqual(json.loads(response.content).get('msg'),'Data submitted successfully')
            submit.reset_mock();cursor.fetchone.return_value=('another_database',)
            self.assertEqual(helper.call('SubmitRemarksForInTransit').status_code,403)
            submit.assert_not_called()

    def test_command_is_disabled_by_default(self):
        with override_settings(VF_MTA_LOGISTICS_CURRENT=False):
            response=reads.LogisticsReadContractTests().call('SubmitRemarksForInTransit')
        self.assertEqual(response.status_code,403)

    @override_settings(VF_MTA_LOGISTICS_CURRENT=True,
        VF_MTA_LOGISTICS_COMMAND_DATABASE='handoff3005_g3_workflow_20261015_003')
    def test_action_route_preserves_batch_return_and_gateway_actor(self):
        cursor=MagicMock();cursor.__enter__.return_value=cursor
        cursor.fetchone.return_value=('handoff3005_g3_workflow_20261015_003',)
        payload={'data':[{'SKUCode':'337','WHCode':'DP','Remark':'Call','ETA':'2026/10/21'}]}
        with patch.object(views.connection,'cursor',return_value=cursor), \
                patch.object(views,'selected_run',return_value='run'), \
                patch.object(commands,'add_expedite_remark',return_value='3') as action:
            response=reads.LogisticsReadContractTests().call('AddRemarkForExpedite',body=payload)
            self.assertEqual(response.status_code,200)
            self.assertEqual(json.loads(response.content)['data'],'3')
            self.assertEqual(action.call_args.args,('run',payload,{'id':1,'name':'fixture'}))
        with self.assertRaises(ValueError):
            commands._batch({'data':[{'SKUCode':'337','WHCode':'DP','Remark':'Call'}]},commands.ACTION_FIELDS)
