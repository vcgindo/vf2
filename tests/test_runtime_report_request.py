"""Standalone captured metadata contract; no dispatch or authority claim."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from mta.application import runtime_report_configuration as definitions
from mta.application.runtime_report_hooks import configuration as hook_configuration
from mta.runtime import runtime_report_request as request
from mta.runtime import runtime_report_catalogue as catalogue
from mta.serialization import digest


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False)


def fixture():
    rows=json.loads((Path(__file__).parent/'fixtures/runtime_reports_retained_20261019.json').read_bytes())
    config=definitions.configuration(dict(schema=definitions.SCHEMA,RuntimeReports=rows,
        DownloadableUIReportSettings=[dict(ReportName='RRR',Active=False,
            GenerationScope='PostBPR',DestFolder='%ReportsDownloadLoc%')]))
    authority='a'*64
    hook=hook_configuration(dict(schema='fresh-runtime-report-hook-configuration-v1',
        site_code='SUPPLIED-INSTANCE',placement='PostBPR',mode='declared-no-op',
        authority='Local test authority witness',source_sha256=authority))
    policy=request.disposition(dict(schema=request.DISPOSITION,purpose='owned-scoped-test',
        site_code='SUPPLIED-INSTANCE',hooks={name:'explicit-test-no-op' for name in request.HOOKS},
        input_download='enabled-five-file-four-table-archive',authority='Local test disposition witness'))
    anchor=catalogue.validate_anchor(dict(schema=catalogue.ANCHOR_SCHEMA,kind='INITIALIZATION',
        identity='10000000-0000-4000-8000-000000000001',output_digest=None,
        configuration_digest=digest(config),definition_digest=definitions.definition_digest(config),
        catalogue={},last_generated=definitions.last_generated(config),
        evidence=dict(approval=authority)),report_configuration=config)
    return dict(schema=request.REFERENCE,purpose='owned-placement-publication-test',
        configuration_json=canonical(config),configuration_digest=digest(config),
        hook_json=canonical(hook),disposition_json=canonical(policy),
        catalogue_anchor_json=canonical(anchor),authority_sha256=authority)


def replace_config(value, config, *, rebind_anchor=True):
    value['configuration_json']=canonical(config)
    value['configuration_digest']=digest(config)
    if rebind_anchor:
        anchor=json.loads(value['catalogue_anchor_json'])
        anchor.update(configuration_digest=digest(config),
            definition_digest=definitions.definition_digest(config))
        value['catalogue_anchor_json']=canonical(anchor)
    return value


class RuntimeReportRequestTests(unittest.TestCase):
    def test_new_factory_pins_release_and_cannot_enter_old_request_factory(self):
        from mta.runtime import production_scope,production_upto_dbm
        with patch.dict('os.environ',{'VF_RUNTIME_REPORT_PUBLISH':'1'}), \
                patch('release.native_identity.require_current',return_value={'local-test':'release-a'}):
            reference=fixture()
            for scope in request.SCOPES:
                value=request.request(scope,'local-test-command',runtime_reports=reference)
                self.assertEqual(request.validate_request(value),value)
                changed=deepcopy(value);changed['scope']='PostDBM'
                with self.assertRaises(ValueError):request.validate_request(changed)
                changed=deepcopy(value);changed['publication_recipe']='b'*64
                with self.assertRaises(ValueError):request.validate_request(changed)
                self.assertEqual(production_scope.validate_request(value),value)
            with self.assertRaises(ValueError):production_scope.request('local-test',runtime_reports=reference)
            with self.assertRaises(ValueError):production_upto_dbm.request('local-test',runtime_reports=reference,
                dispositions=json.loads(reference['disposition_json']))
            with patch('release.native_identity.require_current',return_value={'local-test':'release-b'}):
                with self.assertRaises(ValueError):request.validate_request(value)
                self.assertEqual(request.validate_read_request(value),value)
                changed=deepcopy(value);changed['publication_recipe']='b'*64
                with self.assertRaises(ValueError):request.validate_read_request(changed)
                changed=deepcopy(value);changed['compatibility_digest']='not-a-digest'
                with self.assertRaises(ValueError):request.validate_read_request(changed)

    def test_exact_eight_reports_and_disabled_independent_rrr_validate(self):
        value=fixture(); before=deepcopy(value)
        config,hook,anchor,policy=request.configuration(value)
        self.assertEqual([row['Id'] for row in config['RuntimeReports']],[2,3,4,5,6,7,8,10])
        self.assertEqual(config['DownloadableUIReportSettings'],[dict(ReportName='RRR',Active=False,
            GenerationScope='PostBPR',DestFolder='%ReportsDownloadLoc%')])
        self.assertEqual(anchor['last_generated'],definitions.last_generated(config))
        self.assertEqual(value,before)
        checked=request.validate_reference(value);checked['authority_sha256']='b'*64
        self.assertEqual(value,before)
        self.assertEqual(hook['site_code'],policy['site_code'])
        for placement in request.HOOKS:
            result=request.hook_for(value,placement)
            self.assertEqual(result['placement'],placement)
            self.assertEqual(result['mode'],'explicit-test-no-op')
            self.assertEqual(result['authority_sha256'],value['authority_sha256'])
            self.assertEqual(result['disposition_digest'],digest(policy))
        with self.assertRaises(ValueError):request.hook_for(value,'arbitrary-script')

    def test_enabled_independent_rrr_cannot_hide_in_rehashed_configuration(self):
        value=fixture();config=json.loads(value['configuration_json'])
        config['DownloadableUIReportSettings'][0]['Active']=True
        replace_config(value,config)
        with self.assertRaisesRegex(ValueError,'Enabled downloadable'):
            request.configuration(value)

    def test_changed_query_fields_roster_and_order_deny_even_when_rehashed(self):
        for mutation in ('query','omit','extra','order','site','inactive'):
            value=fixture();config=json.loads(value['configuration_json'])
            rows=config['RuntimeReports']
            if mutation=='query':rows[0]['Query']+=' '
            elif mutation=='omit':rows.pop()
            elif mutation=='extra':rows.append(dict(rows[-1],Id=11))
            elif mutation=='order':rows.reverse()
            elif mutation=='site':rows[3]['FileName']='OtherSite'
            else:rows[0]['Active']=False
            replace_config(value,config)
            with self.subTest(mutation=mutation),self.assertRaisesRegex(ValueError,'eight-report'):
                request.configuration(value)

    def test_anchor_seed_and_configuration_must_agree(self):
        for mutation in ('seed','definition','configuration','catalogue','identity','extra'):
            value=fixture();anchor=json.loads(value['catalogue_anchor_json'])
            if mutation=='seed':anchor['last_generated'][0]['LastGeneratedFileName']='wrong'
            elif mutation=='definition':anchor['definition_digest']='b'*64
            elif mutation=='configuration':anchor['configuration_digest']='b'*64
            elif mutation=='catalogue':anchor['catalogue']=None
            elif mutation=='identity':anchor['identity']='not-a-uuid'
            else:anchor['extra']=1
            value['catalogue_anchor_json']=canonical(anchor)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):request.configuration(value)

    def test_authority_and_explicit_hook_dispositions_deny_drift(self):
        for mutation in ('authority','hook-authority','site','hook-mode','hook-stage',
                         'missing-disposition','disposition-stage','download','empty-authority'):
            value=fixture();hook=json.loads(value['hook_json']);policy=json.loads(value['disposition_json'])
            if mutation=='authority':value['authority_sha256']='b'*64
            elif mutation=='hook-authority':hook['source_sha256']='b'*64
            elif mutation=='site':hook['site_code']='OTHER'
            elif mutation=='hook-mode':hook['mode']='execute-site-script'
            elif mutation=='hook-stage':hook['placement']='PostBTR'
            elif mutation=='missing-disposition':del policy['hooks']['PostBTR']
            elif mutation=='disposition-stage':policy['hooks']['PostBTR']='execute'
            elif mutation=='download':policy['input_download']='absent'
            else:policy['authority']=' '
            value.update(hook_json=canonical(hook),disposition_json=canonical(policy))
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):request.configuration(value)

    def test_coordinated_changed_initial_filename_seed_does_not_replace_retained_seed(self):
        value=fixture();config=json.loads(value['configuration_json'])
        config['RuntimeReports'][0]['LastGeneratedFileName']='invented-prior-output'
        replace_config(value,config)
        anchor=json.loads(value['catalogue_anchor_json'])
        anchor['last_generated']=definitions.last_generated(config)
        value['catalogue_anchor_json']=canonical(anchor)
        with self.assertRaises(ValueError):request.configuration(value)

    def test_noncanonical_duplicate_extra_and_invalid_metadata_deny(self):
        for key in ('configuration_json','hook_json','disposition_json','catalogue_anchor_json'):
            for transform in (lambda raw:raw+' ', lambda raw:json.dumps(json.loads(raw),indent=2),
                              lambda raw:raw[:-1]+',"duplicate":1,"duplicate":2}',
                              lambda raw:'null',lambda raw:'{"value":NaN}'):
                value=fixture();value[key]=transform(value[key])
                with self.subTest(key=key,raw=value[key][:30]),self.assertRaises(ValueError):request.configuration(value)
        for change in (dict(extra=True),dict(authority_sha256=True),dict(purpose='production'),
                       dict(configuration_digest='b'*64),dict(schema=request.SCHEMA)):
            with self.subTest(change=change),self.assertRaises(ValueError):request.configuration(dict(fixture(),**change))


if __name__=='__main__':unittest.main()
