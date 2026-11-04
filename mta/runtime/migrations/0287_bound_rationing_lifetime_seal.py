"""Check the new cut's lifetime membership with one pass per ordinal set."""
from importlib import import_module

from django.db import migrations


prior = import_module('mta.runtime.migrations.0256_preserve_rationing_source_order')
original = """EXISTS(SELECT 1 FROM mta_state.rationing_fact F LEFT JOIN mta_state.rationing_lifetime L
    ON L.fact_cut_id=F.cut_id AND L.original_ordinal=F.vf_ordinal WHERE F.cut_id=c.id AND L.fact_cut_id IS NULL)"""
# Both ordinals are non-null and unique within a cut. Under stale statistics
# the old anti join could rescan all lifetime rows for each fact in a new cut.
replacement = """EXISTS(SELECT vf_ordinal FROM mta_state.rationing_fact WHERE cut_id=c.id
    EXCEPT SELECT original_ordinal FROM mta_state.rationing_lifetime WHERE fact_cut_id=c.id)"""
assert prior.SQL.count(original) == 1
SQL = prior.SQL.replace(original, replacement)


class Migration(migrations.Migration):
    dependencies = [('fresh_mta', '0286_btr_anchor_pair_lookup')]
    operations = [migrations.RunSQL(
        prior.exact(prior.SIGNATURE, prior.SQL.split('$$')[1]) + SQL,
        prior.exact(prior.SIGNATURE, SQL.split('$$')[1]) + prior.SQL,
    )]
