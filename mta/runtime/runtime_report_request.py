"""New captured contract for the released eight-report owned test placement.

This does not adopt old requests, activate arbitrary site hooks, or infer RRR
configuration. Its canonical metadata is captured with the existing day input;
the execution owner still authenticates installation, source and catalogue.
"""
from copy import deepcopy
import inspect

from mta.serialization import digest
from mta.application import runtime_report_configuration as definitions
from mta.application.runtime_report_hooks import configuration as post_bpr_hook
from mta.runtime.runtime_report_catalogue import validate_anchor

REFERENCE='fresh-owned-report-placement-reference-v1'
SCHEMA='fresh-native-report-placement-request-v1'
DISPOSITION='fresh-owned-report-placement-disposition-v1'
DEFINITIONS_DIGEST='f71e65e4d43e7f076a9e15c452ec061e156fb96dc83203ffd7bf7af415cdf6bd'
FILENAME_SEED_DIGEST='4afa2e17e1f84e4212d5578fe306036e4a65a00847c85d9cebb13f72988a1f3f'
HOOKS=('PostBPR','PreDBM','PostDBM','PostBTR','SiteFinal')
SCOPES=('Full','UptoBPR','UptoDBM')


def disposition(value):
    from mta.runtime import production_scope_policy as production
    if isinstance(value, dict) and value.get('schema') == production.SCHEMA:
        return production.disposition(value)
    if (type(value) is not dict or set(value)!={
            'schema','purpose','site_code','hooks','input_download','authority'}
            or value['schema']!=DISPOSITION or value['purpose']!='owned-scoped-test'
            or value['site_code']!='SUPPLIED-INSTANCE'
            or value['hooks']!={name:'explicit-test-no-op' for name in HOOKS}
            or value['input_download']!='enabled-five-file-four-table-archive'
            or type(value['authority']) is not str
            or not 1<=len(value['authority'])<=1000 or not value['authority'].strip()
            or '\0' in value['authority']):
        raise ValueError('Explicit applicable placement test hooks and InputData disposition required')
    return deepcopy(value)


def configuration(value):
    from mta.runtime.scope_runtime_reports import _metadata
    from mta.runtime.ingestion_context import sha
    if (type(value) is not dict or set(value)!={'schema','purpose','configuration_json',
            'configuration_digest','hook_json','disposition_json','catalogue_anchor_json','authority_sha256'}
            or value['schema']!=REFERENCE or value['purpose'] not in (
                'owned-placement-publication-test', 'production-generic-placement')):
        raise ValueError('Explicit new placement publication reference required')
    sha(value['authority_sha256'])
    config=definitions.configuration(_metadata(value['configuration_json']))
    rows=config['RuntimeReports']
    if (digest(config)!=value['configuration_digest']
            or digest([{key:item for key,item in row.items() if key!='LastGeneratedFileName'}
                       for row in rows])!=DEFINITIONS_DIGEST):
        raise ValueError('Exact retained eight-report definitions required')
    # The user explicitly keeps the independent mechanism disabled at this
    # retained boundary. An enabled RRR row must not quietly become a no-op.
    if any(row['Active'] for row in config['DownloadableUIReportSettings']):
        raise ValueError('Enabled downloadable UI reports remain unqualified for this request')
    hook=post_bpr_hook(_metadata(value['hook_json']))
    policy=disposition(_metadata(value['disposition_json']))
    from mta.runtime import production_scope_policy as production
    if policy['schema'] == production.SCHEMA:
        production.report_configuration(config)
        if (value['purpose'] != 'production-generic-placement'
                or hook['schema'] != production.HOOK_SCHEMA):
            raise ValueError('Production generic reference requires its explicit hook policy')
    elif (value['purpose'] != 'owned-placement-publication-test'
            or hook['schema'] != 'fresh-runtime-report-hook-configuration-v1'):
        raise ValueError('Retained test reference cannot adopt production generic policy')
    if (hook['site_code']!=policy['site_code']
            or hook['source_sha256']!=value['authority_sha256']):
        raise ValueError('Captured placement hook authority differs')
    anchor=validate_anchor(_metadata(value['catalogue_anchor_json']),report_configuration=config)
    if (digest(definitions.last_generated(config))!=FILENAME_SEED_DIGEST
            or anchor['last_generated']!=definitions.last_generated(config)
            or anchor['configuration_digest']!=digest(config)):
        raise ValueError('Initial placement filename seed differs')
    return config,hook,anchor,policy


def validate_reference(value):
    configuration(value)
    return deepcopy(value)


