"""Exact S1 retained hierarchy input projection for the approval-day source."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

SHA256 = '833545a508153c8dd53aa426be45efa8997c9a28738e37b66d3f3194a4e5c17c'


def project(rows, *, path, artifact_sha256):
    from mta.mdm.daily_source import APPROVAL_DAY_ARTIFACT_SHA
    if artifact_sha256 != APPROVAL_DAY_ARTIFACT_SHA or not path:
        raise ValueError('Exact approval-day hierarchy source required')
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise ValueError('Approval-day hierarchy file identity differs')
    binding = json.loads(raw)
    if binding['schema'] != 'fresh-mdm-approval-day-hierarchy-v1':
        raise ValueError('Approval-day hierarchy schema differs')
    return project_rows(rows, binding)


def project_rows(rows, binding):
    result = deepcopy(rows)
    for kind, code, prefix, custom in (
            ('products', 'SKUCode', 'SL', 'SKUAtt'),
            ('locations', 'WhCode', 'LL', 'LocAtt')):
        index = {row['code']: row for row in binding[kind]}
        if len(index) != len(binding[kind]):
            raise ValueError('Approval-day hierarchy duplicate identity')
        for row in result:
            # Native compose also emits description-only parent rows. They are
            # not business pairs; preserve their NULL attributes verbatim.
            if row.get('SKUCode') is None or row.get('WhCode') is None:
                if row.get(code) is not None and row[code] not in index:
                    raise ValueError('Approval-day hierarchy dependency unavailable')
                continue
            if row[code] not in index:
                raise ValueError('Approval-day hierarchy identity unavailable')
            for level in (1, 2, 3):
                expected = index[row[code]]['level_' + str(level)]
                field = prefix + str(level)
                if (expected is None or row[custom + f'{level:02}'] != expected
                        or row[field] not in (None, expected)):
                    raise ValueError('Approval-day hierarchy conflicts with retained source')
                row[field] = expected
    return result
