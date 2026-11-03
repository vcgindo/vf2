"""Lossless deferred phase inputs, with only the database transport replaced."""
from copy import deepcopy
from decimal import InvalidOperation
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault('VF_SECRET_KEY','report-source-unit-only')
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()

from mta.runtime import relational_state as typed
from mta.serialization import storage


def report(stage, rows):
    return dict(stage=stage,tables={},deferred={'kind':'component'},sources={'ReasonCodes':rows})


class ReportSourceReuseTests(unittest.TestCase):
    def save(self, closing, reports):
        output=dict(ClosingState=[{'dbm':{'ReasonCodes':closing}}],Reports=reports,Lineage=[])
        run=SimpleNamespace(pk='876adbe4-9372-4f53-96cd-a67eb7630114')
        images={}
        writer=typed.save_image
        def capture(run,path,binding,rows):
            images[path]=deepcopy(rows)
            return writer(run,path,binding,rows)
        with patch.object(typed,'connection',SimpleNamespace(vendor='sqlite')), \
                patch.object(typed,'bulk',side_effect=lambda sql,values:list(values)), \
                patch.object(typed,'save_image',side_effect=capture), \
                patch.object(typed,'load_image',side_effect=lambda run,item:deepcopy(images[item['image']])):
            run.production_manifest=typed.save_daily(run,output)
            actual=typed.read_daily(run)
        self.assertEqual(storage(actual),storage(typed.production_projection(output)))
        return run.production_manifest,images

    def test_same_run_full_typed_ordered_values_share_one_payload(self):
        rows=[{'Id':1,'Reason':None},{'Id':2,'Reason':'same'}, {'Id':2,'Reason':'same'}]
        original=deepcopy(rows)
        manifest,images=self.save(rows,[report('norm-change-export',deepcopy(rows)),
                                        report('norm-change-history',deepcopy(rows))])
        self.assertEqual(list(images),['closing/dbm/ReasonCodes'])
        self.assertEqual([r['sources']['ReasonCodes']['image'] for r in manifest['reports']],
                         ['closing/dbm/ReasonCodes']*2)
        self.assertEqual(rows,original)

    def test_earlier_phase_differs_from_closing_and_reuses_only_equal_phase(self):
        earlier=[{'Id':1,'Reason':'before'}]
        manifest,images=self.save([{'Id':1,'Reason':'after'}],
            [report('norm-change-export',earlier),report('norm-change-history',deepcopy(earlier))])
        self.assertEqual(len(images),2)
        first=manifest['reports'][0]['sources']['ReasonCodes']['image']
        self.assertEqual(first,'report-facts/norm-change-export/ReasonCodes')
        self.assertEqual(manifest['reports'][1]['sources']['ReasonCodes']['image'],first)

    def test_order_multiplicity_null_wire_type_and_raw_spelling_are_not_collapsed(self):
        prior=[{'Id':1,'Reason':None},{'Id':2,'Reason':'A '}]
        variants=[list(reversed(prior)),prior+[deepcopy(prior[-1])],
            [{'Id':1,'Reason':''},prior[1]], [prior[0],{'Id':2,'Reason':'A'}],
            [{'Id':1.0,'Reason':None},{'Id':2.0,'Reason':'A '}],
            [{'id':1,'Reason':None},{'id':2,'Reason':'A '}]]
        for values in variants:
            with self.subTest(values=values):
                _,images=self.save(prior,[report('norm-change-export',values)])
                self.assertEqual(len(images),2)

    def test_empty_sources_and_new_invocation_do_not_reference_another_run(self):
        for _ in range(2):
            manifest,images=self.save([],[report('norm-change-export',[])])
            self.assertEqual(list(images),['closing/dbm/ReasonCodes'])
            self.assertEqual(manifest['reports'][0]['sources']['ReasonCodes'],
                             {'image':'closing/dbm/ReasonCodes'})

    def test_invalid_phase_shape_still_refuses(self):
        with self.assertRaisesRegex(ValueError,'Mixed operational row shape'):
            self.save([],[report('norm-change-export',[{'Id':1,'Reason':'a'},{'Id':2}])])
        with self.assertRaises(InvalidOperation):
            self.save([{'Id':1,'Reason':'a'}],
                      [report('norm-change-export',[{'Id':True,'Reason':'a'}])])


if __name__=='__main__':unittest.main()
