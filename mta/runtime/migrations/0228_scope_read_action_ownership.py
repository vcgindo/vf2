"""Advance live DBM/remark cuts without rebuilding the accepted BPR graph.

The old generation revision remains build provenance.  Only an insert-only read
reference may advance the live cut, under the existing command/remark leases.
"""
from importlib import import_module
from django.db import migrations

prior = import_module('mta.runtime.migrations.0226_scoped_dbm_action_dependencies')
read = import_module('mta.runtime.migrations.0225_scope_read_configuration_alias')
read_original = import_module('mta.runtime.migrations.0218_scope_read_reference_guards')
parent = import_module('mta.runtime.migrations.0216_scope_expedite_parent_guards')
base = import_module('mta.runtime.migrations.0198_scope_report_guards')
remarks = import_module('mta.runtime.migrations.0220_scoped_remark_cache_writer')
exact = import_module('mta.runtime.migrations.0204_scoped_bpr_consumer_ownership').exact
GENERATIONS = prior.GENERATIONS
STAMP = prior.STAMP
PHASE_ROWS_BODY = prior.PHASE_ROWS_BODY
dependency = prior.dependency


def substitute(body, old, new, count=1):
    assert body.count(old) == count, old
    return body.replace(old, new)


# This invoker helper resolves identity only. It neither overrides the native
# action cut nor admits an old generation as a current standalone publication.
READ_REVISION = """
 SELECT coalesce(F.action_command_id,H.action_revision)
 FROM mta.fresh_mta_scopereadreference F
 JOIN mta.fresh_mta_scopereportgeneration H ON H.id=F.report_generation_id
 LEFT JOIN mta.fresh_mta_runcommand C ON C.id=F.action_command_id
 LEFT JOIN mta.fresh_mta_runphaseacceptance D ON D.id=C.phase_acceptance_id
 LEFT JOIN mta.fresh_mta_dailyphasesnapshot S ON S.id=D.snapshot_id
 JOIN mta.fresh_mta_runphaseacceptance B ON B.id=H.phase_id
 WHERE F.id=reference AND H.sealed AND B.phase='BPR' AND B.state_sealed
  AND (F.action_command_id IS NULL OR (C.state_sealed AND C.run_id=H.run_id
   AND D.run_id=H.run_id AND D.phase='DBM' AND D.state_sealed
   AND D.source_id=B.source_id AND S.parent_id=B.snapshot_id
   AND S.manifest->'references'->>'profile'=H.configuration_digest
   AND D.metadata#>>'{effects,parent_acceptance_digest}'=B.digest
   AND C.payload->>'operation' IN ('APPLY','SLEEP')))
"""

# A retained build revision is usable for a new parent only during a complete
# canonical fresh remark append from the exact current reference. All ordinary
# generation, row and ingestion paths retain their old current-revision guard.
REMARK_PARENT = """
DECLARE F mta.fresh_mta_scopereadreference; P mta.fresh_mta_scopeexpediteparentgeneration;
 H mta.fresh_mta_scopereportgeneration; R mta.fresh_mta_calculationrun;
 actor text; previous_highwater bigint; current_highwater bigint; fresh_count bigint; owner_role oid;
BEGIN
 actor=current_setting('fresh.daily_remark_actor',true);
 IF coalesce(actor,'')='' OR coalesce(current_setting('fresh.scope_remark_reference',true),'')=''
  OR coalesce(current_setting('fresh.scope_action_reference',true),'')<>'' THEN RETURN false; END IF;
 SELECT * INTO F FROM mta.fresh_mta_scopereadreference
  WHERE id=current_setting('fresh.scope_remark_reference',true)::uuid;
 SELECT * INTO P FROM mta.fresh_mta_scopeexpediteparentgeneration WHERE id=F.expedite_parent_generation_id;
 SELECT * INTO H FROM mta.fresh_mta_scopereportgeneration WHERE id=F.report_generation_id;
 SELECT * INTO R FROM mta.fresh_mta_calculationrun WHERE id=H.run_id;
 previous_highwater=(F.metadata#>>'{bpr,remarks,live_highwater}')::bigint;
 SELECT next_ordinal INTO current_highwater FROM mta.fresh_mta_remarkowner WHERE family='BPRReport_RemarkDetails';
 IF F.id IS NULL OR P.id IS NULL OR H.id IS NULL OR R.id IS NULL OR NOT H.sealed OR NOT P.sealed
  OR R.kind<>'DAILY_CHAIN' OR R.status NOT IN ('RUNNING','SUCCEEDED')
  OR P.core_generation_id IS DISTINCT FROM core OR P.action_revision IS DISTINCT FROM build_revision
  OR H.action_revision IS DISTINCT FROM build_revision OR P.run_id IS DISTINCT FROM R.id
  OR P.remark_highwater IS DISTINCT FROM previous_highwater
  OR previous_highwater IS NULL OR current_highwater IS NULL OR highwater IS DISTINCT FROM current_highwater
  OR highwater<=previous_highwater
  OR mta.scope_read_action_revision(F.id) IS DISTINCT FROM mta.scope_action_revision(R.id)
  OR EXISTS(SELECT 1 FROM mta.fresh_mta_runscopeattempt WHERE run_id=R.id AND status='ACTIVE') THEN RETURN false; END IF;
 -- The existing installer owns committed-prefix recovery; the application
 -- role must still prove a complete actor-owned append in this transaction.
 SELECT relowner INTO owner_role FROM pg_class WHERE oid='mta.fresh_mta_scopereadreference'::regclass;
 IF owner_role=(SELECT oid FROM pg_roles WHERE rolname=current_user) THEN RETURN true; END IF;
 SELECT count(*) INTO fresh_count FROM mta.fresh_mta_bprliveremark
  WHERE owner_id='BPRReport_RemarkDetails' AND ordinal>=previous_highwater AND ordinal<highwater
   AND append_transaction=pg_current_xact_id()::text AND actor_id=actor;
 RETURN fresh_count=highwater-previous_highwater;
END
"""

