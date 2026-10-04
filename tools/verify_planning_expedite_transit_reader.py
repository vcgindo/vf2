"""Complete nested transit bags: prepared SQL versus independent Python source joins.

Not a legacy wire or browser acceptance claim. Canonical nested SQL has no ORDER BY.
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
import django
django.setup()
from django.db import connection
from mta.presentation import fixture
from mta.presentation.expedite_parent import parent_transit_rows
from mta.presentation.selective import image_rows
from mta.presentation.planning_expedite_transit import transit_rows
from mta.presentation.planning_expedite_transit_preparation import pick_source, PICK_TABLE
from mta.serialization import digest


def main():
    run, source = fixture.binding()
    pick_source(verify_values=True)
    nms = image_rows(run,'closing/consumer_context/NMSAllItems')
    remarks = fixture.bpr_ancillary(run)['BPRReport_RemarkDetails']
    with connection.cursor() as c:
        c.execute('SELECT "SKUCode","WhCode","ParentStockForRationing" FROM '+PICK_TABLE+' ORDER BY vf_source_ordinal')
        pick = [dict(zip(['SKUCode','WhCode','ParentStockForRationing'],row)) for row in c.fetchall()]
    cases = []
    for branch in ('dispatch','availability'):
        for label, condition in [('full','TRUE'),('empty','FALSE'),('subset','H.ordinal %% 2=0')]:
            relation = ('FROM mta.fresh_mta_planningexpeditegridoccurrence H '
                'JOIN mta.fresh_mta_expediterow A ON A.run_id=H.run_id AND A.ordinal=H.fact_ordinal '
                "WHERE H.run_id=%s AND H.direction='parent' AND H.branch=%s AND "+condition)
            params = [run.pk,branch]
            with connection.cursor() as c:
                c.execute('SELECT A."SKUCode",A."WhCode" '+relation,params)
                selected = [dict(sc=sc,wc=wc) for sc,wc in c.fetchall()]
            expected = parent_transit_rows(nms,remarks,pick,selected,availability=branch=='availability')
            actual = transit_rows(run,branch,'SELECT H.ordinal '+relation,params)
            bag = lambda rows:Counter(json.dumps(row,sort_keys=True,ensure_ascii=False) for row in rows)
            assert bag(actual)==bag(expected),(branch,label,len(actual),len(expected))
            cases.append(dict(branch=branch,case=label,rows=len(actual),bag_digest=digest(sorted(bag(actual).items()))))
    assert fixture.binding()[1]==source
    print(json.dumps(dict(status='PASS',cases=cases,source_digest=source)))


if __name__=='__main__': main()
