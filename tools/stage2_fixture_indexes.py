"""Owned fixture-only history indexes after the retained window002 timeout."""
import json
import os
from tools.stage2_vm_load import DATA,DB,IDENTITY
from tools.stage2_vm_contract import atomic,sealed


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
    import django
    django.setup()
    from django.db import connection
    from mta.presentation.fixture import freeze_state
    from mta.serialization import digest
    if connection.settings_dict['NAME']!=DB:raise ValueError('Wrong isolated database')
    _,manifest_sha=sealed(DATA)
    before=digest(freeze_state())
    quote=connection.ops.quote_name
    receipt=[]
    with connection.cursor() as cur:
        cur.execute('SELECT manifest_sha256 FROM stage2_owner.manifest')
        if cur.fetchall()!=[(manifest_sha,)]:raise ValueError('Wrong source identity')
        cur.execute("SET maintenance_work_mem='64MB'")
        cur.execute('SET max_parallel_maintenance_workers=0')
        for name,date in [('dailyconsumption','ReportDate'),('suspendhistory','ReportDate'),('suggestionslog','SuggestionDate')]:
            table='dbm_'+name;index='stage2_'+name+'_pair_date'
            definition='CREATE INDEX '+quote(index)+' ON mta_state.'+quote(table)+' ("SKUCode", "WhCode", '+quote(date)+')'
            cur.execute('SELECT pg_get_indexdef(i.indexrelid),i.indisvalid,i.indisready FROM pg_index i WHERE i.indexrelid=to_regclass(%s)',['mta_state.'+index])
            prior=cur.fetchone()
            if not prior:
                print('Creating fixture index',index,flush=True)
                cur.execute(definition)
            cur.execute('SELECT pg_get_indexdef(i.indexrelid),i.indisvalid,i.indisready FROM pg_index i WHERE i.indexrelid=to_regclass(%s)',['mta_state.'+index])
            row=cur.fetchone()
            expected='CREATE INDEX '+index+' ON mta_state.'+table+' USING btree ("SKUCode", "WhCode", "'+date+'")'
            if row!=(expected,True,True):raise ValueError('Index definition/validity differs')
            cur.execute('ANALYZE mta_state.'+quote(table))
            receipt.append(dict(index=index,definition=row[0],valid=True))
            print('Verified fixture index',index,flush=True)
    if digest(freeze_state())!=before:raise ValueError('Fixture freeze identity changed')
    atomic(DATA/'fixture-indexes.json',dict(status='PASS',identity=IDENTITY,manifest_sha256=manifest_sha,
        freeze_digest=before,indexes=receipt,reason='Window002 DailyDataGraph60-second gateway timeout',row_mutations=0))


if __name__=='__main__':main()