LEASE = substitute(prior.LEASE, 'C.scope_parent_revision IS DISTINCT FROM H.action_revision',
    'C.scope_parent_revision IS DISTINCT FROM mta.scope_read_action_revision(F.id)')
CACHE = prior.CACHE

_old_reference = """    WHERE G.id IS NULL OR G.run_id IS DISTINCT FROM C.run_id OR NOT """ + prior.dependency(
    'G.phase_id', 'C.phase_acceptance_id', 'C.run_id') + """
     OR G.action_revision IS DISTINCT FROM C.id OR N.pick_files_id IS DISTINCT FROM F.pick_files_id
     OR N.runtime_reports_digest IS DISTINCT FROM F.runtime_reports_digest
     OR N.metadata#>>'{bpr,remarks,live_highwater}' IS DISTINCT FROM highwater::text) INTO invalid;"""
_new_reference = """    WHERE G.id IS NULL OR G.run_id IS DISTINCT FROM C.run_id OR NOT """ + prior.dependency(
    'G.phase_id', 'C.phase_acceptance_id', 'C.run_id') + """
     OR (CASE WHEN N.metadata->>'schema'='fresh-bpr-read-reference-v2'
       AND (N.action_command_id IS NOT NULL OR N.previous_reference_id IS NOT NULL) THEN
       N.action_command_id IS DISTINCT FROM C.id OR N.previous_reference_id IS DISTINCT FROM F.id
       OR N.report_generation_id IS DISTINCT FROM F.report_generation_id
       OR N.git_generation_id IS DISTINCT FROM F.git_generation_id
       OR N.expedite_parent_generation_id IS DISTINCT FROM F.expedite_parent_generation_id
      ELSE G.action_revision IS DISTINCT FROM C.id END)
     OR N.pick_files_id IS DISTINCT FROM F.pick_files_id
     OR N.runtime_reports_digest IS DISTINCT FROM F.runtime_reports_digest
     OR N.metadata#>>'{bpr,remarks,live_highwater}' IS DISTINCT FROM highwater::text) INTO invalid;"""
REMARK_GUARD = substitute(prior.REMARK_GUARD, _old_reference, _new_reference)
REMARK_GUARD = substitute(REMARK_GUARD,
    'H.action_revision IS DISTINCT FROM mta.scope_action_revision(R.id)',
    'mta.scope_read_action_revision(F.id) IS DISTINCT FROM mta.scope_action_revision(R.id)')
REMARK_GUARD = substitute(REMARK_GUARD,
    'WHERE N.report_generation_id IS DISTINCT FROM F.report_generation_id',
    """WHERE (N.metadata->>'schema'='fresh-bpr-read-reference-v2' AND
      (N.action_command_id IS DISTINCT FROM F.action_command_id OR N.previous_reference_id IS DISTINCT FROM F.id))
    OR N.report_generation_id IS DISTINCT FROM F.report_generation_id""")

