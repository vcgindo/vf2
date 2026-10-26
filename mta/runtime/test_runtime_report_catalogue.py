"""Pure authority/event tests; these do not certify files or registration."""
from copy import deepcopy
from unittest import TestCase

from mta.application.runtime_report_configuration import SCHEMA, definition_digest, last_generated
from mta.application.runtime_report_projection import describe
from mta.runtime import runtime_report_catalogue as catalogue
from mta.runtime import runtime_report_candidates as candidates
from mta.serialization import digest
from tests.test_runtime_report_files import row

IDENTITY = '11111111-1111-4111-8111-111111111111'
PRIOR = '22222222-2222-4222-8222-222222222222'


def file(path, marker='a'):
    return dict(relative_path=path, sha256=marker*64, size_bytes=31,
        members=([dict(ordinal=0, name=path.split('/')[-1][:-4]+'.csv',
                       sha256='c'*64, size_bytes=7)] if path.endswith('.zip') else []))


def rehash(value):
    value['digest'] = digest({key: item for key, item in value.items() if key != 'digest'})
    return value


def fixture():
    definitions = [dict(row(10), LastGeneratedFileName='OldTotal'),
                   dict(row(7), LastGeneratedFileName='OldSpike')]
    config = dict(schema=SCHEMA, RuntimeReports=definitions, DownloadableUIReportSettings=[])
    provenance = {r['Id']: dict(query_sha256=describe(r)['query_sha256'],
                              phase_digest='d'*64, source_digest='e'*64) for r in definitions}
    variables = dict(TotalReqReport='Total', ReportsDownloadLoc='download')
    reports = []
    for identity, name, removes, extension in (
            (7, 'Spiker_Order_Dump', ['output/OldSpike.csv', 'output/Spiker_Order_Dump.csv',
                'output/OldSpike.zip', 'output/Spiker_Order_Dump.zip',
                'download/OldSpike.zip', 'download/Spiker_Order_Dump.zip'], 'zip'),
            (10, 'Total', ['output/OldTotal.csv', 'output/Total.csv',
                          'download/OldTotal.csv', 'download/Total.csv'], 'csv')):
        definition = next(r for r in definitions if r['Id'] == identity)
        reports.append(dict(report_id=identity,
            definition_digest=digest({k: v for k, v in definition.items() if k != 'LastGeneratedFileName'}),
            source=deepcopy(provenance[identity]), last_generated_file_name=name,
            remove=removes, write=[file(folder+'/'+name+'.'+extension) for folder in ('output', 'download')]))
    value = dict(schema=candidates.SCHEMA, candidate_id=IDENTITY, placement='PostBPR',
        configuration_digest=digest(config), definition_digest=definition_digest(config),
        variables_digest=digest(variables), reports=reports,
        last_generated_before=last_generated(config),
        last_generated_after=[dict(Id=10, LastGeneratedFileName='Total'),
                              dict(Id=7, LastGeneratedFileName='Spiker_Order_Dump')],
        files={f['relative_path']: deepcopy(f) for r in reports for f in r['write']})
    args = dict(report_configuration=config, placement='PostBPR', variables=variables,
        last_generated=last_generated(config), provenance=provenance, previous_catalogue={})
    return rehash(value), args


