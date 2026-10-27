"""Versioned outer capture attachment for registered report definitions.

The executable scope_request remains placement v1. This separate bounded
component enters the same input digest before capture; old inputs remain old.
The capture owner must verify persisted custody in its admitted transaction.
Pure validation authenticates content, never database authority.
"""
from copy import deepcopy
import inspect

from mta.runtime import report_definition_registration as registrations
from mta.runtime import runtime_report_request as placement
from mta.runtime.ingestion_context import identity, sha
from mta.serialization import digest


SCHEMA = 'fresh-registered-report-placement-request-v1'
BINDING_FIELDS = registrations.HEADER_FIELDS | {'registration_digest'}
FIELDS = frozenset({'schema', 'scope_request_digest', 'registration',
                    'attachment_recipe', 'attachment_digest'})


def recipe_digest(*, production=False):
    # Old placement sources and factory remain untouched. This additional
    # identity covers typed reconstruction and the future attachment contract.
    observed=digest(dict(schema=SCHEMA, placement=placement.recipe_digest(production=production), modules={
        module.__name__: inspect.getsource(module) for module in
        (inspect.getmodule(recipe_digest), registrations)}))
    if production:
        return observed
    from mta.runtime.retained_registered_execution_compatibility import attachment_recipe
    return attachment_recipe(observed)


def _binding(stored):
    registrations.decode(stored)
    return dict(stored['header'], registration_digest=stored['registration_digest'])


def _reconstruct(reference, binding):
    if type(binding) is not dict or set(binding) != BINDING_FIELDS:
        raise ValueError('Exact captured report registration binding required')
    stored = registrations.encode(reference,
        initialization_id=binding['initialization_id'], source_digest=binding['source_digest'],
        certificate_id=binding['certificate_id'], certificate_digest=binding['certificate_digest'])
    if _binding(stored) != binding:
        raise ValueError('Captured report registration content or identity differs')
    return stored


def _attachment(scope_request, stored):
    if registrations.decode(stored) != scope_request['runtime_reports']:
        raise ValueError('Executable request differs from registered definitions')
    from mta.runtime.production_scope_policy import SCHEMA as PRODUCTION_POLICY
    production = scope_request['dispositions']['schema'] == PRODUCTION_POLICY
    value = dict(schema=SCHEMA, scope_request_digest=digest(scope_request),
                 registration=_binding(stored), attachment_recipe=recipe_digest(production=production))
    value['attachment_digest'] = digest(value)
    return value


def request(scope, command_key, *, registration_digest, initialization_id, source_digest):
    """Factory reads actual admitted typed rows; no caller-supplied roster."""
    stored = registrations.read(registration_digest, initialization_id=initialization_id,
                                source_digest=source_digest)
    inner = placement.request(scope, command_key, runtime_reports=registrations.decode(stored))
    return dict(scope_request=inner, report_registration_request=_attachment(inner, stored))


def request_for_execution(raw, expected_sha256, *, scope, command_key, registration_digest, arguments):
    """Resolve frozen ownership before consulting live registration admission."""
    from mta.runtime.production_daily import decode
    from mta.runtime.models import CalculationRun
    from mta.runtime.input_reader import read_input
    sha(registration_digest)
    day = decode(raw, expected_sha256)['day']['business_date']
    owners = list(CalculationRun.objects.filter(kind='DAILY_CHAIN', business_date=day,
        execution_revision=arguments['execution_revision'],
        mdm_input_capture__source__digest=arguments['source_digest'])[:2])
    if len(owners) > 1:
        raise ValueError('Registered command has ambiguous captured owners')
    owner = owners[0] if owners else None
    if owner is None and arguments.get('retry_capture_id') is not None:
        owner = CalculationRun.objects.get(pk=arguments['retry_capture_id'])
    if owner is None:
        return request(scope, command_key, registration_digest=registration_digest,
            initialization_id=str(arguments['initialization_id']), source_digest=arguments['source_digest'])
    outer = read_captured(owner)
    if outer is None:
        raise ValueError('A registration command cannot adopt an inner-only capture')
    inner = read_input(owner, components=('scope_request',))['scope_request']
    validate_request(outer, inner, run=owner)
    binding = outer['registration']
    if (binding['registration_digest'] != registration_digest
            or binding['initialization_id'] != str(arguments['initialization_id'])
            or binding['source_digest'] != arguments['source_digest']
            or inner['scope'] != scope or inner['command_key'] != command_key):
        raise ValueError('Registered command differs from original captured owner')
    # The existing repeated/frozen-retry path still checks date, daily bytes,
    # predecessor, root, original capture status and execution arguments.
    return dict(scope_request=inner, report_registration_request=outer)


