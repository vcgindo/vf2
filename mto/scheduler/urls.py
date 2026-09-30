
from django.urls import path
from scheduler.views import *

urlpatterns = [
     ########################################### Scheduler's urls ######################################################
    path('getLatestRunStatus/', GetLatestRunStatusView.as_view(), name='latest-run-status'),
    path('getFileConfiguration/', GetFileConfigurationView.as_view(), name='file configuration details'),
    path('getSchedularFileOnDownload/', GetSchedulerFileOnDownloadView.as_view(), name='download schedular file on download click'),
    path('SaveSchedulerInputFileOnUpload/', SaveSchedulerInputFileOnUploadView.as_view(), name='upload schedular file on upload click'),
    path('getErrorLogFile/', GetErrorLogFileView.as_view(), name='download error file when run failed'),
    path('startSchedulerRun/', StartSchedulerRunView.as_view(), name='start scheduler run'),
    path('getSchedulerRunResultJson/', GetSchedulerRunResultJsonView.as_view(), name='get scheduler run result on successful scheduler run'),
    path('getSchedulerStatus/', GetSchedulerRunStatusView.as_view(), name='get scheduler run status')
]