"""Prepare and seal the exact BOR stable consumer occurrence bag."""
import json
from django.core.management.base import BaseCommand,CommandError
from django.db import connection,transaction
from mta.presentation.bor_sources import admitted_sources,native_binding,verify_values
from mta.presentation.bor_preparation import query,row_receipt,recipe_digest
from mta.runtime.bor_prepared_schema import verify_guards
from mta.runtime.models import BorPreparedReceipt,BorPreparedRow
from mta.runtime.relational_state import quote


class Command(BaseCommand):
    help=__doc__

    def add_arguments(self,parser): parser.add_argument('--verify-only',action='store_true')

    def handle(self,*args,**options):
        run,source_receipt=admitted_sources()
        source=source_receipt.source_digest
        with transaction.atomic():
            type(run).objects.select_for_update().get(pk=run.pk)
            verify_guards(connection);verify_values(run)
            receipt=BorPreparedReceipt.objects.filter(run=run).first()
            if receipt is None:
                if options['verify_only']: raise CommandError('BOR prepared receipt absent')
                if BorPreparedRow.objects.filter(run=run).exists(): raise CommandError('Unsealed BOR prepared rows exist')
                sql,params,columns=query(run)
                with connection.cursor() as c:
                    c.execute("SELECT set_config('fresh.bor_prepared_build',%s,true)",[str(run.pk)])
                    c.execute('INSERT INTO mta.'+quote(BorPreparedRow._meta.db_table)+' (run_id,'+
                        ','.join(map(quote,columns))+') SELECT %s,prepared.* FROM ('+sql+') prepared',[run.pk,*params])
            count,checksum=row_receipt(run)
            expected=dict(source_digest=source,recipe_digest=recipe_digest(),row_count=count,rows_digest=checksum)
            if receipt:
                if any(getattr(receipt,k)!=v for k,v in expected.items()): raise CommandError('BOR prepared receipt changed')
            else: BorPreparedReceipt.objects.create(run=run,**expected)
            if native_binding()[1]!=source: raise CommandError('BOR source changed before commit')
        self.stdout.write(json.dumps(dict(status='PASS',created=receipt is None,**expected)))
