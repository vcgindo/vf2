"""Explicit generic scope policy; validation never grants execution authority.

The existing placement envelope and typed registration own this versioned
policy. Site identity does not select client processing. Native namespace,
certificate, source and captured registration admission remain separate.
"""
from copy import deepcopy
import re

from mta.serialization import digest

SCHEMA = 'vectorflow-production-generic-scope-policy-v1'
HOOK_SCHEMA = 'vectorflow-production-generic-hook-policy-v1'
PURPOSE = 'production-generic-scoped'
MODE = 'client-processing-not-selected'
GENERIC_POLICY = 'generic-finalization-active-nms-v1'
HOOKS = ('PostBPR', 'PreDBM', 'PostDBM', 'PostBTR', 'SiteFinal')
FIELDS = frozenset(('schema', 'purpose', 'site_code', 'hooks', 'input_download', 'authority'))


def text(value, maximum, label):
    if (type(value) is not str or not 1 <= len(value) <= maximum
            or not value.strip() or '\0' in value):
        raise ValueError('Explicit bounded ' + label + ' required')
    return value


def disposition(value):
    if (type(value) is not dict or set(value) != FIELDS
            or value['schema'] != SCHEMA or value['purpose'] != PURPOSE
            or value['hooks'] != {name: MODE for name in HOOKS}
            or value['input_download'] != 'enabled-five-file-four-table-archive'):
        raise ValueError('Explicit supported generic scope policy required; client processing is unavailable')
    text(value['site_code'], 100, 'configured site')
    text(value['authority'], 1000, 'configuration authority')
    return deepcopy(value)


def hook(value):
    if (type(value) is not dict or set(value) != {
            'schema', 'site_code', 'placement', 'mode', 'authority', 'source_sha256'}
            or value['schema'] != HOOK_SCHEMA or value['placement'] != 'PostBPR'
            or value['mode'] != MODE or type(value['source_sha256']) is not str
            or re.fullmatch('[0-9a-f]{64}', value['source_sha256']) is None):
        raise ValueError('Explicit generic hook policy required; client processing is unavailable')
    text(value['site_code'], 100, 'configured site')
    text(value['authority'], 1000, 'configuration authority')
    return deepcopy(value)


def configuration(profile, policy):
    """Bind the policy to the actual initialized generic business profile."""
    checked = disposition(policy)
    if (type(profile) is not dict or type(profile.get('delivery')) is not dict
            or profile['delivery'].get('site_code') != checked['site_code']
            or profile.get('daily_publication') is not True):
        raise ValueError('Generic scope policy differs from initialized site/publication')
    from mta.application.daily_finalization import configuration as finalization
    generic = finalization(profile)
    if generic is None or generic['policy'] != GENERIC_POLICY:
        raise ValueError('Explicit supported active generic finalization policy required')
    return checked


def report_configuration(value):
    """Qualify the existing supported roster; never accept arbitrary SQL."""
    from mta.application import runtime_report_configuration as definitions
    from mta.runtime.runtime_report_request import DEFINITIONS_DIGEST, FILENAME_SEED_DIGEST
    config = definitions.configuration(value)
    rows = config['RuntimeReports']
    if (digest([{key: item for key, item in row.items() if key != 'LastGeneratedFileName'}
                for row in rows]) != DEFINITIONS_DIGEST
            or digest(definitions.last_generated(config)) != FILENAME_SEED_DIGEST
            or any(type(row[field]) is not bool for row in rows for field in definitions.BIT_FIELDS)
            or config['DownloadableUIReportSettings'] != [dict(ReportName='RRR', Active=False,
                GenerationScope='PostBPR', DestFolder='%ReportsDownloadLoc%')]
            or any(type(row['Active']) is not bool for row in config['DownloadableUIReportSettings'])):
        raise ValueError('Only the qualified report roster and disabled independent RRR are supported')
    return config


def archive_label(database):
    """Safe physical owner spelling, after native database admission."""
    if type(database) is not str or re.fullmatch('[A-Za-z_][A-Za-z0-9_]{0,62}', database) is None:
        raise ValueError('Safe actual database label required')
    return database


def require_database(reference, *, run=None):
    """Admit a real registered owner; a valid policy alone grants no access.

    Readers bind the original captured registration. New writers require the
    current certified registration. Existing entry/read admission still owns
    release and transaction checks; this is the extra scope-policy boundary.
    """
    from django.db import connection
    from mta.mdm.owned_namespace import (_database_identity, _registered_identity,
        _catalogue_evidence, _validate_identity)
    from mta.runtime import runtime_report_request, report_definition_registration as registrations
    config, selected_hook, anchor, policy = runtime_report_request.configuration(reference)
    disposition(policy)
    with connection.cursor() as cursor:
        database = _database_identity(cursor)
        registered = _registered_identity(cursor)
        evidence = _catalogue_evidence(cursor, database, registered)
        _validate_identity(database, registered, evidence)
    archive_label(database['name'])
    current = database['current_user_oid']
    session = database['session_user_oid']
    if not ((current == registered['owner_oid'] and session == registered['issuer_oid'])
            or (current == registered['consumer_oid'] and session == registered['consumer_oid'])):
        raise ValueError('Scope access requires its registered installer or consumer role')
    if run is not None:
        from mta.runtime.runtime_report_registered_request import read_captured
        from mta.runtime.input_reader import read_input
        raw = read_input(run, components=('scope_request', 'profile'))
        attachment = read_captured(run)
        if (attachment is None or raw['scope_request']['runtime_reports'] != reference
                or attachment['registration']['initialization_id'] != anchor['identity']):
            raise ValueError('Production scope requires its captured typed registration')
        configuration(raw['profile'], policy)
    else:
        from mta.runtime.models import ProductionInitialization, InitializationCertification
        from mta.runtime.report_definition_models import ReportDefinitionRegistration
        initial = ProductionInitialization.objects.get(pk=anchor['identity'])
        certificate = InitializationCertification.objects.get(initialization=initial, status='CERTIFIED')
        encoded = registrations.encode(reference, initialization_id=str(initial.pk),
            source_digest=initial.source.digest, certificate_id=str(certificate.pk),
            certificate_digest=certificate.receipt_digest)
        owner = ReportDefinitionRegistration.objects.get(pk=encoded['registration_digest'])
        if registrations._stored(owner) != encoded:
            raise ValueError('Production scope registration differs from certified typed custody')
    return database['name']
