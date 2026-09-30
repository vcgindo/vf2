import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from mto_app.models import ReportConfiguration

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Seeds the ReportConfiguration table with default data.'

    def handle(self, *args, **options):
        try:
            # Wrap the entire process in a single database transaction
            with transaction.atomic():
                self.stdout.write(
                    self.style.SUCCESS('Starting Report Configuration seeding...')
                )

                if self.check_seeding_status():
                    return

                data = [
                    {
                        "report_name": "OpenSOSummary",
                        "flag": "0",
                        "start": 0,
                        "end": 0,
                        "desc": "Black,Yellow,Red and Green",
                        "colors": "Black,Yellow,Red,Green",
                        "json_value": None
                    },
                    {
                        "report_name": "OpenSOSummary",
                        "flag": "1",
                        "start": 0,
                        "end": 7,
                        "desc": "Blue and White color order's duedate should be in this range",
                        "colors": "Blue , White",
                        "json_value": None
                    },
                    {
                        "report_name": "OpenSOSummary",
                        "flag": "3",
                        "start": 16,
                        "end": 23,
                        "desc": "Blue and White color order's duedate should be in this range",
                        "colors": "Blue , White",
                        "json_value": None
                    },
                    {
                        "report_name": "OpenSOSummary",
                        "flag": "4",
                        "start": 24,
                        "end": 30,
                        "desc": "Blue and White color order's duedate should be in this range",
                        "colors": "Blue , White",
                        "json_value": None
                    },
                    {
                        "report_name": "OpenSOSummary",
                        "flag": "2",
                        "start": 8,
                        "end": 15,
                        "desc": "Blue and White color order's duedate should be in this range",
                        "colors": "Blue , White",
                        "json_value": None
                    },
                    {
                        "report_name": "ExpiditingRmView",
                        "flag": "Yes",
                        "start": 10,
                        "end": 0,
                        "desc": "ExpiditingRmView",
                        "colors": "",
                        "json_value": None
                    },
                    {
                        "report_name": "IFfailedDifferenceRangeInPercent",
                        "flag": "Yes",
                        "start": 0,
                        "end": 0,
                        "desc": "IF failed range is stored in json format, for screen OT&IF Analysis Screen",
                        "colors": "",
                        "json_value": {
                            "range1": {"low": 0, "high": 20},
                            "range2": {"low": 21, "high": 40},
                            "range3": {"low": 41, "high": 60},
                            "range4": {"low": 61, "high": 80},
                            "range5": {"low": 81, "high": 100}
                        }
                    },
                    {
                        "report_name": "OTFailedDifferenceRange",
                        "flag": "Yes",
                        "start": 0,
                        "end": 0,
                        "desc": "OT failed range is stored in json format, for screen OT&IF Analysis Screen",
                        "colors": "",
                        "json_value": {
                            "range1": {"low": 1, "high": 2},
                            "range2": {"low": 3, "high": 7},
                            "range3": {"low": 8, "high": 15},
                            "range4": {"low": 16, "high": 30}
                        }
                    },
                    {
                        "report_name" : "FutureOrderLoadWeekEndDay",
                        "flag" : "MON",
                        "start" : 0,
                        "end" : 0,
                        "desc" : "Future Order Load flag for configurable week end day and the day should follow the nomenclature MON,TUE,WED,THU,FRI,SAT,SUN",
                        "colors" : "",
                        "json_value" : None
                    }
                ]

                self.seed_report_configuration(data)

                self.stdout.write(self.style.SUCCESS("Seeding process for ReportConfiguration completed successfully."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Seeding failed. Rolled back all changes. Error: {str(e)}"))

    def check_seeding_status(self):
        """
        Checks if the ReportConfiguration table has already been seeded.
        """
        count = ReportConfiguration.objects.count()

        if count > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'The "ReportConfiguration" table is not empty. Found {count} entries.'
                )
            )

            # Ask for confirmation to proceed
            if not self.confirm_proceed():
                self.stdout.write(self.style.NOTICE('Seeding cancelled by user.'))
                return True  

        return False 

    def confirm_proceed(self):
        """Asks the user for confirmation to proceed."""
        try:
            response = input('Do you want to apply updates and create new entries anyway? (y/N): ').lower().strip()
            return response in ['y', 'yes']
        except (EOFError, KeyboardInterrupt):
            # Handle cases where the script is run non-interactively or interrupted
            return False

    def seed_report_configuration(self, data):
        """
        Seeds the ReportConfiguration table. Creates new entries or updates
        existing ones if their values have changed.
        """
        logger.info("Seeding ReportConfiguration data...")

        created_count = 0
        skipped_count = 0

        # Fetch the composite keys of all existing configs.
        existing_config_keys = set(
            ReportConfiguration.objects.values_list('report_name', 'flag')
        )
        self.stdout.write(f"  Found {len(existing_config_keys)} existing report configuration keys.")

        # PREPARE NEW RECORDS IN-MEMORY
        configs_to_create = []

        for item in data:
            lookup_key = (item["report_name"], item["flag"])

            # If the key already exists in the database, we skip this item.
            if lookup_key in existing_config_keys:
                skipped_count += 1
                continue

            # Entry does not exist, so we prepare it for creation 
            configs_to_create.append(
                ReportConfiguration(
                    report_name=item['report_name'],
                    flag=item['flag'],
                    start=item.get('start', 0),
                    end=item.get('end', 0),
                    desc=item.get('desc', ''),
                    colors=item.get('colors', ''),
                    json_value=item.get('json_value')
                )
            )


        # PERFORM A SINGLE BULK CREATE OPERATION 
        if configs_to_create:
            # Create all the new records in one database query.
            created_objects = ReportConfiguration.objects.bulk_create(configs_to_create)
            created_count = len(created_objects)
            self.stdout.write(f"  Bulk created {created_count} new report configurations.")
        else:
            self.stdout.write("  No new report configurations to create.")

        # SHOW SUMMARY 
        self.stdout.write(
            self.style.SUCCESS(
                f'ReportConfiguration: {created_count} created, {skipped_count} skipped.'
            )
        )