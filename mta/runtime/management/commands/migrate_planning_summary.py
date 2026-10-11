"""Apply only the additive Planning summary migration on its serving branch."""
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--plan', action='store_true')

    def handle(self, *args, **options):
        from mta.presentation import fixture
        before=fixture.binding()[1] if fixture.enabled() else None
        executor=MigrationExecutor(connection)
        target=('fresh_mta','0115_planning_summary_constraints')
        plan=executor.migration_plan([target])
        if any(backwards or (m.app_label!='fresh_mta' or m.name not in ('0114_planning_summary','0115_planning_summary_constraints')) for m,backwards in plan):
            raise CommandError('Planning summary requires the applied 0112 serving foundation')
        self.stdout.write(str([(m.app_label,m.name,backwards) for m,backwards in plan]))
        if options['plan']:
            return
        with transaction.atomic():
            if before:
                with connection.cursor() as c:
                    c.execute('ALTER TABLE mta.django_migrations DISABLE TRIGGER stage2_immutable')
            executor.migrate([target])
            if before:
                with connection.cursor() as c:
                    c.execute('ALTER TABLE mta.django_migrations ENABLE TRIGGER stage2_immutable')
            if before and fixture.binding()[1]!=before:
                raise CommandError('Fixture binding changed during additive schema migration')