_parent_original = {name: parent.SQL.split('CREATE FUNCTION mta.' + name + '()', 1)[1]
    .split('AS $guard$', 1)[1].split('$guard$;', 1)[0]
    for name in ('guard_scope_expedite_parent_generation', 'guard_scope_expedite_parent_rows')}
PARENT_GENERATION = substitute(_parent_original['guard_scope_expedite_parent_generation'],
    'NEW.action_revision IS DISTINCT FROM mta.scope_action_revision(R.id)',
    """(NEW.action_revision IS DISTINCT FROM mta.scope_action_revision(R.id)
   AND NOT mta.scope_remark_parent_owner(NEW.core_generation_id,NEW.action_revision,NEW.remark_highwater))""")
PARENT_ROWS = substitute(_parent_original['guard_scope_expedite_parent_rows'],
    'G.action_revision=mta.scope_action_revision(R.id)',
    """(G.action_revision=mta.scope_action_revision(R.id)
      OR mta.scope_remark_parent_owner(G.core_generation_id,G.action_revision,G.remark_highwater))""")

# Existing nineteen dependency keys remain exact. Only the top live cut and the
# finite transition identify a successor; nested graph identities stay retained.
READ_REFERENCE = substitute(read.BODY,
    ' config_node jsonb; frozen jsonb; item text;',
    ' config_node jsonb; frozen jsonb; item text; PreviousReference mta.fresh_mta_scopereadreference;'
    ' ActionCommand mta.fresh_mta_runcommand; DbmPhase mta.fresh_mta_runphaseacceptance; transition jsonb;')
READ_REFERENCE = substitute(READ_REFERENCE,
    'H.action_revision IS DISTINCT FROM mta.scope_action_revision(R.id)',
    'coalesce(NEW.action_command_id,H.action_revision) IS DISTINCT FROM mta.scope_action_revision(R.id)')
READ_REFERENCE = substitute(READ_REFERENCE,
    '(SELECT count(*) FROM jsonb_object_keys(NEW.metadata))<>19',
    '(SELECT count(*) FROM jsonb_object_keys(NEW.metadata))<>20')
READ_REFERENCE = substitute(READ_REFERENCE,
    "OR NOT NEW.metadata ?& ARRAY[", "OR NOT NEW.metadata ?& ARRAY['transition',")
READ_REFERENCE = substitute(READ_REFERENCE,
    "'fresh-bpr-read-reference-v1'", "'fresh-bpr-read-reference-v2'")
READ_REFERENCE = substitute(READ_REFERENCE,
    "NEW.metadata->>'action_revision' IS DISTINCT FROM H.action_revision::text",
    "NEW.metadata->>'action_revision' IS DISTINCT FROM coalesce(NEW.action_command_id,H.action_revision)::text")
READ_REFERENCE = substitute(READ_REFERENCE,
    "OR NEW.metadata->'bpr'->>'report_digest' IS DISTINCT FROM H.digest",
    """OR NEW.metadata->'bpr'->>'report_digest' IS DISTINCT FROM H.digest
  OR NEW.metadata#>'{bpr,remarks}' IS DISTINCT FROM E.metadata#>'{occurrences,remarks}'""")

