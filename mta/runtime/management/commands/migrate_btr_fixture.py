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
        parser.add_argument('--boroa-snapshot', action='store_true',
                            help='Apply only additive BOR-OA source, live history and prepared relations after 0045')
        parser.add_argument('--bor-snapshot', action='store_true',
                            help='Apply only additive BOR snapshot, live history and prepared relations after 0042')
        parser.add_argument('--research-critical-path', action='store_true',
                            help='Apply only Research bands, count and modal indexes after 0039')
        parser.add_argument('--research-availability-index', action='store_true',
                            help='Apply only the narrow Research availability covering index')
        parser.add_argument('--history-report-preparation', action='store_true',
                            help='Apply only additive Research/Buffer memberships after RRR')
        parser.add_argument('--rrr-preparation', action='store_true',
                            help='Apply only the additive sealed RRR membership after Planning')
        parser.add_argument('--planning-excess-index', action='store_true',
                            help='Apply only the Excess run/date covering index after Planning charts')
        parser.add_argument('--planning-expedite-charts', action='store_true',
                            help='Apply only Expedite chart ingredients after custom references')
        parser.add_argument('--planning-expedite-custom', action='store_true',
                            help='Apply only custom Expedite references after transit ingredients')
        parser.add_argument('--planning-expedite-transit', action='store_true',
                            help='Apply only parent Expedite nested transit ingredients after grid occurrences')
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
        parser.add_argument('--planning-expedite-grids', action='store_true',
                            help='Apply only Expedite grid occurrences after GIT')
        parser.add_argument('--planning-git', action='store_true',
                            help='Apply only GIT occurrences after custom grids')
        parser.add_argument('--planning-custom', action='store_true',
                            help='Apply only Planning custom occurrences after chart ingredients')
        parser.add_argument('--planning-charts', action='store_true',
                            help='Apply only Planning chart ingredients after normal grids')
        parser.add_argument('--planning-grids', action='store_true',
                            help='Apply only the normal Planning grid occurrences after source masters')

    def handle(self, *args, **options):
        if not fixture.enabled():
            raise CommandError('Use ordinary migrate for normal publications')
        before = fixture.binding()[1]
        seal = digest(fixture.freeze_state())
        target = ('0047_boroa_guards' if options['boroa_snapshot'] else
                  '0045_bor_prepared_guards' if options['bor_snapshot'] else
                  '0042_research_norm_history_index' if options['research_critical_path'] else
                  '0039_research_availability_cover' if options['research_availability_index'] else
                  '0038_history_prepared_memberships' if options['history_report_preparation'] else
                  '0037_rrr_prepared_membership' if options['rrr_preparation'] else
                  '0036_planning_excess_date_index' if options['planning_excess_index'] else
                  '0035_planning_expedite_charts' if options['planning_expedite_charts'] else
                  '0034_planning_expedite_custom' if options['planning_expedite_custom'] else
                  '0033_planning_expedite_transit' if options['planning_expedite_transit'] else
                  '0032_planning_expedite_grid_occurrences' if options['planning_expedite_grids'] else
                  '0031_planning_git_occurrences' if options['planning_git'] else
                  '0030_planning_custom_occurrences' if options['planning_custom'] else
                  '0029_planning_chart_ingredients' if options['planning_charts'] else
                  '0028_planning_normal_grid_occurrences' if options['planning_grids'] else
                  '0027_planning_derived_sources' if options['planning_sources'] else
                  '0026_guided_history_covering_index' if options['guided_history_preparation'] else
                  '0022_guided_chronic_prepared_candidates' if options['guided_preparation'] else
                  '0020_bpr_prepared_seals' if options['bpr_preparation'] else
                  '0018_guided_history_date_index' if options['guided_history_index']
                  else '0017_btr_snapshot_scope_indexes')
        plan = MigrationExecutor(connection).migration_plan([('fresh_mta', target)])
        if options['boroa_snapshot'] and any(backwards or migration.app_label != 'fresh_mta'
                or migration.name not in ('0046_boroa_snapshot_and_prepared', '0047_boroa_guards')
                for migration, backwards in plan):
            raise CommandError('BOR-OA snapshot requires the complete 0045 baseline')
        if options['bor_snapshot'] and any(backwards or migration.app_label != 'fresh_mta'
                or migration.name not in ('0043_bor_snapshot_sources', '0044_bor_prepared_membership',
                                          '0045_bor_prepared_guards') for migration, backwards in plan):
            raise CommandError('BOR snapshot requires the complete 0042 baseline')
        if options['research_critical_path'] and any(backwards or migration.app_label != 'fresh_mta'
                or migration.name not in ('0040_research_availability_bands', '0041_research_count_index',
                                          '0042_research_norm_history_index')
                for migration, backwards in plan):
            raise CommandError('Research critical path requires the complete 0039 baseline')
        if options['research_availability_index'] and any(backwards or migration.app_label != 'fresh_mta'
                or migration.name != '0039_research_availability_cover' for migration, backwards in plan):
            raise CommandError('Research availability index requires the complete history baseline')
        if options['history_report_preparation'] and any(backwards or migration.app_label != 'fresh_mta'
                or migration.name != '0038_history_prepared_memberships' for migration, backwards in plan):
            raise CommandError('History report preparation requires the complete RRR baseline')
        if options['rrr_preparation'] and any(backwards or migration.app_label != 'fresh_mta'
                or migration.name != '0037_rrr_prepared_membership' for migration, backwards in plan):
            raise CommandError('RRR preparation requires the complete Planning baseline')
        if options['planning_excess_index'] and any(backwards or migration.app_label != 'fresh_mta'
                or migration.name != '0036_planning_excess_date_index' for migration, backwards in plan):
            raise CommandError('Planning Excess index requires the Planning chart baseline')
        if options['planning_expedite_charts'] and any(backwards or migration.app_label != 'fresh_mta'
                or migration.name != '0035_planning_expedite_charts' for migration, backwards in plan):
            raise CommandError('Planning Expedite charts require the custom baseline')
        if options['planning_expedite_custom'] and any(backwards or migration.app_label != 'fresh_mta'
                or migration.name != '0034_planning_expedite_custom' for migration, backwards in plan):
            raise CommandError('Planning Expedite custom requires the transit baseline')
        if options['planning_expedite_transit'] and any(backwards or migration.app_label != 'fresh_mta'
                or migration.name != '0033_planning_expedite_transit' for migration, backwards in plan):
            raise CommandError('Planning Expedite transit requires the grid baseline')
        if options['planning_expedite_grids'] and any(backwards or migration.app_label != 'fresh_mta'
                or migration.name != '0032_planning_expedite_grid_occurrences' for migration, backwards in plan):
            raise CommandError('Planning Expedite grids require the GIT baseline')
        if options['planning_git'] and any(backwards or migration.app_label != 'fresh_mta'
                or migration.name != '0031_planning_git_occurrences' for migration, backwards in plan):
            raise CommandError('Planning GIT requires the custom baseline')
        if options['planning_custom'] and any(backwards or migration.app_label != 'fresh_mta'
                or migration.name != '0030_planning_custom_occurrences' for migration, backwards in plan):
            raise CommandError('Planning custom requires the chart baseline')
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
                *(['0046_boroa_snapshot_and_prepared', '0047_boroa_guards'] if options['boroa_snapshot'] else []),
                *(['0043_bor_snapshot_sources', '0044_bor_prepared_membership',
                   '0045_bor_prepared_guards'] if options['bor_snapshot'] else []),
                *(['0040_research_availability_bands', '0041_research_count_index',
                   '0042_research_norm_history_index'] if options['research_critical_path'] else []),
                *(['0039_research_availability_cover'] if options['research_availability_index'] else []),
                *(['0038_history_prepared_memberships'] if options['history_report_preparation'] else []),
                *(['0037_rrr_prepared_membership'] if options['rrr_preparation'] else []),
                *(['0036_planning_excess_date_index'] if options['planning_excess_index'] else []),
                *(['0027_planning_derived_sources'] if options['planning_sources'] else []),
                *(['0032_planning_expedite_grid_occurrences'] if options['planning_expedite_grids'] else []),
                *(['0033_planning_expedite_transit'] if options['planning_expedite_transit'] else []),
                *(['0034_planning_expedite_custom'] if options['planning_expedite_custom'] else []),
                *(['0035_planning_expedite_charts'] if options['planning_expedite_charts'] else []),
                *(['0031_planning_git_occurrences'] if options['planning_git'] else []),
                *(['0030_planning_custom_occurrences'] if options['planning_custom'] else []),
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
