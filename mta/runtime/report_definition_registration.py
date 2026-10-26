"""Finite typed registration contract for future owned placement requests.

These codecs do not grant installation, capture or execution authority. The
registrar must authenticate the installation/certificate and persist the four
separate row sets atomically before a request may reference their identity.
No registration adopts an existing capture or writes generated catalogue state.
"""
from copy import deepcopy
import json

from mta.application import runtime_report_configuration as definitions
from mta.runtime import runtime_report_request as placement
from mta.runtime.ingestion_context import identity, sha
from mta.serialization import digest


SCHEMA = 'fresh-retained-report-definition-registration-v1'
DEFINITION_FIELDS = frozenset({'Id', *definitions.TEXT_FIELDS, *definitions.BIT_FIELDS}) - {
    'LastGeneratedFileName'}
UI_FIELDS = frozenset({'Active', *definitions.UI_TEXT_FIELDS})
POLICY_FIELDS = frozenset({'hook_json', 'disposition_json', 'catalogue_anchor_json', 'authority_sha256'})
HEADER_FIELDS = frozenset({'schema', 'initialization_id', 'source_digest', 'certificate_id',
    'certificate_digest', 'configuration_digest', 'definition_digest', 'seed_digest',
    'policy_digest', 'reference_digest'})
DISABLED_UI = [dict(ReportName='RRR', Active=False, GenerationScope='PostBPR',
                   DestFolder='%ReportsDownloadLoc%')]


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False)


def _ordered(rows, fields, name):
    if (type(rows) is not list or any(type(row) is not dict or set(row) != fields | {'ordinal'}
                                    for row in rows)
            or any(type(row['ordinal']) is not int or row['ordinal'] != n
                   for n, row in enumerate(rows))):
        raise ValueError('Exact ordered registration rows required: ' + name)


def configuration_from_rows(report_rows, seed_rows, ui_rows):
    """Reconstruct native fields without JSON row payloads or implicit joins.

    The seeds have their own ordered Id custody. In particular, dictionary
    joins must not hide duplicate seeds, missing rows or a reordered definition.
    """
    _ordered(report_rows, DEFINITION_FIELDS, 'RuntimeReports definitions')
    _ordered(seed_rows, frozenset({'Id', 'LastGeneratedFileName'}), 'filename seeds')
    _ordered(ui_rows, UI_FIELDS, 'DownloadableUIReportSettings')
    if len(report_rows) != len(seed_rows):
        raise ValueError('One exact filename seed per definition required')
    reports = []
    for definition, seed in zip(report_rows, seed_rows):
        if type(seed['Id']) is not int or seed['Id'] != definition['Id']:
            raise ValueError('Filename seed definition/order differs')
        reports.append({**{k: deepcopy(v) for k, v in definition.items() if k != 'ordinal'},
                        'LastGeneratedFileName': seed['LastGeneratedFileName']})
    return definitions.configuration(dict(schema=definitions.SCHEMA, RuntimeReports=reports,
        DownloadableUIReportSettings=[{k: deepcopy(v) for k, v in row.items() if k != 'ordinal'}
                                      for row in ui_rows]))


def _supported(reference, initialization_id):
    config, _hook, anchor, _policy = placement.configuration(reference)
    # Only the retained declared disabled mechanism is released for registration;
    # parser support for other inactive rows is not installation authority.
    if config['DownloadableUIReportSettings'] != DISABLED_UI or any(
            type(row['Active']) is not bool for row in config['DownloadableUIReportSettings']):
        raise ValueError('Exact retained disabled downloadable RRR setting required')
    if (anchor['kind'] != 'INITIALIZATION' or anchor['identity'] != initialization_id
            or anchor['output_digest'] is not None or anchor['catalogue']):
        raise ValueError('Registration requires its own explicit initial catalogue seed')
    # The qualified roster uses true native bits. Never lose an input scalar tag
    # by allowing an int through a BooleanField round trip.
    if any(type(row[field]) is not bool for row in config['RuntimeReports']
           for field in definitions.BIT_FIELDS):
        raise ValueError('Retained report bit representation differs')
    return config


def encode(reference, *, initialization_id, source_digest, certificate_id, certificate_digest):
    """Produce typed rows and bounded identity metadata, not an admission receipt."""
    identity(initialization_id); identity(certificate_id)
    sha(source_digest); sha(certificate_digest)
    config = _supported(reference, initialization_id)
    rows = [dict(ordinal=n, **{key: deepcopy(row[key]) for key in DEFINITION_FIELDS})
            for n, row in enumerate(config['RuntimeReports'])]
    seeds = [dict(ordinal=n, Id=row['Id'], LastGeneratedFileName=row['LastGeneratedFileName'])
             for n, row in enumerate(config['RuntimeReports'])]
    ui = [dict(ordinal=n, **row) for n, row in enumerate(config['DownloadableUIReportSettings'])]
    policy = {key: deepcopy(reference[key]) for key in POLICY_FIELDS}
    header = dict(schema=SCHEMA, initialization_id=initialization_id, source_digest=source_digest,
        certificate_id=certificate_id, certificate_digest=certificate_digest,
        configuration_digest=digest(config), definition_digest=definitions.definition_digest(config),
        seed_digest=digest(definitions.last_generated(config)), policy_digest=digest(policy),
        reference_digest=digest(reference))
    return dict(header=header, policy=policy, report_rows=rows, seed_rows=seeds, ui_rows=ui,
                registration_digest=digest(header))


