from django.db import models

# Create your models here.

# ###############################################################################################################################################
# Scheduler Models
# ###############################################################################################################################################


# ========================================================
# 1. Client
# Stores client-specific metadata
# ========================================================
class ClientDetails(models.Model):
    name = models.CharField(max_length=255, unique=True)  # Display name of the client
    code = models.CharField(max_length=50, unique=True)   # Internal reference code
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp of creation

    class Meta:
        db_table = 'Scheduler_ClientDetails'

    def __str__(self):
        return self.name


# ========================================================
# 2. FileRequirement
# Defines expected input files for each client
# ========================================================
class FileSource(models.TextChoices):
    UI = "UI", "Uploaded via UI"
    FTP = "FTP", "Fetched from FTP"
    DB = "DB", "Generated from Database"

class FileRequirement(models.Model):
    client = models.ForeignKey(ClientDetails, on_delete=models.DO_NOTHING, related_name='file_requirements')
    name = models.CharField(max_length=255)  # Logical name of the file
    expected_extension = models.CharField(max_length=10)  # e.g., .csv, .json
    source = models.CharField(max_length=10, choices=FileSource.choices)  # Where the file comes from
    is_mandatory = models.BooleanField(default=True)  # Whether the file is required to run the module

    class Meta:
        unique_together = ('client', 'name', 'source')
        db_table = 'Scheduler_FileRequirement'

    def __str__(self):
        return f"{self.name} ({self.source}) for {self.client.name}"


# ========================================================
# 4. Scheduler_Input_Files
# Tracks actual input files received or generated
# ========================================================
class SchedulerInputFiles(models.Model):
    file_name = models.CharField(max_length=50, unique=True)
    input_folder = models.CharField(max_length=100)
    file_type = models.CharField(max_length=1)
    day = models.IntegerField(null=True, blank=True)
    is_critical = models.BooleanField()
    variable_name = models.CharField(max_length=100)
    resolved_filename = models.CharField(max_length=100, null=True, blank=True)
    uploaded_at = models.DateTimeField()
    uploaded_by_userid = models.IntegerField()
    uploaded_by_username =  models.CharField(max_length=150)

    class Meta:
        db_table = 'Scheduler_InputFiles'

    def __str__(self):
        return f'{self.file_name}'


# ========================================================
# 5. RunStatusDetails
# Tracks each execution of the run per client
# ========================================================
class RunStatus(models.TextChoices):
    TRIGGER = "TRIGGER", "Trigger"
    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"
    ABORT = "ABORT", "Abort"

class RunStatusDetails(models.Model):
    client = models.ForeignKey(ClientDetails, on_delete=models.DO_NOTHING, related_name='code_module_runs')
    run_id = models.CharField(max_length=100, unique=True)  # Unique identifier for the run
    triggered_by_user_id = models.IntegerField()  # External user ID
    triggered_by_username = models.CharField(max_length=150)  # External username
    started_at = models.DateTimeField(auto_now_add=True)  # When the run started
    ended_at = models.DateTimeField(null=True, blank=True)  # When the run ended
    is_in_progress = models.BooleanField(default=True)  # Used to prevent concurrent runs
    status = models.CharField(max_length=20, choices=RunStatus.choices, default=RunStatus.PENDING)  # Run status
    notes = models.TextField(blank=True, null=True)  # Optional comments or logs

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['client', 'is_in_progress']),
            models.Index(fields=['run_id']),
        ]
        db_table = 'Scheduler_RunStatusDetails'

    def __str__(self):
        return f"Run {self.run_id} for {self.client.name} [{self.status}]"


# ========================================================
# 6. ClientScriptDetails
# Defines individual scripts that make up a code module
# ========================================================
class ClientScriptDetails(models.Model):
    client = models.ForeignKey(ClientDetails, on_delete=models.DO_NOTHING, related_name='scripts')
    name = models.CharField(max_length=255)  # Script name
    order = models.PositiveIntegerField()  # Execution order
    module_name = models.CharField(max_length=255)

    class Meta:
        unique_together = ('client', 'name')
        ordering = ['order']
        db_table = 'Scheduler_ClientScriptDetails'

    def __str__(self):
        return f"{self.name} for {self.client.name}"


# ==========================================================
# 7. ScriptExecutionStatus
# Tracks execution status of each script within a module run
# ==========================================================
class ScriptStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    SUCCESS = "SUCCESS", "Success"
    FAILED = "FAILED", "Failed"
    SKIPPED = "SKIPPED", "Skipped"
    NOTSTARTED = "NOTSTARTED", "NotStarted"

class ScriptExecutionStatus(models.Model):
    script = models.ForeignKey(ClientScriptDetails, on_delete=models.DO_NOTHING, related_name='runs')
    run_id = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=ScriptStatus.choices, default=ScriptStatus.PENDING)
    started_at = models.DateTimeField(auto_now_add=True)  # When script started
    completed_at = models.DateTimeField(null=True, blank=True)  # When script ended
    error_message = models.TextField(blank=True, null=True)  # If failed, store error
    progress_percent = models.FloatField(default=0.0)  # Contribution to overall progress

    class Meta:
        db_table = 'Scheduler_ScriptExecutionStatus'

    def __str__(self):
        return f"{self.script.name} [{self.status}]"


# ========================================================
# 8. ClientProgress
# Aggregates progress for a full run
# ========================================================
class ClientProgress(models.Model):
    run_id = models.CharField(max_length=200)
    total_scripts = models.PositiveIntegerField()  # Total scripts expected
    completed_scripts = models.PositiveIntegerField(default=0)  # Scripts completed
    failed_scripts = models.PositiveIntegerField(default=0)  # Scripts failed
    progress_percent = models.FloatField(default=0.0)  # Overall progress
    last_updated = models.DateTimeField(auto_now=True)  # Timestamp of last update
    run_status = models.CharField(max_length=20, choices=RunStatus.choices)
    user_name = models.CharField(max_length=150)

    class Meta:
        db_table = 'Scheduler_ClientProgress'

    def __str__(self):
        return f"Progress for {self.run_id} ({self.progress_percent:.2f}%)"
        

# ========================================================
# 9. SchedulerSettings
# Stores Scheduler Settings
# ========================================================

class SchedulerSettings(models.Model):
    parameter = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True, null=True)  # Can store any simple value as string
    json_value = models.JSONField(blank=True, null=True)  # Structured data

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'Scheduler_Settings'

    def __str__(self):
        return f"{self.parameter} - {self.value} - {self.json_value}"