_transition = """
 transition=NEW.metadata->'transition';
 IF NEW.previous_reference_id IS NULL THEN
  IF NEW.action_command_id IS NOT NULL OR transition IS DISTINCT FROM 'null'::jsonb THEN
   RAISE EXCEPTION 'Base scope read reference cannot carry a transition'; END IF;
 ELSE
  SELECT * INTO F FROM mta.fresh_mta_scopereadreference WHERE id=NEW.previous_reference_id;
  IF F.id IS NULL OR F.id=NEW.id OR F.report_generation_id IS DISTINCT FROM NEW.report_generation_id
   OR F.git_generation_id IS DISTINCT FROM NEW.git_generation_id OR F.pick_files_id IS DISTINCT FROM NEW.pick_files_id
   OR F.runtime_reports_digest IS DISTINCT FROM NEW.runtime_reports_digest
   OR F.recipe_digest IS DISTINCT FROM NEW.recipe_digest
   OR jsonb_typeof(transition) IS DISTINCT FROM 'object'
   OR transition IS DISTINCT FROM jsonb_build_object('kind',transition->>'kind',
      'command_id',NEW.action_command_id,'previous_reference_id',F.id::text,'previous_reference_digest',F.digest) THEN
   RAISE EXCEPTION 'Scope read transition requires its exact retained predecessor'; END IF;
  IF transition->>'kind'='ACTION' THEN
   A=mta.scope_cache_command(F.id,current_setting('fresh.scope_action_actor',true));
   IF current_setting('fresh.scope_action_reference',true) IS DISTINCT FROM F.id::text
    OR NEW.action_command_id IS DISTINCT FROM A.id
    OR NEW.action_command_id IS NOT DISTINCT FROM F.action_command_id
    OR NEW.expedite_parent_generation_id IS DISTINCT FROM F.expedite_parent_generation_id
    OR (NEW.metadata-ARRAY['schema','recipe_digest','action_revision','transition']) IS DISTINCT FROM
       (F.metadata-ARRAY['schema','recipe_digest','action_revision','transition']) THEN
    RAISE EXCEPTION 'Scope action reference may advance only its live command'; END IF;
  ELSIF transition->>'kind'='REMARK' THEN
   IF NEW.action_command_id IS DISTINCT FROM F.action_command_id
    OR current_setting('fresh.scope_remark_reference',true) IS DISTINCT FROM F.id::text
    OR NOT mta.scope_remark_parent_owner(E.core_generation_id,E.action_revision,E.remark_highwater)
    OR (((NEW.metadata-ARRAY['schema','recipe_digest','action_revision','transition']) #- '{bpr,remarks}')
        #- '{expedite,parent_generation_id}' #- '{expedite,parent_digest}') IS DISTINCT FROM
       (((F.metadata-ARRAY['schema','recipe_digest','action_revision','transition']) #- '{bpr,remarks}')
        #- '{expedite,parent_generation_id}' #- '{expedite,parent_digest}') THEN
    RAISE EXCEPTION 'Scope remark reference may advance only its dependent parent'; END IF;
  ELSE RAISE EXCEPTION 'Unknown scope read transition'; END IF;
 END IF;
 IF NEW.action_command_id IS NOT NULL THEN
  SELECT * INTO A FROM mta.fresh_mta_runcommand WHERE id=NEW.action_command_id;
  SELECT * INTO D FROM mta.fresh_mta_runphaseacceptance WHERE id=A.phase_acceptance_id;
  IF A.id IS NULL OR NOT A.state_sealed OR A.run_id IS DISTINCT FROM R.id
   OR A.payload->>'operation' NOT IN ('APPLY','SLEEP') OR coalesce(A.payload->>'actor','')=''
   OR D.id IS NULL OR D.phase<>'DBM' OR NOT D.state_sealed
   OR (SELECT manifest->'references'->>'profile' FROM mta.fresh_mta_dailyphasesnapshot WHERE id=D.snapshot_id)
      IS DISTINCT FROM H.configuration_digest
   OR NOT """ + prior.dependency('P.id', 'D.id', 'R.id') + """ THEN
   RAISE EXCEPTION 'Scope read live command requires its exact accepted DBM descendant'; END IF;
 END IF;
"""
_transition = _transition.replace('F.', 'PreviousReference.').replace('INTO F FROM', 'INTO PreviousReference FROM')
_transition = (_transition.replace('A.', 'ActionCommand.').replace('D.', 'DbmPhase.')
    .replace('INTO A FROM', 'INTO ActionCommand FROM').replace('INTO D FROM', 'INTO DbmPhase FROM')
    .replace('A=mta.scope_cache_command', 'ActionCommand=mta.scope_cache_command'))
READ_REFERENCE = substitute(READ_REFERENCE, ' RETURN NEW;', _transition + ' RETURN NEW;')

# Retained v1 inserts preserve their original checks and cannot populate the new
# FKs. This branch is kept separate from all v2 transition authorization.
READ_REFERENCE = substitute(READ_REFERENCE, 'BEGIN\n', """BEGIN
 IF NEW.metadata->>'schema'='fresh-bpr-read-reference-v1' THEN
  IF NEW.action_command_id IS NOT NULL OR NEW.previous_reference_id IS NOT NULL THEN
   RAISE EXCEPTION 'Legacy scope reference cannot carry live transition fields'; END IF;
""" + read.BODY.split('BEGIN\n', 1)[1].rsplit('END', 1)[0] + "\n END IF;\n", 1)
BODY = READ_REFERENCE