def decode(value):
    """Independently reconstruct a persisted registration and verify every cut.

    Database ownership and live admission are deliberately outside this codec.
    A valid dictionary cannot authorize a capture or any configuration write.
    """
    if (type(value) is not dict or set(value) != {'header', 'policy', 'report_rows',
            'seed_rows', 'ui_rows', 'registration_digest'}
            or type(value['header']) is not dict or set(value['header']) != HEADER_FIELDS
            or value['header']['schema'] != SCHEMA
            or type(value['policy']) is not dict or set(value['policy']) != POLICY_FIELDS):
        raise ValueError('Complete typed report registration required')
    header = value['header']
    identity(header['initialization_id']); identity(header['certificate_id'])
    for key in HEADER_FIELDS - {'schema', 'initialization_id', 'certificate_id'}:
        sha(header[key])
    sha(value['registration_digest'])
    config = configuration_from_rows(value['report_rows'], value['seed_rows'], value['ui_rows'])
    reference = dict(schema=placement.REFERENCE, purpose='owned-placement-publication-test',
        configuration_json=_canonical(config), configuration_digest=digest(config), **value['policy'])
    _supported(reference, header['initialization_id'])
    expected = dict(configuration_digest=digest(config),
        definition_digest=definitions.definition_digest(config),
        seed_digest=digest(definitions.last_generated(config)),
        policy_digest=digest(value['policy']), reference_digest=digest(reference))
    if (any(header[key] != item for key, item in expected.items())
            or value['registration_digest'] != digest(header)):
        raise ValueError('Persisted report registration content/identity differs')
    return reference


def _stored(owner):
    """Read every typed row; never trust a cached copy of the input JSON."""
    header = {key: getattr(owner, key) for key in HEADER_FIELDS}
    header['initialization_id'] = str(header['initialization_id'])
    header['certificate_id'] = str(header['certificate_id'])
    reports = list(owner.report_rows.order_by('ordinal').values('ordinal', *sorted(DEFINITION_FIELDS)))
    from mta.runtime.report_definition_models import RegisteredRuntimeReportSeed
    seeds = [dict(ordinal=row['definition__ordinal'], Id=row['definition__Id'],
                  LastGeneratedFileName=row['LastGeneratedFileName']) for row in
        RegisteredRuntimeReportSeed.objects.filter(definition__registration=owner).order_by(
            'definition__ordinal').values('definition__ordinal', 'definition__Id', 'LastGeneratedFileName')]
    ui = list(owner.ui_rows.order_by('ordinal').values('ordinal', *sorted(UI_FIELDS)))
    value = dict(header=header, policy=owner.policy, report_rows=reports, seed_rows=seeds,
                 ui_rows=ui, registration_digest=owner.pk)
    decode(value)
    return value


def verify_guards(cursor):
    from importlib import import_module
    guards = import_module('mta.runtime.migrations.0234_report_definition_guards')
    cursor.execute("SELECT P.proname,P.prosrc,P.prosecdef,P.proconfig,L.lanname "
        "FROM pg_proc P JOIN pg_namespace N ON N.oid=P.pronamespace "
        "JOIN pg_language L ON L.oid=P.prolang WHERE N.nspname='mta' AND P.pronargs=0 "
        "AND P.proname IN ('guard_report_definition','check_report_definition_complete') ORDER BY P.proname")
    if cursor.fetchall() != [
            ('check_report_definition_complete', guards.COMPLETE, False, ['search_path=pg_catalog, mta'], 'plpgsql'),
            ('guard_report_definition', guards.GUARD, False, ['search_path=pg_catalog, mta'], 'plpgsql')]:
        raise ValueError('Exact report registration guards required')
    cursor.execute("SELECT C.relname,T.tgname,T.tgtype,T.tgenabled,T.tgdeferrable,T.tginitdeferred,"
        "P.proname,T.tgnargs,T.tgqual::text FROM pg_trigger T JOIN pg_class C ON C.oid=T.tgrelid "
        "JOIN pg_namespace N ON N.oid=C.relnamespace JOIN pg_proc P ON P.oid=T.tgfoid "
        "JOIN pg_namespace F ON F.oid=P.pronamespace WHERE N.nspname='mta' AND F.nspname='mta' "
        "AND C.relname=ANY(%s) AND T.tgname LIKE 'report_definition_%%' ORDER BY C.relname,T.tgname",
        [list(guards.TABLES)])
    expected = [(table, name, kind, 'O', False, False, 'guard_report_definition', 0, None)
        for table in guards.TABLES for name, kind in
        (('report_definition_immutable', 31), ('report_definition_no_truncate', 34))]
    expected.append((guards.TABLES[0], 'report_definition_complete', 5, 'O', True, True,
                     'check_report_definition_complete', 0, None))
    if cursor.fetchall() != sorted(expected):
        raise ValueError('Report registration trigger coverage differs')


