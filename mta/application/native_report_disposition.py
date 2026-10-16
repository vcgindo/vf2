"""Two exact human-approved occurrence-text dispositions; never a default.

This identity is separate from the immutable daily request. Its only permitted
effect is unavailable text for the evidenced day-five/day-six Norm0/30 group.
"""
from copy import deepcopy
from datetime import date

from mta.serialization import digest

ID = 'handoff3005-day05-norm0-occurrences-v1'
KEY = ('5954', 'DP010290')
DAY = '2026-10-17'
ORIGIN = '04f76972-375c-480f-8d57-16207bb174ae'
INPUT = '53b9d6939b3ad2e3589cd81c47ead6b8e8d4e83f160bf3d3c19f2ff5a718cfee'
DAILY_INPUT = '496e5dbbb08f7ba0ea3864ee96f7f8213db8cd7edcafba6213efb1977165d130'
PARENT = 'a2aa00df-b5c4-42f0-8205-e579f0709d2c'
PARENT_OUTPUT = 'cfa1a0d366d691dba7ebfca31cf02aba4f93cecd978a77be0a80d2ee2e2eab64'
INITIALIZATION = '25cceb52-e68f-446b-b2d2-5e212ceec173'
SOURCE = '2e22cdb6866c3e43587aa26612abd8201865e903243919add92fffc2c454fa5f'
REQUEST = '99f576f843ac8b40cfc64965c4126f41d3f6acf5b0cf522d6c9fa00c61e95ff4'
CONFIGURATION = 'c3e2e2f1395ca40b0557b0edaceb96a01c2c02b37d8f962e6b732586a9d5d27c'
RETRY = 'g3-hierarchy-day-05-report-disposition-v1'
CLASSIFICATION = 'LEGACY_FLAW/NOT_PARITY'
REASON = 'Canonical STRING_AGG does not specify occurrence order.'
DISPLAY = 'UNAVAILABLE: LEGACY_FLAW/NOT_PARITY - unordered STRING_AGG'
OBSERVATIONS = [(f'2026-10-{n:02}', 1) for n in range(13, 18)]
POLICY = dict(id=ID, business_date=DAY, origin_run_id=ORIGIN, input_digest=INPUT,
    daily_input_sha256=DAILY_INPUT, predecessor_id=PARENT,
    predecessor_output_digest=PARENT_OUTPUT, initialization_id=INITIALIZATION,
    source_digest=SOURCE, request_digest=REQUEST, configuration_digest=CONFIGURATION,
    execution_revision=RETRY, norm=0, horizon=30,
    SKUCode=KEY[0], WhCode=KEY[1], field='Occurances',
    observations_digest=digest(OBSERVATIONS), classification=CLASSIFICATION,
    reason=REASON, authorization='human-controller-2026-10-16',
    source_sql_sha256='c47103cd5d309c8d692766fcef798ab138694627d944dee7c3d25619c9ed9766')


DAY6_ID = 'handoff3005-day06-norm0-occurrences-v1'
DAY6_RETRY = 'g3-hierarchy-day-06-report-disposition-v1'
DAY6_OBSERVATIONS = [(f'2026-10-{n:02}', 1) for n in range(13, 19)]
DAY6_POLICY = dict(POLICY, id=DAY6_ID, business_date='2026-10-18',
    origin_run_id='47d1a1c8-f40c-40fb-916a-20a0ef968ef4',
    origin_execution_revision='g3-hierarchy-day-06-v1',
    input_digest='8f6a31781336f11cb58994d158666f6c3e86f92fd628daeb2a0b45b897fb1234',
    daily_input_sha256='6b3fe71cd0ebef456af01e0f4a43f8a413bf2451eeae154e1395b73c5570a949',
    request_digest='5a66c6aa700ecb46434df65f4239d0da2d9528da97500c5456b832345431f538',
    capture_revision_digest='01b8e27cbf261ff21804ba2522cde908fa308dafaa38dba8b0c8c634f73a5bd0',
    predecessor_id='8afb96de-bfaf-4119-902d-f31db149cf54',
    predecessor_output_digest='d0d32d986754e7d76b78e315e60568f9104c437709f6c6e364b80a7a1c332f3b',
    execution_revision=DAY6_RETRY, observations_digest=digest(DAY6_OBSERVATIONS))
POLICIES = {ID: POLICY, DAY6_ID: DAY6_POLICY}
RETRIES = {ID: RETRY, DAY6_ID: DAY6_RETRY}


def binding(requested=ID):
    if requested not in POLICIES:
        raise ValueError('Unknown exact native report disposition')
    policy = POLICIES[requested]
    return dict(policy=deepcopy(policy), policy_digest=digest(policy))


def require_binding(value):
    requested = value.get('policy', {}).get('id') if isinstance(value, dict) else None
    if (requested not in POLICIES or value != binding(requested)
            or digest(value) != digest(binding(requested))):
        raise ValueError('Exact native report disposition binding differs')
    return value


