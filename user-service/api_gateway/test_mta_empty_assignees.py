from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from api_gateway.utils import getAllUserDetails


class MtaEmptyAssigneesTests(SimpleTestCase):
    def read(self, products, locations, *, typed=True):
        with ExitStack() as stack:
            product = stack.enter_context(patch('api_gateway.utils.User_Application_Product_Permission.objects'))
            location = stack.enter_context(patch('api_gateway.utils.User_Application_Location_Permission.objects'))
            roles = stack.enter_context(patch('api_gateway.utils.Roles.objects'))
            users = stack.enter_context(patch('api_gateway.utils.User.objects'))
            permissions = stack.enter_context(patch('common.api_gateway_utils.ALL_PERMISSIONS'))
            serializer = stack.enter_context(patch('api_gateway.utils.UserProfileSerializer'))
            for manager, rows, field in ((product, products, 'productfilter_id'),
                                         (location, locations, 'locationfilter_id')):
                manager.all.return_value.values.return_value = rows
                manager.filter.return_value.values.return_value = [
                    {k: row[k] for k in ('application_id', field)}
                    for row in rows if row['user_id'] == 7]
            roles.filter.return_value.values.return_value.filter.return_value = [dict(user_id=8)]
            chain = users.filter.return_value.exclude.return_value.distinct.return_value.order_by.return_value
            chain.filter.return_value = []
            if products and locations:
                chain.filter.return_value = [SimpleNamespace(id=8)]
                serializer.return_value.data = dict(id=8, email='approver@example.invalid', name='Approver')
                permissions.generateProductAndLocationPermissions.return_value = [
                    dict(application_id=2, permissions=[dict(id=11)])]
            result = getAllUserDetails(SimpleNamespace(user=SimpleNamespace(id=7)), 2,
                                       typed_empty_permissions=typed)
            return result, users.filter.call_args.kwargs

    def test_no_permission_rows_means_no_assignees(self):
        self.assertEqual(self.read([], []), ([], dict(pk__in=[], is_active=True)))

    def test_either_empty_relation_preserves_other_relation_overlap(self):
        for field in ('productfilter_id', 'locationfilter_id'):
            rows = [dict(user_id=user, application_id=2, **{field:11}) for user in (7, 8)]
            products, locations = (rows, []) if field == 'productfilter_id' else ([], rows)
            result, selection = self.read(products, locations)
            self.assertEqual(result, [])
            self.assertEqual(set(selection['pk__in']), {7, 8})

    def test_nonempty_eligibility_and_response_match_existing_algorithm(self):
        products = [dict(user_id=u, application_id=2, productfilter_id=11) for u in (7, 8)]
        locations = [dict(user_id=u, application_id=2, locationfilter_id=22) for u in (7, 8)]
        self.assertEqual(self.read(products, locations), self.read(products, locations, typed=False))

    def test_other_callers_retain_the_existing_empty_behavior(self):
        with self.assertRaises(KeyError):
            self.read([], [], typed=False)
