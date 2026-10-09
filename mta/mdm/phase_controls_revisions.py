"""Shared source lock with separate master7/8/9 task revision fences."""
from django.db.models import F
from mta.runtime.mdm_phase_controls_models import MdmPhaseControlsTaskRevision


def bump_task(source, master_id, task_id):
    if int(master_id) not in (7, 8, 9):
        raise ValueError('Phase control master required')
    row, _ = MdmPhaseControlsTaskRevision.objects.get_or_create(
        source=source, master_id=int(master_id), task_id=task_id)
    MdmPhaseControlsTaskRevision.objects.filter(pk=row.pk).update(revision=F('revision') + 1)


def task_revisions(source):
    return list(MdmPhaseControlsTaskRevision.objects.filter(source=source)
        .order_by('master_id', 'task_id').values('master_id', 'task_id', 'revision'))


def superseded_tasks(snapshot):
    if 'phase_controls' not in snapshot:
        return set()
    frozen = {(r['master_id'], r['task_id']): r['revision']
              for r in snapshot['phase_controls']['task_revisions']}
    live = {(r['master_id'], r['task_id']): r['revision']
            for r in task_revisions(snapshot['source_id'])}
    if any(live.get(k, -1) < v for k, v in frozen.items()):
        raise ValueError('Phase control task revision regressed or disappeared')
    return {k for k, v in live.items() if v > frozen.get(k, 0)}
