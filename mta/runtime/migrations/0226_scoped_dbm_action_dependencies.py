"""Permit a DBM command to refresh only its exact BPR-parent dependencies."""
from importlib import import_module
from django.db import migrations

prior = import_module('mta.runtime.migrations.0221_scoped_action_cache_writer')
GENERATIONS = prior.GENERATIONS
STAMP = prior.STAMP
PHASE_ROWS_BODY = prior.PHASE_ROWS_BODY


def dependency(reference_phase, command_phase, run):
    # The command is independently checked by actionable_scope_phase. This
    # predicate grants no new phase, revision, transaction or actor capability.
    return f"""({reference_phase}={command_phase} OR EXISTS(
     SELECT 1 FROM mta.fresh_mta_runphaseacceptance DependencyBpr
     JOIN mta.fresh_mta_runphaseacceptance DependencyDbm
      ON DependencyDbm.run_id=DependencyBpr.run_id
     JOIN mta.fresh_mta_dailyphasesnapshot DependencySnapshot
      ON DependencySnapshot.id=DependencyDbm.snapshot_id
     WHERE DependencyBpr.id={reference_phase} AND DependencyDbm.id={command_phase}
      AND DependencyBpr.run_id={run} AND DependencyBpr.phase='BPR' AND DependencyBpr.state_sealed
      AND DependencyDbm.phase='DBM' AND DependencyDbm.state_sealed
      AND DependencySnapshot.parent_id=DependencyBpr.snapshot_id
      AND DependencyDbm.source_id=DependencyBpr.source_id
      AND DependencyDbm.metadata#>>'{{effects,parent_acceptance_digest}}'=DependencyBpr.digest))"""


def substitute(body, old, new, count=1):
    assert body.count(old) == count, old
    return body.replace(old,new)


LEASE = substitute(prior.LEASE,'C.phase_acceptance_id IS DISTINCT FROM H.phase_id',
    'NOT '+dependency('H.phase_id','C.phase_acceptance_id','C.run_id'))
LEASE = substitute(LEASE,'mta.actionable_scope_phase(R.id,H.phase_id)',
    'mta.actionable_scope_phase(R.id,C.phase_acceptance_id)')
CACHE = prior.CACHE
for reference in ('H.phase_id','NEW.phase_id'):
    CACHE = substitute(CACHE,reference+' IS DISTINCT FROM C.phase_acceptance_id',
        'NOT '+dependency(reference,'C.phase_acceptance_id','C.run_id'))
REMARK_GUARD = prior.REMARK_GUARD
for reference,count in (('N.phase_id',1),('G.phase_id',2)):
    REMARK_GUARD = substitute(REMARK_GUARD,reference+' IS DISTINCT FROM C.phase_acceptance_id',
        'NOT '+dependency(reference,'C.phase_acceptance_id','C.run_id'),count)

exact = import_module('mta.runtime.migrations.0204_scoped_bpr_consumer_ownership').exact
SQL = ''
for signature,result,before,after in (
    ('scope_cache_command(reference uuid,actor text)','mta.fresh_mta_runcommand',prior.LEASE,LEASE),
    ('guard_scoped_action_cache()','trigger',prior.CACHE,CACHE),
    ('guard_scoped_remark_cache_writer()','trigger',prior.REMARK_GUARD,REMARK_GUARD)):
    SQL += exact(signature.replace('reference uuid,actor text','uuid,text'),before)
    SQL += ('CREATE OR REPLACE FUNCTION mta.'+signature+' RETURNS '+result+
        ' LANGUAGE plpgsql SET search_path=pg_catalog,mta AS $body$'+after+'$body$;\n')


class Migration(migrations.Migration):
    dependencies = [('fresh_mta','0225_scope_read_configuration_alias')]
    operations = [migrations.RunSQL(SQL)]
