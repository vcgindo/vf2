"""Offline writer adapter over the ordinary daily service, not another engine."""
from mta.runtime.temporal import execute_day as _execute_day
from development.validation_storage import persist_trace


def execute_day(**kwargs):
    if kwargs.get('evidence_mode', 'validation') == 'validation':
        kwargs['checkpoint_writer'] = persist_trace
    return _execute_day(**kwargs)
