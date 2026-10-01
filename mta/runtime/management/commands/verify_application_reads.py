"""Read-only HTTP/relational wiring proof; not an independent API parity oracle."""
import gzip
import hashlib
import json
import time
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client

from mta.presentation.context import permission_catalogue, publication
from mta.runtime.models import CalculationRun
from mta.serialization import digest


def run_identity(run):
    run.refresh_from_db()
    return dict(id=str(run.pk), status=run.status, input_digest=run.input_digest,
        output_digest=run.output_digest, production_digest=run.production_digest,
        parity_summary=run.parity_summary, commands=list(run.commands.values('id','digest','before_digest','after_digest')))


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--evidence', type=Path, required=True)
        parser.add_argument('--insights', action='store_true')
        parser.add_argument('--history', action='store_true')
        parser.add_argument('--rrr', action='store_true')
        parser.add_argument('--excess', action='store_true')
        parser.add_argument('--fulfillment', action='store_true')
        parser.add_argument('--expedite', action='store_true')
        parser.add_argument('--expedite-charts', action='store_true')

    def handle(self, *args, **options):
        target = options['evidence']
        if target.exists():
            raise CommandError('Use a new evidence directory; preserve earlier receipts')
        target.mkdir(parents=True)
        root = Path(__file__).resolve().parents[4]
        sources = [*sorted((root/'mta/presentation').glob('*.py')), *sorted((root/'mta/config').glob('*.json')),
                   root/'vectorflow/settings.py', root/'vectorflow/urls.py', Path(__file__)]
        source_hashes = {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
        (target/'source.json').write_text(json.dumps(source_hashes,indent=2),encoding='utf-8')
        catalogue = permission_catalogue()
        run = CalculationRun.objects.get(pk=settings.VF_MTA_PUBLISHED_RUN)
        before = run_identity(run)
        hierarchy_receipt = publication().hierarchy_receipt
        payload = dict(product_permissions=[r['id'] for r in catalogue['products']['records'] if r['level_2'] is None],
                       location_permissions=[r['id'] for r in catalogue['locations']['records'] if r['level_2'] is None],
                       paginationParameter=dict(pageNumber=1,recordsPerPage=10))
        requests = [
            ('GET', 'GetLastRunDate', None),
            ('GET', 'GetUIConfig?reportName=NormSuggestion', None),
            ('POST', 'DBMDataCount', payload),
            ('POST', 'DBMData', payload),
            ('POST', 'GetBTRDataCount', payload),
            ('POST', 'GetBTRData', payload),
            ('POST', 'DailyDataGraph', {**payload,'SKUCode':'337','WHCode':'AG515802'}),
        ]
        if options['insights']:
            requests = [('POST', path, payload) for path in (
                'GetBufferTrendGraphData', 'GetResearchInsightData',
                'DBMNormSuggestionLoc', 'DBMNormSuggestionSKUs', 'DBMNormSuggestionPie', 'DBMNormSuggestionAgeing',
                'ChronicUnavailabilityLoc', 'ChronicUnavailabilitySku', 'ChronicUnavailabilityGridViewData',
                'AvailabilityTrend', 'AvailabilityAgeing')]
            requests.append(('GET', 'GetHistroricalAvailabilityBPRData', payload))
            requests=[(method,path,{**body,'data':[dict(SKUCode='337',WhCode='AG515802')]}
                if path=='GetResearchInsightData' else body) for method,path,body in requests]
        if options['rrr']:
            if options['insights']:
                raise CommandError('Select one focused consumer packet')
            payload['paginationParameter']['recordsPerPage'] = 5000
            requests = [('GET','GetUIConfig?reportName=RationRequirementReport',None),
                        ('POST','RRRDataCount',payload), ('POST','RRRData',payload)]
        if options['excess']:
            if options['insights'] or options['rrr']:
                raise CommandError('Select one focused consumer packet')
            payload.update(category='excessInventory',type='parent')
            payload['paginationParameter']['recordsPerPage']=5000
            requests=[('GET','GetUIConfig?reportName=Excess_Inventory_Review',None),
                      ('POST','GetPlanningDataGridCount',payload),('POST','GetPlanningDataGrid',payload),
                      ('POST','GetPlanningDataGraph',payload)]
        if options['fulfillment']:
            if options['insights'] or options['rrr'] or options['excess']:
                raise CommandError('Select one focused consumer packet')
            payload.update(category='orderFulfillment',type='parent')
            payload['paginationParameter']['recordsPerPage']=5000
            requests=[('POST','GetPlanningDataGridCount',payload),('POST','GetPlanningDataGrid',payload),
                      ('POST','GetPlanningDataGraph',payload)]
        if options['expedite']:
            if any(options[k] for k in ('insights','rrr','excess','fulfillment')):
                raise CommandError('Select one focused consumer packet')
            requests=[('POST','GetPlanningDataGridCount',{**payload,'category':'expedite','type':kind})
                      for kind in ('parent','child')]
        if options['expedite_charts']:
            if any(options[k] for k in ('insights','rrr','excess','fulfillment','expedite')):
                raise CommandError('Select one focused consumer packet')
            requests=[('POST','GetPlanningDataGraph',{**payload,'category':'expedite','type':kind})
                      for kind in ('parent','child')]
        if options['history']:
            if any(options[k] for k in ('insights','rrr','excess','fulfillment','expedite','expedite_charts')):
                raise CommandError('Select one focused consumer packet')
            requests=[('POST','DBMDataCount',payload),('POST','DBMData',payload),
                ('POST','GetBufferTrendGraphData',{**payload,'days':12,'bufferTrendType':'tech'}),
                ('POST','GetResearchInsightData',{**payload,'data':[dict(SKUCode='337',WhCode='AG515802')]}),
                ('GET','GetHistroricalAvailabilityBPRData',payload)]
        client, observations = Client(), []
        headers = {'HTTP_X_VECTORFLOW_IDENTITY': json.dumps(dict(id='isolated-application-read-proof',name='readonly'))}
        try:
            for index, (method, path, body) in enumerate(requests):
                started = time.monotonic()
                if method == 'POST':
                    response = client.post('/api/mta/' + path, json.dumps(body), content_type='application/json', **headers)
                else:
                    response = client.generic('GET', '/api/mta/' + path, json.dumps(body or {}),
                                              content_type='application/json', **headers)
                data = response.json()
                evidence = target / ('response-%02d.json.gz' % index)
                with gzip.open(evidence, 'wt', encoding='utf-8') as stream:
                    json.dump(dict(method=method, path=path, request=body, status=response.status_code, response=data), stream)
                observations.append(dict(path=path, status=response.status_code, payload=evidence.name,
                    sha256=hashlib.sha256(evidence.read_bytes()).hexdigest(), seconds=round(time.monotonic()-started,3)))
                if response.status_code != 200:
                    raise CommandError('Application read failed: ' + path + ': ' + json.dumps(data))
                self.stdout.write(path + ' HTTP200', ending='\n')
                self.stdout.flush()
            after = run_identity(run)
            if before != after:
                raise CommandError('Read endpoint mutated accepted run/action/parity identity')
            if any(hashlib.sha256((root/name).read_bytes()).hexdigest()!=sha for name,sha in source_hashes.items()):
                raise CommandError('Application source changed during proof')
            result = dict(status='APPLICATION_READBACK_PASS_NOT_API_PARITY_ACCEPTANCE',
                hierarchy_supplement=hierarchy_receipt,
                run=before, selected_scope=payload, observations=observations,
                accepted_run_unchanged=True, calculations_executed=0, serving_changes=False,
                sources_sha256=hashlib.sha256((target/'source.json').read_bytes()).hexdigest(),
                authority='Client exercises actual Django routes against accepted PostgreSQL rows; authenticated gateway/browser and independent consumer comparisons remain required')
        except Exception as exc:
            result = dict(status='FAILED',run=before,observations=observations,
                          error=dict(type=type(exc).__name__,message=str(exc)))
            (target/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
            raise
        (target/'receipt.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        self.stdout.write(json.dumps(dict(status=result['status'],run_id=str(run.pk),
            observations=len(observations),receipt_sha256=hashlib.sha256((target/'receipt.json').read_bytes()).hexdigest())))
