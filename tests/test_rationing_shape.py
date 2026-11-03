import unittest

from mta.domain.btr_rationing_history import COLUMNS
from mta.runtime.rationing_shape import require_fields


class RationingShapeTests(unittest.TestCase):
    def setUp(self):
        self.fields = [[c['name'], c['name'], 'str'] for c in COLUMNS]

    def test_empty_old_shape_and_full_null_shape(self):
        require_fields([], 0)
        require_fields(self.fields, 0)
        require_fields(self.fields, 4)
        with self.assertRaises(ValueError):
            require_fields([], 1)

    def test_exact_order_names_and_scalar_wire_kinds(self):
        for mutate in (lambda f: f.reverse(),
                       lambda f: f[0].__setitem__(0, 'Other'),
                       lambda f: f[0].__setitem__(1, 'Other'),
                       lambda f: f[0].__setitem__(2, 'bool'),
                       lambda f: f[0].__setitem__(2, ['str'])):
            fields = [list(f) for f in self.fields]
            mutate(fields)
            with self.assertRaises(ValueError):
                require_fields(fields, 1)

    def test_existing_numeric_and_boolean_representations(self):
        for index, column in enumerate(COLUMNS):
            kinds = {'int': ('int',), 'bit': ('bool', 'int'),
                     'decimal': ('str', 'int', 'float')}.get(column['type'], ('str',))
            for kind in kinds:
                fields = [list(f) for f in self.fields]
                fields[index][2] = kind
                require_fields(fields, 1)

    def test_count_is_not_coerced(self):
        for count in (True, '1', -1, 1.0, None):
            with self.assertRaises(ValueError):
                require_fields(self.fields, count)
