"""Import the four explicitly authorized April BOROA presentation bags once."""
import gzip,json
from pathlib import Path
from datetime import datetime,timezone
from django.core.management.base import BaseCommand,CommandError
from django.db import connection,transaction
from mta.presentation.boroa_contract import SOURCE_FIELDS as FIELDS,source_recipe as recipe_digest
from mta.presentation.boroa_sources import MODELS,native_binding,validate_capture,verify_values
from mta.runtime.boroa_models import BorOaSourceReceipt
from mta.runtime.boroa_source_schema import verify_guards


class Command(BaseCommand):
    help=__doc__

    def add_arguments(self,parser):
        parser.add_argument('--directory')
        parser.add_argument('--verify-only',action='store_true')

    def handle(self,*args,**options):
        if connection.vendor!='postgresql': raise CommandError('BOROA requires PostgreSQL')
        run,source=native_binding()
        with transaction.atomic():
            type(run).objects.select_for_update().get(pk=run.pk)
            verify_guards(connection)
            receipt=BorOaSourceReceipt.objects.filter(run=run).first()
            if receipt is None:
                if options['verify_only'] or not options['directory']:
                    raise CommandError('BOROA source receipt absent; explicit capture directory required')
                captures={}
                for name,model in MODELS.items():
                    if model.objects.filter(run=run).exists(): raise CommandError('Unsealed BOROA rows exist')
                    path=Path(options['directory'])/(name+'.json.gz')
                    rows=json.loads(gzip.decompress(path.read_bytes()))
                    validate_capture(name,rows)
                    captures[name]=rows
                with connection.cursor() as c:
                    c.execute("SELECT set_config('fresh.boroa_source_build',%s,true)",[str(run.pk)])
                for name,rows in captures.items():
                    instances=[]
                    for ordinal,row in enumerate(rows):
                        values=dict(row)
                        for field,kind in FIELDS[name].items():
                            if kind['kind']=='datetime': values[field]=datetime.fromisoformat(values[field]).replace(tzinfo=timezone.utc)
                        instances.append(MODELS[name](run=run,ordinal=ordinal,**values))
                    MODELS[name].objects.bulk_create(instances,batch_size=300)
            expected=dict(source_digest=source,recipe_digest=recipe_digest(),**verify_values(run))
            if receipt:
                if any(getattr(receipt,k)!=v for k,v in expected.items()):
                    raise CommandError('BOROA receipt differs; overwrite forbidden')
            else: BorOaSourceReceipt.objects.create(run=run,**expected)
            if native_binding()[1]!=source: raise CommandError('Native fixture changed during preparation')
        self.stdout.write(json.dumps(dict(status='PASS',created=receipt is None,**expected)))
