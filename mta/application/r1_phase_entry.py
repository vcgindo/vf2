"""Source-only phase entry projection shared with the independent SQL adapter."""
from copy import deepcopy
from datetime import date

PHASE_FIELDS = {
    'phase_out': ('SKUCode','WhCode','OldNorm','NewNorm','PhaseOutFinished','PhaseOutStartDate','LastProcessedDate','PhaseInSKUCode'),
    'phase_in': ('SKUCode','WhCode','PhaseOutSKUOrigNorm','TargetNorm','OldNorm','NewNorm','PhaseInStartDate','LastProcessedDate'),
    'phase_map': ('PhaseOutSKUCode','WhCode','PhaseInSKUCode','PhaseOutSKUOrigNorm'),
    'phase_in_norms': ('SKUCode','WhCode','TargetNorm'),
    'phase_exceptions': ('PhaseOutSKUCode','WhCode','PhaseInSKUCode','TargetNorm','Reason','Log_Date'),
    'phase_requests': ('SKUCode','WhCode','PhaseInSKUCode','Approved'),
    'phase_stops': ('SKUCode','WhCode'),
    'phase_in_requests': ('SKUCode','WhCode','TargetNorm','Approved'),
    'seasonality': ('SKUCode','WhCode','Status'),
    'season_status': ('Id','Status'),
}
PRIOR_TABLES = {'phase_out','phase_in','phase_map','phase_in_norms','phase_exceptions'}
STATE_FIELDS = {**{k: v for k,v in PHASE_FIELDS.items() if k not in ('seasonality','season_status')},
    'log': ('SKUCode','WhCode','OldNorm','NewNorm','NormChangeDate','NormChangeReason'),
    'force_requests': ('SKUCode','WhCode','NewNorm','Approved')}


def phase_checkpoint(state):
    """Canonical table-grain multisets, including empty and duplicate rows."""
    import json
    result = []
    for name, fields in STATE_FIELDS.items():
        rows = [{f: int(r[f]) if isinstance(r[f], bool) else r[f] for f in fields} for r in state[name]]
        result.append(dict(table=name, rows=sorted(rows, key=lambda r: json.dumps(r, sort_keys=True))))
    return result


def validate_phase_input(source, business_date):
    required = set(PHASE_FIELDS) | {'from_ui','start_percent','opening_date','run_timestamp'}
    if not isinstance(source, dict) or set(source) not in (required, required | {'history_horizon'}):
        raise ValueError('Invalid phase source contract')
    horizon = source.get('history_horizon')
    if horizon is not None and (type(horizon) is not int or not -2147483648 <= horizon <= 2147483647):
        raise ValueError('Phase history horizon must be a SQL integer or absent')
    if date.fromisoformat(source['opening_date']) >= date.fromisoformat(business_date):
        raise ValueError('Phase opening must precede current business date')
    if type(source['from_ui']) is not bool or (source['start_percent'] is not None and
            (type(source['start_percent']) not in (int,float) or not 0 <= source['start_percent'] <= 100)):
        raise ValueError('Explicit phase configuration required')
    from datetime import datetime
    if datetime.fromisoformat(source['run_timestamp']).date().isoformat() != business_date:
        raise ValueError('Phase timestamp and business date disagree')
    for name, fields in PHASE_FIELDS.items():
        if not isinstance(source[name], list):
            raise ValueError('Phase source tables must be lists')
        for row in source[name]:
            if not isinstance(row, dict) or set(row) != set(fields):
                raise ValueError('Invalid phase source fields: ' + name)
            for field, value in row.items():
                if value is None:
                    continue
                if field.endswith('Code') or field in ('Reason','Log_Date','PhaseOutStartDate','PhaseInStartDate','LastProcessedDate') or name == 'season_status' and field == 'Status':
                    if not isinstance(value, str) or not value.strip():
                        raise ValueError('Invalid phase source text/date')
                elif type(value) is not int:
                    raise ValueError('Phase numeric values must be SQL integers')
            if name in PRIOR_TABLES:
                for field in ('LastProcessedDate','PhaseOutStartDate','PhaseInStartDate'):
                    if row.get(field) is not None and date.fromisoformat(row[field]) > date.fromisoformat(source['opening_date']):
                        raise ValueError('Current-day phase results cannot be seeded as prior state')


def attach_phase_sources(state, source, payload):
    """No phase calculation here: map source facts already in the entry."""
    out = deepcopy(state)
    out.update({name: deepcopy(source[name]) for name in PHASE_FIELDS})
    for name in ('dbm_master','importer_master'):
        originals = {(r['sku_code'],r['location_code']): r for r in payload['master_state'][
            'dbm_opening' if name == 'dbm_master' else 'importer_master']}
        importer = {(r['sku_code'],r['location_code']): r for r in payload['master_state']['importer_master']}
        for row in out[name]:
            k = row['SKUCode'],row['WhCode']
            row['ParentWhCode'] = importer[k]['parent_location_code']
            row['SKUIntroDate'] = originals.get(k, importer[k])['sku_intro_date']
    out['daily'] = [dict(SKUCode=r['sku_code'], WhCode=r['location_code'], Stock=r['stock_quantity'],
        GIT=r['goods_in_transit_quantity'], ReportDate=r['business_date']) for r in payload['foundation']['inventory_positions']]
    out['attributes'] = [dict(SKUCode=r['sku_code'], WhCode=r['location_code'], PackSize=r['pack_size'])
                         for r in payload['master_state']['importer_master']]
    return out


def clear_phase_inputs(state, day, *, history_horizon):
    """ClearPhaseInPhaseOutData: approved inputs only; inclusive midnight cutoff.

    A missing setting makes SQL DATEADD NULL, so history is retained.
    """
    from datetime import datetime, timedelta
    out = deepcopy(state)
    for name in ('phase_requests','phase_in_requests'):
        out[name] = [r for r in out[name] if r['Approved'] != 1]
    out['phase_stops'] = []
    if history_horizon is not None:
        cutoff = datetime.fromisoformat(day) - timedelta(days=history_horizon)
        out['phase_exceptions'] = [r for r in out['phase_exceptions']
                                   if datetime.fromisoformat(r['Log_Date']) > cutoff]
    return out
