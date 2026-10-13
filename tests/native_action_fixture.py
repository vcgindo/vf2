"""Small supplied inputs for pure native action-component tests only."""
from copy import deepcopy
from tests.production_h3_fixture import PARENT, supplied_input as accepted_supplied_input

TARGET = ('SUPPLIED-Z9', PARENT)
ACTION_TIMESTAMP = '2037-04-12T12:00:00+05:30'
ACTOR = 'h3-owned-proof'


def operator_input(*, moq_format='WithDestLoc'):
    """Build the external operator input for this exact positive-action proof."""
    value = accepted_supplied_input(moq_format=moq_format)
    value['configuration']['delivery']['batch']['AutoDBMActive'] = 0
    reasons = [dict(Id=5, Reason='Supplied rule 5')]
    value['opening']['state']['dbm']['ReasonCodes'] = deepcopy(reasons)
    value['opening']['state']['controls']['reason_codes'] = deepcopy(reasons)
    value['recipe']['version'] = 'supplied-h3-native-actions-v1'
    value['opening']['identity'] = 'SUPPLIED-H3-NATIVE-ACTIONS-' + moq_format
    return value