def hook_for(value,placement):
    """Return only a captured qualified disposition, never execute a hook."""
    config,hook,anchor,policy=configuration(value)
    if placement not in HOOKS:
        raise ValueError('Unknown placement hook')
    return dict(placement=placement,site_code=policy['site_code'],
        mode=policy['hooks'][placement],authority_sha256=value['authority_sha256'],
        disposition_digest=digest(policy))


def recipe_digest(*, production=False):
    from mta.application import runtime_report_bpr_inputs,runtime_report_postbtr_inputs
    from mta.application.runtime_report_btr_stage import recipe_digest as btr_recipe
    from mta.runtime import runtime_report_stage_storage,runtime_report_stage_work,runtime_report_placement_publication,runtime_report_execution,placement_master_publication
    observed=digest(dict(schema=SCHEMA,btr=btr_recipe(),modules={
        module.__name__:inspect.getsource(module) for module in (
            inspect.getmodule(recipe_digest),runtime_report_bpr_inputs,runtime_report_postbtr_inputs,
            runtime_report_stage_storage,runtime_report_stage_work,runtime_report_placement_publication,runtime_report_execution,placement_master_publication)}))
    if production:
        from mta.runtime import production_scope_policy
        # This is the actual producer recipe of a NEW request, not an alias
        # requiring every unrelated native file to equal a migration trial.
        return digest(dict(recipe=observed,
            policy=inspect.getsource(production_scope_policy)))
    from mta.runtime.retained_registered_execution_compatibility import publication_recipe
    return publication_recipe(observed)


def _request_fields(scope,command_key,runtime_reports):
    if (scope not in SCOPES or type(command_key) is not str or not 1<=len(command_key)<=120
            or not command_key.strip() or '\0' in command_key):
        raise ValueError('Explicit placement scope and bounded command key required')
    reference=validate_reference(runtime_reports)
    _config,hook,_anchor,policy=configuration(reference)
    return dict(schema=SCHEMA,scope=scope,command_key=command_key,runtime_reports=reference,
        report_hooks=hook,dispositions=policy)


def request(scope,command_key,*,runtime_reports):
    """Versioned capture factory; old factories must not adopt this reference."""
    from release.native_identity import require_current
    from mta.runtime.phase_state import recipe_digest as phase_recipe
    from mta.runtime.production_scope_policy import SCHEMA as PRODUCTION_POLICY
    value=_request_fields(scope,command_key,runtime_reports)
    value['publication_recipe']=recipe_digest(production=value['dispositions']['schema'] == PRODUCTION_POLICY)
    value['compatibility_digest']=digest(dict(request=value,release=require_current(),phase_recipe=phase_recipe()))
    return value


def validate_request(value, *, run=None):
    if (type(value) is not dict or set(value)!={'schema','scope','command_key','runtime_reports',
            'report_hooks','dispositions','publication_recipe','compatibility_digest'}):
        raise ValueError('Captured placement request or implementation differs')
    expected=request(value.get('scope'),value.get('command_key'),runtime_reports=value.get('runtime_reports'))
    if value!=expected:
        if run is None:
            raise ValueError('Captured placement request or implementation differs')
        from mta.runtime.retained_registered_execution_compatibility import validate_retained
        validate_retained(run,value,expected)
    return deepcopy(value)


def validate_read_request(value):
    """Decode supported metadata; callers still authenticate captured custody.

    Original producer digests are provenance, never authority to execute. Typed
    registration, run/phase receipts and input/file pins are verified by the
    consumers. Every mutation continues through strict validate_request().
    """
    from mta.runtime.ingestion_context import sha
    from mta.runtime.production_scope_policy import SCHEMA as PRODUCTION_POLICY
    fields={'schema','scope','command_key','runtime_reports','report_hooks',
        'dispositions','publication_recipe','compatibility_digest'}
    if type(value) is not dict or set(value)!=fields or value['schema']!=SCHEMA:
        raise ValueError('Captured placement request required')
    expected=_request_fields(value['scope'],value['command_key'],value['runtime_reports'])
    sha(value['compatibility_digest']);sha(value['publication_recipe'])
    if expected['dispositions']['schema']!=PRODUCTION_POLICY:
        # Exact finite historical TEST readers retain their old source checks.
        expected=request(value['scope'],value['command_key'],runtime_reports=value['runtime_reports'])
    if any(value[key]!=item for key,item in expected.items() if key!='compatibility_digest'):
        raise ValueError('Captured placement read recipe or configuration differs')
    return deepcopy(value)


def validate_day(profile,day,value):
    """Use the existing history/publication policy; never infer missing fields."""
    validate_request(value)
    from mta.runtime import production_scope_policy as production
    if value['dispositions']['schema'] == production.SCHEMA:
        production.configuration(profile, value['dispositions'])
    from mta.runtime.production_upto_dbm import configuration as validate_production
    validate_production(profile,day,value)
