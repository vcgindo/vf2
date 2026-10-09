"""Master6 uses the existing source-wide decision lock and retry fence."""
from django.db.models import F
from mta.runtime.mdm_stop_pipo_models import MdmStopPipoTaskRevision


def bump_task(source, master_id, task_id):
    if int(master_id) != 6:
        raise ValueError('StopPIPO master required')
    row, _ = MdmStopPipoTaskRevision.objects.get_or_create(source=source, task_id=task_id)
    MdmStopPipoTaskRevision.objects.filter(pk=row.pk).update(revision=F('revision') + 1)


def task_revisions(source):
    return list(MdmStopPipoTaskRevision.objects.filter(source=source)
        .order_by('task_id').values('task_id', 'revision'))


def superseded_tasks(snapshot):
    if 'stop_pipo' not in snapshot:
        return set()
    frozen = {r['task_id']: r['revision'] for r in snapshot['stop_pipo']['task_revisions']}
    live = {r['task_id']: r['revision'] for r in task_revisions(snapshot['source_id'])}
    if any(live.get(k, -1) < v for k, v in frozen.items()):
        raise ValueError('StopPIPO task revision regressed or disappeared')
    return {(6, k) for k, v in live.items() if v > frozen.get(k, 0)}
