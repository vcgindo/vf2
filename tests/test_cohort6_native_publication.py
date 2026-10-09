from copy import deepcopy
import unittest
from tools.cohort6_native_publication import validate,RUN,PRIOR,NATIVE


class NativePublicationTransitionTests(unittest.TestCase):
    def setUp(self):
        self.row=dict(run_id=RUN,status='INCOMPLETE',seal_digest='',sealed_at=None,
            configuration_digest=PRIOR,output_digest='output',source_digest='source',
            recipe_digest='recipe',layers={'btr':{'status':'READY','receipt':{'rows_digest':'unchanged'}}})
        self.options=dict(configuration=PRIOR,native=NATIVE,
            identities=dict(output_digest='output',source_digest='source',recipe_digest='recipe'),
            activated=False,accepted=False)

    def test_exact_pending_transition(self):
        validate(self.row,deepcopy(self.row),**self.options)

    def test_sealed_activated_accepted_drift_and_changed_receipt_deny(self):
        for delta in [dict(status='READY'),dict(seal_digest='seal'),dict(sealed_at='date'),
                      dict(configuration_digest='other'),dict(run_id='another'),
                      dict(layers={}),dict(source_digest='other')]:
            with self.subTest(delta=delta),self.assertRaises(ValueError):
                validate({**self.row,**delta},self.row,**self.options)
        for delta in [dict(activated=True),dict(accepted=True),dict(configuration='other'),
                      dict(native='other'),dict(identities={'recipe_digest':'other'})]:
            with self.subTest(delta=delta),self.assertRaises(ValueError):
                validate(self.row,self.row,**{**self.options,**delta})
