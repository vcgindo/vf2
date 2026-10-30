"""Admit the shipped field policy at capture, outside immutable source facts."""
from mta.application.occurrence_text_policy import KEY, binding, owner_for, verify_owner


def admit(run, configuration_digest):
    from release.native_identity import require_current
    return binding(owner_for(run, configuration_digest, require_current()['source_commit']))


def context(run):
    captured = run.production_manifest.get('ingestion_preparation', {})
    value = run.production_manifest.get(KEY, captured.get(KEY))
    if value is None:
        raise ValueError('Captured occurrence availability admission missing')
    if captured and captured.get(KEY) != value:
        raise ValueError('Captured occurrence availability receipt differs')
    verify_owner(value, run, captured.get('configuration_digest',value['owner']['configuration_digest']))
    return {KEY: value}


def admitted(run):
    return (KEY in run.production_manifest
            or KEY in run.production_manifest.get('ingestion_preparation',{}))


def verify_phase(run, phase):
    if (KEY not in run.production_manifest
            and KEY not in run.production_manifest.get('ingestion_preparation',{})):
        if (phase.context.report_exceptions or {}).get(KEY) is not None:
            raise ValueError('Accepted phase occurrence availability admission missing')
        return  # Pre-policy accepted phases retain their original strict contract.
    if phase.context.report_exceptions != context(run):
        raise ValueError('Accepted phase occurrence availability binding differs')


def verify_output(run, lineage, configuration_digest, admitted, reports=None):
    value = (lineage or [{}])[0].get(KEY)
    if value != admitted:
        raise ValueError('Occurrence availability admission/output binding differs')
    if value is not None:
        verify_owner(value, run, configuration_digest)
        from mta.application.occurrence_text_policy import summaries
        if reports is None or (lineage or [{}])[0].get('occurrence_text_availability') != summaries(reports,value):
            raise ValueError('Occurrence availability affected-group metadata differs')
    elif 'occurrence_text_availability' in (lineage or [{}])[0]:
        raise ValueError('Occurrence availability metadata has no admitted policy')
