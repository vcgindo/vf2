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
        parser.add_argument('--bpr-preparation', action='store_true',
                            help='Apply the additive typed BPR candidate relation and seals')
        parser.add_argument('--guided-history-index', action='store_true',
                            help='Apply only the additive Guided history date index after BTR migrations')
        parser.add_argument('--guided-preparation', action='store_true',
                            help='Apply the additive sealed Guided DBM and Chronic grid relations')
        parser.add_argument('--guided-history-preparation', action='store_true',
                            help='Apply the additive sealed Guided history occurrence relations')
        parser.add_argument('--planning-sources', action='store_true',
                            help='Apply only the two additive Planning source masters after Guided history')
        parser.add_argument('--planning-charts', action='store_true',
                            help='Apply only Planning chart ingredients after normal grids')
        parser.add_argument('--planning-grids', action='store_true',
                            help='Apply only the normal Planning grid occurrences after source masters')

    def handle(self, *args, **options):
        if not fixture.enabled():
            raise CommandError('Use ordinary migrate for normal publications')
        before = fixture.binding()[1]
        seal = digest(fixture.freeze_state())
        target = ('0029_planning_chart_ingredients' if options['planning_charts'] else
                  '0028_planning_normal_grid_occurrences' if options['planning_grids'] else
                  '0027_planning_derived_sources' if options['planning_sources'] else
                  '0026_guided_history_covering_index' if options['guided_history_preparation'] else
                  '0022_guided_chronic_prepared_candidates' if options['guided_preparation'] else
                  '0020_bpr_prepared_seals' if options['bpr_preparation'] else
                  '0018_guided_history_date_index' if options['guided_history_index']
                  else '0017_btr_snapshot_scope_indexes')
        plan = MigrationExecutor(connection).migration_plan([('fresh_mta', target)])
        if options['planning_charts'] and any(backwards or migration.app_label != 'fresh_mta'
                or migration.name != '0029_planning_chart_ingredients' for migration, backwards in plan):
            raise CommandError('Planning charts require the normal-grid baseline')
        if options['planning_grids'] and any(backwards or migration.app_label != 'fresh_mta'
                or migration.name != '0028_planning_normal_grid_occurrences' for migration, backwards in plan):
            raise CommandError('Planning grids require the prepared source baseline')
        if options['planning_sources'] and any(backwards or migration.app_label != 'fresh_mta'
                or migration.name != '0027_planning_derived_sources' for migration, backwards in plan):
            raise CommandError('Planning source migration requires the existing Guided history baseline')
        if any(backwards or migration.app_label != 'fresh_mta' or migration.name not in (
                '0013_btr_reporting_references', '0014_btr_reporting_immutability',
                '0015_btr_reporting_truncate_guard', '0016_btr_presentation_rows', '0017_btr_snapshot_scope_indexes',
                *(['0027_planning_derived_sources'] if options['planning_sources'] else []),
                *(['0029_planning_chart_ingredients'] if options['planning_charts'] else []),
                *(['0028_planning_normal_grid_occurrences'] if options['planning_grids'] else []),
                *(['0018_guided_history_date_index'] if options['guided_history_index'] or options['bpr_preparation'] or options['guided_preparation'] or options['guided_history_preparation'] else []),
                *(['0019_bpr_prepared_candidates', '0020_bpr_prepared_seals']
                  if options['bpr_preparation'] or options['guided_preparation'] or options['guided_history_preparation'] else []),
                *(['0021_guided_dbm_prepared_candidates']
                  if options['guided_preparation'] or options['guided_history_preparation'] else []),
                *(['0022_guided_chronic_prepared_candidates']
                  if options['guided_preparation'] or options['guided_history_preparation'] else []),
                *(['0023_guided_history_prepared_occurrences']
                  if options['guided_history_preparation'] else []),
                *(['0024_guided_history_receipt_verification']
                  if options['guided_history_preparation'] else []),
                *(['0025_guided_history_statement_guard']
                  if options['guided_history_preparation'] else []),
                *(['0026_guided_history_covering_index']
                  if options['guided_history_preparation'] else [])) for migration, backwards in plan):
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
