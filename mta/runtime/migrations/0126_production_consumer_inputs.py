"""Typed nonempty request/remark frozen input; preserves aware remark timestamps."""
from django.db import migrations

FORWARD=r'''
CREATE TABLE mta_state.input_production_request (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "SKUCode" text CHECK (char_length("SKUCode") + char_length(regexp_replace("SKUCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "WhCode" text CHECK (char_length("WhCode") + char_length(regexp_replace("WhCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "ParentWhCode" text CHECK (char_length("ParentWhCode") + char_length(regexp_replace("ParentWhCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "Request" text,
 "RequestDate" timestamp without time zone,
 "Action" text,
 "ActionDate" timestamp without time zone,
 "UserId" text,
 "ETA" timestamp without time zone,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER production_input BEFORE INSERT OR UPDATE OR DELETE ON mta_state.input_production_request FOR EACH ROW EXECUTE FUNCTION mta.guard_supplier_input_image();
CREATE TRIGGER production_input_truncate BEFORE TRUNCATE ON mta_state.input_production_request FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE TABLE mta_state.input_production_remark_bpr (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "source_ordinal" bigint NOT NULL CHECK (source_ordinal>=0),
 "SKUCode" text NOT NULL CHECK (char_length("SKUCode") + char_length(regexp_replace("SKUCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "WhCode" text NOT NULL CHECK (char_length("WhCode") + char_length(regexp_replace("WhCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "Remark" text,
 "Username" text CHECK (char_length("Username") + char_length(regexp_replace("Username", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 100),
 "RemarkDate" timestamp with time zone NOT NULL,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER production_input BEFORE INSERT OR UPDATE OR DELETE ON mta_state.input_production_remark_bpr FOR EACH ROW EXECUTE FUNCTION mta.guard_supplier_input_image();
CREATE TRIGGER production_input_truncate BEFORE TRUNCATE ON mta_state.input_production_remark_bpr FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE TABLE mta_state.input_production_remark_bor (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "source_ordinal" bigint NOT NULL CHECK (source_ordinal>=0),
 "SKUCode" text NOT NULL CHECK (char_length("SKUCode") + char_length(regexp_replace("SKUCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "WhCode" text NOT NULL CHECK (char_length("WhCode") + char_length(regexp_replace("WhCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "SupplierCode" text NOT NULL CHECK (char_length("SupplierCode") + char_length(regexp_replace("SupplierCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "Remark" text,
 "Username" text CHECK (char_length("Username") + char_length(regexp_replace("Username", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 100),
 "RemarkDate" timestamp with time zone NOT NULL,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER production_input BEFORE INSERT OR UPDATE OR DELETE ON mta_state.input_production_remark_bor FOR EACH ROW EXECUTE FUNCTION mta.guard_supplier_input_image();
CREATE TRIGGER production_input_truncate BEFORE TRUNCATE ON mta_state.input_production_remark_bor FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE TABLE mta_state.input_production_remark_boroa (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "source_ordinal" bigint NOT NULL CHECK (source_ordinal>=0),
 "SKUCode" text NOT NULL CHECK (char_length("SKUCode") + char_length(regexp_replace("SKUCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "WhCode" text NOT NULL CHECK (char_length("WhCode") + char_length(regexp_replace("WhCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "SupplierCode" text NOT NULL CHECK (char_length("SupplierCode") + char_length(regexp_replace("SupplierCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "Remark" text,
 "Username" text CHECK (char_length("Username") + char_length(regexp_replace("Username", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "RemarkDate" timestamp with time zone NOT NULL,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER production_input BEFORE INSERT OR UPDATE OR DELETE ON mta_state.input_production_remark_boroa FOR EACH ROW EXECUTE FUNCTION mta.guard_supplier_input_image();
CREATE TRIGGER production_input_truncate BEFORE TRUNCATE ON mta_state.input_production_remark_boroa FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
REVERSE='''
DROP TABLE mta_state.input_production_remark_boroa;
DROP TABLE mta_state.input_production_remark_bor;
DROP TABLE mta_state.input_production_remark_bpr;
DROP TABLE mta_state.input_production_request;
'''

class Migration(migrations.Migration):
    dependencies=[('fresh_mta','0125_production_output_sources')]
    operations=[migrations.RunSQL(FORWARD,REVERSE)]