class RuntimeReportCatalogueTests(TestCase):
    def test_native_id_order_cleanup_names_and_unchanged_prior_custody(self):
        candidate, args = fixture()
        prior = {path: dict(candidate_id=PRIOR, file=file(path, 'b')) for path in
                 ('output/OldTotal.csv', 'download/OldTotal.csv', 'download/keep.csv')}
        args['previous_catalogue'] = prior
        before = deepcopy((candidate, args))
        result = catalogue.validate_candidate(candidate=candidate, **args)
        self.assertEqual([r['report_id'] for r in result['events']], [7, 10])
        self.assertEqual(result['events'][0]['remove'], candidate['reports'][0]['remove'])
        self.assertEqual(result['last_generated'], candidate['last_generated_after'])
        self.assertEqual(result['catalogue']['download/keep.csv'], prior['download/keep.csv'])
        self.assertNotIn('download/OldTotal.csv', result['catalogue'])
        self.assertEqual(result['catalogue']['download/Total.csv']['candidate_id'], IDENTITY)
        self.assertEqual((candidate, args), before)

    def test_self_consistent_rehash_does_not_authorize_wrong_metadata(self):
        for mutation in ('remove', 'order', 'source', 'definition', 'before', 'after',
                         'name', 'layout', 'variables', 'config', 'roster', 'file_manifest'):
            value, args = fixture()
            if mutation == 'remove': value['reports'][0]['remove'] = []
            elif mutation == 'order': value['reports'].reverse()
            elif mutation == 'source': value['reports'][0]['source']['source_digest'] = 'f'*64
            elif mutation == 'definition': value['reports'][0]['definition_digest'] = 'f'*64
            elif mutation == 'before': value['last_generated_before'][0]['LastGeneratedFileName'] = 'Wrong'
            elif mutation == 'after': value['last_generated_after'][0]['LastGeneratedFileName'] = 'Wrong'
            elif mutation == 'name': value['reports'][0]['last_generated_file_name'] = 'Wrong'
            elif mutation == 'layout':
                value['reports'][0]['write'][0]['relative_path'] = 'download/wrong.zip'
                value['files'] = {f['relative_path']: f for r in value['reports'] for f in r['write']}
            elif mutation == 'variables': value['variables_digest'] = digest(dict(args['variables'], TotalReqReport='Wrong'))
            elif mutation == 'config':
                wrong = deepcopy(args['report_configuration']); wrong['RuntimeReports'][0]['ReportName'] = 'Wrong'
                value['configuration_digest'] = digest(wrong)
                value['definition_digest'] = definition_digest(wrong)
            elif mutation == 'roster': value['reports'].pop()
            else: value['files'].pop('download/Total.csv')
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                catalogue.validate_candidate(candidate=rehash(value), **args)

    def test_missing_prior_names_or_provenance_is_unavailable(self):
        for key, value in (('previous_catalogue', None), ('last_generated', None),
                           ('last_generated', []), ('provenance', {})):
            candidate, args = fixture(); args[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                catalogue.validate_candidate(candidate=candidate, **args)

    def test_prior_case_aliases_deny_even_when_removed_or_overwritten(self):
        for paths in (('download/total.csv',), ('download/oldtotal.csv',),
                      ('download/Keep.csv', 'download/keep.csv')):
            candidate, args = fixture()
            args['previous_catalogue'] = {path: dict(candidate_id=PRIOR, file=file(path)) for path in paths}
            with self.subTest(paths=paths), self.assertRaisesRegex(ValueError, 'path-case'):
                catalogue.validate_candidate(candidate=candidate, **args)

    def test_same_path_overwrite_follows_ids_and_keeps_last_writer(self):
        candidate, args = fixture()
        definitions = [dict(row(7), Id=17), row(7)]
        config = dict(schema=SCHEMA, RuntimeReports=definitions, DownloadableUIReportSettings=[])
        first = deepcopy(candidate['reports'][0]); first['remove'] = [
            'output/Spiker_Order_Dump.csv', 'output/Spiker_Order_Dump.zip', 'download/Spiker_Order_Dump.zip']
        second = deepcopy(first); second['report_id'] = 17
        second['definition_digest'] = digest({k:v for k,v in definitions[0].items() if k != 'LastGeneratedFileName'})
        second['write'] = [file(path, 'b') for path in ('output/Spiker_Order_Dump.zip', 'download/Spiker_Order_Dump.zip')]
        candidate.update(configuration_digest=digest(config), definition_digest=definition_digest(config),
            reports=[first,second], last_generated_before=last_generated(config),
            last_generated_after=last_generated(config), files={f['relative_path']: f for f in second['write']})
        args.update(report_configuration=config, last_generated=last_generated(config),
                    provenance={7:first['source'],17:second['source']})
        result = catalogue.validate_candidate(candidate=rehash(candidate), **args)
        self.assertEqual(result['catalogue']['download/Spiker_Order_Dump.zip']['file']['sha256'], 'b'*64)

    def test_empty_placement_preserves_explicit_prior_and_all_names(self):
        candidate, args = fixture()
        args['placement'] = 'PostDBM'; args['provenance'] = {}
        candidate.update(placement='PostDBM', reports=[], files={},
                         last_generated_after=deepcopy(candidate['last_generated_before']))
        prior = {'download/keep.csv': dict(candidate_id=PRIOR, file=file('download/keep.csv'))}
        args['previous_catalogue'] = prior
        self.assertEqual(catalogue.validate_candidate(candidate=rehash(candidate), **args)['catalogue'], prior)

    def test_null_name_cleanup_delete_old_false_and_inactive_text_keep_native_meaning(self):
        _candidate, args = fixture()
        config = args['report_configuration']
        config['RuntimeReports'][0].update(LastGeneratedFileName=None, DeleteOldFile=False)
        config['RuntimeReports'].append(dict(row(7), Id=99, Active=False, LastGeneratedFileName=''))
        args['last_generated'] = last_generated(config)
        args.pop('previous_catalogue')
        expected = catalogue.reconstruct_events(**args)
        total = expected['events'][1]
        self.assertEqual(total['remove'], ['output/ .csv', 'output/Total.csv', 'download/Total.csv'])
        self.assertEqual(expected['last_generated_after'][-1], dict(Id=99, LastGeneratedFileName=''))

    def test_wrong_trusted_inputs_deny_a_previously_valid_candidate(self):
        for field in ('variables', 'provenance', 'report_configuration'):
            candidate, args = fixture()
            if field == 'variables': args[field]['TotalReqReport'] = 'Wrong'
            elif field == 'provenance': args[field][7]['phase_digest'] = 'f'*64
            else: args[field]['RuntimeReports'][0]['DeleteOldFile'] = False
            with self.subTest(field=field), self.assertRaises(ValueError):
                catalogue.validate_candidate(candidate=candidate, **args)

    def test_path_traversal_and_invalid_custody_are_denied(self):
        for path in ('../bad.csv', '/bad.csv', 'download/../bad.csv', 'download//bad.csv',
                     'download\\bad.csv', 'download/CON.csv'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                catalogue.validate_catalogue({path: dict(candidate_id=PRIOR, file=file(path))})
        with self.assertRaises(ValueError):
            catalogue.validate_catalogue({'download/a.csv':dict(candidate_id='invented', file=file('download/a.csv'))})

    def test_anchor_is_finite_explicit_shape_not_authentication(self):
        _candidate, args = fixture()
        config = args['report_configuration']
        anchor = dict(schema=catalogue.ANCHOR_SCHEMA, kind='PRE_FEATURE', identity=PRIOR,
            output_digest='a'*64, configuration_digest=digest(config),
            definition_digest=definition_digest(config), catalogue={},
            last_generated=args['last_generated'], evidence=dict(retained_manifest='b'*64))
        self.assertEqual(catalogue.validate_anchor(anchor, report_configuration=config), anchor)
        initialized = dict(anchor, kind='INITIALIZATION', output_digest=None)
        self.assertEqual(catalogue.validate_anchor(initialized, report_configuration=config), initialized)
        for field, value in (('catalogue', None), ('last_generated', []), ('evidence', {}),
                             ('evidence', {'rows':[1,2]}), ('identity','invented'),
                             ('configuration_digest','f'*64), ('extra','unexpected')):
            wrong = dict(anchor); wrong[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                catalogue.validate_anchor(wrong, report_configuration=config)
        with self.assertRaises(ValueError):
            catalogue.validate_anchor(dict(anchor, kind='INITIALIZATION'), report_configuration=config)
