"""Admit only registered generic-policy reads on the real owned namespace.

Custom guard SQL has no Django model-state equivalent. Old serialized requests
retain their original prefix predicate and all common graph/action checks.
"""
from importlib import import_module
from django.db import migrations

prior = import_module('mta.runtime.migrations.0238_registered_read_action_cut')
OLD = prior.BODY
DECLARATION = ' generic_reference jsonb; generic_policy jsonb; generic_allowed boolean := false;'
declaration_marker = ' outer_node jsonb; binding_node jsonb; registered_binding jsonb;'
assert OLD.count(declaration_marker) == 1
BODY = OLD.replace(declaration_marker, declaration_marker + DECLARATION, 1)

# 0228 kept an independent early v1 body. Extend only the current body, before
# its inherited database-name guard. Captured bytes, never caller metadata,
# supply the new policy; typed registration and physical namespace own admission.
MARKER = ' -- The new native entry uses its physical V2/V3 scope request.'
assert BODY.count(MARKER) == 2
ADMISSION = r'''
 IF NEW.metadata#>>'{runtime_reports,schema}'='fresh-registered-placement-read-configuration-v1' THEN
  SELECT jsonb_object_agg(F.value->>0,F.value->1->'scalar') INTO generic_reference
    FROM jsonb_array_elements(R.input_payload#>'{tree,object}') Q(value)
    CROSS JOIN LATERAL jsonb_array_elements(Q.value->1->'object') T(value)
    CROSS JOIN LATERAL jsonb_array_elements(T.value->1->'object') F(value)
    WHERE Q.value->>0='scope_request' AND T.value->>0='runtime_reports';
  IF generic_reference->>'purpose'='production-generic-placement'
    AND generic_reference->>'schema'='fresh-owned-report-placement-reference-v1' THEN
   generic_policy=(generic_reference->>'disposition_json')::jsonb;
   IF jsonb_typeof(generic_policy)='object'
    AND (SELECT count(*) FROM jsonb_object_keys(generic_policy))=6
    AND generic_policy->>'schema'='vectorflow-production-generic-scope-policy-v1'
    AND generic_policy->>'purpose'='production-generic-scoped'
    AND generic_policy->>'input_download'='enabled-five-file-four-table-archive'
    AND length(btrim(generic_policy->>'site_code')) BETWEEN 1 AND 100
    AND length(btrim(generic_policy->>'authority')) BETWEEN 1 AND 1000
    AND generic_policy->'hooks'='{"PostBPR":"client-processing-not-selected",
      "PreDBM":"client-processing-not-selected","PostDBM":"client-processing-not-selected",
      "PostBTR":"client-processing-not-selected","SiteFinal":"client-processing-not-selected"}'::jsonb
    AND EXISTS(SELECT 1 FROM fresh_control.owned_namespace N
      WHERE N.singleton AND N.database_name=current_database()
       AND N.database_oid=(SELECT oid FROM pg_database WHERE datname=current_database())
       AND N.owner_oid=(SELECT oid FROM pg_roles WHERE rolname=current_user)
       AND N.issuer_oid=(SELECT oid FROM pg_roles WHERE rolname=session_user))
    AND EXISTS(SELECT 1 FROM mta.fresh_mta_reportdefinitionregistration D
      JOIN mta.fresh_mta_productioninitialization I ON I.id=D.initialization_id
      WHERE I.source_id=P.source_id
       AND D.configuration_digest=generic_reference->>'configuration_digest'
       AND D.policy=jsonb_build_object('hook_json',generic_reference->>'hook_json',
         'disposition_json',generic_reference->>'disposition_json',
         'catalogue_anchor_json',generic_reference->>'catalogue_anchor_json',
         'authority_sha256',generic_reference->>'authority_sha256')) THEN
    generic_allowed=true;
   END IF;
  END IF;
 END IF;
'''
prefix, suffix = BODY.rsplit(MARKER, 1)
PREDICATE = "left(lower(current_database()),13)<>'vftest_fresh_'"
assert prefix.count(PREDICATE) == 1 and suffix.count(PREDICATE) == 1
suffix = suffix.replace(PREDICATE, '(' + PREDICATE + ' AND NOT generic_allowed)', 1)
BODY = prefix + ADMISSION + MARKER + suffix
SQL = prior.replace_read(OLD, BODY)
REVERSE = r'''DO $stop$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_reportdefinitionregistration
   WHERE (policy->>'disposition_json')::jsonb->>'schema'='vectorflow-production-generic-scope-policy-v1') THEN
  RAISE EXCEPTION 'Generic production registrations require a compatible forward release';
 END IF;
END $stop$;
''' + prior.replace_read(BODY, OLD)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0238_registered_read_action_cut')]
    operations = [migrations.RunSQL(SQL, REVERSE)]
