"""Explicit empty RuntimeReports configuration for newly owned scoped tests.

This declaration does not certify production configuration, other downloads or
site hooks. Nonempty report rosters need their applicable query/template owner.
The existing captured scope request owns these bounded metadata bytes.
"""
from copy import deepcopy
import hashlib
import json

from mta.serialization import digest

SCHEMA='fresh-scoped-test-runtime-reports-v1'
REFERENCE='fresh-scoped-runtime-reports-reference-v1'
LIMIT=4096

# New, separately captured TEST contract. Canonical JSON is bounded definition
# metadata, not a substitute for typed business/source rows. Keeping it scalar
# also avoids silently mapping RuntimeReports into an unrelated input table.
PUBLICATION_REFERENCE='fresh-postbpr-publication-reference-v1'
PUBLICATION_LIMIT=1024*1024


def require_publication_writer():
    """The forward-schema compatibility build can read but cannot start work."""
    import os
    if os.environ.get('VF_RUNTIME_REPORT_PUBLISH')!='1':
        raise ValueError('This application mode does not enable new runtime report publication')


def _metadata(raw):
    from mta.application.runtime_report_configuration import _pairs, _nonfinite
    if type(raw) is not str or not 0<len(raw.encode('utf-8'))<=PUBLICATION_LIMIT:
        raise ValueError('Bounded canonical report metadata required')
    value=json.loads(raw,object_pairs_hook=_pairs,parse_constant=_nonfinite)
    if raw!=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False):
        raise ValueError('Canonical report metadata bytes differ')
    return value


def publication_configuration(value):
    """Validate only the released two-report NEW owned-test request contract."""
    from mta.application import runtime_report_configuration as definitions
    from mta.application.runtime_report_projection import describe
    from mta.application.runtime_report_hooks import configuration as hook_configuration
    from mta.runtime.runtime_report_catalogue import validate_anchor
    if (type(value) is not dict or set(value)!={'schema','purpose','configuration_json',
            'configuration_digest','hook_json','catalogue_anchor_json','authority_sha256'}
            or value['schema']!=PUBLICATION_REFERENCE
            or value['purpose']!='owned-postbpr-publication-test'):
        raise ValueError('Explicit new PostBPR publication reference required')
    from mta.runtime.ingestion_context import sha
    sha(value['authority_sha256'])
    config=definitions.configuration(_metadata(value['configuration_json']))
    if digest(config)!=value['configuration_digest']:
        raise ValueError('Captured publication configuration digest differs')
    rows=config['RuntimeReports']
    if (config['DownloadableUIReportSettings'] or len(rows)!=2
            or {row['Id'] for row in rows}!={7,10}
            or any(not row['Active'] or row['Placement']!='PostBPR'
                   or describe(row)['captured_source_id']!=row['Id'] for row in rows)):
        raise ValueError('Only the explicit Total Requirement and Spike placement is released')
    expected={7:('Spike_Order_Dump','Spiker_Order_Dump',True),
              10:('TotalReqReport_YYYY-MM-DD','%TotalReqReport%',False)}
    for row in rows:
        if ((row['ReportName'],row['FileName'],bool(row['Compression']))!=expected[row['Id']]
                or row['DestFolder']!='%ReportsDownloadLoc%'):
            raise ValueError('Captured report selector or destination is outside the released placement')
    hook=hook_configuration(_metadata(value['hook_json']))
    anchor=validate_anchor(_metadata(value['catalogue_anchor_json']),report_configuration=config)
    if (anchor['configuration_digest']!=digest(config)
            or anchor['definition_digest']!=definitions.definition_digest(config)
            or anchor['last_generated']!=definitions.last_generated(config)):
        raise ValueError('Initial catalogue configuration or filename seed differs')
    return config,hook,anchor


def configuration(value):
    if (type(value) is not dict or set(value)!={'schema','purpose','provenance','RuntimeReports'}
            or value['schema']!=SCHEMA or value['purpose']!='owned-scoped-test'
            or type(value['provenance']) is not str or not 1<=len(value['provenance'])<=1000
            or not value['provenance'].strip()
            or type(value['RuntimeReports']) is not list or value['RuntimeReports']):
        raise ValueError('Explicit authorized empty test RuntimeReports roster required')
    return deepcopy(value)


def validate(value):
    from mta.runtime import runtime_report_request as placement
    if isinstance(value,dict) and value.get('schema')==placement.REFERENCE:
        return placement.validate_reference(value)
    if isinstance(value,dict) and value.get('schema')==PUBLICATION_REFERENCE:
        publication_configuration(value)
        return deepcopy(value)
    from mta.runtime.ingestion_context import sha
    if type(value) is not dict or set(value)!={'schema','sha256','configuration','configuration_digest'} or value['schema']!=REFERENCE:
        raise ValueError('Complete scoped RuntimeReports reference required')
    sha(value['sha256'])
    checked=configuration(value['configuration'])
    if value['configuration_digest']!=digest(checked):
        raise ValueError('Scoped RuntimeReports configuration digest differs')
    return deepcopy(value)


def decode(raw,expected_sha256):
    from mta.mdm.initialization_contract import object_pairs,sha
    sha(expected_sha256,'RuntimeReports file')
    if type(raw) is not bytes or not 0<len(raw)<=PUBLICATION_LIMIT or hashlib.sha256(raw).hexdigest()!=expected_sha256:
        raise ValueError('Bounded RuntimeReports file bytes differ')
    def nonfinite(value):raise ValueError('Nonfinite RuntimeReports value')
    parsed=json.loads(raw,object_pairs_hook=object_pairs,parse_constant=nonfinite)
    from mta.runtime.runtime_report_request import REFERENCE as PLACEMENT_REFERENCE
    if isinstance(parsed,dict) and parsed.get('schema') in (PUBLICATION_REFERENCE,PLACEMENT_REFERENCE):
        return validate(parsed)
    if len(raw)>LIMIT:raise ValueError('Bounded empty TEST RuntimeReports file bytes differ')
    checked=configuration(parsed)
    return validate(dict(schema=REFERENCE,sha256=expected_sha256,configuration=checked,configuration_digest=digest(checked)))


def load(path,expected_sha256):
    # Read at most the bound even when the supplied file is unexpectedly large.
    with path.open('rb') as stream:raw=stream.read(PUBLICATION_LIMIT+1)
    return decode(raw,expected_sha256)


def require_test_database():
    """Additional restriction, after the native installer's ownership check."""
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute('SELECT current_database()')
        name=cursor.fetchone()[0]
    if not name.lower().startswith('vftest_fresh_'):
        raise ValueError('Empty test RuntimeReports declaration requires an owned VFTEST_Fresh database')


def status(value):
    if value is None:return dict(configured=False)
    checked=validate(value)
    from mta.runtime.runtime_report_request import REFERENCE as PLACEMENT_REFERENCE
    if checked['schema']==PLACEMENT_REFERENCE:
        return dict(configured=True,purpose=checked['purpose'],row_count=8,
            configuration_digest=checked['configuration_digest'])
    if checked['schema']==PUBLICATION_REFERENCE:
        return dict(configured=True,purpose=checked['purpose'],row_count=2,
            configuration_digest=checked['configuration_digest'])
    return dict(configured=True,purpose='owned-scoped-test',row_count=0,
        sha256=checked['sha256'],configuration_digest=checked['configuration_digest'])
