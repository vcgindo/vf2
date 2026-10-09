"""Selected Importer ValidatePhaseout/ValidatePhaseInNorms SQL statements.

Only explicitly owned masters7–9 input opts in. Existing accepted timelines are
not silently reinterpreted. No phase calculation or manufactured phase outcome.
"""
from collections import Counter
from copy import deepcopy
from mta.application.r1_importer_master import _sql_key


def _pair(row):
    return _sql_key(row['SKUCode']), _sql_key(row['WhCode'])


def _distinct(rows):
    seen = {}
    for row in rows:
        key = tuple((f, _sql_key(row[f])) for f in sorted(row))
        if key in seen and seen[key] != row:
            raise ValueError('Native phase DISTINCT has incomparable collation-equal values')
        seen.setdefault(key, row)
    return list(seen.values())


def _trim(rows, fields):
    result = deepcopy(rows)
    for row in result:
        for field in fields:
            if row[field] is not None:
                row[field] = row[field].strip(' ')
    return result


def validate_phase_inputs(phase_out, stops, phase_in, rejected_master, timestamp):
    rejected = deepcopy(rejected_master)

    def reject(rows, code, description, null_marker=False):
        for row in rows:
            rejected.append(dict(SKUCode='-NULL-' if null_marker and row['SKUCode'] is None else row['SKUCode'],
                WhCode='-NULL-' if null_marker and row['WhCode'] is None else row['WhCode'],
                RejectionDate=timestamp, ReasonCode=code, ReasonDescription=description))

    def warning(code, description):
        reject([dict(SKUCode='-NA-', WhCode='-NA-')], code, description)

    # ValidatePhaseout.sql: trim only PhaseOut, DISTINCT both inputs separately.
    phase_out = _distinct(_trim(phase_out, ('SKUCode', 'WhCode', 'PhaseInSKUCode')))
    phase_out = [r for r in phase_out if any(r[f] is not None
                 for f in ('SKUCode', 'WhCode', 'PhaseInSKUCode'))]
    if not phase_out:
        warning(-141, 'Warning-PhaseOut file/table not available or unreadable')
    invalid = [r for r in phase_out if r['SKUCode'] is None or r['WhCode'] is None]
    if invalid:
        reject(invalid, 141, 'Null SKUCode/WhCode in PhaseOut File', True)
        phase_out = []
    invalid = [r for r in phase_out if r['SKUCode'] is not None and r['PhaseInSKUCode'] is not None
               and _sql_key(r['SKUCode']) == _sql_key(r['PhaseInSKUCode'])]
    if invalid:
        reject(invalid, 144, 'Same Phasein Phaseout SKUCode')
        phase_out = []
    counts = Counter(_pair(r) for r in phase_out)
    duplicate_pairs = {}
    for row in phase_out:
        if counts[_pair(row)] > 1:
            duplicate_pairs.setdefault(_pair(row), row)
    if duplicate_pairs:
        reject(duplicate_pairs.values(), 147, 'Multiple Phase-in items for single Phase-out item')
        phase_out = []
    stops = _distinct(deepcopy(stops))
    stops = [r for r in stops if r['SKUCode'] is not None or r['WhCode'] is not None]
    if not stops:
        warning(-146, 'Warning-Stop PhaseOut file/table not available or unreadable')
    invalid = [r for r in stops if r['SKUCode'] is None or r['WhCode'] is None]
    if invalid:
        reject(invalid, 142, 'Null SKUCode/WhCode in stop PhaseOut File', True)
        stops = []  # Native RETURN skips the common-pair step, not the next script.
    else:
        common = [dict(SKUCode=a['SKUCode'], WhCode=b['WhCode'])
                  for a in phase_out for b in stops if _pair(a) == _pair(b)]
        if common:
            reject(common, 143, 'common records in Phase out and stop PhaseOut File/table')
            phase_out, stops = [], []

    # The next batch runs even when ValidatePhaseout returned early.
    phase_in = _distinct(_trim(phase_in, ('SKUCode', 'WhCode')))
    phase_in = [r for r in phase_in if any(r[f] is not None
                for f in ('SKUCode', 'WhCode', 'TargetNorm'))]
    if not phase_in:
        warning(-142, 'Warning-PhaseInNorms file/table not available or unreadable')
    else:
        invalid = [r for r in phase_in if any(r[f] is None
                   for f in ('SKUCode', 'WhCode', 'TargetNorm'))]
        if invalid:
            reject(invalid, 145, 'Null SKU/WhCode/TargetNorm in PhaseInNorms File/Table', True)
            phase_in = []
        else:
            counts = Counter(_pair(r) for r in phase_in)
            duplicate_pairs = {}
            for row in phase_in:
                if counts[_pair(row)] > 1:
                    duplicate_pairs.setdefault(_pair(row), row)
            if duplicate_pairs:
                reject(duplicate_pairs.values(), 146, 'Duplicate entries in PhaseInNorms File')
                phase_in = []
    return dict(phase_requests=phase_out, phase_stops=stops,
                phase_in_requests=phase_in, rejected_master=rejected)
