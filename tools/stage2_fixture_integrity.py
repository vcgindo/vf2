"""Focused isolated fixture integrity/denial proof; no business action call."""
import os
from tools.stage2_vm_contract import atomic
from tools.stage2_vm_load import DATA,DB


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','vectorflow.settings')
    import django
    django.setup()
    from django.db import connection,transaction,DatabaseError
    from django.test import override_settings
    from mta.presentation import fixture
    from mta.presentation.context import PublicationUnavailable
    if connection.settings_dict['NAME']!=DB:raise ValueError('Wrong fixture database')
    run,before=fixture.binding()
    blocked=False
    try:
        with transaction.atomic():
            with connection.cursor() as cur:
                # No row would change even if the trigger were missing.
                cur.execute('UPDATE '+connection.ops.quote_name(run._meta.db_table)+' SET status=status WHERE FALSE')
    except DatabaseError as exc:
        if 'immutable Stage2 legacy fixture' not in str(exc):raise
        blocked=True
    if not blocked:raise ValueError('Fixture mutation guard did not fire')
    denials=[]
    for overrides in (dict(VF_MTA_FIXTURE_SHA256='0'*64),dict(VF_MTA_PUBLISHED_RUN=str(run.pk))):
        with override_settings(**overrides):
            try:fixture.binding()
            except PublicationUnavailable as exc:denials.append(str(exc))
            else:raise ValueError('Invalid fixture selection was admitted')
    _,after=fixture.binding()
    if before!=after:raise ValueError('Integrity probe changed dataset identity')
    atomic(DATA/'fixture-integrity.json',dict(status='PASS',admission_digest=before,immutable_zero_row_statement_denied=blocked,
        invalid_selection_denials=denials,run_id=str(run.pk),engine_action_calls=0))
    print('Fixture mutation/selection guards passed; identity unchanged')


if __name__=='__main__':main()