def _expected(value, scope_request):
    if type(value) is not dict or set(value) != FIELDS or value['schema'] != SCHEMA:
        raise ValueError('Versioned registered placement request required')
    stored = _reconstruct(scope_request['runtime_reports'], value['registration'])
    return _attachment(scope_request, stored)


def validate_request(value, scope_request, *, run=None):
    placement.validate_request(scope_request,run=run)
    if value != _expected(value, scope_request):
        raise ValueError('Registered placement attachment or execution recipe differs')
    return deepcopy(value)


def validate_read_request(value, scope_request):
    """Preserve original execution identity in an admitted compatible reader."""
    placement.validate_read_request(scope_request)
    if value != _expected(value, scope_request):
        raise ValueError('Registered placement read attachment or configuration differs')
    return deepcopy(value)


def attach_input(raw, value):
    """Add the bounded component before hashing; absence is byte-preserving."""
    if value is None:
        return raw
    validate_request(value, raw.get('scope_request'))
    binding = raw.get('initialization_binding')
    registered = value['registration']
    if (type(binding) is not dict or binding.get('id') != registered['initialization_id']
            or binding.get('source_digest') != registered['source_digest']):
        raise ValueError('Registration attachment belongs to another captured initialization')
    return dict(raw, report_registration_request=deepcopy(value))


def check_repeated(run, scope_request, expected):
    """A new registration command cannot adopt an existing inner-only run."""
    from mta.runtime.input_reader import read_input
    captured = read_input(run, components=('scope_request', 'report_registration_request'))
    if (captured.get('scope_request') != scope_request
            or captured.get('report_registration_request') != expected):
        raise ValueError('Repeated registration attachment differs from frozen capture')
    if expected is not None:
        validate_request(expected, scope_request,run=run)


def read_captured(run):
    """Decode original attachment and typed custody without adopting old runs.

    Existing caller admission/read-integrity remains required. A certificate
    change must not substitute today's registration for this captured one.
    """
    from mta.runtime.input_reader import read_input
    from mta.runtime.report_definition_models import ReportDefinitionRegistration
    raw = read_input(run, components=('scope_request', 'report_registration_request', 'initialization_binding'))
    value = raw.get('report_registration_request')
    if value is None:
        return None
    validate_read_request(value, raw.get('scope_request'))
    binding = value['registration']; initial = raw.get('initialization_binding', {})
    if (initial.get('id') != binding['initialization_id']
            or initial.get('source_digest') != binding['source_digest']):
        raise ValueError('Captured registration installation differs')
    owner = ReportDefinitionRegistration.objects.get(pk=binding['registration_digest'],
        initialization_id=binding['initialization_id'], source_digest=binding['source_digest'],
        certificate_id=binding['certificate_id'], certificate_digest=binding['certificate_digest'])
    stored = registrations._stored(owner)
    if _attachment(raw['scope_request'], stored) != value:
        raise ValueError('Captured registration differs from immutable typed custody')
    return deepcopy(value)


def verify_capture(value, scope_request, *, initialization_id, source_digest, certificate_digest):
    """Recheck typed custody inside the capture owner's admitted transaction.

    The owner supplies its actual admission cut and retains its source lock.
    The earlier factory read is not sufficient: never accept a self-consistent
    dictionary without an installed immutable registration at this exact cut.
    """
    from django.db import connection
    from mta.runtime.report_definition_models import ReportDefinitionRegistration
    identity(initialization_id); sha(source_digest); sha(certificate_digest)
    validate_request(value, scope_request)
    if not connection.in_atomic_block:
        raise ValueError('Registered report capture requires its admitted transaction')
    binding = value['registration']
    if (binding['initialization_id'] != initialization_id
            or binding['source_digest'] != source_digest
            or binding['certificate_digest'] != certificate_digest):
        raise ValueError('Registered report capture belongs to another admission cut')
    with connection.cursor() as cursor:
        registrations.verify_guards(cursor)
        owner = ReportDefinitionRegistration.objects.get(pk=binding['registration_digest'],
            initialization_id=initialization_id, source_digest=source_digest,
            certificate_id=binding['certificate_id'], certificate_digest=certificate_digest)
        stored = registrations._stored(owner)
    if (_binding(stored) != binding or registrations.decode(stored) != scope_request['runtime_reports']):
        raise ValueError('Registered report capture differs from persisted typed custody')
    return deepcopy(value)
