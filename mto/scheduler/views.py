from http import client
import json
from urllib import response
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ClientProgress, RunStatusDetails, SchedulerInputFiles, FileRequirement, SchedulerSettings, RunStatus
from .serializers import RunStatusDetailsSerializer, FileDetailSerializer, SchedulerInputFilesSerializer
import logging
from django.http import FileResponse
from django.utils.encoding import iri_to_uri
import mimetypes
from pathlib import Path
import os
from django.utils import timezone
from mto_app.common.commonfunctions import (api_response, generate_scheduler_run_id)
import requests
import secrets
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.db.models import Subquery, OuterRef, Case, When
import dotenv

# Need to store token securely (e.g., in DB or cache)
EXPECTED_TOKEN = secrets.token_urlsafe(32)

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent

dotenv_file = os.path.join(BASE_DIR, '.env')
dotenv.load_dotenv(dotenv_file)

FASTAPI_PORT = os.environ.get("FASTAPI_PORT")
FASTAPI_HOST = os.environ.get("FASTAPI_HOST")


class GetLatestRunStatusView(APIView):
    def get(self, request):
        try:
            client_progress_queryset = ClientProgress.objects.values('last_updated','run_id','run_status','user_name')
            started_by_sq = Subquery(
                client_progress_queryset.filter(
                    run_id=OuterRef('run_id')
                ).order_by('last_updated').values('user_name')[:1]
            )

            aborted_by_sq = Subquery(
                client_progress_queryset.filter(
                    run_id=OuterRef('run_id'),
                    run_status=RunStatus.ABORT
                ).order_by('-last_updated').values('user_name')[:1]
            )

            last_success_sq = Subquery(
                client_progress_queryset.filter(
                    last_updated__lt=OuterRef('started_at'),
                    run_status= RunStatus.SUCCESS
                ).order_by('-last_updated').values('last_updated')[:1]
            )

            latest_run = RunStatusDetails.objects.annotate(
                started_by_username = started_by_sq,
                aborted_by_username = Case(When(status=RunStatus.ABORT, then=aborted_by_sq)),
                last_success_run_datetime = Case(When(status__in=[RunStatus.ABORT,RunStatus.FAILED], then=last_success_sq))
            ).first()

            if not latest_run :
                return api_response(msg={"detail": "No run data available."}, status_code=status.HTTP_404_NOT_FOUND)

            serializer = RunStatusDetailsSerializer(latest_run)
            return api_response(data=serializer.data, msg="latest run status fetched successfully", status_code=status.HTTP_200_OK)
        except Exception as e:
            logger.info(f'An Exception has occurred in get latest run status due to {str(e)}')
            return api_response(msg=f'An Exception has occurred in get latest run status API due to {str(e)}', status_code=status.HTTP_400_BAD_REQUEST)

