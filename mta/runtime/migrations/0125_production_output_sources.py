"""Additive typed native output/history and external ledger images."""
from django.db import migrations

FORWARD = r'''
CREATE FUNCTION mta.guard_production_report_image() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF TG_OP<>'INSERT' THEN RAISE EXCEPTION 'Native producer image is immutable'; END IF;
 PERFORM 1 FROM mta.fresh_mta_calculationrun R WHERE R.id=NEW.vf_run_id
 AND R.kind='DAILY_CHAIN' AND R.status='RUNNING'
 AND NOT EXISTS(SELECT 1 FROM mta.fresh_mta_dailysourcereceipt S WHERE S.run_id=R.id) FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'Native producer image requires its unsealed running day'; END IF;
 RETURN NEW;
END $$;
CREATE TABLE mta_state.production_borwithorderallocation (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "SKUCode" text NOT NULL CHECK (char_length("SKUCode") + char_length(regexp_replace("SKUCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "WhCode" text NOT NULL CHECK (char_length("WhCode") + char_length(regexp_replace("WhCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "SupplierCode" text NOT NULL CHECK (char_length("SupplierCode") + char_length(regexp_replace("SupplierCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "Norm" integer NOT NULL,
 "VirtualNorm" integer NOT NULL,
 "Stock" integer NOT NULL,
 "GIT" integer NOT NULL,
 "ParentLeftoverStock" integer NOT NULL,
 "Requirement" integer NOT NULL,
 "Req_TOB" integer NOT NULL,
 "Req_TOR" integer NOT NULL,
 "Req_TOY" integer NOT NULL,
 "Req_TOG" integer NOT NULL,
 "Req_TOBlue" integer NOT NULL,
 "DispatchQty" integer NOT NULL,
 "Dispatch_TOB" integer NOT NULL,
 "Dispatch_TOR" integer NOT NULL,
 "Dispatch_TOY" integer NOT NULL,
 "Dispatch_TOG" integer NOT NULL,
 "Dispatch_ToBlue" integer NOT NULL,
 "DispatchColor" text NOT NULL CHECK (char_length("DispatchColor") + char_length(regexp_replace("DispatchColor", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 10),
 "OrderBlackUnsatisfiedPercentage" numeric(10,2) NOT NULL,
 "OrderRedUnsatisfiedPercentage" numeric(10,2) NOT NULL,
 "OrderYellowUnsatisfiedPercentage" numeric(10,2) NOT NULL,
 "OrderGreenUnsatisfiedPercentage" numeric(10,2) NOT NULL,
 "DispatchPen" numeric(10,2) NOT NULL,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER production_source BEFORE INSERT OR UPDATE OR DELETE ON mta_state.production_borwithorderallocation FOR EACH ROW EXECUTE FUNCTION mta.guard_production_report_image();
CREATE TRIGGER production_source_truncate BEFORE TRUNCATE ON mta_state.production_borwithorderallocation FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_production_report_image();
CREATE TABLE mta_state.production_bor_orderallocationhistory (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "SKUCode" text NOT NULL CHECK (char_length("SKUCode") + char_length(regexp_replace("SKUCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "WhCode" text NOT NULL CHECK (char_length("WhCode") + char_length(regexp_replace("WhCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "SupplierCode" text NOT NULL CHECK (char_length("SupplierCode") + char_length(regexp_replace("SupplierCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "Norm" integer NOT NULL,
 "VirtualNorm" integer NOT NULL,
 "Stock" integer NOT NULL,
 "GIT" integer NOT NULL,
 "ParentLeftoverStock" integer NOT NULL,
 "Requirement" integer NOT NULL,
 "Req_TOB" integer NOT NULL,
 "Req_TOR" integer NOT NULL,
 "Req_TOY" integer NOT NULL,
 "Req_TOG" integer NOT NULL,
 "Req_TOBlue" integer NOT NULL,
 "DispatchQty" integer NOT NULL,
 "Dispatch_TOB" integer NOT NULL,
 "Dispatch_TOR" integer NOT NULL,
 "Dispatch_TOY" integer NOT NULL,
 "Dispatch_TOG" integer NOT NULL,
 "Dispatch_ToBlue" integer NOT NULL,
 "DispatchColor" text NOT NULL CHECK (char_length("DispatchColor") + char_length(regexp_replace("DispatchColor", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 10),
 "OrderBlackUnsatisfiedPercentage" numeric(10,2) NOT NULL,
 "OrderRedUnsatisfiedPercentage" numeric(10,2) NOT NULL,
 "OrderYellowUnsatisfiedPercentage" numeric(10,2) NOT NULL,
 "OrderGreenUnsatisfiedPercentage" numeric(10,2) NOT NULL,
 "DispatchPen" numeric(10,2) NOT NULL,
 "ReportDate" date NOT NULL CHECK ("ReportDate" BETWEEN DATE '0001-01-01' AND DATE '9999-12-31'),
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER production_source BEFORE INSERT OR UPDATE OR DELETE ON mta_state.production_bor_orderallocationhistory FOR EACH ROW EXECUTE FUNCTION mta.guard_production_report_image();
CREATE TRIGGER production_source_truncate BEFORE TRUNCATE ON mta_state.production_bor_orderallocationhistory FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_production_report_image();
CREATE TABLE mta_state.production_rrr_orderallocation (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "SKUCode" text NOT NULL CHECK (char_length("SKUCode") + char_length(regexp_replace("SKUCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "WhCode" text NOT NULL CHECK (char_length("WhCode") + char_length(regexp_replace("WhCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "ParentWhCode" text NOT NULL CHECK (char_length("ParentWhCode") + char_length(regexp_replace("ParentWhCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "AllocationFor" text CHECK (char_length("AllocationFor") + char_length(regexp_replace("AllocationFor", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 10),
 "Norm" integer,
 "VirtualNorm" integer,
 "Stock" integer,
 "GIT" integer,
 "LeftoverParentStock" integer,
 "Requirement" integer,
 "TOBlack_ReqQty" integer NOT NULL,
 "TOR_ReqQty" integer NOT NULL,
 "TOY_ReqQty" integer NOT NULL,
 "TOGreen_ReqQty" integer NOT NULL,
 "TOBlue_ReqQty" integer NOT NULL,
 "RationedQty" integer,
 "RationedCasePacks" integer,
 "TOBlack_AllocQty" integer NOT NULL,
 "TOR_AllocQty" integer NOT NULL,
 "TOY_AllocQty" integer NOT NULL,
 "TOGreen_AllocQty" integer NOT NULL,
 "TOBlue_AllocQty" integer NOT NULL,
 "DispatchColor" text CHECK (char_length("DispatchColor") + char_length(regexp_replace("DispatchColor", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 10),
 "AdvAllocDone" integer NOT NULL,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER production_source BEFORE INSERT OR UPDATE OR DELETE ON mta_state.production_rrr_orderallocation FOR EACH ROW EXECUTE FUNCTION mta.guard_production_report_image();
CREATE TRIGGER production_source_truncate BEFORE TRUNCATE ON mta_state.production_rrr_orderallocation FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_production_report_image();
CREATE TABLE mta_state.production_rrr_orderallocationhistory (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "SKUCode" text NOT NULL CHECK (char_length("SKUCode") + char_length(regexp_replace("SKUCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "WhCode" text NOT NULL CHECK (char_length("WhCode") + char_length(regexp_replace("WhCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "ParentWhCode" text NOT NULL CHECK (char_length("ParentWhCode") + char_length(regexp_replace("ParentWhCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "AllocationFor" text CHECK (char_length("AllocationFor") + char_length(regexp_replace("AllocationFor", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 10),
 "Norm" integer,
 "VirtualNorm" integer,
 "Stock" integer,
 "GIT" integer,
 "LeftoverParentStock" integer,
 "Requirement" integer,
 "TOBlack_ReqQty" integer NOT NULL,
 "TOR_ReqQty" integer NOT NULL,
 "TOY_ReqQty" integer NOT NULL,
 "TOGreen_ReqQty" integer NOT NULL,
 "TOBlue_ReqQty" integer NOT NULL,
 "RationedQty" integer,
 "RationedCasePacks" integer,
 "TOBlack_AllocQty" integer NOT NULL,
 "TOR_AllocQty" integer NOT NULL,
 "TOY_AllocQty" integer NOT NULL,
 "TOGreen_AllocQty" integer NOT NULL,
 "TOBlue_AllocQty" integer NOT NULL,
 "DispatchColor" text CHECK (char_length("DispatchColor") + char_length(regexp_replace("DispatchColor", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 10),
 "AdvAllocDone" integer NOT NULL,
 "ReportDate" date NOT NULL CHECK ("ReportDate" BETWEEN DATE '0001-01-01' AND DATE '9999-12-31'),
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER production_source BEFORE INSERT OR UPDATE OR DELETE ON mta_state.production_rrr_orderallocationhistory FOR EACH ROW EXECUTE FUNCTION mta.guard_production_report_image();
CREATE TRIGGER production_source_truncate BEFORE TRUNCATE ON mta_state.production_rrr_orderallocationhistory FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_production_report_image();
CREATE TABLE mta_state.production_allocatedorders (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "SKUCode" text NOT NULL CHECK (char_length("SKUCode") + char_length(regexp_replace("SKUCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "DestWhCode" text NOT NULL CHECK (char_length("DestWhCode") + char_length(regexp_replace("DestWhCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "SrcWhCode" text NOT NULL CHECK (char_length("SrcWhCode") + char_length(regexp_replace("SrcWhCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "OrderKey" integer NOT NULL,
 "DueDate" date CHECK ("DueDate" BETWEEN DATE '0001-01-01' AND DATE '9999-12-31'),
 "CustomerOrderId" text CHECK (char_length("CustomerOrderId") + char_length(regexp_replace("CustomerOrderId", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "IsSpike" integer,
 "Qty" integer NOT NULL,
 "OrderWiseAllocatedQty" integer NOT NULL,
 "BPP" numeric(10,2),
 "OrderColor" text CHECK (char_length("OrderColor") + char_length(regexp_replace("OrderColor", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 10),
 "DueDateAtDest" date CHECK ("DueDateAtDest" BETWEEN DATE '0001-01-01' AND DATE '9999-12-31'),
 "PackSizeWiseAllocatedQty" integer NOT NULL,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER production_source BEFORE INSERT OR UPDATE OR DELETE ON mta_state.production_allocatedorders FOR EACH ROW EXECUTE FUNCTION mta.guard_production_report_image();
CREATE TRIGGER production_source_truncate BEFORE TRUNCATE ON mta_state.production_allocatedorders FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_production_report_image();
CREATE TABLE mta_state.production_boroarequirement (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "SKUCode" text NOT NULL CHECK (char_length("SKUCode") + char_length(regexp_replace("SKUCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "WhCode" text NOT NULL CHECK (char_length("WhCode") + char_length(regexp_replace("WhCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "AdvAllocDone" integer NOT NULL,
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER production_source BEFORE INSERT OR UPDATE OR DELETE ON mta_state.production_boroarequirement FOR EACH ROW EXECUTE FUNCTION mta.guard_production_report_image();
CREATE TRIGGER production_source_truncate BEFORE TRUNCATE ON mta_state.production_boroarequirement FOR EACH STATEMENT EXECUTE FUNCTION mta.guard_production_report_image();
CREATE TABLE mta_state.input_production_shipment (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "SKUCode" text CHECK (char_length("SKUCode") + char_length(regexp_replace("SKUCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "ToLocationCode" text CHECK (char_length("ToLocationCode") + char_length(regexp_replace("ToLocationCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "FromLocationCode" text CHECK (char_length("FromLocationCode") + char_length(regexp_replace("FromLocationCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "CurrentLocationCode" text CHECK (char_length("CurrentLocationCode") + char_length(regexp_replace("CurrentLocationCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "LRCode" text CHECK (char_length("LRCode") + char_length(regexp_replace("LRCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "OrderNo" text CHECK (char_length("OrderNo") + char_length(regexp_replace("OrderNo", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "CreationDate" date CHECK ("CreationDate" BETWEEN DATE '0001-01-01' AND DATE '9999-12-31'),
 "GateOutDate" date CHECK ("GateOutDate" BETWEEN DATE '0001-01-01' AND DATE '9999-12-31'),
 "InTransitQty" integer,
 "TransporterCode" text CHECK (char_length("TransporterCode") + char_length(regexp_replace("TransporterCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "Remark" text,
 "ReportDate" date CHECK ("ReportDate" BETWEEN DATE '0001-01-01' AND DATE '9999-12-31'),
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER production_input BEFORE INSERT OR UPDATE OR DELETE ON mta_state.input_production_shipment FOR EACH ROW EXECUTE FUNCTION mta.guard_supplier_input_image();
CREATE TRIGGER production_input_truncate BEFORE TRUNCATE ON mta_state.input_production_shipment FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
CREATE TABLE mta_state.input_production_transporter (
 vf_run_id uuid NOT NULL REFERENCES mta.fresh_mta_calculationrun(id) ON DELETE RESTRICT,
 vf_image text NOT NULL, vf_ordinal bigint NOT NULL,
 "TransporterCode" text CHECK (char_length("TransporterCode") + char_length(regexp_replace("TransporterCode", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 50),
 "TransporterName" text CHECK (char_length("TransporterName") + char_length(regexp_replace("TransporterName", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 125),
 "TransporterContact" text CHECK (char_length("TransporterContact") + char_length(regexp_replace("TransporterContact", U&'[^\+010000-\+10FFFF]', '', 'g')) <= 20),
 PRIMARY KEY(vf_run_id,vf_image,vf_ordinal));
CREATE TRIGGER production_input BEFORE INSERT OR UPDATE OR DELETE ON mta_state.input_production_transporter FOR EACH ROW EXECUTE FUNCTION mta.guard_supplier_input_image();
CREATE TRIGGER production_input_truncate BEFORE TRUNCATE ON mta_state.input_production_transporter FOR EACH STATEMENT EXECUTE FUNCTION mta.deny_daily_source_mutation();
'''
REVERSE = '''
DROP TABLE mta_state.input_production_transporter;
DROP TABLE mta_state.input_production_shipment;
DROP TABLE mta_state.production_boroarequirement;
DROP TABLE mta_state.production_allocatedorders;
DROP TABLE mta_state.production_rrr_orderallocationhistory;
DROP TABLE mta_state.production_rrr_orderallocation;
DROP TABLE mta_state.production_bor_orderallocationhistory;
DROP TABLE mta_state.production_borwithorderallocation;
DROP FUNCTION mta.guard_production_report_image();'''

class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0124_native_inactive_current_guard')]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
