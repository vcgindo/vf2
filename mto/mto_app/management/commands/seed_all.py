# app/management/commands/seed_all.py
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
class Command(BaseCommand):
    help = "Run all seeding commands in order"

    def handle(self, *args, **kwargs):
        try:
            with transaction.atomic():
                seeds = [
                    "seed_dbr_settings",
                    "seed_mdm_config",
                    "seed_report_config",
                    "seed_ui_report_config",
                ]

                for seed in seeds:
                    self.stdout.write(self.style.NOTICE(f"Running {seed}..."))
                    call_command(seed)
                    self.stdout.write(self.style.SUCCESS(f"{seed} completed!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Seeding failed. Rolled back all changes. Error: {str(e)}"))