def admit(*, requested, native, origin, parent, initialization, raw,
          request_digest, execution_revision):
    """Additional guard only; existing native and frozen-request gates remain."""
    if requested not in POLICIES or not native or origin is None or parent is None:
        raise ValueError('Native report disposition requires its exact frozen retry')
    policy = POLICIES[requested]
    failed = origin.run
    if (str(failed.pk) != policy['origin_run_id'] or failed.status != 'FAILED'
            or failed.input_digest != policy['input_digest'] or origin.status != 'CAPTURED'
            or failed.failure != dict(type='AmbiguousReport',
                message='Unordered occurrence STRING_AGG has distinct fragments')
            or failed.execution_revision != policy.get('origin_execution_revision', 'g3-hierarchy-day-05-v1')
            or str(failed.predecessor_id) != policy['predecessor_id']
            or origin.request_digest != request_digest or request_digest != policy['request_digest']
            or str(parent.pk) != policy['predecessor_id'] or parent.status != 'SUCCEEDED'
            or parent.output_digest != policy['predecessor_output_digest']
            or str(initialization.pk) != INITIALIZATION
            or initialization.source.digest != SOURCE
            or initialization.configuration_digest != CONFIGURATION
            or origin.source_id != initialization.source_id
            or execution_revision != policy['execution_revision']
            or raw['day']['business_date'] != policy['business_date']
            or raw['daily_input_sha256'] != policy['daily_input_sha256']
            or raw['report_exceptions'] != {} or digest(raw) != policy['input_digest']
            or requested == DAY6_ID and origin.revision_digest != policy['capture_revision_digest']):
        raise ValueError('Native report disposition owner/input/retry differs')
    return binding(requested)


def report_group(today, state, value, *, norm, horizon):
    """Prove the exact actual producer rows immediately before report assembly."""
    require_binding(value)
    policy = value['policy']
    observations = DAY6_OBSERVATIONS if policy['id'] == DAY6_ID else OBSERVATIONS
    today = today.isoformat() if isinstance(today, date) else today
    if today != policy['business_date'] or (norm, horizon) != (0, 30):
        raise ValueError('Native report disposition date/horizon differs')
    masters = [r for r in state['DBMMaster'] if (r['SKUCode'], r['WhCode']) == KEY]
    descriptions = [r for r in state['SKUDescriptionTbl'] if r['SKUCode'] == KEY[0]]
    if (len(masters) != 1 or type(masters[0]['Norm']) is not int
            or masters[0]['Norm'] != 0 or len(descriptions) != 1):
        raise ValueError('Native report disposition master/description multiplicity differs')
    rows = [r for r in state['DailyConsumption']
            if (r['SKUCode'], r['WhCode']) == KEY]
    observed = [(r['ReportDate'], r['Consumption']) for r in rows]
    if (observed != observations or any(type(r['Consumption']) is not int for r in rows)
            or digest(observed) != policy['observations_digest']):
        raise ValueError('Native report disposition observations/types/order differ')
    return [KEY]


def disclose_export(state, value):
    """Keep typed text NULL, but never expose a silent empty export cell."""
    require_binding(value)
    count = 6 if value['policy']['id'] == DAY6_ID else 5
    report = [r for r in state['Norm0Norm1Norm2Report']
              if (r['SKUCode'], r['WHCode']) == KEY]
    details = [r for r in state['Norm0_1_2ReportDetails']
               if (r['SKUCode'], r['WhCode']) == KEY]
    if (len(report) != 1 or len(details) != 1
            or report[0]['Occurances'] is not None or details[0]['Occurances'] is not None
            or any(type(report[0][k]) is not int or report[0][k] != count for k in ('Count','TotalSale'))
            or any(type(details[0][k]) is not int or details[0][k] != count for k in ('NumOfDaysSold','TotalSale'))):
        raise ValueError('Native report disposition numeric/population/text drift')
    exported = [r for r in state['ReportRows']
                if len(r['values']) == 9 and (r['values'][0], r['values'][2]) == KEY]
    if len(exported) != 1 or exported[0]['values'][8] != ' ':
        raise ValueError('Native report disposition export population/text differs')
    exported[0]['values'][8] = '"' + DISPLAY + '"'


def verify_export(tables, value):
    """Consumer check of already disclosed cells; no report recalculation."""
    copied = deepcopy(tables)
    rows = [r for r in copied['ReportRows'] if (r['values'][0], r['values'][2]) == KEY]
    if len(rows) != 1 or rows[0]['values'][8] != '"' + DISPLAY + '"':
        raise ValueError('Native report disposition disclosure missing')
    rows[0]['values'][8] = ' '
    disclose_export(copied, value)


def verify_commit(admitted, lineage, run):
    actual = (lineage or [{}])[0].get('native_report_disposition')
    if actual != admitted:
        raise ValueError('Native report disposition admission/lineage differs')
    if actual is not None:
        require_binding(actual)
        policy = actual['policy']
        if (run.input_digest != policy['input_digest'] or str(run.predecessor_id) != policy['predecessor_id']
                or run.business_date.isoformat() != policy['business_date'] or run.execution_revision != policy['execution_revision']):
            raise ValueError('Native report disposition output owner differs')


def verify_replay(run, lineage, requested):
    """An idempotent read may never drop or replace an attempt's authorization."""
    actual = ((lineage or [{}])[0].get('native_report_disposition')
              if run.status == 'SUCCEEDED' else run.production_manifest.get('native_report_disposition'))
    if requested is None:
        if actual is not None:
            raise ValueError('Native report disposition required for this repeated attempt')
    elif requested not in POLICIES or actual is None or actual != binding(requested):
        raise ValueError('Native report disposition repeated attempt differs')
    else:
        if run.status != 'SUCCEEDED' and run.production_manifest != {'native_report_disposition': actual}:
            raise ValueError('Native report disposition repeated admission metadata differs')
        verify_commit(actual, [{'native_report_disposition': actual}], run)


def limitation(value):
    require_binding(value)
    return dict(disposition_id=value['policy']['id'], policy_digest=value['policy_digest'],
        SKUCode=KEY[0], WhCode=KEY[1], norm=0, horizon=30, field='Occurances',
        classification=CLASSIFICATION, reason=REASON, display=DISPLAY)
