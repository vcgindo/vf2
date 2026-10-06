# views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models.excel_upload import ExcelUpload
from ..docs.upload_progress import upload_progress_docs

class GetUploadProgressView(APIView):
    permission_classes = [IsAuthenticated]
    @upload_progress_docs()
    def get(self, request,processId):
        try:
            process_id = processId

            # DRF APIView dispatch is synchronous. Read the live progress row on
            # each poll; a cached model instance freezes the displayed progress.
            task = ExcelUpload.objects.only("process_id", "progress", "total_rows").get(process_id=process_id)

            progress = task.get_progress()
            total_rows = task.get_total_rows()

            return Response({'progress': progress, 'totalRows': total_rows})
        except ExcelUpload.DoesNotExist:
            return Response({'error': 'Process Not Found'}, status=404)