class GetFileConfigurationView(APIView):
    def get(self, request):
        try:
            client_id = request.query_params.get("client_id")

            if not client_id:
                return api_response(
                    msg={"detail": "client_id query param is required"},
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Build lookup: {name: (source, expected_extension)}
            requirements_qs = FileRequirement.objects.filter(client_id=client_id).values(
                "name", "source", "expected_extension"
            )
            requirement_map = {
                r["name"]: {
                    "file_from": r["source"],
                    "expected_extension": r["expected_extension"]
                }
                for r in requirements_qs
            }

            input_qs = SchedulerInputFiles.objects.values(
                "file_name", "uploaded_at", "uploaded_by_username"
            ).order_by("-uploaded_at")

            results = []
            unmatched = []

            for rec in input_qs:
                file_name = rec["file_name"]
                # file_name = file_name.split(".")[0]
                match = requirement_map.get(file_name)

                if match:
                    results.append({
                        "file_name": file_name,
                        "last_updated": rec["uploaded_at"],
                        "uploaded_by": rec["uploaded_by_username"],
                        "file_from": match["file_from"],
                        "expected_extension": match["expected_extension"]
                    })
                else:
                    unmatched.append({
                        "file_name": file_name,
                        "reason": "No matching file in FileRequirement for this client"
                    })

            # if unmatched:
            #     return api_response(
            #         msg={
            #             "detail": "Unmatched files found",
            #             "unmatched": unmatched
            #         },
            #         status_code=status.HTTP_400_BAD_REQUEST
            #     )

            if not results:
                return api_response(
                    msg={"detail": "No matching file data found for the provided client_id",
                    "unmatched_files_found": unmatched},
                    status_code=status.HTTP_404_NOT_FOUND
                )

            serializer = FileDetailSerializer(results, many=True)

            
            if unmatched:
                return api_response(
                    msg = {
                        "detail": "File configuration fetched with some unmatched records skipped",
                        "skipped": unmatched
                    },
                    status_code=status.HTTP_404_NOT_FOUND
                )
            else:
                msg = "File configuration fetched successfully"

            return api_response(data=serializer.data, msg=msg, status_code=status.HTTP_200_OK)

        except Exception as e:
            logger.info(f"Exception in File configuration API: {str(e)}")
            return api_response(
                msg=f"An error occurred in File configuration API: {str(e)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )

class GetSchedulerFileOnDownloadView(APIView):
    def get(self, request):
        file_name = request.query_params.get("file_name")
        if not file_name:
            return api_response(msg="Missing 'file_name' query parameter", status_code=status.HTTP_400_BAD_REQUEST)

        if any(part in file_name for part in ["..", "/", "\\"]):
            return api_response(msg="Invalid file_name", status_code=status.HTTP_400_BAD_REQUEST)

        try:
            record = SchedulerInputFiles.objects.filter(file_name=file_name).order_by("-uploaded_at").first()
            if not record:
                return api_response(msg=f"No record found for file_name '{file_name}'", status_code=status.HTTP_404_NOT_FOUND)

            input_folder = Path(record.input_folder).resolve()
            resolved_filename = record.resolved_filename or file_name
            file_path = (input_folder / resolved_filename).resolve()

            if not str(file_path).startswith(str(input_folder)):
                return api_response(msg="Resolved path is outside allowed folder", status_code=status.HTTP_400_BAD_REQUEST)

            if not file_path.exists() or not file_path.is_file():
                return api_response(
                    msg="File not found",
                    data={"expected_path": str(file_path)},
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Check if file is blank (zero bytes)
            is_blank = file_path.stat().st_size == 0

            content_type, _ = mimetypes.guess_type(file_path.name)
            content_type = content_type or "application/octet-stream"

            response = FileResponse(open(file_path, "rb"), content_type=content_type, as_attachment=True)
            response["Content-Disposition"] = f'attachment; filename="{iri_to_uri(file_path.name)}"'

            # Add custom header to indicate blank file
            if is_blank:
                response["X-File-Status"] = "Blank file"
            else:
                response["X-File-Status"] = "File contains data"

            return response

        except Exception as e:
            return api_response(msg=f" in Scheduler file download API Error: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SaveSchedulerInputFileOnUploadView(APIView):
    def post(self, request):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch target folder from SchedulerSettings
        try:
            setting = SchedulerSettings.objects.filter(parameter='InputFileFolder').first()
            if not setting or not setting.value:
                return Response({'error': 'InputFolder path not configured in SchedulerSettings'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            target_folder = Path(setting.value).resolve()
            os.makedirs(target_folder, exist_ok=True)
        except Exception as e:
            return Response({'error': f'Failed to resolve target folder: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save file to target folder
        try:
            file_path = target_folder / uploaded_file.name
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
        except Exception as e:
            return Response({'error': f'Failed to save file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Prepare data for DB entry
        data = {
            'file_name': os.path.splitext(uploaded_file.name)[0],
            'input_folder': str(target_folder),
            'file_type': request.data.get('file_type'),
            'day': request.data.get('day', None),
            'is_critical': request.data.get('is_critical'),
            'variable_name': uploaded_file.name.split('.')[0],
            'resolved_filename': uploaded_file.name,
            'uploaded_at': timezone.now(),
            'uploaded_by_userid': request.data.get('userid'),
            'uploaded_by_username': request.data.get('username'),
        }

        # Check for existing record by file_name
        try:
            existing_record = SchedulerInputFiles.objects.filter(file_name=os.path.splitext(uploaded_file.name)[0]).first()
            if existing_record:
                # Update existing record
                serializer = SchedulerInputFilesSerializer(existing_record, data=data, partial=True)
                action = "updated"
            else:
                # Create new record
                serializer = SchedulerInputFilesSerializer(data=data)
                action = "created"

            if serializer.is_valid():
                serializer.save()
                return api_response(msg=f"File {action} successfully", status_code=status.HTTP_200_OK if action == "updated" else status.HTTP_201_CREATED)
            return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({'error': f'Database operation failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetErrorLogFileView(APIView):
    def get(self, request):
        try:
            # Step 1: Fetch file name from SchedulerSettings
            settings_queryset = SchedulerSettings.objects.filter(parameter__in=["ClientErrorLogFileName", "ErrorLogFolder"])
            settings_map = {setting.parameter: setting for setting in settings_queryset}
            client_error_log_file_name = settings_map.get("ClientErrorLogFileName")
            # client_error_log_file_name = SchedulerSettings.objects.filter(parameter="ClientErrorLogFileName").first()
            if not client_error_log_file_name or not client_error_log_file_name.value:
                return api_response(msg="ClientErrorLogFileName not configured in Scheduler Settings", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

            file_name = client_error_log_file_name.value.strip()

            # Step 2: Validate file name to prevent path traversal
            if any(part in file_name for part in ["..", "/", "\\"]):
                return api_response(msg="Invalid file name from settings", status_code=status.HTTP_400_BAD_REQUEST)

            # Step 3: Fetch ErrorLogFolder path from SchedulerSettings
            # folder_setting = SchedulerSettings.objects.filter(parameter="ErrorLogFolder").first()
            folder_setting = settings_map.get("ErrorLogFolder")
            if not folder_setting or not folder_setting.value:
                return api_response(msg="ErrorLogFolder path not configured in Scheduler Settings", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

            folder_path = Path(folder_setting.value).resolve()
            file_path = (folder_path / file_name).resolve()

            # Step 4: Ensure resolved path is within allowed folder
            if not str(file_path).startswith(str(folder_path)):
                return api_response(msg="Resolved path is outside allowed folder", status_code=status.HTTP_400_BAD_REQUEST)

            # Step 5: Check if file exists and is a file
            if not file_path.exists() or not file_path.is_file():
                return api_response(
                    msg="File not found",
                    data={"expected_path": str(file_path)},
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Step 6: Check if file is blank
            is_blank = file_path.stat().st_size == 0

            # Step 7: Determine content type
            content_type, _ = mimetypes.guess_type(file_path.name)
            content_type = content_type or "application/octet-stream"

            # Step 8: Return file as downloadable response
            response = FileResponse(open(file_path, "rb"), content_type=content_type, as_attachment=True)
            response["Content-Disposition"] = f'attachment; filename="{iri_to_uri(file_path.name)}"'
            response["X-File-Status"] = "Blank file" if is_blank else "File contains data"

            return response

        except Exception as e:
            return api_response(msg=f"Error in ErrorLog file download API: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class GetSchedulerRunResultJsonView(APIView):
    def get(self, request):
        try:
            # Step 1: Get the file name from SchedulerSettings
            settings_queryset = SchedulerSettings.objects.filter(parameter__in=["ClientSchedulerRunFileName", "SchedulerRunResultFolder"])
            settings_map = {setting.parameter: setting for setting in settings_queryset}

            # client_run_file_name = SchedulerSettings.objects.filter(parameter="ClientSchedulerRunFileName").first()
            client_run_file_name = settings_map.get("ClientSchedulerRunFileName")
            if not client_run_file_name or not client_run_file_name.value:
                return api_response(msg="ClientSchedulerRunFileName not configured", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

            file_name = client_run_file_name.value.strip()

            # Step 2: Validate file name
            if any(part in file_name for part in ["..", "/", "\\"]) or not file_name.endswith(".json"):
                return api_response(msg="Invalid or unsupported file name from settings", status_code=status.HTTP_400_BAD_REQUEST)

            # Step 3: Get the folder path from SchedulerSettings
            # folder_setting = SchedulerSettings.objects.filter(parameter="SchedulerRunResultFolder").first()
            folder_setting = settings_map.get("SchedulerRunResultFolder")
            if not folder_setting or not folder_setting.value:
                return api_response(msg="SchedulerRunResultFolder path not configured", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

            folder_path = Path(folder_setting.value).resolve()
            file_path = (folder_path / file_name).resolve()

            # Step 4: Ensure the resolved file path is within the allowed folder
            if not str(file_path).startswith(str(folder_path)):
                return api_response(msg="Resolved path is outside allowed folder", status_code=status.HTTP_400_BAD_REQUEST)

            # Step 5: Check if file exists
            if not file_path.exists() or not file_path.is_file():
                return api_response(
                    msg="File not found",
                    data={"expected_path": str(file_path)},
                    status_code=status.HTTP_404_NOT_FOUND
                )

            # Step 6: Read and parse JSON file
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    json_data = json.load(f)
                except json.JSONDecodeError as decode_err:
                    return api_response(msg=f"Invalid JSON format: {str(decode_err)}", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

            return api_response(msg="Scheduler run result loaded successfully", data=json_data, status_code=status.HTTP_200_OK)

        except Exception as e:
            return api_response(msg=f"Error in Scheduler Run Result JSON API: {str(e)}", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StartSchedulerRunView(APIView):
    def post(self, request):
        callback_url = request.build_absolute_uri('/getSchedulerStatus/')
        user_id = request.data.get("user_id")
        user_name = request.data.get("user_name")
        run_id = generate_scheduler_run_id(user_id)

        response = requests.post(
            f'{FASTAPI_HOST}:{FASTAPI_PORT}/run-scheduler',
            json={
                "callback_url": callback_url,
                "user_id": user_id,
                "user_name": user_name,
                "run_id": run_id,
                "auth_token": EXPECTED_TOKEN
            }
        )
        return Response({
            "status": "started",
            "run_id": run_id,
            "message": "Scheduler triggered"
        }, status=response.status_code)

class GetSchedulerRunStatusView(APIView):
    def post(self, request):
        auth_header = request.headers.get("Authorization")
        if auth_header != f"Bearer {EXPECTED_TOKEN}":
            return Response({"error": "Unauthorized"}, status=401)

        run_id = request.data.get("run_id")
        channel_layer = get_channel_layer()
        data = dict(request.data)  # Convert to plain dict
        async_to_sync(channel_layer.group_send)(
            f"scheduler_{run_id}",
            {
                "type": "scheduler_status",
                "data": data
            }
        )
        return Response({"received": True})

class StopSchedulerRunView(APIView):
    def post(self, request):
        callback_url = request.build_absolute_uri('/getSchedulerStatus/')
        user_id = request.data.get("user_id")
        user_name = request.data.get("user_name")
        run_id = request.data.get("run_id")

        response = requests.post(
            f'{FASTAPI_HOST}:{FASTAPI_PORT}/stop-scheduler',
            json={
                "callback_url": callback_url,
                "user_id": user_id,
                "user_name": user_name,
                "run_id": run_id,
                "auth_token": EXPECTED_TOKEN
            }
        )
        return Response({
            "status": "Run termination initiated",
            "run_id": run_id,
            "message": "Terminating Scheduler Code Execution"
        }, status=response.status_code)