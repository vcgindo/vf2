from http.client import REQUESTED_RANGE_NOT_SATISFIABLE
from rest_framework import serializers
from yaml import serialize_all
from .models import RunStatusDetails, ScriptExecutionStatus, FileRequirement, SchedulerInputFiles, ScriptStatus, RunStatus, ClientProgress
class RunStatusDetailsSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    current_step = serializers.SerializerMethodField()
    
    started_by_username = serializers.CharField(read_only=True)
    aborted_by_username = serializers.CharField(read_only=True)
    last_success_run_datetime = serializers.DateTimeField(read_only=True)

    class Meta:
        model = RunStatusDetails
        fields = [
            'run_id',
            'status',
            'started_at',
            'ended_at',
            'progress',
            'current_step',
            'started_by_username',
            'aborted_by_username',
            'last_success_run_datetime',
        ]
    
    def get_progress(self, obj):
        script_runs = ScriptExecutionStatus.objects.filter(run_id=obj.run_id)
        if not script_runs.exists():
            return "0%"
        total = sum(script_run.progress_percent for script_run in script_runs)
        percent = min(int(total), 100)
        return f"{percent}%"


    def get_current_step(self, obj):
        running_script = ScriptExecutionStatus.objects.filter(
            run_id=obj.run_id, 
            status=ScriptStatus.RUNNING
        ).order_by('script__order').first()
        if running_script:
            return running_script.script.name
        return "No script running"
class FileDetailSerializer(serializers.Serializer):
    file_name = serializers.CharField()
    last_updated = serializers.DateTimeField()
    uploaded_by = serializers.CharField()
    file_from = serializers.CharField()  # UI/FTP/DB, taken from FileRequirement
    expected_extension = serializers.CharField()

class SchedulerInputFilesSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchedulerInputFiles
        exclude = ['id']