# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models.excel_upload import ExcelUpload
from ..docs.upload_progress import upload_progress_docs
from django.core.cache import cache

class GetUploadProgressView(APIView):
    permission_classes = [IsAuthenticated]
    @upload_progress_docs()
    async def get(self, request,processId):
        try:
            process_id = processId

        # Check if the process data is cached
            task = cache.get(f"upload_progress_{process_id}")
            
            if not task:
                try:
                    task = ExcelUpload.objects.only("process_id", "progress", "total_rows").get(process_id=process_id)
                    cache.set(f"upload_progress_{process_id}", task, timeout=60)  # Cache for 60 seconds
                except ExcelUpload.DoesNotExist:
                    return Response({'error': 'Process Not Found'}, status=404)

            progress = task.get_progress()
            total_rows = task.get_total_rows()

            return Response({'progress': progress, 'totalRows': total_rows})
        except ExcelUpload.DoesNotExist:
            return Response({'error': 'Process Not Found'}, status=404)
