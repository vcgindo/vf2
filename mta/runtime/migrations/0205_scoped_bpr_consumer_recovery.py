"""Incomplete external appends conflict without preventing explicit fencing."""
from importlib import import_module
from django.db import migrations

prior=import_module('mta.runtime.migrations.0204_scoped_bpr_consumer_ownership')
OLD=prior.NORMALIZE
anchor="   AND C.watermark=(policy->>'watermark')::bigint AND O.next_ordinal>=C.watermark"
assert OLD.count(anchor)==1
NEW=OLD.replace(anchor,anchor+'''
   AND (O.provenance_receipt->>'schema' IS DISTINCT FROM 'fresh-production-consumer-opening-v1'
    OR (O.provenance_receipt->>'initialization_id' IS NOT DISTINCT FROM binding->>'initialization_id'
     AND O.provenance_receipt->>'source_digest' IS NOT DISTINCT FROM binding->>'source_digest'))''',1)
before='''   AND O.next_ordinal=(SELECT coalesce(max(L.ordinal)+1,0) FROM mta.fresh_mta_bprliveremark L
       WHERE L.owner_id=O.family)) INTO complete;
 IF NOT complete THEN RAISE EXCEPTION 'Scoped BPR consumer owner or complete journal prefix differs'; END IF;'''
after='''  ) INTO complete;
 IF NOT complete THEN RAISE EXCEPTION 'Scoped BPR consumer capture owner differs'; END IF;
 SELECT O.next_ordinal=(SELECT coalesce(max(L.ordinal)+1,0) FROM mta.fresh_mta_bprliveremark L
  WHERE L.owner_id=O.family) INTO complete FROM mta.fresh_mta_remarkowner O
  WHERE O.family='BPRReport_RemarkDetails';
 -- Do not waive any consumer deltas while its prefix is incomplete. The raw
 -- conflict remains observable by both admission and explicit failure/fence.
 IF NOT complete THEN RETURN observed; END IF;'''
assert NEW.count(before)==1
NEW=NEW.replace(before,after,1)


def replace(before,after):
    return prior.exact('scope_bpr_consumer_cut(uuid,jsonb)',before)+(
        'CREATE OR REPLACE FUNCTION mta.scope_bpr_consumer_cut(target uuid,observed jsonb) '
        'RETURNS jsonb LANGUAGE plpgsql SET search_path=pg_catalog,mta AS $body$'+after+'$body$;\n')


class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0204_scoped_bpr_consumer_ownership')]
    operations=[migrations.RunSQL(replace(OLD,NEW),replace(NEW,OLD))]