def register(reference, *, initialization_id, source_digest, certificate_digest):
    """Atomically register future definitions under existing native authority.

    Neither existing requests nor live/generated settings are updated. An exact
    retry reconstructs the original typed registration without inserting again.
    """
    from django.db import connection, transaction
    from release.native_identity import require_current
    from mta.runtime import ingestion_admission
    from mta.runtime.models import ProductionInitialization, MdmSource, InitializationCertification, IngestionRevisionState
    from mta.runtime.report_definition_models import (ReportDefinitionRegistration,
        RegisteredRuntimeReport, RegisteredRuntimeReportSeed, RegisteredDownloadableUiSetting)
    identity(initialization_id); sha(source_digest); sha(certificate_digest)
    _supported(reference, initialization_id)
    if connection.in_atomic_block:
        raise ValueError('Report registration owns its native transaction')
    release = require_current()
    initial = ProductionInitialization.objects.get(pk=initialization_id)
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        MdmSource.objects.select_for_update().get(pk=initial.source_id)
        owner = ProductionInitialization.objects.select_for_update().get(pk=initialization_id)
        IngestionRevisionState.objects.select_for_update().get(initialization=owner)
        before = ingestion_admission._admit(cursor, initialization_id, release)
        verify_guards(cursor)
        cursor.execute("SELECT N.owner_oid=(SELECT oid FROM pg_roles WHERE rolname=current_user) "
            "FROM fresh_control.owned_namespace N WHERE N.singleton AND N.database_name=current_database()")
        if cursor.fetchone() != (True,):
            raise ValueError('Report registration requires the registered database owner')
        if before.source_digest != source_digest or before.certification_digest != certificate_digest:
            raise ValueError('Explicit current source/certificate differs')
        cert = InitializationCertification.objects.get(initialization=owner, status='CERTIFIED',
                                                        receipt_digest=certificate_digest)
        value = encode(reference, initialization_id=initialization_id, source_digest=source_digest,
                       certificate_id=str(cert.pk), certificate_digest=certificate_digest)
        existing = ReportDefinitionRegistration.objects.filter(pk=value['registration_digest']).first()
        if existing is not None:
            if _stored(existing) != value:
                raise ValueError('Existing report registration differs')
            return existing
        cursor.execute("SELECT set_config('vectorflow.report_definition_registration',%s,true)",
                       [value['registration_digest']])
        installed = ReportDefinitionRegistration.objects.create(id=value['registration_digest'],
            **value['header'], policy=value['policy'])
        rows = RegisteredRuntimeReport.objects.bulk_create([
            RegisteredRuntimeReport(registration=installed, **row) for row in value['report_rows']])
        RegisteredRuntimeReportSeed.objects.bulk_create([
            RegisteredRuntimeReportSeed(definition=row, LastGeneratedFileName=seed['LastGeneratedFileName'])
            for row, seed in zip(rows, value['seed_rows'])])
        RegisteredDownloadableUiSetting.objects.bulk_create([
            RegisteredDownloadableUiSetting(registration=installed, **row) for row in value['ui_rows']])
        if _stored(installed) != value:
            raise ValueError('Independent typed report registration readback differs')
        cursor.execute('SET CONSTRAINTS report_definition_complete IMMEDIATE')
        if ingestion_admission._admit(cursor, initialization_id, release) != before:
            raise ValueError('Future report registration changed the accepted state')
        return installed


def read(registration_digest, *, initialization_id, source_digest):
    """Read-only admission plus typed readback; no configuration repair on read."""
    from django.db import connection, transaction
    from release.native_identity import require_current
    from mta.runtime.ingestion_admission import _admit
    from mta.runtime.report_definition_models import ReportDefinitionRegistration
    sha(registration_digest); identity(initialization_id); sha(source_digest)
    if connection.in_atomic_block:
        raise ValueError('Report registration read owns its admitted snapshot')
    release = require_current()
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        # This read supplies a future capture, not a serving selection. Preserve
        # pending master/configuration changes through the existing preparation
        # admission contract; the locked capture revalidates this actual cut.
        admitted = _admit(cursor, initialization_id, release, pending=True)
        if admitted.source_digest != source_digest:
            raise ValueError('Report registration source differs from admitted installation')
        verify_guards(cursor)
        owner = ReportDefinitionRegistration.objects.get(pk=registration_digest,
            initialization_id=initialization_id, source_digest=source_digest,
            certificate_digest=admitted.certification_digest)
        return _stored(owner)
