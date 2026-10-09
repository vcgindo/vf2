"""Seasonality decisions share the existing source-wide lock and retry fence."""
from django.db.models import F
from mta.runtime.mdm_season_models import MdmSeasonTaskRevision


def bump_task(source, master_id, task_id):
    token, _ = MdmSeasonTaskRevision.objects.get_or_create(
        source=source, master_id=master_id, task_id=task_id)
    MdmSeasonTaskRevision.objects.filter(pk=token.pk).update(revision=F('revision') + 1)


def task_revisions(source):
    return list(MdmSeasonTaskRevision.objects.filter(source=source)
        .order_by('master_id', 'task_id').values('master_id', 'task_id', 'revision'))


def superseded_tasks(snapshot):
    if 'season' not in snapshot:
        return set()
    frozen = {(r['master_id'], r['task_id']): r['revision']
              for r in snapshot['season']['task_revisions']}
    live = {(r['master_id'], r['task_id']): r['revision']
            for r in task_revisions(snapshot['source_id'])}
    if any(live.get(k, -1) < v for k, v in frozen.items()):
        raise ValueError('Seasonality task revision regressed or disappeared')
    return {k for k, v in live.items() if v > frozen.get(k, 0)}
