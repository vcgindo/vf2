"""Master13 decision generations using the existing source-wide advisory lock."""
from django.db.models import F
from mta.runtime.mdm_force_models import MdmForceTaskRevision


def bump_task(source, task_id):
    token, _ = MdmForceTaskRevision.objects.get_or_create(source=source, task_id=task_id)
    MdmForceTaskRevision.objects.filter(pk=token.pk).update(revision=F('revision') + 1)


def task_revisions(source):
    return list(MdmForceTaskRevision.objects.filter(source=source).order_by('id')
                .values('task_id', 'revision'))


def superseded_tasks(snapshot):
    if 'force' not in snapshot:
        return set()
    frozen = {r['task_id']: r['revision'] for r in snapshot['force']['task_revisions']}
    current = dict(MdmForceTaskRevision.objects.filter(source_id=snapshot['source_id'])
                   .values_list('task_id', 'revision'))
    if any(current.get(task_id, -1) < revision for task_id, revision in frozen.items()):
        raise ValueError('Force task revision regressed or disappeared')
    return {(13, task_id) for task_id, revision in current.items()
            if revision > frozen.get(task_id, 0)}