OLD = import_module('mta.runtime.migrations.0223_bpr_history_completion').NEW
_valid_reference = substitute(base.VALID.replace('G.', 'H.'),
    'H.action_revision IS DISTINCT FROM mta.scope_action_revision(R.id)',
    'coalesce(G.action_command_id,H.action_revision) IS DISTINCT FROM mta.scope_action_revision(R.id)')
_reference_added = substitute(read_original.ADDED,
    base.VALID.replace('G.', 'H.'), _valid_reference)
_parent_valid = substitute(base.VALID,
    'G.action_revision IS DISTINCT FROM mta.scope_action_revision(R.id)',
    """(G.action_revision IS DISTINCT FROM mta.scope_action_revision(R.id)
 AND NOT mta.scope_remark_parent_owner(G.core_generation_id,G.action_revision,G.remark_highwater))""")
_parent_added = substitute(parent.ADDED, base.VALID, _parent_valid, 2)
NEW = substitute(substitute(OLD, read_original.ADDED, _reference_added), parent.ADDED, _parent_added)

FUNCTIONS = {
    'scope_read_action_revision(reference uuid)': ('bigint', 'sql STABLE', READ_REVISION),
    'scope_remark_parent_owner(core uuid, build_revision bigint, highwater bigint)': ('boolean', 'plpgsql', REMARK_PARENT),
}


def signature(declaration):
    name, arguments = declaration.split('(', 1)
    return name + '(' + ','.join(arg.strip().split()[-1] for arg in arguments[:-1].split(',') if arg.strip()) + ')'


SQL = ''
for declaration, (result, language, body) in FUNCTIONS.items():
    SQL += ('CREATE FUNCTION mta.' + declaration + ' RETURNS ' + result + ' LANGUAGE ' + language
        + ' SET search_path=pg_catalog,mta AS $body$' + body + '$body$;\n'
        + 'REVOKE ALL ON FUNCTION mta.' + signature(declaration) + ' FROM PUBLIC;\n')
REPLACEMENTS = (
    ('scope_cache_command(reference uuid,actor text)', 'mta.fresh_mta_runcommand', prior.LEASE, LEASE),
    ('guard_scoped_remark_cache_writer()', 'trigger', prior.REMARK_GUARD, REMARK_GUARD),
    ('guard_scope_read_reference()', 'trigger', read.BODY, READ_REFERENCE),
    ('guard_scope_expedite_parent_generation()', 'trigger', _parent_original['guard_scope_expedite_parent_generation'], PARENT_GENERATION),
    ('guard_scope_expedite_parent_rows()', 'trigger', _parent_original['guard_scope_expedite_parent_rows'], PARENT_ROWS),
)
for declaration, result, before, after in REPLACEMENTS:
    SQL += exact(signature(declaration), before)
    SQL += ('CREATE OR REPLACE FUNCTION mta.' + declaration + ' RETURNS ' + result
        + ' LANGUAGE plpgsql SET search_path=pg_catalog,mta AS $body$' + after + '$body$;\n')
SQL += base.transition(OLD, NEW)

REVERSE = """DO $pre$ BEGIN
 IF EXISTS(SELECT 1 FROM mta.fresh_mta_scopereadreference
  WHERE action_command_id IS NOT NULL OR previous_reference_id IS NOT NULL
   OR metadata->>'schema'='fresh-bpr-read-reference-v2')
  OR to_regclass('fresh_control.application_capability') IS NOT NULL THEN
  RAISE EXCEPTION 'Retained live references or application capability require a compatible forward release'; END IF;
END $pre$;
""" + base.transition(NEW, OLD)
for declaration, result, before, after in reversed(REPLACEMENTS):
    REVERSE += exact(signature(declaration), after)
    REVERSE += ('CREATE OR REPLACE FUNCTION mta.' + declaration + ' RETURNS ' + result
        + ' LANGUAGE plpgsql SET search_path=pg_catalog,mta AS $body$' + before + '$body$;\n')
for declaration in reversed(FUNCTIONS):
    REVERSE += 'DROP FUNCTION mta.' + signature(declaration) + ';\n'


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0227_scope_read_action_reference')]
    operations = [migrations.RunSQL(SQL, REVERSE)]
