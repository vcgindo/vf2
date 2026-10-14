"""Additive approved BOR/BOROA source fields only; no UI configuration tables."""
from django.db import migrations

FORWARD = r'''
ALTER TABLE mta_state.production_boroarequirement ADD COLUMN "ParentWhCode" text CHECK (char_length("ParentWhCode") + char_length(regexp_replace("ParentWhCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_borwithorderallocation ADD COLUMN "SKULocAtt01" text CHECK (char_length("SKULocAtt01") + char_length(regexp_replace("SKULocAtt01", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_borwithorderallocation ADD COLUMN "SKULocAtt02" text CHECK (char_length("SKULocAtt02") + char_length(regexp_replace("SKULocAtt02", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_borwithorderallocation ADD COLUMN "SKULocAtt03" text CHECK (char_length("SKULocAtt03") + char_length(regexp_replace("SKULocAtt03", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_borwithorderallocation ADD COLUMN "SKULocAtt04" text CHECK (char_length("SKULocAtt04") + char_length(regexp_replace("SKULocAtt04", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_borwithorderallocation ADD COLUMN "SKULocAtt05" text CHECK (char_length("SKULocAtt05") + char_length(regexp_replace("SKULocAtt05", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_borwithorderallocation ADD COLUMN "SKULocAtt06" text CHECK (char_length("SKULocAtt06") + char_length(regexp_replace("SKULocAtt06", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_borwithorderallocation ADD COLUMN "SKULocAtt07" text CHECK (char_length("SKULocAtt07") + char_length(regexp_replace("SKULocAtt07", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_borwithorderallocation ADD COLUMN "SKULocAtt08" text CHECK (char_length("SKULocAtt08") + char_length(regexp_replace("SKULocAtt08", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_borwithorderallocation ADD COLUMN "SKULocAtt09" text CHECK (char_length("SKULocAtt09") + char_length(regexp_replace("SKULocAtt09", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_borwithorderallocation ADD COLUMN "SKULocAtt10" text CHECK (char_length("SKULocAtt10") + char_length(regexp_replace("SKULocAtt10", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_borwithorderallocation ADD COLUMN "SKULocAtt11" text CHECK (char_length("SKULocAtt11") + char_length(regexp_replace("SKULocAtt11", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_borwithorderallocation ADD COLUMN "SKULocAtt12" text CHECK (char_length("SKULocAtt12") + char_length(regexp_replace("SKULocAtt12", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_borwithorderallocation ADD COLUMN "SKULocAtt13" text CHECK (char_length("SKULocAtt13") + char_length(regexp_replace("SKULocAtt13", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_borwithorderallocation ADD COLUMN "SKULocAtt14" text CHECK (char_length("SKULocAtt14") + char_length(regexp_replace("SKULocAtt14", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_borwithorderallocation ADD COLUMN "SKULocAtt15" text CHECK (char_length("SKULocAtt15") + char_length(regexp_replace("SKULocAtt15", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_bor_orderallocationhistory ADD COLUMN "SKULocAtt01" text CHECK (char_length("SKULocAtt01") + char_length(regexp_replace("SKULocAtt01", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_bor_orderallocationhistory ADD COLUMN "SKULocAtt02" text CHECK (char_length("SKULocAtt02") + char_length(regexp_replace("SKULocAtt02", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_bor_orderallocationhistory ADD COLUMN "SKULocAtt03" text CHECK (char_length("SKULocAtt03") + char_length(regexp_replace("SKULocAtt03", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_bor_orderallocationhistory ADD COLUMN "SKULocAtt04" text CHECK (char_length("SKULocAtt04") + char_length(regexp_replace("SKULocAtt04", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_bor_orderallocationhistory ADD COLUMN "SKULocAtt05" text CHECK (char_length("SKULocAtt05") + char_length(regexp_replace("SKULocAtt05", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_bor_orderallocationhistory ADD COLUMN "SKULocAtt06" text CHECK (char_length("SKULocAtt06") + char_length(regexp_replace("SKULocAtt06", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_bor_orderallocationhistory ADD COLUMN "SKULocAtt07" text CHECK (char_length("SKULocAtt07") + char_length(regexp_replace("SKULocAtt07", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_bor_orderallocationhistory ADD COLUMN "SKULocAtt08" text CHECK (char_length("SKULocAtt08") + char_length(regexp_replace("SKULocAtt08", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_bor_orderallocationhistory ADD COLUMN "SKULocAtt09" text CHECK (char_length("SKULocAtt09") + char_length(regexp_replace("SKULocAtt09", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_bor_orderallocationhistory ADD COLUMN "SKULocAtt10" text CHECK (char_length("SKULocAtt10") + char_length(regexp_replace("SKULocAtt10", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_bor_orderallocationhistory ADD COLUMN "SKULocAtt11" text CHECK (char_length("SKULocAtt11") + char_length(regexp_replace("SKULocAtt11", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_bor_orderallocationhistory ADD COLUMN "SKULocAtt12" text CHECK (char_length("SKULocAtt12") + char_length(regexp_replace("SKULocAtt12", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_bor_orderallocationhistory ADD COLUMN "SKULocAtt13" text CHECK (char_length("SKULocAtt13") + char_length(regexp_replace("SKULocAtt13", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_bor_orderallocationhistory ADD COLUMN "SKULocAtt14" text CHECK (char_length("SKULocAtt14") + char_length(regexp_replace("SKULocAtt14", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
ALTER TABLE mta_state.production_bor_orderallocationhistory ADD COLUMN "SKULocAtt15" text CHECK (char_length("SKULocAtt15") + char_length(regexp_replace("SKULocAtt15", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50);
CREATE TABLE mta_state.production_supplierdispatchreq (vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT, vf_image text NOT NULL, vf_ordinal bigint NOT NULL, "SKUCode" text CHECK (char_length("SKUCode") + char_length(regexp_replace("SKUCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50) NOT NULL, "WHCode" text CHECK (char_length("WHCode") + char_length(regexp_replace("WHCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50) NOT NULL, "SupplierCode" text CHECK (char_length("SupplierCode") + char_length(regexp_replace("SupplierCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50) NOT NULL, "OriginalReq" integer NOT NULL, "DispatchReq" integer NOT NULL, "ReqTopOfRed" integer NOT NULL, "ReqTopOfYellow" integer NOT NULL, "ReqTopOfGreen" integer NOT NULL, "ReqTopOfBlue" integer NOT NULL, "SKULocAtt01" text CHECK (char_length("SKULocAtt01") + char_length(regexp_replace("SKULocAtt01", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50), "SKULocAtt02" text CHECK (char_length("SKULocAtt02") + char_length(regexp_replace("SKULocAtt02", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50), "SKULocAtt03" text CHECK (char_length("SKULocAtt03") + char_length(regexp_replace("SKULocAtt03", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50), "SKULocAtt04" text CHECK (char_length("SKULocAtt04") + char_length(regexp_replace("SKULocAtt04", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50), "SKULocAtt05" text CHECK (char_length("SKULocAtt05") + char_length(regexp_replace("SKULocAtt05", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50), "SKULocAtt06" text CHECK (char_length("SKULocAtt06") + char_length(regexp_replace("SKULocAtt06", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50), "SKULocAtt07" text CHECK (char_length("SKULocAtt07") + char_length(regexp_replace("SKULocAtt07", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50), "SKULocAtt08" text CHECK (char_length("SKULocAtt08") + char_length(regexp_replace("SKULocAtt08", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50), "SKULocAtt09" text CHECK (char_length("SKULocAtt09") + char_length(regexp_replace("SKULocAtt09", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50), "SKULocAtt10" text CHECK (char_length("SKULocAtt10") + char_length(regexp_replace("SKULocAtt10", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50), "SKULocAtt11" text CHECK (char_length("SKULocAtt11") + char_length(regexp_replace("SKULocAtt11", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50), "SKULocAtt12" text CHECK (char_length("SKULocAtt12") + char_length(regexp_replace("SKULocAtt12", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50), "SKULocAtt13" text CHECK (char_length("SKULocAtt13") + char_length(regexp_replace("SKULocAtt13", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50), "SKULocAtt14" text CHECK (char_length("SKULocAtt14") + char_length(regexp_replace("SKULocAtt14", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50), "SKULocAtt15" text CHECK (char_length("SKULocAtt15") + char_length(regexp_replace("SKULocAtt15", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50), "CumulativeTOR" integer NOT NULL, "CumulativeTOY" integer NOT NULL, "CumulativeTOG" integer NOT NULL, "CumulativeTOB" integer NOT NULL, "ReqTopOfBlack" integer NOT NULL, "CumulativeTOBlack" integer NOT NULL, PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER production_source BEFORE INSERT OR UPDATE OR DELETE ON mta_state.production_supplierdispatchreq FOR EACH ROW EXECUTE FUNCTION mta.guard_production_report_image();
CREATE TRIGGER production_source_truncate BEFORE TRUNCATE ON mta_state.production_supplierdispatchreq FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
REVERSE = r'''
ALTER TABLE mta_state.production_boroarequirement DROP COLUMN "ParentWhCode";
DROP TABLE mta_state.production_supplierdispatchreq;
ALTER TABLE mta_state.production_bor_orderallocationhistory DROP COLUMN "SKULocAtt15";
ALTER TABLE mta_state.production_bor_orderallocationhistory DROP COLUMN "SKULocAtt14";
ALTER TABLE mta_state.production_bor_orderallocationhistory DROP COLUMN "SKULocAtt13";
ALTER TABLE mta_state.production_bor_orderallocationhistory DROP COLUMN "SKULocAtt12";
ALTER TABLE mta_state.production_bor_orderallocationhistory DROP COLUMN "SKULocAtt11";
ALTER TABLE mta_state.production_bor_orderallocationhistory DROP COLUMN "SKULocAtt10";
ALTER TABLE mta_state.production_bor_orderallocationhistory DROP COLUMN "SKULocAtt09";
ALTER TABLE mta_state.production_bor_orderallocationhistory DROP COLUMN "SKULocAtt08";
ALTER TABLE mta_state.production_bor_orderallocationhistory DROP COLUMN "SKULocAtt07";
ALTER TABLE mta_state.production_bor_orderallocationhistory DROP COLUMN "SKULocAtt06";
ALTER TABLE mta_state.production_bor_orderallocationhistory DROP COLUMN "SKULocAtt05";
ALTER TABLE mta_state.production_bor_orderallocationhistory DROP COLUMN "SKULocAtt04";
ALTER TABLE mta_state.production_bor_orderallocationhistory DROP COLUMN "SKULocAtt03";
ALTER TABLE mta_state.production_bor_orderallocationhistory DROP COLUMN "SKULocAtt02";
ALTER TABLE mta_state.production_bor_orderallocationhistory DROP COLUMN "SKULocAtt01";
ALTER TABLE mta_state.production_borwithorderallocation DROP COLUMN "SKULocAtt15";
ALTER TABLE mta_state.production_borwithorderallocation DROP COLUMN "SKULocAtt14";
ALTER TABLE mta_state.production_borwithorderallocation DROP COLUMN "SKULocAtt13";
ALTER TABLE mta_state.production_borwithorderallocation DROP COLUMN "SKULocAtt12";
ALTER TABLE mta_state.production_borwithorderallocation DROP COLUMN "SKULocAtt11";
ALTER TABLE mta_state.production_borwithorderallocation DROP COLUMN "SKULocAtt10";
ALTER TABLE mta_state.production_borwithorderallocation DROP COLUMN "SKULocAtt09";
ALTER TABLE mta_state.production_borwithorderallocation DROP COLUMN "SKULocAtt08";
ALTER TABLE mta_state.production_borwithorderallocation DROP COLUMN "SKULocAtt07";
ALTER TABLE mta_state.production_borwithorderallocation DROP COLUMN "SKULocAtt06";
ALTER TABLE mta_state.production_borwithorderallocation DROP COLUMN "SKULocAtt05";
ALTER TABLE mta_state.production_borwithorderallocation DROP COLUMN "SKULocAtt04";
ALTER TABLE mta_state.production_borwithorderallocation DROP COLUMN "SKULocAtt03";
ALTER TABLE mta_state.production_borwithorderallocation DROP COLUMN "SKULocAtt02";
ALTER TABLE mta_state.production_borwithorderallocation DROP COLUMN "SKULocAtt01";
'''

class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0126_production_consumer_inputs')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
