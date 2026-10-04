"""Apply allowlisted reporting migrations and restore fixture guards atomically."""
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from mta.presentation import fixture
from mta.serialization import digest


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument('--guided-history-index', action='store_true',
                            help='Apply only the additive Guided history date index after BTR migrations')

    def handle(self, *args, **options):
        if not fixture.enabled():
            raise CommandError('Use ordinary migrate for normal publications')
        before = fixture.binding()[1]
        seal = digest(fixture.freeze_state())
        target = ('0018_guided_history_date_index' if options['guided_history_index']
                  else '0017_btr_snapshot_scope_indexes')
        plan = MigrationExecutor(connection).migration_plan([('fresh_mta', target)])
        if any(backwards or migration.app_label != 'fresh_mta' or migration.name not in (
                '0013_btr_reporting_references', '0014_btr_reporting_immutability',
                '0015_btr_reporting_truncate_guard', '0016_btr_presentation_rows', '0017_btr_snapshot_scope_indexes',
                *(['0018_guided_history_date_index'] if options['guided_history_index'] else [])) for migration, backwards in plan):
            raise CommandError('Only allowlisted forward reporting migrations are allowed')
        with transaction.atomic():
            with connection.cursor() as cursor:
                for table in ('django_migrations', 'django_content_type'):
                    cursor.execute('ALTER TABLE mta.' + table + ' DISABLE TRIGGER stage2_immutable')
            call_command('migrate', 'fresh_mta', target,
                         interactive=False, stdout=self.stdout)
            with connection.cursor() as cursor:
                for table in ('django_migrations', 'django_content_type'):
                    cursor.execute('ALTER TABLE mta.' + table + ' ENABLE TRIGGER stage2_immutable')
            if fixture.binding()[1] != before or digest(fixture.freeze_state()) != seal:
                raise CommandError('Fixture admission or freeze changed; migration rolled back')
        self.stdout.write('Reporting migrations applied; fixture admission and source guards unchanged')
