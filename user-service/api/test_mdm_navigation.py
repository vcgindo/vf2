import unittest

from api.mdm_navigation import with_mdm_menu_aliases


class MdmNavigationTests(unittest.TestCase):
    def test_exact_existing_mta_grants_get_only_matching_menu_aliases(self):
        pages = ('control-panel', 'saved-drafts', 'task-pending', 'task-status',
                 'data-modification-history')
        for page in pages:
            grant = '/mta/master-data-management/' + page
            self.assertEqual(set(with_mdm_menu_aliases([grant, grant])),
                             {grant, '/masters-interceptor/' + page})

    def test_absent_child_and_other_application_grants_do_not_widen_access(self):
        grants = ['/mta/master-data-management/control-panel/add',
                  '/mto/master-data-management/control-panel', '/profile']
        self.assertEqual(set(with_mdm_menu_aliases(grants)), set(grants))
        self.assertEqual(with_mdm_menu_aliases([]), [])
