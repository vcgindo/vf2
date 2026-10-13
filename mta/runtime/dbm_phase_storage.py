"""Additive typed phase recommendation images; earlier catalogues stay pinned."""
import hashlib
import json
from pathlib import Path

TABLE = 'DBM/PhaseOutRecommendation'
POPULATION = 'PhaseOutRecommendation'
STAGES = tuple(f'phase-recommendation-{h}' for h in (30, 60, 90))
OPENING = 'input/opening/state/dbm/'+POPULATION+'/values'
FROZEN = 'input/predecessor/dbm/'+POPULATION+'/values'
_raw = (Path(__file__).resolve().parents[1]/'config/dbm_phase_recommendation_v1.json').read_bytes()
if hashlib.sha256(_raw).hexdigest() != 'dfbbff41bc6c89813083b6e50566f49ec0a693bd99133f056062cee1b9f1ea86':
    raise ValueError('Phase recommendation typed schema identity differs')
CATALOG = json.loads(_raw)
TABLES = {TABLE: [(column['name'], column['type']) for column in CATALOG['columns']]}
BINDINGS = {'closing/dbm/'+POPULATION: TABLE,
    **{'reports/'+stage+'/'+POPULATION:TABLE for stage in STAGES}}


def validate_write(image, binding, rows):
    from mta.domain.dbm_phase_recommendation import FIELDS, validate_target
    if not (image == FROZEN and binding is None or BINDINGS.get(binding) == TABLE and image == binding):
        raise ValueError('Phase recommendation typed owner differs')
    for row in rows:
        if tuple(row) != FIELDS:
            raise ValueError('Complete ordered phase recommendation fields required')
        validate_target(row)
